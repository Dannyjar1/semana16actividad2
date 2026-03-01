/* ========================================================
   main.js — Semana 16 Actividad 2
   Gobernanza, Inmutabilidad y Orquestación del Gemelo Digital de Loja
   ======================================================== */

'use strict';

// ── Intersection Observer: animación de secciones ─────────────────────────────
const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            e.target.classList.add('visible');
            sectionObserver.unobserve(e.target);
        }
    });
}, { threshold: 0.07, rootMargin: '0px 0px -60px 0px' });

document.querySelectorAll('.section').forEach(s => sectionObserver.observe(s));

// ── Sidebar activa & scroll spy ───────────────────────────────────────────────
const navLinks = document.querySelectorAll('.nav-link[data-section]');
const sections = document.querySelectorAll('section[id]');

const scrollSpy = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            navLinks.forEach(l => l.classList.remove('active'));
            const link = document.querySelector(`.nav-link[data-section="${e.target.id}"]`);
            if (link) link.classList.add('active');
        }
    });
}, { threshold: 0.35 });

sections.forEach(s => scrollSpy.observe(s));

// ── Mobile sidebar toggle ─────────────────────────────────────────────────────
const toggle = document.querySelector('.sidebar-toggle');
const sidebar = document.querySelector('.sidebar');

toggle?.addEventListener('click', () => {
    sidebar.classList.toggle('open');
});
document.addEventListener('click', (e) => {
    if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebar.classList.remove('open');
    }
});

// ── Smooth scroll ─────────────────────────────────────────────────────────────
navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const target = document.getElementById(link.dataset.section);
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            sidebar.classList.remove('open');
        }
    });
});

// ── Animación de contadores ───────────────────────────────────────────────────
function animateCounter(el) {
    const target = parseInt(el.dataset.count, 10);
    const suffix = el.dataset.suffix || '';
    const duration = 1400;
    const start = performance.now();

    function step(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 4);
        el.textContent = Math.round(eased * target).toLocaleString('es') + suffix;
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            animateCounter(e.target);
            counterObserver.unobserve(e.target);
        }
    });
}, { threshold: 0.5 });

document.querySelectorAll('[data-count]').forEach(el => counterObserver.observe(el));

// ── Animación de barras de progreso ──────────────────────────────────────────
const barObserver = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            const fills = e.target.querySelectorAll('.scenario-fill[data-width]');
            fills.forEach(f => {
                setTimeout(() => { f.style.width = f.dataset.width + '%'; }, 150);
            });
            barObserver.unobserve(e.target);
        }
    });
}, { threshold: 0.2 });

document.querySelectorAll('.scenario-bars').forEach(el => barObserver.observe(el));

