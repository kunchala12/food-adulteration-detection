/* Food Adulteration Detection v2 - Frontend JS */
const API = '';
let currentImageData = null, currentMode = 'file', cameraStream = null;

// ── PAGE NAV ──
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(a => a.classList.remove('active'));
  const pg = document.getElementById(`page-${name}`);
  if (pg) { pg.classList.add('active'); window.scrollTo(0, 0); }
  document.querySelectorAll(`[data-page="${name}"]`).forEach(a => a.classList.add('active'));
  if (name === 'history')   loadHistory();
  if (name === 'dashboard') loadDashboard();
}

// ── AUTH STATE ──
async function checkAuth() {
  try {
    const data = await fetch(`${API}/api/me`).then(r => r.json());
    if (data.logged_in) setUserUI(data.username);
  } catch(_) {}
}
function setUserUI(u) {
  document.getElementById('authButtons').classList.add('hidden');
  document.getElementById('userMenu').classList.remove('hidden');
  document.getElementById('usernameDisplay').textContent = u;
}
function clearUserUI() {
  document.getElementById('authButtons').classList.remove('hidden');
  document.getElementById('userMenu').classList.add('hidden');
}

// ── LOGIN / SIGNUP / LOGOUT ──
async function doLogin() {
  const u = document.getElementById('loginUser').value.trim();
  const p = document.getElementById('loginPass').value;
  const errEl = document.getElementById('loginErr');
  errEl.classList.add('hidden');
  if (!u || !p) { errEl.textContent='Fill in all fields'; errEl.classList.remove('hidden'); return; }
  try {
    const data = await fetch(`${API}/api/login`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})}).then(r=>r.json());
    if (data.success) { closeModal('loginModal'); setUserUI(data.username); showToast(`Welcome back, ${data.username}! 👋`); }
    else { errEl.textContent=data.msg; errEl.classList.remove('hidden'); }
  } catch(_) { errEl.textContent='Network error.'; errEl.classList.remove('hidden'); }
}

async function doSignup() {
  const u = document.getElementById('signUser').value.trim();
  const e = document.getElementById('signEmail').value.trim();
  const p = document.getElementById('signPass').value;
  const errEl = document.getElementById('signErr'), okEl = document.getElementById('signOk');
  errEl.classList.add('hidden'); okEl.classList.add('hidden');
  if (!u||!e||!p) { errEl.textContent='All fields required'; errEl.classList.remove('hidden'); return; }
  try {
    const data = await fetch(`${API}/api/signup`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,email:e,password:p})}).then(r=>r.json());
    if (data.success) { okEl.textContent='Account created! Redirecting to login…'; okEl.classList.remove('hidden'); setTimeout(()=>switchModal('signupModal','loginModal'),1500); }
    else { errEl.textContent=data.msg; errEl.classList.remove('hidden'); }
  } catch(_) { errEl.textContent='Network error.'; errEl.classList.remove('hidden'); }
}

async function doLogout() {
  await fetch(`${API}/api/logout`,{method:'POST'});
  clearUserUI(); showPage('home'); showToast('Logged out.');
}

// ── MODAL HELPERS ──
function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }
function closeModalBg(e, id) { if (e.target===document.getElementById(id)) closeModal(id); }
function switchModal(a,b) { closeModal(a); openModal(b); }

// ── DETECT GATE ──
function handleDetectClick() {
  if (document.getElementById('userMenu').classList.contains('hidden')) {
    openModal('loginModal'); showToast('Please log in to use detection.');
  } else { showPage('detect'); }
}

// ── TABS ──
function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
  document.getElementById(`tab-${name}`).classList.add('active');
  document.getElementById(`panel-${name}`).classList.add('active');
  if (name!=='camera') stopCamera();
}

// ── FILE UPLOAD ──
function handleFileSelect(e) { const f=e.target.files[0]; if(f) loadFilePreview(f); }
function handleDrop(e) {
  e.preventDefault(); document.getElementById('dropZone').classList.remove('drag-over');
  const f=e.dataTransfer.files[0]; if(f&&f.type.startsWith('image/')) loadFilePreview(f);
}
function loadFilePreview(file) {
  currentMode='file'; currentImageData=file;
  const reader=new FileReader();
  reader.onload=ev=>{ document.getElementById('previewImg').src=ev.target.result; showPreview(); };
  reader.readAsDataURL(file);
}

