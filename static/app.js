/* ============================================================
   REDFORGE — Frontend Logic
   ============================================================ */

/* ============ NAV ============ */
const navItems = document.querySelectorAll('.nav-item');
const views = document.querySelectorAll('.view');

function showView(name) {
  views.forEach(v => v.classList.toggle('active', v.id === 'view-' + name));
  navItems.forEach(n => n.classList.toggle('active', n.dataset.view === name));
  window.scrollTo({ top: 0 });
  if (name === 'terminal') { loadDeployerAgents(); loadDeployerList(); }
  if (name === 'c2') loadDeployerAgents();
}
document.querySelectorAll('[data-view]').forEach(el =>
  el.addEventListener('click', () => showView(el.dataset.view)));

/* ============ CLOCK ============ */
const pad = n => String(n).padStart(2, '0');
const fmt = s => `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s % 3600 / 60))}:${pad(s % 60)}`;
const bootAt = Date.now();

function tickClock() {
  const d = new Date();
  const c = document.getElementById('clock');
  const u = document.getElementById('uptime');
  if (c) c.textContent = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  if (u) u.textContent = fmt(Math.floor((Date.now() - bootAt) / 1000));
}
tickClock(); setInterval(tickClock, 1000);

/* ============ PROGRESS ============ */
const SEGMENTS = 40;
const bar = document.getElementById('bar');
if (bar) for (let i = 0; i < SEGMENTS; i++) bar.appendChild(document.createElement('i'));
const segs = bar ? [...bar.children] : [];
const phases = ['Recon','Initial access','Execution','Persistence','Lateral move','Exfil check'];
const phaseList = document.getElementById('phases');
let progress = 12, running = true;

function render() {
  if (!bar || !phaseList) return;
  const p = Math.min(100, Math.floor(progress));
  const filled = Math.round(p / 100 * SEGMENTS);
  segs.forEach((s, i) => s.className = i < filled - 1 ? 'on' : (i === filled - 1 ? 'head' : ''));
  const pctEl = document.getElementById('pct'); if (pctEl) pctEl.textContent = p + '%';
  const cur = Math.min(phases.length - 1, Math.floor(p / (100 / phases.length)));
  phaseList.innerHTML = phases.map((ph, i) => {
    const cls = p >= 100 ? 'done' : (i < cur ? 'done' : (i === cur ? 'now' : ''));
    const st = p >= 100 ? 'done' : (i < cur ? 'done' : (i === cur ? 'active' : 'pending'));
    return `<li class="${cls}">${ph}<span>${st}</span></li>`;
  }).join('');
  const pn = document.getElementById('phase-name');
  if (pn) pn.textContent = p >= 100 ? 'Complete' : phases[cur];
}
render();

const feed = [
  ['info','scheduler: task queue healthy'],
  ['ok','tunnel: status check ok'],
  ['warn','blue-team: anomalous request rate flagged'],
  ['crit','finding: default admin page reachable (staged)']
];
const term = document.getElementById('term');
let evtCount = 0, feedIdx = 0;
function addLine(level, msg) {
  if (!term) return;
  const d = new Date();
  const ts = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  const tagTxt = { info: 'INFO', ok: ' OK ', warn: 'WARN', crit: 'CRIT' }[level];
  const row = document.createElement('div');
  row.className = 'ln';
  row.innerHTML = `<span class="ts">[${ts}]</span> <span class="lvl-${level}">${tagTxt}</span> ${msg}`;
  term.appendChild(row);
  while (term.children.length > 200) term.removeChild(term.firstChild);
  term.scrollTop = term.scrollHeight;
  evtCount++;
  const c = document.getElementById('evt-count'); if (c) c.textContent = evtCount + ' events';
}
for (let i = 0; i < 5; i++) { const f = feed[feedIdx++ % feed.length]; addLine(f[0], f[1]); }
setInterval(() => { if (!running || progress >= 100) return; progress = Math.min(100, progress + 0.4); render(); }, 1200);
setInterval(() => { if (!running || progress >= 100) return; addLine(feed[feedIdx % feed.length][0], feed[feedIdx++ % feed.length][1]); }, 2200);