// ── Diagrama SVG: Arquitectura Blockchain + SDN ───────────────────────────────
function buildArchDiagram() {
    const container = document.getElementById('arch-blockchain-diagram');
    if (!container) return;

    const nodes = [
        { id: 'sensor', x: 60, y: 100, label: '📡 Sensores\nIoT', color: '#3b82f6', w: 110, h: 52 },
        { id: 'gateway', x: 240, y: 100, label: '⚙️ Edge Gateway\n+ Hash SHA-256', color: '#10b981', w: 140, h: 52 },
        { id: 'sdn', x: 460, y: 30, label: '🔀 SDN Controller\nOpenFlow / P4', color: '#8b5cf6', w: 140, h: 52 },
        { id: 'cloud', x: 460, y: 170, label: '☁️ AWS IoT Core\nKafka + TimescaleDB', color: '#06b6d4', w: 145, h: 52 },
        { id: 'fabric', x: 680, y: 100, label: '⛓ Hyperledger\nFabric', color: '#f59e0b', w: 120, h: 52 },
        { id: 'twin', x: 880, y: 100, label: '🌐 Gemelo Digital\nUnity 3D + AR', color: '#ec4899', w: 130, h: 52 },
        { id: 'ai', x: 880, y: 220, label: '🤖 LSTM AI\nPredicción 6h', color: '#a78bfa', w: 120, h: 52 },
    ];

    const edges = [
        { from: 'sensor', to: 'gateway', label: 'MQTT-SN/BLE', color: '#3b82f6' },
        { from: 'gateway', to: 'sdn', label: 'OpenFlow', color: '#8b5cf6' },
        { from: 'gateway', to: 'cloud', label: 'MQTT 5G/TLS', color: '#10b981' },
        { from: 'gateway', to: 'fabric', label: 'gRPC / Hash', color: '#f59e0b' },
        { from: 'sdn', to: 'cloud', label: 'Prioridad', color: '#8b5cf6' },
        { from: 'cloud', to: 'twin', label: 'WebSocket', color: '#06b6d4' },
        { from: 'cloud', to: 'ai', label: 'Time-series', color: '#a78bfa' },
        { from: 'fabric', to: 'twin', label: 'Audit trail', color: '#f59e0b' },
    ];

    const W = 1060, H = 310;
    let svg = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" style="font-family:Inter,sans-serif;">
    <defs>
      ${nodes.map(n => `
        <radialGradient id="g-${n.id}" cx="50%" cy="30%">
          <stop offset="0%" stop-color="${n.color}" stop-opacity="0.25"/>
          <stop offset="100%" stop-color="${n.color}" stop-opacity="0.06"/>
        </radialGradient>
      `).join('')}
      <filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      ${edges.map((e, i) => `<marker id="arr${i}" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="${e.color}" opacity="0.7"/></marker>`).join('')}
    </defs>`;

    // get center of a node
    const cx = id => { const n = nodes.find(x => x.id === id); return n.x + n.w / 2; };
    const cy = id => { const n = nodes.find(x => x.id === id); return n.y + n.h / 2; };

    // Edges
    edges.forEach((e, i) => {
        const x1 = cx(e.from), y1 = cy(e.from), x2 = cx(e.to), y2 = cy(e.to);
        const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
        svg += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${e.color}" stroke-width="1.5" stroke-opacity="0.5" stroke-dasharray="5,4" marker-end="url(#arr${i})"/>
    <text x="${mx}" y="${my - 5}" text-anchor="middle" fill="${e.color}" font-size="9" opacity="0.75">${e.label}</text>`;
    });

    // Nodes
    nodes.forEach(n => {
        const lines = n.label.split('\n');
        svg += `
    <rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="10" fill="url(#g-${n.id})" stroke="${n.color}" stroke-width="1.2" stroke-opacity="0.6" filter="url(#glow)"/>
    ${lines.map((l, i) => `<text x="${n.x + n.w / 2}" y="${n.y + (n.h / (lines.length + 1)) * (i + 1) + 2}" text-anchor="middle" fill="${i === 0 ? n.color : '#94a3b8'}" font-size="${i === 0 ? 11 : 9}" font-weight="${i === 0 ? 600 : 400}">${l}</text>`).join('')}`;
    });

    svg += '</svg>';
    container.innerHTML = svg;
}