// ── CAMERA ──
async function startCamera() {
  try {
    cameraStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}});
    document.getElementById('cameraFeed').srcObject=cameraStream;
    document.getElementById('startCamBtn').classList.add('hidden');
    document.getElementById('captureBtn').classList.remove('hidden');
    document.getElementById('stopCamBtn').classList.remove('hidden');
  } catch(_) { showToast('Camera access denied or unavailable.'); }
}
function capturePhoto() {
  const v=document.getElementById('cameraFeed'), c=document.getElementById('cameraCanvas');
  c.width=v.videoWidth||640; c.height=v.videoHeight||480;
  c.getContext('2d').drawImage(v,0,0);
  const dataUrl=c.toDataURL('image/jpeg',0.9);
  currentMode='camera'; currentImageData=dataUrl;
  document.getElementById('previewImg').src=dataUrl;
  showPreview(); stopCamera(); switchTab('upload');
}
function stopCamera() {
  if (cameraStream) { cameraStream.getTracks().forEach(t=>t.stop()); cameraStream=null; }
  document.getElementById('startCamBtn').classList.remove('hidden');
  document.getElementById('captureBtn').classList.add('hidden');
  document.getElementById('stopCamBtn').classList.add('hidden');
  document.getElementById('cameraFeed').srcObject=null;
}
function showPreview() {
  document.getElementById('imagePreview').classList.remove('hidden');
  document.getElementById('resultSection').classList.add('hidden');
}
function clearPreview() {
  currentImageData=null; currentMode='file';
  document.getElementById('imagePreview').classList.add('hidden');
  document.getElementById('fileInput').value='';
}

// ── ANALYZE ──
async function analyzeImage() {
  if (!currentImageData) { showToast('Select or capture an image first.'); return; }
  document.getElementById('loadingOverlay').classList.remove('hidden');
  document.getElementById('resultSection').classList.add('hidden');
  try {
    let res;
    if (currentMode==='camera') {
      res=await fetch(`${API}/api/predict`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image:currentImageData})});
    } else {
      const form=new FormData(); form.append('image',currentImageData);
      res=await fetch(`${API}/api/predict`,{method:'POST',body:form});
    }
    const data=await res.json();
    document.getElementById('loadingOverlay').classList.add('hidden');
    if (!data.success) { if(res.status===401){showToast('Session expired. Please log in again.');openModal('loginModal');}else{showToast(data.msg||'Analysis failed.');} return; }
    displayResult(data);
  } catch(err) {
    document.getElementById('loadingOverlay').classList.add('hidden');
    showToast('Server error. Is the Flask app running?'); console.error(err);
  }
}

function displayResult(data) {
  const sec=document.getElementById('resultSection'); sec.classList.remove('hidden');
  document.getElementById('resultCard').style.borderColor=data.color;
  document.getElementById('resultIcon').textContent=data.icon;
  document.getElementById('resultStatus').textContent=data.status;
  document.getElementById('resultStatus').style.color=data.color;
  document.getElementById('resultLabel').textContent=data.display;
  document.getElementById('resultDesc').textContent=data.desc;
  const fill=document.getElementById('confidenceFill');
  fill.style.width='0%';
  if (data.status==='ADULTERATED') fill.style.background='linear-gradient(90deg,#e74c3c,#c0392b)';
  else if (data.status==='INVALID') fill.style.background='linear-gradient(90deg,#f39c12,#e67e22)';
  else fill.style.background='linear-gradient(90deg,#58a6ff,#2ecc71)';
  setTimeout(()=>fill.style.width=data.confidence+'%',60);
  document.getElementById('confidenceText').textContent=data.confidence.toFixed(1)+'%';
  const container=document.getElementById('top3Container'); container.innerHTML='';
  (data.top3||[]).forEach(([label,pct])=>{
    const clean=label.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
    container.innerHTML+=`<div class="prob-row"><span class="prob-label">${clean}</span><div class="prob-bar"><div class="prob-bar-fill" style="width:${pct}%"></div></div><span class="prob-pct">${pct}%</span></div>`;
  });
  sec.scrollIntoView({behavior:'smooth',block:'start'});
}