const toggleBtn = document.getElementById('btn-toggle');
if (toggleBtn) toggleBtn.addEventListener('click', () => {
  running = !running;
  toggleBtn.textContent = running ? 'Pause simulation' : 'Resume simulation';
  render();
});
const resetBtn = document.getElementById('btn-reset');
if (resetBtn) resetBtn.addEventListener('click', () => {
  progress = 0; running = true;
  if (toggleBtn) toggleBtn.textContent = 'Pause simulation';
  render();
});

/* ============ MITRE ============ */
const MITRE_TACTICS = [
  { name: 'Reconnaissance', techniques: ['T1595 Active Scanning','T1592 Gather Host Info','T1590 Gather Network Info'] },
  { name: 'Resource Dev', techniques: ['T1587 Develop Capabilities','T1583 Acquire Infrastructure'] },
  { name: 'Initial Access', techniques: ['T1566 Phishing','T1190 Exploit Public App'] },
  { name: 'Execution', techniques: ['T1059 Command & Scripting','T1106 Native API'] },
  { name: 'Persistence', techniques: ['T1053 Scheduled Task','T1547 Boot/Logon Autostart'] },
  { name: 'Priv. Escalation', techniques: ['T1068 Exploit for Priv Esc','T1548 Abuse Elevation'] },
  { name: 'Defense Evasion', techniques: ['T1562 Impair Defenses','T1070 Indicator Removal'] },
  { name: 'Credential Access', techniques: ['T1003 OS Credential Dump','T1555 Credentials from Stores'] },
  { name: 'Discovery', techniques: ['T1033 System Owner/User','T1018 Remote System Discovery','T1082 System Info Discovery'] },
  { name: 'Lateral Movement', techniques: ['T1021 Remote Services','T1570 Lateral Tool Transfer'] },
  { name: 'Collection', techniques: ['T1005 Data from Local','T1114 Email Collection'] },
  { name: 'Command & Control', techniques: ['T1071 App Layer Protocol','T1105 Ingress Tool Transfer','T1573 Encrypted Channel'] },
  { name: 'Exfiltration', techniques: ['T1041 Exfil Over C2','T1048 Exfil Alt Protocol'] },
  { name: 'Impact', techniques: ['T1486 Data Encrypted','T1490 Inhibit Recovery'] }
];
const mitreState = {};

function renderMitre() {
  const grid = document.getElementById('mitre-grid'); if (!grid) return;
  grid.innerHTML = MITRE_TACTICS.map(t => `
    <div class="mitre-col"><h4>${t.name}</h4>
      ${t.techniques.map(tech => {
        const cls = mitreState[tech] || '';
        return `<span class="mitre-cell ${cls}" title="${tech}">${tech}</span>`;
      }).join('')}
    </div>`).join('');
}
renderMitre();

function markMitre(prefix, status) {
  for (const tac of MITRE_TACTICS)
    for (const tech of tac.techniques)
      if (tech.startsWith(prefix)) mitreState[tech] = status;
  renderMitre();
}