// ── Diagrama SVG: Flujo NETCONF ───────────────────────────────────────────────
function buildNetconfDiagram() {
    const container = document.getElementById('netconf-diagram');
    if (!container) return;

    const steps = [
        { label: 'Centro de\nControl', icon: '🖥', color: '#3b82f6' },
        { label: 'Sesión SSH/TLS\n(Port 830)', icon: '🔒', color: '#10b981' },
        { label: 'Lock\nCandidate', icon: '🔐', color: '#f59e0b' },
        { label: 'edit-config\n50 GWs', icon: '⚙️', color: '#8b5cf6' },
        { label: 'validate\n(YANG check)', icon: '✅', color: '#06b6d4' },
        { label: 'commit\nRunning', icon: '✔', color: '#10b981' },
        { label: '50 Gateways\nActualizados', icon: '📡', color: '#3b82f6' },
    ];

    const W = 900, H = 110, stepW = W / steps.length;

    let svg = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" style="font-family:Inter,sans-serif;">
    <defs>
      ${steps.map((s, i) => `<marker id="na${i}" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="${s.color}88"/></marker>`).join('')}
    </defs>`;

    steps.forEach((s, i) => {
        const cx = stepW * i + stepW / 2;
        const cy = 55;
        const r = 28;
        svg += `
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="${s.color}15" stroke="${s.color}" stroke-width="1.5" stroke-opacity="0.7"/>
    <text x="${cx}" y="${cy}" text-anchor="middle" dominant-baseline="middle" font-size="16">${s.icon}</text>`;

        const lbls = s.label.split('\n');
        lbls.forEach((l, j) => {
            svg += `<text x="${cx}" y="${cy + r + 14 + j * 12}" text-anchor="middle" fill="#94a3b8" font-size="9">${l}</text>`;
        });

        if (i < steps.length - 1) {
            const x1 = cx + r, x2 = cx + stepW - r;
            svg += `<line x1="${x1}" y1="${cy}" x2="${x2}" y2="${cy}" stroke="${s.color}" stroke-width="1.5" stroke-opacity="0.5" stroke-dasharray="4,3" marker-end="url(#na${i})"/>`;
        }
    });

    svg += '</svg>';
    container.innerHTML = svg;
}

// ── Simulación de hashing en tiempo real ─────────────────────────────────────
async function sha256(message) {
    const msgBuf = new TextEncoder().encode(message);
    const hashBuf = await crypto.subtle.digest('SHA-256', msgBuf);
    return Array.from(new Uint8Array(hashBuf)).map(b => b.toString(16).padStart(2, '0')).join('');
}

function animateHashDemo() {
    const hashOut = document.getElementById('hash-output');
    const hashInput = document.getElementById('hash-input');
    const hashBtn = document.getElementById('hash-btn');
    if (!hashOut || !hashInput) return;

    hashBtn?.addEventListener('click', async () => {
        const val = hashInput.value.trim();
        if (!val) return;
        hashOut.style.opacity = '0.4';
        const canonical = JSON.stringify({
            gateway_id: 'ZA-GW-001',
            sensor_id: 'ZA-S01-RIV',
            sensor_type: 'river-level',
            timestamp_utc: new Date().toISOString(),
            unit: 'm',
            value: parseFloat(val) || 0
        });
        const h = await sha256(canonical);
        hashOut.textContent = h;
        hashOut.style.opacity = '1';
        hashOut.style.animation = 'none';
        void hashOut.offsetWidth;
        hashOut.style.animation = 'hashReveal 0.5s ease';
    });

    // Auto-demo con valores predefinidos
    const demos = [1.82, 2.95, 3.62, 1.20];
    let di = 0;
    setInterval(async () => {
        if (document.hidden) return;
        if (hashInput.value !== '') return; // no interrumpir si el usuario está escribiendo
        const v = demos[di++ % demos.length];
        const canonical = JSON.stringify({
            gateway_id: 'ZA-GW-001', sensor_id: 'ZA-S01-RIV',
            sensor_type: 'river-level', timestamp_utc: new Date().toISOString(),
            unit: 'm', value: v
        });
        const h = await sha256(canonical);
        hashOut.textContent = h;
        hashOut.dataset.currentVal = v;
    }, 3000);
}

// ── Toast de notificación ─────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
    const colors = { info: '#3b82f6', success: '#10b981', warning: '#f59e0b', error: '#ef4444' };
    const toast = document.createElement('div');
    toast.style.cssText = `
    position:fixed; bottom:24px; right:24px; z-index:9999;
    padding:14px 22px; border-radius:12px; font-size:0.88rem;
    background:rgba(8,12,24,0.95); border:1px solid ${colors[type]}55;
    color:${colors[type]}; backdrop-filter:blur(12px);
    box-shadow:0 8px 32px rgba(0,0,0,0.4);
    transform:translateY(20px); opacity:0;
    transition:all 0.3s cubic-bezier(0.22,1,0.36,1);
    max-width:320px; line-height:1.5;
  `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    requestAnimationFrame(() => { toast.style.transform = 'translateY(0)'; toast.style.opacity = '1'; });
    setTimeout(() => {
        toast.style.opacity = '0'; toast.style.transform = 'translateY(12px)';
        setTimeout(() => toast.remove(), 400);
    }, 3800);
}

// ── Simulación de blockchain commit ──────────────────────────────────────────
function setupBlockchainDemo() {
    const btn = document.getElementById('bc-demo-btn');
    const log = document.getElementById('bc-log');
    if (!btn || !log) return;

    let blockNum = 1001;

    btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.textContent = '⏳ Procesando...';

        const riverValue = (Math.random() * 2 + 2).toFixed(3);
        const canonical = JSON.stringify({
            gateway_id: 'ZA-GW-001', sensor_id: 'ZA-S01-RIV',
            sensor_type: 'river-level', timestamp_utc: new Date().toISOString(),
            unit: 'm', value: parseFloat(riverValue)
        });

        await new Promise(r => setTimeout(r, 600));
        const hash = await sha256(canonical);
        const txId = await sha256(hash + Date.now());

        const entry = document.createElement('div');
        entry.style.cssText = 'padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-family:var(--jb-mono,"JetBrains Mono",monospace);font-size:0.78rem;color:#94a3b8;animation:fadeInUp 0.4s ease';

        const alert = parseFloat(riverValue) >= 3.5 ? '🚨 EMERGENCY' :
            parseFloat(riverValue) >= 3.0 ? '🟠 CRITICAL' :
                parseFloat(riverValue) >= 2.5 ? '🟡 WARNING' : '✅ NORMAL';

        entry.innerHTML = `
      <span style="color:#10b981">Block #${blockNum++}</span>
      <span style="margin:0 8px;opacity:0.4">│</span>
      <span style="color:#3b82f6">Sensor: ZA-S01-RIV</span>
      <span style="margin:0 8px;opacity:0.4">│</span>
      <span style="color:#f59e0b">Nivel: ${riverValue}m</span>
      <span style="margin:0 8px;opacity:0.4">│</span>
      ${alert}
      <br>
      <span style="color:#64748b;font-size:0.72rem">
        SHA-256: ${hash.substring(0, 32)}...
        │ TxID: ${txId.substring(0, 16)}...
        │ ${new Date().toLocaleTimeString('es')}
      </span>`;

        log.prepend(entry);

        if (parseFloat(riverValue) >= 2.5) {
            showToast(`⚠ Alerta registrada en blockchain: Río Zamora ${riverValue}m`, 'warning');
        } else {
            showToast(`✓ Hash registrado en Hyperledger Fabric — Block #${blockNum - 1}`, 'success');
        }

        await new Promise(r => setTimeout(r, 400));
        btn.disabled = false;
        btn.textContent = '⛓ Simular nuevo bloque';
    });
}

