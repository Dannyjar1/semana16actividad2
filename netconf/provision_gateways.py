#!/usr/bin/env python3
"""
=============================================================================
Simulación de Aprovisionamiento NETCONF — Gemelo Digital de Loja
Módulo 1: Gobernanza y Administración de Infraestructura

Propósito:
  Demostrar cómo un operador desde el centro de control puede modificar
  el umbral de alerta de hasta 50 gateways simultáneamente sin
  intervención física, usando el protocolo NETCONF con el modelo YANG
  definido en loja-sensors.yang.

Requisitos:
  pip install ncclient lxml

UIDE — Tecnologías Emergentes — 8.° Ciclo — 2026
=============================================================================
"""

import time
import json
import hashlib
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional
from xml.etree import ElementTree as ET

# ── Configuración de logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger("netconf_provisioner")

# ── Constantes del sistema ────────────────────────────────────────────────────
NETCONF_PORT = 830
NETCONF_USERNAME = "admin"
NAMESPACE = "urn:uide:loja:digital-twin"
MAX_WORKERS = 10          # Hilos paralelos para aprovisionamiento concurrente
CONNECT_TIMEOUT = 15      # segundos
OPERATION_TIMEOUT = 30    # segundos


# =============================================================================
# Estructuras de datos
# =============================================================================

@dataclass
class GatewayConfig:
    """Representa un Edge Gateway del gemelo digital de Loja."""
    gateway_id: str       # Ej: ZA-GW-001
    ip_address: str
    location_name: str
    zone: str             # ZA=Zamora, ML=Malacatos, JP=Jipiro, CH=Centro Histórico
    sensor_types: list = field(default_factory=list)


@dataclass
class ThresholdUpdate:
    """Parámetros de actualización de umbrales."""
    sensor_type: str      # river-level | air-quality | traffic | precipitation
    warning_threshold: float
    critical_threshold: float
    emergency_threshold: float
    hysteresis: float = 0.10


@dataclass
class ProvisionResult:
    """Resultado de la operación NETCONF en un gateway."""
    gateway_id: str
    success: bool
    sensors_updated: int = 0
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    commit_hash: Optional[str] = None


# =============================================================================
# Inventario de gateways (50 unidades simuladas)
# =============================================================================

def build_gateway_inventory() -> list[GatewayConfig]:
    """
    Genera el inventario de 50 gateways distribuidos por Loja.
    En producción, esta lista vendría de un sistema de gestión de inventario
    (CMDB o IPAM).
    """
    inventory = []
    zones = {
        "ZA": ("Zamora", "10.10.1.{}"),
        "ML": ("Malacatos", "10.10.2.{}"),
        "JP": ("Jipiro", "10.10.3.{}"),
        "CH": ("Centro Histórico", "10.10.4.{}"),
        "UR": ("Urb. Zamora Huayco", "10.10.5.{}")
    }
    
    gw_counter = {z: 1 for z in zones}
    
    for i in range(1, 51):
        zone_key = list(zones.keys())[i % len(zones)]
        zone_name, ip_template = zones[zone_key]
        gw_num = gw_counter[zone_key]
        gw_counter[zone_key] += 1
        
        gateway_id = f"{zone_key}-GW-{gw_num:03d}"
        ip = ip_template.format(gw_num)
        
        # Asignar tipos de sensores según la zona
        if zone_key in ("ZA", "ML"):
            sensors = ["river-level", "flow-velocity", "precipitation"]
        elif zone_key == "JP":
            sensors = ["river-level", "precipitation", "air-quality"]
        elif zone_key == "CH":
            sensors = ["air-quality", "traffic", "weather"]
        else:
            sensors = ["air-quality", "weather"]
        
        inventory.append(GatewayConfig(
            gateway_id=gateway_id,
            ip_address=ip,
            location_name=f"Estación {zone_name} #{gw_num}",
            zone=zone_key,
            sensor_types=sensors
        ))
    
    return inventory


# =============================================================================
# Constructor de payloads XML para NETCONF
# =============================================================================

def build_edit_config_rpc(gateway_id: str, update: ThresholdUpdate) -> str:
    """
    Construye el mensaje NETCONF <edit-config> en formato XML para modificar
    los umbrales de alerta de todos los sensores del tipo indicado en el gateway.

    La operación uses 'merge' para no borrar configuraciones existentes.
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
     message-id="1">
  <edit-config>
    <target>
      <running/>
    </target>
    <default-operation>merge</default-operation>
    <config>
      <digital-twin-infrastructure xmlns="{NAMESPACE}">
        <gateway>
          <gateway-id>{gateway_id}</gateway-id>
          <sensor nc:operation="merge"
                  xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
            <!-- Aplicar a todos los sensores de tipo: {update.sensor_type} -->
            <type>{update.sensor_type}</type>
            <warning-threshold>{update.warning_threshold:.2f}</warning-threshold>
            <critical-threshold>{update.critical_threshold:.2f}</critical-threshold>
            <emergency-threshold>{update.emergency_threshold:.2f}</emergency-threshold>
            <hysteresis>{update.hysteresis:.2f}</hysteresis>
          </sensor>
        </gateway>
      </digital-twin-infrastructure>
    </config>
  </edit-config>
</rpc>"""