const exportBtn = document.getElementById('btn-export-attack');
if (exportBtn) exportBtn.addEventListener('click', () => {
  const blob = new Blob([JSON.stringify({ coverage: mitreState }, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'mitre-coverage.json'; a.click();
});

/* ============ HINTS ============ */
function reconHint(cmd) { const el = document.getElementById('nmap-cmd'); if (el) { el.value = cmd; el.focus(); } }
function mfHint(cmd) { const el = document.getElementById('mf-cmd'); if (el) { el.value = cmd; el.focus(); } }
function msfHint(cmd) { const el = document.getElementById('msf-input'); if (el && !el.disabled) { el.value = cmd; el.focus(); } }

/* ============ NMAP ============ */
const nmapForm = document.getElementById('nmap-form');
const nmapTerm = document.getElementById('nmap-term');
const nmapCmd = document.getElementById('nmap-cmd');
function nmapAppend(t) { if (!nmapTerm) return; nmapTerm.textContent += t; nmapTerm.scrollTop = nmapTerm.scrollHeight; }

if (nmapForm) nmapForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const cmd = nmapCmd.value.trim(); if (!cmd) return;
  nmapCmd.value = '';
  if (!document.getElementById('nmap-consent').checked) { nmapAppend('$ ' + cmd + '\n[!] Check authorization.\n\n'); return; }
  if (!cmd.startsWith('nmap ')) { nmapAppend('$ ' + cmd + '\n[!] Only nmap commands accepted.\n\n'); return; }
  nmapAppend('$ ' + cmd + '\n');
  document.getElementById('nmap-status').textContent = 'running...';
  markMitre('T1595', 'running');
  const parts = cmd.split(/\s+/);
  const target = parts[parts.length - 1];
  const args = parts.slice(1, parts.length - 1).join(' ') || '-sV -T4 --top-ports 100';
  try {
    const res = await fetch('/api/run-nmap', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, args, consent: true }) });
    const j = await res.json();
    if (j.error) { nmapAppend('[error] ' + j.error + '\n\n'); document.getElementById('nmap-status').textContent = 'error'; markMitre('T1595','failed'); return; }
    nmapAppend(j.stdout + (j.stderr ? '\n[stderr]\n' + j.stderr : '') + '\n');
    document.getElementById('nmap-status').textContent = 'done';
    markMitre('T1595', 'covered');
  } catch (err) { nmapAppend('[network error] ' + err.message + '\n\n'); document.getElementById('nmap-status').textContent = 'error'; }
});

/* ============ MSFVENOM ============ */
const mfForm = document.getElementById('mf-form');
const mfTerm = document.getElementById('mf-term');
const mfCmd = document.getElementById('mf-cmd');
function mfAppend(t) { if (!mfTerm) return; mfTerm.textContent += t; mfTerm.scrollTop = mfTerm.scrollHeight; }

if (mfForm) mfForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const cmd = mfCmd.value.trim(); if (!cmd) return;
  mfCmd.value = '';
  if (!document.getElementById('mf-consent').checked) { mfAppend('$ ' + cmd + '\n[!] Check consent.\n\n'); return; }
  // Strip a leading "$ " or "$"
  const clean = cmd.replace(/^\$\s*/, '');
  if (!clean.startsWith('msfvenom ')) { mfAppend('$ ' + cmd + '\n[!] Only msfvenom commands accepted.\n\n'); return; }
  mfAppend('$ ' + clean + '\n');
  document.getElementById('mf-status').textContent = 'running...';
  try {
    const res = await fetch('/api/run-msfvenom', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: clean, consent: true }) });
    const j = await res.json();
    if (j.error) { mfAppend('[error] ' + j.error + '\n\n'); document.getElementById('mf-status').textContent = 'error'; return; }
    mfAppend(j.stdout + (j.stderr ? '\n[stderr]\n' + j.stderr : '') + '\n');
    if (j.file_exists && j.download_url) { mfAppend('[+] Payload ready: ' + j.download_url + '\n'); markMitre('T1587', 'covered'); loadDeployerList(); }
    document.getElementById('mf-status').textContent = 'done';
  } catch (err) { mfAppend('[network error] ' + err.message + '\n\n'); document.getElementById('mf-status').textContent = 'error'; }
});

/* ============ TOOL STATUS ============ */
async function loadToolStatus() {
  try {
    const res = await fetch('/api/tools-status');
    const j = await res.json();
    const el = document.getElementById('tools-tag');
    if (el) {
      const ok = Object.entries(j).filter(([k,v]) => v).map(([k]) => k);
      const missing = Object.entries(j).filter(([k,v]) => !v).map(([k]) => k);
      el.textContent = 'available: ' + (ok.join(', ') || 'none') + (missing.length ? ' | missing: ' + missing.join(', ') : '');
      el.style.color = missing.length ? 'var(--amber)' : 'var(--green)';
    }
  } catch (e) {}
}
loadToolStatus();

