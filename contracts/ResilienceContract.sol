// SPDX-License-Identifier: MIT
// ============================================================
// Smart Contract de Resiliencia Urbana — Gemelo Digital de Loja
// Blockchain Permisionada (Hyperledger Besu / Quorum)
// UIDE — Tecnologías Emergentes — 8.° Ciclo
// ============================================================
//
// PROPÓSITO:
// Garantizar la inmutabilidad de los datos de sensores críticos
// del gemelo digital. Ejecuta acciones automáticas cuando los
// valores exceden las normas legales ambientales del Ecuador
// (TULSMA, Norma INEN, Ordenanza Municipal de Loja).
//
// NOTA: Este es pseudocódigo con sintaxis Solidity para
// demostración académica. En producción se desplegaría en
// Hyperledger Besu (EVM compatible) dentro de la red
// permisionada municipal.
// ============================================================

pragma solidity ^0.8.19;

contract LojaResilienceContract {

    // ════════════════════════════════════════════════════
    // ESTRUCTURAS DE DATOS
    // ════════════════════════════════════════════════════

    struct SensorReading {
        string sensorId;        // Ej: "ZA-S01-RIV" (Zamora, sensor 01, río)
        string sensorType;      // "river_level", "air_quality", "traffic"
        int256 value;           // Valor × 10000 (para simular decimales)
        uint256 timestamp;      // Unix timestamp de la lectura
        bytes32 dataHash;       // SHA-256 del paquete original (generado en Edge)
        string gatewayId;       // Gateway que envió el dato
        bool verified;          // True si el hash coincide con el dato
    }

    struct AlertRecord {
        uint256 readingIndex;   // Índice del reading que disparó la alerta
        string sensorId;
        string alertType;       // "WARNING", "CRITICAL", "EMERGENCY"
        int256 value;           // Valor que excedió el umbral
        int256 threshold;       // Umbral legal excedido
        uint256 timestamp;
        bool notificationSent;  // Se envió notificación a emergencias
        bool sanctionApplied;   // Se aplicó sanción automática
    }

    struct Threshold {
        int256 warningLevel;     // Nivel de advertencia
        int256 criticalLevel;    // Nivel crítico (requiere acción)
        int256 emergencyLevel;   // Nivel de emergencia (peligro para vidas)
        string legalReference;   // Referencia legal (ej: "TULSMA Libro VI Anexo 4")
    }

    // ════════════════════════════════════════════════════
    // ESTADO DEL CONTRATO
    // ════════════════════════════════════════════════════

    address public owner;                    // Municipio de Loja (administrador)
    address public emergencyService;         // Dirección del servicio de emergencias
    address public environmentalAuthority;   // MAE delegación Loja

    // Almacenamiento inmutable de lecturas
    SensorReading[] public readings;
    AlertRecord[] public alerts;

    // Umbrales por tipo de sensor (configurables por el municipio)
    mapping(string => Threshold) public thresholds;

    // Contadores
    uint256 public totalReadings;
    uint256 public totalAlerts;
    uint256 public totalSanctions;

    // Registro de infracciones por gateway (para auditoría)
    mapping(string => uint256) public gatewayViolationCount;

    // ════════════════════════════════════════════════════
    // EVENTOS (Logs inmutables en la blockchain)
    // ════════════════════════════════════════════════════

    event DataRegistered(
        uint256 indexed readingIndex,
        string sensorId,
        int256 value,
        bytes32 dataHash,
        uint256 timestamp
    );

    event AlertTriggered(
        uint256 indexed alertIndex,
        string sensorId,
        string alertType,
        int256 value,
        int256 threshold
    );

    event EmergencyNotification(
        string sensorId,
        string message,
        uint256 timestamp
    );

    event SanctionApplied(
        string gatewayId,
        string reason,
        uint256 violationCount,
        uint256 timestamp
    );

    event ThresholdUpdated(
        string sensorType,
        int256 newWarning,
        int256 newCritical,
        int256 newEmergency
    );

    // ════════════════════════════════════════════════════
    // MODIFICADORES DE ACCESO
    // ════════════════════════════════════════════════════

    modifier onlyOwner() {
        require(msg.sender == owner, "Solo el municipio puede ejecutar esta accion");
        _;
    }

    modifier onlyAuthorizedGateway() {
        // En producción: verificar que msg.sender es un gateway autorizado
        // via certificado X.509 registrado en el contrato
        _;
    }

    // ════════════════════════════════════════════════════
    // CONSTRUCTOR
    // ════════════════════════════════════════════════════

    constructor(address _emergencyService, address _environmentalAuthority) {
        owner = msg.sender; // Municipio de Loja
        emergencyService = _emergencyService;
        environmentalAuthority = _environmentalAuthority;

        // ── Umbrales iniciales basados en normativa ecuatoriana ──

        // Nivel del río Zamora (metros) — Referencia: COE Cantonal Loja
        // Normal: 0-2.5m | Warning: 2.5m | Critical: 3.5m | Emergency: 4.5m
        thresholds["river_level"] = Threshold({
            warningLevel:   25000,     // 2.5000 m
            criticalLevel:  35000,     // 3.5000 m
            emergencyLevel: 45000,     // 4.5000 m
            legalReference: "COE Cantonal Loja - Protocolo de Inundaciones 2024"
        });

        // Calidad de aire PM2.5 (µg/m³) — Referencia: TULSMA Libro VI Anexo 4
        // Normal: 0-15 | Warning: 15 | Critical: 35 | Emergency: 55
        thresholds["air_quality_pm25"] = Threshold({
            warningLevel:   150000,    // 15.0000 µg/m³
            criticalLevel:  350000,    // 35.0000 µg/m³
            emergencyLevel: 550000,    // 55.0000 µg/m³
            legalReference: "TULSMA Libro VI Anexo 4 - Norma Calidad Aire Ambiente"
        });

        // Velocidad de flujo del río (m/s)
        thresholds["flow_velocity"] = Threshold({
            warningLevel:   20000,     // 2.0000 m/s
            criticalLevel:  35000,     // 3.5000 m/s
            emergencyLevel: 50000,     // 5.0000 m/s
            legalReference: "INAMHI - Umbrales hidrológicos cuenca Zamora"
        });

        // Precipitación acumulada 1h (mm/h)
        thresholds["precipitation"] = Threshold({
            warningLevel:   200000,    // 20.0000 mm/h
            criticalLevel:  400000,    // 40.0000 mm/h
            emergencyLevel: 600000,    // 60.0000 mm/h
            legalReference: "INAMHI - Alertas meteorológicas"
        });
    }

    // ════════════════════════════════════════════════════
    // FUNCIÓN PRINCIPAL: Registrar dato de sensor
    // ════════════════════════════════════════════════════

    function registerSensorData(
        string memory _sensorId,
        string memory _sensorType,
        int256 _value,
        uint256 _timestamp,
        bytes32 _dataHash,
        string memory _gatewayId
    ) public onlyAuthorizedGateway returns (uint256 readingIndex) {

        // 1. Verificar integridad: comparar hash recibido con hash calculado
        bytes32 calculatedHash = keccak256(
            abi.encodePacked(_sensorId, _sensorType, _value, _timestamp)
        );
        bool hashValid = (calculatedHash == _dataHash);

        // 2. Almacenar lectura de forma inmutable
        readings.push(SensorReading({
            sensorId: _sensorId,
            sensorType: _sensorType,
            value: _value,
            timestamp: _timestamp,
            dataHash: _dataHash,
            gatewayId: _gatewayId,
            verified: hashValid
        }));

        readingIndex = readings.length - 1;
        totalReadings++;

        emit DataRegistered(readingIndex, _sensorId, _value, _dataHash, _timestamp);

        // 3. Verificar umbrales y ejecutar acciones automáticas
        _checkThresholds(readingIndex, _sensorId, _sensorType, _value, _gatewayId);

        return readingIndex;
    }

    // ════════════════════════════════════════════════════
    // VERIFICACIÓN DE UMBRALES (Lógica automática)
    // ════════════════════════════════════════════════════

    function _checkThresholds(
        uint256 _readingIndex,
        string memory _sensorId,
        string memory _sensorType,
        int256 _value,
        string memory _gatewayId
    ) internal {

        Threshold memory t = thresholds[_sensorType];

        // Si no hay umbrales configurados para este tipo, salir
        if (t.emergencyLevel == 0) return;

        string memory alertType;
        int256 exceededThreshold;
        bool shouldNotify = false;
        bool shouldSanction = false;

        // ── Evaluar severidad (de mayor a menor) ──

        if (_value >= t.emergencyLevel) {
            // ⚠️ EMERGENCIA: Peligro para vidas humanas
            alertType = "EMERGENCY";
            exceededThreshold = t.emergencyLevel;
            shouldNotify = true;
            shouldSanction = true;

        } else if (_value >= t.criticalLevel) {
            // 🔴 CRÍTICO: Acción inmediata requerida
            alertType = "CRITICAL";
            exceededThreshold = t.criticalLevel;
            shouldNotify = true;

        } else if (_value >= t.warningLevel) {
            // 🟡 ADVERTENCIA: Monitoreo intensificado
            alertType = "WARNING";
            exceededThreshold = t.warningLevel;

        } else {
            // ✅ Normal: no se requiere acción
            return;
        }

        // ── Registrar alerta inmutable ──
        alerts.push(AlertRecord({
            readingIndex: _readingIndex,
            sensorId: _sensorId,
            alertType: alertType,
            value: _value,
            threshold: exceededThreshold,
            timestamp: block.timestamp,
            notificationSent: shouldNotify,
            sanctionApplied: shouldSanction
        }));

        totalAlerts++;

        emit AlertTriggered(
            alerts.length - 1,
            _sensorId,
            alertType,
            _value,
            exceededThreshold
        );

        // ── Notificar a servicios de emergencia ──
        if (shouldNotify) {
            _notifyEmergencyServices(_sensorId, _sensorType, _value, alertType);
        }

        // ── Aplicar sanción automática si corresponde ──
        if (shouldSanction) {
            _applySanction(_gatewayId, _sensorId, _sensorType, _value);
        }
    }

    // ════════════════════════════════════════════════════
    // NOTIFICACIÓN AUTOMÁTICA A EMERGENCIAS
    // ════════════════════════════════════════════════════

    function _notifyEmergencyServices(
        string memory _sensorId,
        string memory _sensorType,
        int256 _value,
        string memory _alertType
    ) internal {

        // En producción: llamada a oracle que envía SMS/push al COE
        // Aquí registramos el evento inmutable en blockchain

        string memory message = string(abi.encodePacked(
            "ALERTA ", _alertType, " en sensor ", _sensorId,
            " tipo ", _sensorType,
            " - Activar protocolo de respuesta COE Loja"
        ));

        emit EmergencyNotification(_sensorId, message, block.timestamp);

        // Log: Esta transacción queda registrada permanentemente
        // El COE puede auditar todas las alertas emitidas
    }

    // ════════════════════════════════════════════════════
    // SANCIÓN AUTOMÁTICA
    // ════════════════════════════════════════════════════

    function _applySanction(
        string memory _gatewayId,
        string memory _sensorId,
        string memory _sensorType,
        int256 _value
    ) internal {

        gatewayViolationCount[_gatewayId]++;
        totalSanctions++;

        string memory reason = string(abi.encodePacked(
            "Valor fuera de norma legal en ", _sensorId,
            " tipo ", _sensorType,
            " - Referencia: ", thresholds[_sensorType].legalReference
        ));

        emit SanctionApplied(
            _gatewayId,
            reason,
            gatewayViolationCount[_gatewayId],
            block.timestamp
        );

        // En producción: si violations > 3 en 24h,
        // se genera una orden de inspección automática
        // al Departamento de Gestión Ambiental del Municipio
    }

    // ════════════════════════════════════════════════════
    // FUNCIONES ADMINISTRATIVAS (Solo municipio)
    // ════════════════════════════════════════════════════

    function updateThresholds(
        string memory _sensorType,
        int256 _newWarning,
        int256 _newCritical,
        int256 _newEmergency,
        string memory _legalReference
    ) public onlyOwner {

        require(_newWarning < _newCritical, "Warning debe ser menor que critical");
        require(_newCritical < _newEmergency, "Critical debe ser menor que emergency");

        thresholds[_sensorType] = Threshold({
            warningLevel: _newWarning,
            criticalLevel: _newCritical,
            emergencyLevel: _newEmergency,
            legalReference: _legalReference
        });

        emit ThresholdUpdated(_sensorType, _newWarning, _newCritical, _newEmergency);
    }

    // ════════════════════════════════════════════════════
    // CONSULTAS (Views — no consumen gas)
    // ════════════════════════════════════════════════════

    function getReading(uint256 _index) public view returns (SensorReading memory) {
        require(_index < readings.length, "Lectura no existe");
        return readings[_index];
    }

    function getAlert(uint256 _index) public view returns (AlertRecord memory) {
        require(_index < alerts.length, "Alerta no existe");
        return alerts[_index];
    }

    function verifyDataIntegrity(uint256 _readingIndex) public view returns (bool) {
        SensorReading memory r = readings[_readingIndex];
        bytes32 calculated = keccak256(
            abi.encodePacked(r.sensorId, r.sensorType, r.value, r.timestamp)
        );
        return calculated == r.dataHash;
    }

    function getSystemStats() public view returns (
        uint256 _totalReadings,
        uint256 _totalAlerts,
        uint256 _totalSanctions
    ) {
        return (totalReadings, totalAlerts, totalSanctions);
    }
}