def build_validate_rpc() -> str:
    """RPC de validación antes del commit."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="2">
  <validate>
    <source><candidate/></source>
  </validate>
</rpc>"""


def build_commit_rpc() -> str:
    """RPC de commit para confirmar la configuración."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="3">
  <commit/>
</rpc>"""


def build_bulk_rpc(sensor_type: str, warning: float,
                   critical: float, emergency: float) -> str:
    """
    Usa el RPC personalizado 'bulk-update-thresholds' definido en el
    modelo YANG para actualizar TODOS los gateways de una vez con
    un solo mensaje NETCONF.
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
     message-id="10">
  <bulk-update-thresholds xmlns="{NAMESPACE}">
    <sensor-type-filter>{sensor_type}</sensor-type-filter>
    <new-warning-threshold>{warning:.2f}</new-warning-threshold>
    <new-critical-threshold>{critical:.2f}</new-critical-threshold>
    <new-emergency-threshold>{emergency:.2f}</new-emergency-threshold>
  </bulk-update-thresholds>
</rpc>"""


# =============================================================================
# Cliente NETCONF simulado
# (En producción, se utilizaría ncclient.manager.connect())
# =============================================================================

class SimulatedNetconfClient:
    """
    Simulación del cliente ncclient para demostración sin infraestructura real.
    
    En producción se usaría:
        from ncclient import manager
        conn = manager.connect(
            host=ip,
            port=NETCONF_PORT,
            username=NETCONF_USERNAME,
            key_filename="/certs/admin_rsa",
            hostkey_verify=True,
            device_params={'name': 'default'}
        )
    """

    def __init__(self, gateway: GatewayConfig):
        self.gateway = gateway
        self.connected = False
        self._session_id = hashlib.md5(
            gateway.gateway_id.encode()
        ).hexdigest()[:8].upper()

    def connect(self) -> bool:
        # Simular latencia de red (5G ~4ms, con overhead TLS ~25ms)
        time.sleep(0.025)
        self.connected = True
        log.debug(f"  [{self.gateway.gateway_id}] Sesión NETCONF establecida "
                  f"(ID: {self._session_id})")
        return True

    def send_rpc(self, rpc_xml: str) -> dict:
        """Simula el envío de un RPC y retorna la respuesta del servidor."""
        time.sleep(0.010)  # Simular RTT de operación
        return {
            "status": "ok",
            "message-id": "1",
            "session-id": self._session_id
        }

    def close(self):
        self.connected = False


# =============================================================================
# Función principal de aprovisionamiento por gateway
# =============================================================================

def provision_single_gateway(
    gateway: GatewayConfig,
    update: ThresholdUpdate
) -> ProvisionResult:
    """
    Ejecuta el flujo completo de NETCONF para un gateway:
    1. Establecer sesión TLS mutual auth
    2. Lock del datastore <candidate>
    3. <edit-config> con los nuevos umbrales
    4. <validate> para verificar consistencia del modelo YANG
    5. <commit> para activar la configuración
    6. Unlock del datastore
    7. Cerrar sesión
    """
    start_time = time.monotonic()
    client = SimulatedNetconfClient(gateway)

    try:
        # Paso 1: Conectar
        client.connect()

        # Paso 2: Lock del candidate datastore
        lock_rpc = """<rpc message-id="0"><lock><target><candidate/></target></lock></rpc>"""
        client.send_rpc(lock_rpc)

        # Paso 3: Editar configuración
        edit_rpc = build_edit_config_rpc(gateway.gateway_id, update)
        response = client.send_rpc(edit_rpc)

        # Paso 4: Validar
        validate_rpc = build_validate_rpc()
        client.send_rpc(validate_rpc)

        # Paso 5: Commit
        commit_rpc = build_commit_rpc()
        client.send_rpc(commit_rpc)

        # Paso 6: Unlock
        unlock_rpc = """<rpc message-id="4"><unlock><target><candidate/></target></unlock></rpc>"""
        client.send_rpc(unlock_rpc)

        duration_ms = (time.monotonic() - start_time) * 1000

        # Calcular cuántos sensores del tipo indicado tiene este gateway
        matching_sensors = sum(
            1 for s in gateway.sensor_types
            if s == update.sensor_type
        )

        # Hash del commit para auditoría
        commit_hash = hashlib.sha256(
            f"{gateway.gateway_id}{datetime.utcnow().isoformat()}{update.critical_threshold}".encode()
        ).hexdigest()[:16]

        return ProvisionResult(
            gateway_id=gateway.gateway_id,
            success=True,
            sensors_updated=matching_sensors,
            duration_ms=duration_ms,
            commit_hash=commit_hash
        )

    except Exception as exc:
        duration_ms = (time.monotonic() - start_time) * 1000
        log.error(f"  [{gateway.gateway_id}] ERROR: {exc}")
        return ProvisionResult(
            gateway_id=gateway.gateway_id,
            success=False,
            duration_ms=duration_ms,
            error_message=str(exc)
        )

    finally:
        client.close()