/* ============ CLOUDFLARE TUNNEL ============ */
async function refreshTunnel() {
  try {
    const res = await fetch('/api/tunnel/status');
    const j = await res.json();
    const st = document.getElementById('tunnel-status');
    const box = document.getElementById('tunnel-url');
    const side = document.getElementById('side-tunnel');
    const settings = document.getElementById('settings-tunnel');

    if (j.running && j.url) {
      if (st) { st.textContent = 'running'; st.className = 'tag ok'; }
      if (box) { box.textContent = j.url; box.style.color = 'var(--green)'; }
      if (side) side.textContent = 'on';
      if (settings) settings.textContent = j.url;
    } else if (j.available) {
      if (st) { st.textContent = 'idle'; st.className = 'tag idle'; }
      if (box) { box.textContent = '— tunnel not running —'; box.style.color = 'var(--text-low)'; }
      if (side) side.textContent = 'off';
      if (settings) settings.textContent = 'off';
    } else {
      if (st) { st.textContent = 'cloudflared not installed'; st.className = 'tag warn'; }
      if (box) { box.textContent = 'Install cloudflared first.'; box.style.color = 'var(--amber)'; }
      if (side) side.textContent = 'not installed';
      if (settings) settings.textContent = 'cloudflared not installed';
    }
  } catch (e) {}
}
refreshTunnel(); setInterval(refreshTunnel, 5000);

const btnTunnelStart = document.getElementById('btn-tunnel-start');
if (btnTunnelStart) btnTunnelStart.addEventListener('click', async () => {
  if (!confirm('Start a public Cloudflare tunnel? Only use with a consenting partner on a VM they own.')) return;
  btnTunnelStart.disabled = true;
  btnTunnelStart.textContent = 'starting...';
  try {
    const res = await fetch('/api/tunnel/start', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ consent: true })
    });
    const j = await res.json();
    if (j.error) { alert('Error: ' + j.error); return; }
    showToast('🌐 Tunnel: ' + j.url);
    setTimeout(() => location.reload(), 1200);
  } catch (e) { alert('Network error: ' + e.message); }
  finally { btnTunnelStart.disabled = false; btnTunnelStart.textContent = '▶ Start tunnel'; }
});

const btnTunnelStop = document.getElementById('btn-tunnel-stop');
if (btnTunnelStop) btnTunnelStop.addEventListener('click', async () => {
  await fetch('/api/tunnel/stop', { method: 'POST' });
  showToast('Tunnel stopped');
  setTimeout(() => location.reload(), 800);
});

const btnTunnelCopy = document.getElementById('btn-tunnel-copy');
if (btnTunnelCopy) btnTunnelCopy.addEventListener('click', () => {
  const text = document.getElementById('tunnel-url').textContent;
  if (!text || text.startsWith('—') || text.startsWith('Install')) return;
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => showToast('✅ URL copied')).catch(() => fallbackCopy(text));
  } else {
    fallbackCopy(text);
  }
});

/* ============ MSF CONSOLE (PTY) ============ */
let msfSession = null, msfPollTimer = null;
const msfHistory = []; let msfHistoryIdx = -1;

const msfStart = document.getElementById('btn-msf-start');
const msfStop  = document.getElementById('btn-msf-stop');
const msfTermEl = document.getElementById('msf-term');
const msfInput = document.getElementById('msf-input');
const msfForm  = document.getElementById('msf-form');
const msfTag   = document.getElementById('msf-session-tag');
const msfStat  = document.getElementById('msf-status');

function msfAppend(t) {
  if (!msfTermEl) return;
  msfTermEl.textContent += t;
  msfTermEl.scrollTop = msfTermEl.scrollHeight;
}

function msfEnableInput(enable) {
  if (!msfInput) return;
  msfInput.disabled = !enable;
  if (enable) {
    msfInput.focus();
  }
}

// Allow clicking anywhere on the terminal input row to focus the input
if (msfForm) msfForm.addEventListener('click', () => {
  if (msfInput && !msfInput.disabled) msfInput.focus();
});
if (msfTermEl) msfTermEl.addEventListener('click', () => {
  if (msfInput && !msfInput.disabled) msfInput.focus();
});

