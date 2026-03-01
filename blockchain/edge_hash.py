#!/usr/bin/env python3
"""
=============================================================================
Edge Hash Generator — Integridad de Datos en el Borde
Módulo 2: Inmutabilidad de Datos con Blockchain
UIDE — Tecnologías Emergentes — 8.° Ciclo — 2026
=============================================================================
Propósito:
  Antes de enviar cada paquete de datos a la nube, el gateway genera un
  hash SHA-256 del contenido. Este hash se registra en la blockchain
  permisionada (Hyperledger Fabric). Cualquier alteración posterior del
  dato es detectable comparando el hash en blockchain con el recalculado.
Flujo:
  Sensor → MQTT-SN → [Gateway: CBOR + SHA-256 + HMAC] → MQTT 5.0 → AWS IoT
                                                     ↓
                                           Hyperledger Fabric (inmutable)
=============================================================================
"""

import hashlib, hmac, json, time, logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [EDGE-HASH] %(message)s',
                    datefmt='%H:%M:%S')
log = logging.getLogger("edge_hash")

# Clave del gateway (en producción: almacenada en TPM 2.0 del RPi4)
GATEWAY_SECRET = b"LOJA_ZA001_TPM_KEY_2026_PRIVATE"

ALERT_THRESHOLDS = {
    "river-level": {"warning": 2.50, "critical": 3.00, "emergency": 3.50},
    "air-quality":  {"warning": 75.0, "critical": 150.0, "emergency": 250.0},
    "traffic":      {"warning": 120.0, "critical": 180.0, "emergency": 220.0},
}


@dataclass
class SensorReading:
    sensor_id: str
    gateway_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp_utc: str
    firmware: str = "v2.3.1"


@dataclass
class SignedPacket:
    sensor_id: str
    gateway_id: str
    value: float
    unit: str
    timestamp_utc: str
    sha256_hash: str          # Hash del payload canónico
    hmac_sha256: str          # HMAC-SHA256 firmado por gateway (autenticidad)
    alert_level: Optional[str]
    seq: int
    proc_us: int              # Tiempo de procesamiento en microsegundos


def build_canonical(r: SensorReading) -> bytes:
    """
    Payload canónico: JSON con llaves SIEMPRE ordenadas, sin espacios.
    Garantiza que el mismo dato siempre produzca el mismo hash.
    """
    canonical = {
        "gateway_id": r.gateway_id,
        "sensor_id":  r.sensor_id,
        "sensor_type": r.sensor_type,
        "timestamp_utc": r.timestamp_utc,
        "unit": r.unit,
        "value": round(float(r.value), 6),
    }
    return json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode()


def check_alert(r: SensorReading) -> Optional[str]:
    th = ALERT_THRESHOLDS.get(r.sensor_type, {})
    if r.value >= th.get("emergency", float('inf')): return "EMERGENCY"
    if r.value >= th.get("critical",  float('inf')): return "CRITICAL"
    if r.value >= th.get("warning",   float('inf')): return "WARNING"
    return None