# =============================================================================
# Orquestador de aprovisionamiento masivo
# =============================================================================

def bulk_provision(
    gateways: list[GatewayConfig],
    update: ThresholdUpdate,
    max_workers: int = MAX_WORKERS
) -> dict:
    """
    Aprovisiona TODOS los gateways en paralelo usando un pool de hilos.
    
    La concurrencia es clave: con 50 gateways y latencia ~65ms por gateway,
    secuencialmente tomaría ~3.25 segundos. Con 10 hilos paralelos,
    se completa en ~400ms.
    """
    results = []
    failed = []
    
    print("\n" + "═" * 68)
    print("  NETCONF BULK PROVISIONER — Gemelo Digital Loja")
    print("═" * 68)
    print(f"  Operación: Actualización masiva de umbrales")
    print(f"  Tipo de sensor:  {update.sensor_type}")
    print(f"  Umbral WARNING:  {update.warning_threshold} m")
    print(f"  Umbral CRITICAL: {update.critical_threshold} m")
    print(f"  Umbral EMERGENCY:{update.emergency_threshold} m")
    print(f"  Gateways objetivo: {len(gateways)}")
    print(f"  Concurrent workers: {max_workers}")
    print("═" * 68 + "\n")

    global_start = time.monotonic()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(provision_single_gateway, gw, update): gw
            for gw in gateways
        }

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            
            status_icon = "✓" if result.success else "✗"
            log.info(
                f"  [{i:02d}/{len(gateways)}] {status_icon} {result.gateway_id}"
                f" — {result.duration_ms:.1f}ms"
                + (f" — {result.sensors_updated} sensor(es) actualizado(s)" if result.success else "")
                + (f" — hash:{result.commit_hash}" if result.commit_hash else "")
            )
            
            if not result.success:
                failed.append(result)

    global_duration = (time.monotonic() - global_start) * 1000
    total_sensors = sum(r.sensors_updated for r in results if r.success)

    # ── Reporte final ──────────────────────────────────────────────────────────
    print("\n" + "═" * 68)
    print("  REPORTE DE APROVISIONAMIENTO")
    print("═" * 68)
    print(f"  ✓ Gateways exitosos:     {len(results) - len(failed)} / {len(gateways)}")
    print(f"  ✗ Gateways fallidos:     {len(failed)}")
    print(f"  📡 Sensores actualizados: {total_sensors}")
    print(f"  ⏱ Tiempo total:          {global_duration:.0f} ms")
    print(f"  ⚡ Tiempo promedio/GW:   {global_duration / len(results):.1f} ms")
    seq_estimate = sum(r.duration_ms for r in results)
    speedup = seq_estimate / global_duration if global_duration > 0 else 1
    print(f"  🚀 Speedup vs. secuencial: {speedup:.1f}×")
    
    if failed:
        print(f"\n  ⚠ GATEWAYS FALLIDOS:")
        for r in failed:
            print(f"    - {r.gateway_id}: {r.error_message}")

    print("═" * 68 + "\n")

    return {
        "total_gateways": len(gateways),
        "successful": len(results) - len(failed),
        "failed": len(failed),
        "sensors_updated": total_sensors,
        "duration_ms": global_duration,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# =============================================================================
# Punto de entrada
# =============================================================================

if __name__ == "__main__":
    # ── Escenario 1: Tormenta detectada —————————————————————————————————————
    # El centro de control baja el umbral de emergencia del río Zamora a 3.5m
    # debido a pronóstico de lluvia intensa en los próximas 6 horas.
    
    print("\n🌧 ESCENARIO: TORMENTA DETECTADA — Ajuste preventivo de umbrales")
    print("   Pronóstico: 40mm de lluvia en 3 horas en la cuenca del Zamora\n")
    
    gateways = build_gateway_inventory()
    
    update = ThresholdUpdate(
        sensor_type="river-level",
        warning_threshold=2.50,    # antes: 3.00m
        critical_threshold=3.00,   # antes: 3.80m  
        emergency_threshold=3.50,  # antes: 4.50m
        hysteresis=0.15
    )
    
    summary = bulk_provision(gateways, update, max_workers=MAX_WORKERS)
    
    # Guardar log de auditoría
    audit_log = {
        "operation": "bulk-threshold-update",
        "operator": "control_center_loja",
        "reason": "Tormenta inminente — pronóstico INAMHI 6hrs",
        "result": summary,
        "yang_model_version": "2026-02-24",
        "netconf_version": "1.1"
    }
    
    print("📋 Registro de auditoría:")
    print(json.dumps(audit_log, indent=2, ensure_ascii=False))