async function startMsf() {
  if (!msfTermEl) return;
  msfTermEl.textContent = '[*] launching msfconsole via PTY...\n';
  if (msfStat) msfStat.textContent = 'starting...';
  if (msfStart) { msfStart.disabled = true; msfStart.textContent = 'starting...'; }

  try {
    const res = await fetch('/api/msf/start', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ consent: true })
    });
    const j = await res.json();
    if (j.error) {
      msfAppend('ERROR: ' + j.error + '\n');
      if (msfStat) msfStat.textContent = 'error';
      if (msfStart) { msfStart.disabled = false; msfStart.textContent = '▶ Start msfconsole'; }
      return;
    }
    msfSession = j.session_id;
    if (msfTag) { msfTag.textContent = 'session ' + msfSession; msfTag.className = 'tag run'; }
    if (msfStat) msfStat.textContent = 'running';
    msfEnableInput(true);
    if (msfStart) { msfStart.disabled = false; msfStart.textContent = '▶ Start msfconsole'; }
    pollMsf();
    msfPollTimer = setInterval(pollMsf, 400);
  } catch (e) {
    msfAppend('Network error: ' + e.message + '\n');
    if (msfStat) msfStat.textContent = 'error';
    if (msfStart) { msfStart.disabled = false; msfStart.textContent = '▶ Start msfconsole'; }
  }
}

async function pollMsf() {
  if (!msfSession) return;
  try {
    const res = await fetch('/api/msf/read/' + msfSession);
    const text = await res.text();
    if (text) msfAppend(text);
  } catch (e) {}
}

async function stopMsf() {
  if (!msfSession) return;
  try { await fetch('/api/msf/stop/' + msfSession, { method: 'POST' }); } catch (e) {}
  if (msfPollTimer) clearInterval(msfPollTimer);
  msfSession = null;
  msfEnableInput(false);
  if (msfTag) { msfTag.textContent = 'no session'; msfTag.className = 'tag idle'; }
  if (msfStat) msfStat.textContent = 'stopped';
  msfAppend('\n[msfconsole session closed]\n');
}

if (msfStart) msfStart.addEventListener('click', startMsf);
if (msfStop)  msfStop.addEventListener('click', stopMsf);

if (msfForm) msfForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!msfSession || !msfInput || msfInput.disabled) return;
  const text = msfInput.value; if (!text) return;
  msfInput.value = '';
  msfHistory.push(text); msfHistoryIdx = msfHistory.length;
  msfAppend(text + '\n');
  try {
    await fetch('/api/msf/write/' + msfSession, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text + '\n' })
    });
  } catch (e) { msfAppend('[write error: ' + e.message + ']\n'); }
});

if (msfInput) msfInput.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowUp') {
    if (msfHistoryIdx > 0) { msfHistoryIdx--; msfInput.value = msfHistory[msfHistoryIdx]; }
    e.preventDefault();
  } else if (e.key === 'ArrowDown') {
    if (msfHistoryIdx < msfHistory.length - 1) { msfHistoryIdx++; msfInput.value = msfHistory[msfHistoryIdx]; }
    else { msfHistoryIdx = msfHistory.length; msfInput.value = ''; }
    e.preventDefault();
  }
});

/* ============ DEPLOYER ============ */
async function loadDeployerAgents() {
  const sel = document.getElementById('deployer-agent'); if (!sel) return;
  try {
    const res = await fetch('/api/state');
    const j = await res.json();
    const agents = j.agents || {};
    sel.innerHTML = '<option value="">— select a connected agent —</option>' +
      Object.entries(agents).map(([aid, info]) =>
        `<option value="${aid}">${info.hostname} (${info.user}) — ${aid}</option>`).join('');
  } catch (e) {}
}
async function loadDeployerList() {
  const sel = document.getElementById('deployer-select'); if (!sel) return;
  try {
    const res = await fetch('/api/deployer/payloads');
    const files = await res.json();
    sel.innerHTML = '<option value="">— none —</option>' +
      files.map(f => `<option value="${f.name}">${f.name} (${f.size} bytes)</option>`).join('');
  } catch (e) {}
}
loadDeployerList(); setInterval(loadDeployerList, 15000);

const btnDeployerRefresh = document.getElementById('btn-deployer-refresh');
if (btnDeployerRefresh) btnDeployerRefresh.addEventListener('click', () => { loadDeployerAgents(); loadDeployerList(); });

let defenderOk = false;