class EdgeHashEngine:
    """
    Motor de integridad que corre dentro del Edge Gateway (RPi4).

    Proceso técnico completo:
    1. Recibe lectura del sensor (deserializada de CBOR).
    2. Construye payload canónico (JSON, llaves ordenadas).
    3. SHA-256 del payload = prueba de contenido.
    4. HMAC-SHA256 con clave TPM = prueba de origen (este gateway).
    5. Detecta si el valor excede umbral NETCONF-configurado.
    6. Publica dato + hashes a AWS IoT Core (MQTT 5.0 / TLS 1.3).
    7. Publica SOLO el hash (no el dato) a Hyperledger Fabric.
    """

    def __init__(self, gw_id: str, secret: bytes = GATEWAY_SECRET):
        self.gw_id = gw_id
        self._secret = secret
        self._seq = 0
        self._n_packets = 0
        self._n_alerts = 0
        self._total_us = 0

    def process(self, r: SensorReading) -> SignedPacket:
        t0 = time.perf_counter_ns()
        self._seq += 1

        payload = build_canonical(r)
        sha = hashlib.sha256(payload).hexdigest()
        mac = hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
        alert = check_alert(r)
        elapsed = (time.perf_counter_ns() - t0) // 1000

        self._n_packets += 1
        self._total_us  += elapsed
        if alert: self._n_alerts += 1

        pkt = SignedPacket(
            sensor_id=r.sensor_id, gateway_id=r.gateway_id,
            value=r.value, unit=r.unit, timestamp_utc=r.timestamp_utc,
            sha256_hash=sha, hmac_sha256=mac,
            alert_level=alert, seq=self._seq, proc_us=elapsed
        )
        log.info(f"  [{r.sensor_id}] {r.value} {r.unit} | SHA256={sha[:16]}... | HMAC={mac[:12]}... | {elapsed}µs{' | ⚠ '+alert if alert else ''}")
        return pkt

    def publish_to_cloud(self, pkt: SignedPacket):
        """Simula MQTT 5.0 publish a AWS IoT Core."""
        topic = f"loja/dt/{pkt.gateway_id}/{pkt.sensor_id}/telemetry"
        log.info(f"  📡 MQTT → {topic} | seq={pkt.seq}")

    def publish_to_blockchain(self, pkt: SignedPacket) -> str:
        """
        Simula el envío al chaincode Hyperledger Fabric.
        Solo se envía hash + metadata, nunca el valor bruto.
        En producción: fabric-sdk-py → IngestSensorHash(record_json)
        """
        tx = hashlib.sha256(f"{pkt.sensor_id}{pkt.timestamp_utc}{pkt.seq}".encode()).hexdigest()
        log.info(f"  ⛓ FABRIC → TxID={tx[:16]}... | Block ~{1000+self._n_packets}")
        return tx

    def stats(self) -> dict:
        avg = self._total_us / max(self._n_packets, 1)
        return {"packets": self._n_packets, "alerts": self._n_alerts,
                "avg_proc_µs": round(avg, 1)}


class CloudVerifier:
    """
    Verifica integridad en la nube recalculando el hash y comparándolo
    con el almacenado en Hyperledger Fabric.
    """
    def verify(self, cloud_data: dict, blockchain_hash: str) -> tuple[bool, str]:
        canonical = json.dumps(
            {k: (round(float(v), 6) if k == "value" else v)
             for k, v in sorted(cloud_data.items())},
            sort_keys=True, separators=(',', ':')
        ).encode()
        recalc = hashlib.sha256(canonical).hexdigest()
        ok = (recalc == blockchain_hash)
        return ok, ("✓ ÍNTEGRO" if ok else
                    f"✗ MANIPULACIÓN DETECTADA: {recalc[:16]} ≠ {blockchain_hash[:16]}")


if __name__ == "__main__":
    print("\n" + "═"*60)
    print("  EDGE HASH ENGINE — Demo de integridad de datos")
    print("═"*60)

    engine   = EdgeHashEngine(gw_id="ZA-GW-001")
    verifier = CloudVerifier()
    records  = []

    lecturas = [
        SensorReading("ZA-S01-RIV","ZA-GW-001","river-level",1.82,"m","2026-02-24T23:00:00Z"),
        SensorReading("ZA-S01-RIV","ZA-GW-001","river-level",2.95,"m","2026-02-24T23:05:00Z"),
        SensorReading("ZA-S01-RIV","ZA-GW-001","river-level",3.62,"m","2026-02-24T23:10:00Z"),
    ]

    for r in lecturas:
        pkt = engine.process(r)
        engine.publish_to_cloud(pkt)
        tx  = engine.publish_to_blockchain(pkt)
        records.append((r, pkt, tx))

    print("\n  --- Verificación de integridad (lado cloud) ---")
    for r, pkt, _ in records:
        data = {"gateway_id":r.gateway_id,"sensor_id":r.sensor_id,
                "sensor_type":r.sensor_type,"timestamp_utc":r.timestamp_utc,
                "unit":r.unit,"value":r.value}
        ok, msg = verifier.verify(data, pkt.sha256_hash)
        print(f"  {r.timestamp_utc}: {msg}")

    # Simular manipulación
    r, pkt, _ = records[-1]
    tampered = {"gateway_id":r.gateway_id,"sensor_id":r.sensor_id,
                "sensor_type":r.sensor_type,"timestamp_utc":r.timestamp_utc,
                "unit":r.unit,"value":1.20}   # alguien cambió 3.62 → 1.20
    ok, msg = verifier.verify(tampered, pkt.sha256_hash)
    print(f"\n  Dato alterado (3.62→1.20): {msg}")

    print("\n  --- Estadísticas del gateway ---")
    for k,v in engine.stats().items(): print(f"  {k}: {v}")
    print("═"*60+"\n")