// ── Simulación SDN: priorización de tráfico ───────────────────────────────────
function setupSDNDemo() {
    const btn = document.getElementById('sdn-btn');
    const bars = document.querySelectorAll('.sdn-bar');
    if (!btn) return;

    let stormMode = false;

    btn.addEventListener('click', () => {
        stormMode = !stormMode;
        btn.textContent = stormMode ? '☀️ Modo Normal' : '🌧 Simular Tormenta';
        btn.style.borderColor = stormMode ? '#ef4444' : '#8b5cf6';
        btn.style.color = stormMode ? '#ef4444' : '#8b5cf6';

        bars.forEach(bar => {
            const type = bar.dataset.type;
            const fill = bar.querySelector('.sdn-fill');
            const label = bar.querySelector('.sdn-pct');

            let pct;
            if (stormMode) {
                pct = type === 'flood' ? 85 : type === 'rain' ? 10 : type === 'air' ? 3 : 2;
            } else {
                pct = type === 'flood' ? 25 : type === 'rain' ? 20 : type === 'air' ? 30 : 25;
            }

            fill.style.width = pct + '%';
            label.textContent = pct + '%';

            if (stormMode && type === 'flood') {
                fill.style.background = 'linear-gradient(90deg,#ef4444,#f59e0b)';
                bar.querySelector('.sdn-label').style.color = '#ef4444';
            } else {
                fill.style.background = '';
                bar.querySelector('.sdn-label').style.color = '';
            }
        });

        if (stormMode) showToast('🌧 SDN activó QoS Clase 1: Sensores de inundación al 85% del ancho de banda', 'warning');
        else showToast('☀️ SDN revirtió QoS a distribución equitativa', 'info');
    });
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    buildArchDiagram();
    buildNetconfDiagram();
    animateHashDemo();
    setupBlockchainDemo();
    setupSDNDemo();

    // Año dinámico en footer
    const yearEl = document.getElementById('current-year');
    if (yearEl) yearEl.textContent = new Date().getFullYear();
});