const btnCheckDefender = document.getElementById('btn-deployer-check');
if (btnCheckDefender) btnCheckDefender.addEventListener('click', async () => {
  const out = document.getElementById('deployer-out');
  const status = document.getElementById('deployer-status');
  const agentId = document.getElementById('deployer-agent').value;
  const consent = document.getElementById('deployer-consent').checked;
  if (!agentId) { alert('Select a target agent.'); return; }
  if (!consent) { alert('Check the authorization box.'); return; }

  out.textContent = '[*] Queuing Defender check on ' + agentId + '...\n';
  status.textContent = 'checking defender...';
  defenderOk = false;
  document.getElementById('btn-deployer-run').disabled = true;
  markMitre('T1562', 'running');

  try {
    const res = await fetch('/api/deployer/check-defender/' + agentId, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ consent: true })
    });
    const j = await res.json();
    if (j.error) { out.textContent += '[error] ' + j.error + '\n'; status.textContent = 'error'; markMitre('T1562','failed'); return; }
    out.textContent += '[+] Check queued. Waiting for agent result (~8s)...\n';

    let tries = 0;
    const poll = setInterval(async () => {
      tries++;
      try {
        const s = await fetch('/api/state');
        const state = await s.json();
        const agent = state.agents[agentId] || {};
        const lastResults = agent._last_results || {};
        const defender = lastResults['T1562.001'];
        if (defender) {
          clearInterval(poll);
          out.textContent += '\n[+] Defender check result:\n' + defender + '\n';
          if (defender.replace(/\s/g,'').includes('RealTimeProtectionEnabled=True')) {
            out.textContent += '\n[!] DEFENDER IS ON. Deployment is BLOCKED.\n';
            status.textContent = 'blocked: defender on';
            markMitre('T1562', 'failed');
            defenderOk = false;
            document.getElementById('btn-deployer-run').disabled = true;
          } else {
            out.textContent += '\n[+] Defender check passed. You may now click "2. Deploy + Execute".\n';
            status.textContent = 'defender off — ready';
            markMitre('T1562', 'covered');
            defenderOk = true;
            document.getElementById('btn-deployer-run').disabled = false;
          }
        }
      } catch (e) {}
      if (tries > 20) { clearInterval(poll); out.textContent += '\n[!] Timed out waiting for Defender result.\n'; status.textContent = 'timeout'; }
    }, 2000);
  } catch (e) { out.textContent += '[network error] ' + e.message + '\n'; status.textContent = 'error'; markMitre('T1562', 'failed'); }
});

const btnDeployerRun = document.getElementById('btn-deployer-run');
if (btnDeployerRun) btnDeployerRun.addEventListener('click', async () => {
  const out = document.getElementById('deployer-out');
  const status = document.getElementById('deployer-status');
  if (!defenderOk) { alert('Run Step 1 (Check Defender) first.'); return; }
  const agentId = document.getElementById('deployer-agent').value;
  const pathVal = document.getElementById('deployer-path').value.trim();
  const selVal  = document.getElementById('deployer-select').value;
  const src_path = pathVal || selVal;
  if (!agentId) { alert('Select a target agent.'); return; }
  if (!src_path) { alert('Provide a path or pick a file.'); return; }

  out.textContent += '\n[*] Deploying ' + src_path + ' to ' + agentId + '...\n';
  status.textContent = 'deploying...';
  markMitre('T1105', 'running');

  try {
    const res = await fetch('/api/deployer/from-path', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ src_path, agent_id: agentId, consent: true, defender_confirmed: true })
    });
    const j = await res.json();
    if (j.error) { out.textContent += '[error] ' + j.error + '\n'; status.textContent = 'error'; markMitre('T1105','failed'); return; }
    out.textContent += '[+] Stored as: ' + j.stored_as + '\n';
    out.textContent += '[+] Size: ' + j.size + ' bytes\n';
    out.textContent += '[+] ' + j.message + '\n';
    out.textContent += '[*] Watch the msfconsole session above for the incoming connection.\n';
    status.textContent = 'queued';
    markMitre('T1105', 'covered');
  } catch (e) { out.textContent += '[network error] ' + e.message + '\n'; status.textContent = 'error'; markMitre('T1105', 'failed'); }
});

/* ============ C2 ============ */
let selectedAgent = null, toastTimer = null;