// ── DASHBOARD ──
async function loadDashboard() {
  const c=document.getElementById('dashboardContainer');
  c.innerHTML='<div class="loading-history">Loading dashboard…</div>';
  try {
    const data=await fetch(`${API}/api/stats`).then(r=>r.json());
    if (!data.success) { c.innerHTML='<div class="empty-dash">Please log in to view dashboard.</div>'; return; }
    if (data.total===0) {
      c.innerHTML=`<div class="empty-dash"><p style="font-size:2rem;margin-bottom:1rem">📊</p><p>No detections yet!</p><p style="margin-top:.5rem;font-size:.9rem;color:var(--sub)">Run your first food analysis to see stats here.</p><button class="btn-primary" style="margin-top:1.5rem" onclick="showPage('detect')">Start Detecting</button></div>`;
      return;
    }
    renderDashboard(c, data);
  } catch(_) { c.innerHTML='<div class="empty-dash">Failed to load dashboard.</div>'; }
}

function renderDashboard(container, d) {
  const purityColor = d.purity_rate >= 70 ? 'var(--green)' : d.purity_rate >= 40 ? 'var(--orange)' : 'var(--red)';
  const r = 54; const circ = 2*Math.PI*r;
  const offset = circ * (1 - d.purity_rate/100);

  // Daily bar chart
  const last7 = buildLast7(d.daily);
  const maxDay = Math.max(...last7.map(x=>x.cnt), 1);
  const dailyBars = last7.map(x=>{
    const h = Math.round((x.cnt/maxDay)*70);
    const label = x.day.slice(5);
    return `<div class="daily-bar-col"><div class="daily-bar" style="height:${h}px"></div><div class="daily-label">${label}</div></div>`;
  }).join('');

  // Food group bars
  const groups = Object.entries(d.by_group);
  const fgBars = groups.map(([grp, v])=>{
    const total = (v.pure||0)+(v.adulterated||0)+(v.invalid||0)||1;
    const pPct = Math.round((v.pure||0)/total*100);
    const aPct = Math.round((v.adulterated||0)/total*100);
    const iPct = 100-pPct-aPct;
    return `<div class="fg-row">
      <span class="fg-label">${grp}</span>
      <div class="fg-bar-wrap">
        <div class="fg-bar" style="width:${pPct}%;background:var(--green)"></div>
        <div class="fg-bar" style="width:${aPct}%;background:var(--red)"></div>
        <div class="fg-bar" style="width:${iPct}%;background:var(--border)"></div>
      </div>
      <span class="fg-counts">${v.pure||0}P / ${v.adulterated||0}A</span>
    </div>`;
  }).join('');

  container.innerHTML = `
    <div class="dash-stats">
      <div class="dash-stat-card"><div class="dash-stat-n" style="color:var(--accent)">${d.total}</div><div class="dash-stat-l">Total Tests</div></div>
      <div class="dash-stat-card"><div class="dash-stat-n" style="color:var(--green)">${d.pure}</div><div class="dash-stat-l">Pure Samples</div></div>
      <div class="dash-stat-card"><div class="dash-stat-n" style="color:var(--red)">${d.adulterated}</div><div class="dash-stat-l">Adulterated</div></div>
      <div class="dash-stat-card"><div class="dash-stat-n" style="color:${purityColor}">${d.purity_rate}%</div><div class="dash-stat-l">Purity Rate</div></div>
    </div>
    <div class="dash-row">
      <div class="dash-card">
        <h3>Purity Rate</h3>
        <div class="purity-ring">
          <svg class="ring-svg" viewBox="0 0 140 140">
            <circle class="ring-bg" cx="70" cy="70" r="${r}"/>
            <circle class="ring-fill" cx="70" cy="70" r="${r}" stroke="${purityColor}"
              stroke-dasharray="${circ}" stroke-dashoffset="${circ}" id="ringFill"/>
            <text class="ring-text" x="70" y="68" text-anchor="middle" dominant-baseline="middle">${d.purity_rate}%</text>
            <text class="ring-sub" x="70" y="86" text-anchor="middle">Purity</text>
          </svg>
          <p style="color:var(--sub);font-size:.8rem;text-align:center">${d.pure} pure out of ${d.total} tests</p>
        </div>
      </div>
      <div class="dash-card">
        <h3>7-Day Activity</h3>
        <div class="daily-bars">${dailyBars}</div>
      </div>
    </div>
    <div class="dash-card" style="margin-bottom:2rem">
      <h3>By Food Group (🟢 Pure &nbsp;🔴 Adulterated)</h3>
      <div class="food-group-bars" style="margin-top:.5rem">${fgBars || '<p style="color:var(--sub);font-size:.85rem">No group data yet.</p>'}</div>
    </div>
    <div style="text-align:center"><button class="btn-primary" onclick="showPage('detect')">🔍 Analyze Another Sample</button></div>`;

  // Animate ring
  setTimeout(()=>{
    const ring = document.getElementById('ringFill');
    if (ring) ring.style.strokeDashoffset = offset;
  }, 200);
}