function showToast(msg) {
  const t = document.getElementById('toast'); if (!t) return;
  t.textContent = msg; t.className = 'toast show';
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.className = 'toast', 3000);
}

function copyOneLiner(id) {
  const el = document.getElementById(id); if (!el) return;
  const text = el.innerText;
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => showToast('✅ Copied')).catch(() => fallbackCopy(text));
    return;
  }
  fallbackCopy(text);
}
function fallbackCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text; ta.style.position = 'fixed'; ta.style.top = '-9999px';
  document.body.appendChild(ta); ta.select();
  try { document.execCommand('copy'); showToast('✅ Copied'); } catch (e) { showToast('⚠️ Press Ctrl+C'); }
  document.body.removeChild(ta);
}

function selectAgent(aid) {
  selectedAgent = aid;
  document.querySelectorAll('.agent-card').forEach(c => c.classList.remove('selected'));
  const el = document.querySelector('[data-agent="' + aid + '"]');
  if (el) el.classList.add('selected');
  showToast('Selected: ' + aid);
}

function queueAbility(tid) {
  if (!selectedAgent) { showToast('⚠️ Select an agent first'); return; }
  fetch('/queue/' + selectedAgent + '/' + tid, { method: 'POST' })
    .then(r => r.json())
    .then(d => {
      if (d.status === 'queued') { showToast('▶ Queued ' + tid); markMitre(tid.split('.')[0], 'running'); }
      else showToast('❌ ' + (d.error || 'Failed'));
    })
    .catch(() => showToast('❌ Network error'));
}

function terminateAll() {
  if (!confirm('⚠️ Terminate ALL agents?')) return;
  fetch('/terminate-all', { method: 'POST' }).then(r => r.json())
    .then(d => { showToast('⏻ Terminated ' + d.count + ' agents'); setTimeout(() => location.reload(), 1000); });
}

function clearResults() {
  if (!confirm('Clear all results?')) return;
  fetch('/clear-results', { method: 'POST' }).then(() => { showToast('🗑 Cleared'); location.reload(); });
}

function filterAbilities() {
  const q = document.getElementById('abilitySearch').value.toLowerCase();
  document.querySelectorAll('.ability-card').forEach(card => {
    card.style.display = card.dataset.search.toLowerCase().includes(q) ? '' : 'none';
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function renderAgents(agents) {
  window.__agents = agents;
  const list = document.getElementById('agentList'); if (!list) return;
  list.innerHTML = '';
  const ids = Object.keys(agents);
  const c = document.getElementById('agentCount'); if (c) c.textContent = ids.length;
  const s = document.getElementById('stat-sessions'); if (s) s.textContent = pad(ids.length);
  ids.forEach(aid => {
    const info = agents[aid];
    const div = document.createElement('div');
    div.className = 'agent-card' + (aid === selectedAgent ? ' selected' : '');
    div.dataset.agent = aid;
    div.onclick = () => selectAgent(aid);
    div.innerHTML =
      '<div class="agent-name">' + escapeHtml(info.hostname) + '</div>' +
      '<div class="agent-meta">' + escapeHtml(info.user) + '</div>' +
      '<div class="agent-status ' + info.status + '">' + info.status + '</div>';
    list.appendChild(div);
  });
}

function renderResults(results) {
  const area = document.getElementById('resultsArea'); if (!area) return;
  area.innerHTML = '';
  Object.entries(results).forEach(([aid, resList]) => {
    resList.forEach(r => {
      const div = document.createElement('div');
      div.className = 'result-card';
      div.innerHTML =
        '<div class="result-header">' +
          '<span class="result-tech">' + escapeHtml(r.technique) + '</span>' +
          '<span class="result-agent">' + escapeHtml(aid) + '</span>' +
          '<span class="result-time">' + escapeHtml(r.time) + '</span>' +
        '</div>' +
        '<pre class="result-output">' + escapeHtml(r.output) + '</pre>';
      area.appendChild(div);
    });
  });
}

function pollState() {
  fetch('/api/state').then(r => r.json())
    .then(state => { renderAgents(state.agents || {}); renderResults(state.results || {}); })
    .catch(() => {});
}
pollState(); setInterval(pollState, 5000);