function buildLast7(daily) {
  const result = [];
  for (let i=6; i>=0; i--) {
    const d = new Date(); d.setDate(d.getDate()-i);
    const key = d.toISOString().slice(0,10);
    const found = daily.find(x=>x.day===key);
    result.push({day:key, cnt: found ? found.cnt : 0});
  }
  return result;
}

// ── HISTORY ──
async function loadHistory() {
  const container=document.getElementById('historyContainer');
  container.innerHTML='<div class="loading-history">Loading history…</div>';
  try {
    const data=await fetch(`${API}/api/history`).then(r=>r.json());
    if (!data.success) { container.innerHTML='<div class="history-empty">Please log in to view history.</div>'; return; }
    if (!data.history.length) { container.innerHTML='<div class="history-empty">No analysis history yet. Start detecting food samples!</div>'; return; }
    container.innerHTML='';
    data.history.forEach(item=>{
      const badge=item.status==='PURE'?'badge-pure':item.status==='ADULTERATED'?'badge-adulterated':'badge-invalid';
      const date=new Date(item.created).toLocaleString();
      const div=document.createElement('div');
      div.className='history-item';
      div.style.borderLeftColor=item.color;
      div.innerHTML=`<div class="hist-icon">${item.icon}</div>
        <div class="hist-info"><div class="hist-food">${item.food_type}</div><div class="hist-date">${date}</div></div>
        <span class="hist-badge ${badge}">${item.status}</span>
        <span class="hist-conf">${item.confidence?item.confidence.toFixed(1)+'%':'—'}</span>`;
      container.appendChild(div);
    });
  } catch(_) { container.innerHTML='<div class="history-empty">Failed to load history.</div>'; }
}

// ── CONTACT ──
async function submitContact() {
  const name=document.getElementById('cName').value.trim();
  const email=document.getElementById('cEmail').value.trim();
  const message=document.getElementById('cMessage').value.trim();
  const msgEl=document.getElementById('contactMsg');
  if (!name||!email||!message) {
    msgEl.textContent='Please fill in all fields.'; msgEl.style.cssText='background:rgba(231,76,60,0.1);color:#e74c3c;'; msgEl.classList.remove('hidden'); return;
  }
  try {
    const data=await fetch(`${API}/api/contact`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,email,message})}).then(r=>r.json());
    msgEl.textContent=data.msg;
    msgEl.style.cssText=data.success?'background:rgba(46,204,113,0.1);color:#2ecc71;':'background:rgba(231,76,60,0.1);color:#e74c3c;';
    msgEl.classList.remove('hidden');
    if (data.success) { document.getElementById('cName').value=''; document.getElementById('cEmail').value=''; document.getElementById('cMessage').value=''; }
  } catch(_) { msgEl.textContent='Failed to send.'; msgEl.classList.remove('hidden'); }
}

// ── TOAST ──
let toastTimeout;
function showToast(msg) {
  const t=document.getElementById('toast'); t.textContent=msg; t.classList.remove('hidden');
  clearTimeout(toastTimeout); toastTimeout=setTimeout(()=>t.classList.add('hidden'),3200);
}

// ── PARTICLES ──
function initParticles() {
  const container=document.getElementById('heroParticles'); if(!container) return;
  for (let i=0;i<18;i++) {
    const p=document.createElement('div'); p.className='particle';
    p.style.left=Math.random()*100+'%';
    p.style.animationDuration=(6+Math.random()*10)+'s';
    p.style.animationDelay=(Math.random()*8)+'s';
    p.style.width=p.style.height=(2+Math.random()*3)+'px';
    container.appendChild(p);
  }
}

// ── KEYBOARD ──
document.addEventListener('keydown', e => {
  if (e.key==='Escape') { closeModal('loginModal'); closeModal('signupModal'); }
});

// ── INIT ──
window.addEventListener('DOMContentLoaded', () => {
  checkAuth(); initParticles();
});
