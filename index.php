<?php
include 'connectin.php';
session_start();
if (!isset($_SESSION['company_id'])) {
    header("Location: login.php");
    exit();
}
$current_company_id = $_SESSION['company_id'];
$current_company_name = $_SESSION['company_name'];
?>

<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Employee Face Registration System</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@300;400;600;700&display=swap" rel="stylesheet"/>
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet"/>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

:root{
  /* ── Dashboard-matching palette ── */
  --bg-dark:#0d0d1a;
  --bg-panel:#131326;
  --bg-card:#1a1a35;
  --bg-entry:#0d0d2a;

  /* Dashboard purple/blue gradient colours */
  --grad-a:#667eea;
  --grad-b:#764ba2;

  --accent:#667eea;
  --accent2:#764ba2;
  --success:#10b981;
  --warning:#f59e0b;
  --danger:#ef4444;
  --text-pri:#e8e8ff;
  --text-sec:#7878a8;
  --border:#2a2a50;
  --mono:'Share Tech Mono',monospace;
  --sans:'Exo 2',sans-serif;
}

body{
  background:var(--bg-dark);
  color:var(--text-pri);
  font-family:var(--sans);
  font-size:14px;
  min-height:100vh;
  display:flex;
  flex-direction:column;
  overflow:hidden;
}

/* ── Header — matches dashboard gradient bar ── */
header{
  background:linear-gradient(135deg,var(--grad-a) 0%,var(--grad-b) 100%);
  border-bottom:1px solid rgba(255,255,255,0.12);
  padding:0 24px;
  height:64px;
  display:flex;
  align-items:center;
  gap:0;
  flex-shrink:0;
  position:relative;
  box-shadow:0 4px 12px rgba(0,0,0,0.3);
}
.hdr-icon{
  color:#fff;
  font-family:var(--mono);
  font-size:22px;
  margin-right:12px;
}
.hdr-title{
  display:flex;
  flex-direction:column;
}
.hdr-title h1{
  font-family:var(--mono);
  font-size:15px;
  font-weight:700;
  color:#fff;
  letter-spacing:0.04em;
}
.hdr-title span{
  font-family:var(--mono);
  font-size:8px;
  color:rgba(255,255,255,0.65);
  letter-spacing:0.1em;
  margin-top:2px;
}
.hdr-badge{
  margin-left:auto;
  font-family:var(--mono);
  font-size:9px;
  color:#fff;
  background:rgba(255,255,255,0.15);
  border:1px solid rgba(255,255,255,0.3);
  padding:4px 12px;
  border-radius:6px;
  letter-spacing:0.06em;
  backdrop-filter:blur(4px);
}

/* ── Dashboard button ── */
.btn-dashboard{
  margin-left:14px;
  background:#10b981;
  color:#fff;
  padding:8px 15px;
  border-radius:6px;
  text-decoration:none;
  font-family:var(--sans);
  font-size:14px;
  font-weight:600;
  display:flex;
  align-items:center;
  gap:6px;
  white-space:nowrap;
  transition:opacity 0.15s,transform 0.15s;
  box-shadow:0 2px 8px rgba(16,185,129,0.35);
}
.btn-dashboard:hover{opacity:0.88;transform:translateY(-1px);color:#fff;}

/* ── Body layout ── */
main{
  flex:1;
  display:grid;
  grid-template-columns:320px 1fr;
  overflow:hidden;
}

/* ── Left panel ── */
.left-panel{
  background:var(--bg-panel);
  border-right:1px solid var(--border);
  display:flex;
  flex-direction:column;
  overflow-y:auto;
  padding-bottom:16px;
}
.section-header{
  display:flex;
  align-items:center;
  gap:8px;
  padding:16px 16px 6px;
}
.section-header span{
  font-family:var(--mono);
  font-size:8px;
  color:rgba(255,255,255,0.55);
  letter-spacing:0.14em;
  white-space:nowrap;
}
.section-line{flex:1;height:1px;background:var(--border);}

/* Form */
.form-block{padding:0 16px 10px;}
.field{margin-bottom:12px;}
.field label{
  display:block;
  font-family:var(--mono);
  font-size:9px;
  color:var(--text-sec);
  letter-spacing:0.1em;
  margin-bottom:5px;
}
.field input{
  width:100%;
  background:var(--bg-entry);
  border:1px solid var(--border);
  border-radius:6px;
  color:var(--text-pri);
  font-family:var(--mono);
  font-size:12px;
  padding:9px 12px;
  outline:none;
  transition:border-color 0.15s,box-shadow 0.15s;
}
.field input:focus{
  border-color:var(--accent);
  box-shadow:0 0 0 3px rgba(102,126,234,0.15);
}
.field input::placeholder{color:var(--text-sec);opacity:0.6;}
.field input:disabled{opacity:0.45;cursor:not-allowed;}

/* Pose list */
.poses-block{padding:0 16px 8px;}
.pose-row{
  display:flex;
  align-items:center;
  gap:8px;
  padding:5px 0;
}
.pose-dot{
  font-family:var(--mono);
  font-size:14px;
  color:var(--text-sec);
  width:20px;
  flex-shrink:0;
  text-align:center;
  transition:color 0.2s;
}
.pose-lbl{
  font-family:var(--mono);
  font-size:9px;
  color:var(--text-sec);
  letter-spacing:0.04em;
  transition:color 0.2s;
}
.pose-row.active .pose-dot,.pose-row.active .pose-lbl{color:var(--accent);}
.pose-row.done   .pose-dot,.pose-row.done   .pose-lbl{color:var(--success);}
.pose-row.skipped .pose-dot,.pose-row.skipped .pose-lbl{color:var(--text-sec);opacity:0.4;text-decoration:line-through;}

/* Progress bar — matches dashboard gradient */
.prog-wrap{padding:4px 16px 12px;}
.prog-bg{
  height:6px;
  background:var(--bg-entry);
  border-radius:3px;
  overflow:hidden;
}
.prog-fill{
  height:100%;
  background:linear-gradient(90deg,var(--grad-a),var(--grad-b));
  border-radius:3px;
  width:0%;
  transition:width 0.4s ease;
}
.prog-label{
  font-family:var(--mono);
  font-size:9px;
  color:var(--text-sec);
  text-align:right;
  margin-top:4px;
}

/* Buttons — match dashboard style */
.btn-block{padding:0 16px 8px;}
.btn{
  width:100%;
  padding:10px 14px;
  border-radius:6px;
  border:1px solid var(--border);
  background:transparent;
  color:var(--text-pri);
  font-family:var(--sans);
  font-size:13px;
  font-weight:600;
  letter-spacing:0.04em;
  cursor:pointer;
  transition:opacity 0.15s,background 0.15s,border-color 0.15s,transform 0.15s,box-shadow 0.15s;
  text-align:center;
  margin-bottom:6px;
}
.btn:hover:not(:disabled){opacity:0.85;transform:translateY(-1px);}
.btn:disabled{opacity:0.3;cursor:not-allowed;}
.btn.primary{
  background:linear-gradient(135deg,var(--grad-a) 0%,var(--grad-b) 100%);
  border-color:transparent;
  color:#fff;
  box-shadow:0 4px 12px rgba(102,126,234,0.3);
}
.btn.success{
  background:var(--success);
  border-color:var(--success);
  color:#fff;
  box-shadow:0 4px 12px rgba(16,185,129,0.3);
}
.btn.muted{
  background:var(--bg-card);
  color:var(--text-sec);
  border-color:var(--border);
}
.btn-row-2{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:0;}

/* Status */
.status-wrap{padding:6px 16px 4px;text-align:center;}
#statusMsg{
  font-family:var(--mono);
  font-size:9px;
  color:var(--text-sec);
  line-height:1.6;
  word-break:break-word;
}

/* ── Right / Camera panel ── */
.right-panel{
  background:var(--bg-card);
  display:flex;
  flex-direction:column;
  overflow:hidden;
}
.cam-top{
  display:flex;
  align-items:center;
  gap:8px;
  padding:12px 16px 8px;
  border-bottom:1px solid var(--border);
}
.cam-top span{
  font-family:var(--sans);
  font-size:13px;
  color:var(--text-pri);
  font-weight:600;
  letter-spacing:0.06em;
}
#liveDot{
  width:10px;height:10px;
  border-radius:50%;
  background:var(--border);
  flex-shrink:0;
  transition:background 0.3s;
}
#liveDot.on{
  background:var(--success);
  box-shadow:0 0 8px var(--success);
  animation:pulse 2s infinite;
}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.5;}}

.cam-frame{
  position:relative;
  flex:1;
  background:#050510;
  overflow:hidden;
  margin:12px 14px;
  border-radius:12px;
  border:1px solid var(--border);
  box-shadow:0 4px 12px rgba(0,0,0,0.3);
}
#videoEl{
  width:100%;height:100%;
  object-fit:cover;
  display:block;
  transform:scaleX(-1);
}
#idleScreen{
  position:absolute;
  inset:0;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  gap:14px;
  background:#050510;
}
.idle-icon{
  font-size:60px;
  color:var(--border);
}
#idleScreen p{font-family:var(--mono);font-size:11px;color:var(--text-sec);}

/* Face detection canvas */
 #overlayCanvas{
  position:absolute;
  inset:0;
  width:100%;
  height:100%;
  object-fit:cover;
  pointer-events:none;
  transform:scaleX(-1); /* මේ පේළිය අනිවාර්යයෙන් දාන්න */
}


/* Pose instruction bottom bar */
.cam-bottom{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:8px 16px 14px;
  flex-shrink:0;
}
#instrText{
  font-family:var(--mono);
  font-size:10px;
  color:var(--success);
  font-weight:600;
  letter-spacing:0.04em;
}
#counterText{
  font-family:var(--mono);
  font-size:10px;
  color:var(--accent);
  font-weight:600;
}

/* ── Toast ── */
#toast{
  position:fixed;
  bottom:28px;left:50%;
  transform:translateX(-50%) translateY(20px);
  background:white;
  border-left:4px solid var(--success);
  color:#333;
  font-family:var(--sans);
  font-size:13px;
  font-weight:500;
  padding:12px 20px;
  border-radius:8px;
  box-shadow:0 4px 12px rgba(0,0,0,0.15);
  opacity:0;
  transition:opacity 0.25s,transform 0.25s;
  pointer-events:none;
  z-index:200;
  white-space:nowrap;
}
#toast.show{opacity:1;transform:translateX(-50%) translateY(0);}

/* Processing spinner overlay */
#spinnerOverlay{
  position:absolute;
  inset:0;
  background:rgba(5,5,16,0.75);
  display:none;
  align-items:center;
  justify-content:center;
  flex-direction:column;
  gap:12px;
  border-radius:12px;
}
#spinnerOverlay.visible{display:flex;}
.spinner{
  width:40px;height:40px;
  border:3px solid var(--border);
  border-top-color:var(--accent);
  border-radius:50%;
  animation:spin 0.8s linear infinite;
}
@keyframes spin{to{transform:rotate(360deg)}}
#spinnerOverlay p{
  font-family:var(--mono);
  font-size:10px;
  color:var(--accent);
  letter-spacing:0.1em;
}

/* ── Success banner — matches dashboard card style ── */
#successBanner{
  display:none;
  margin:0 16px 10px;
  background:rgba(16,185,129,0.08);
  border:1px solid var(--success);
  border-radius:8px;
  padding:14px 16px;
  font-family:var(--mono);
  font-size:9px;
  color:var(--success);
  line-height:2;
  letter-spacing:0.04em;
  box-shadow:0 2px 8px rgba(16,185,129,0.1);
}
</style>
</head>
<body>

<header>
  <div class="hdr-icon"><i class="bi bi-camera-video-fill"></i></div>
  <div class="hdr-title">
    <h1><i class="bi bi-person-badge"></i> Employee Face Registration System</h1>
    <span>DeepFace · Facenet512 · OpenCV</span>
  </div>
  <div class="hdr-badge" id="hdrBadge">Registered: 0 employees</div>

  <a href="dashboard.php" class="btn-dashboard">
    <i class="bi bi-speedometer2"></i> Attendance Dashboard
  </a>
</header>

<main>

  <div class="left-panel">

    <div class="section-header">
      <span>EMPLOYEE DETAILS</span>
      <div class="section-line"></div>
    </div>
    <div class="form-block">
      <div class="field">
        <label>EMPLOYEE ID</label>
        <input id="inpId"   type="text" placeholder="e.g. EMP-001"/>
      </div>
      <div class="field">
        <label>EMPLOYEE NAME</label>
        <input id="inpName" type="text" placeholder="Full name"/>
      </div>
      <div class="field">
        <label>OUTLET</label>
        <input id="inpOutlet" type="text" placeholder="Branch / location"/>
      </div>
    </div>

    <div class="section-header">
      <span>POSE PROGRESS</span>
      <div class="section-line"></div>
    </div>
    <div class="poses-block" id="posesBlock">
    </div>
    <div class="prog-wrap">
      <div class="prog-bg"><div class="prog-fill" id="progFill"></div></div>
      <div class="prog-label" id="progLabel">0 / 5</div>
    </div>

    <div id="successBanner"></div>

    <div class="btn-block">
      <button class="btn primary" id="btnStart"   onclick="startRegistration()">▶  START REGISTRATION</button>
      <button class="btn success" id="btnCapture" onclick="capturePose()" disabled>📸  CAPTURE POSE</button>
      <div class="btn-row-2">
        <button class="btn muted" id="btnSkip"  onclick="skipPose()"  disabled>⏭ SKIP</button>
        <button class="btn muted" id="btnReset" onclick="doReset()">🔄 RESET</button>
      </div>
    </div>

    <div class="status-wrap">
      <div id="statusMsg">Enter employee details and click START</div>
    </div>

  </div>

  <div class="right-panel">
    <div class="cam-top">
      <span>LIVE FEED</span>
      <div id="liveDot"></div>
    </div>

    <div class="cam-frame" id="camFrame">
      <video id="videoEl" autoplay playsinline muted style="display:none;"></video>
      <canvas id="overlayCanvas"></canvas>
      <div id="idleScreen">
        <div class="idle-icon"><i class="bi bi-camera-video" style="font-size:60px;color:var(--border);"></i></div>
        <p>Camera starts after registration begins</p>
      </div>
      <div id="spinnerOverlay">
        <div class="spinner"></div>
        <p>DEEPFACE PROCESSING…</p>
      </div>
    </div>

    <div class="cam-bottom">
      <div id="instrText">Camera feed will appear after START</div>
      <div id="counterText">0 / 5</div>
    </div>
  </div>

</main>

<div id="toast"></div>

<script>
// මතක තබා ගන්න: සැබෑ සර්වර් එකේ (VPS) IP එක මෙතනට දෙන්න
    const API = "http://<?php echo $_SERVER['SERVER_NAME']; ?>:5000";

const POSES = [
  { key:'straight',     label:'Look STRAIGHT at camera' },
  { key:'slight_left',  label:'Turn head slightly LEFT' },
  { key:'slight_right', label:'Turn head slightly RIGHT' },
  { key:'slight_up',    label:'Look slightly UP' },
  { key:'slight_down',  label:'Look slightly DOWN' },
];

let stream = null;
let currentPose = 0;
let poseStates = POSES.map(() => 'pending'); 
let capturing  = false;
let liveDotInterval = null;
let liveDetectInterval = null;
let faceBoxes  = []; 
let registeredCount = 0;

/* ── Build pose rows ── */
const posesBlock = document.getElementById('posesBlock');
POSES.forEach((p, i) => {
  const row = document.createElement('div');
  row.className = 'pose-row';
  row.id = `prow-${i}`;
  row.innerHTML = `<div class="pose-dot" id="pdot-${i}">○</div><div class="pose-lbl" id="plbl-${i}">${p.label}</div>`;
  posesBlock.appendChild(row);
});

/* ── Refresh pose UI ── */
function refreshPoses() {
  POSES.forEach((p, i) => {
    const row = document.getElementById(`prow-${i}`);
    const dot = document.getElementById(`pdot-${i}`);
    row.className = 'pose-row ' + (
      i < currentPose
        ? (poseStates[i] === 'skipped' ? 'skipped' : 'done')
        : i === currentPose ? 'active' : ''
    );
    if (i < currentPose) {
      dot.textContent = poseStates[i] === 'skipped' ? '○' : '✓';
    } else if (i === currentPose) {
      dot.textContent = '►';
    } else {
      dot.textContent = '○';
    }
  });

  const done = poseStates.filter(s => s === 'done').length;
  const pct  = Math.round(done / POSES.length * 100);
  document.getElementById('progFill').style.width = pct + '%';
  document.getElementById('progLabel').textContent = `${done} / ${POSES.length}`;
  document.getElementById('counterText').textContent = `${currentPose} / ${POSES.length}`;

  if (currentPose < POSES.length) {
    document.getElementById('instrText').textContent =
      `[${currentPose+1}/${POSES.length}]  ${POSES[currentPose].label}`;
  } else {
    document.getElementById('instrText').textContent = '✅  All poses captured — saving profile…';
  }
}

/* ── Status ── */
function setStatus(msg, color) {
  const el = document.getElementById('statusMsg');
  el.textContent = msg;
  el.style.color = color || 'var(--text-sec)';
}

/* ── Toast ── */
let toastTimer;
function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2600);
}

/* ── Badge ── */
function refreshBadge() {
  document.getElementById('hdrBadge').textContent =
    `Registered: ${registeredCount} employee${registeredCount !== 1 ? 's' : ''}`;
}

/* ── Spinner ── */
function showSpinner(v) {
  document.getElementById('spinnerOverlay').classList.toggle('visible', v);
}

/* ── Live dot blink ── */
function startDot() {
  let on = true;
  liveDotInterval = setInterval(() => {
    document.getElementById('liveDot').className = on ? 'on' : '';
    on = !on;
  }, 600);
}
function stopDot() {
  clearInterval(liveDotInterval);
  document.getElementById('liveDot').className = '';
}

/* ── Live background polling for bounding box ── */
async function pollFaceDetection() {
  if (!stream || capturing) return;

  const vid = document.getElementById('videoEl');
  if (!vid.videoWidth || !vid.videoHeight) return;

  // Aspect ratio එක හරියටම තියාගන්න
  const targetWidth = 400; // Resolution එක ටිකක් වැඩි කළා පැහැදිලි වෙන්න
  const targetHeight = Math.round((vid.videoHeight / vid.videoWidth) * targetWidth);

  const canvas = document.createElement('canvas');
  canvas.width = targetWidth; 
  canvas.height = targetHeight;
  const ctx = canvas.getContext('2d');
  
  // කලින් තිබ්බ flip කරන කොටස (translate, scale) අයින් කළා
  ctx.drawImage(vid, 0, 0, canvas.width, canvas.height);

  // Quality එක 0.8 ට වැඩි කළා (Haar Cascade එකට හොඳට අඳුරගන්න)
  const imageData = canvas.toDataURL('image/jpeg', 0.8); 

  try {
    const res = await fetch(`${API}/live_detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: imageData })
    });
    
    if (!res.ok) return;
    
    const data = await res.json();
    if (data && data.face_boxes !== undefined) {
      const scaleX = vid.videoWidth / targetWidth;
      const scaleY = vid.videoHeight / targetHeight;
      
      faceBoxes = data.face_boxes.map(b => ({
          x: b.x * scaleX,
          y: b.y * scaleY,
          w: b.w * scaleX,
          h: b.h * scaleY,
          conf: b.conf
      }));
    }
  } catch (e) {
    console.error("Live detection error: ", e);
  }
}
    // Ignore networking errors silently

/* ── Draw face-detection overlay ── */
function drawFaceBoxes() {
  const canvas = document.getElementById('overlayCanvas');
  const vid    = document.getElementById('videoEl');

  if (vid.videoWidth && canvas.width !== vid.videoWidth) {
    canvas.width  = vid.videoWidth;
    canvas.height = vid.videoHeight;
  }

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  faceBoxes.forEach(b => {
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 2;
    ctx.strokeRect(b.x, b.y, b.w, b.h);
    
    ctx.fillStyle = '#00ff00';
    ctx.font = '16px "Share Tech Mono", monospace';
    ctx.fillText(b.conf, b.x, b.y - 6);
  });

  if (stream) requestAnimationFrame(drawFaceBoxes);
}

/* ── Camera ── */
async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { width:640, height:480, facingMode:'user' } });
    const vid = document.getElementById('videoEl');
    vid.srcObject = stream;
    vid.style.display = 'block';
    document.getElementById('idleScreen').style.display = 'none';
    startDot();
    drawFaceBoxes();
    
    if (liveDetectInterval) clearInterval(liveDetectInterval);
    liveDetectInterval = setInterval(pollFaceDetection, 150);
    
    setStatus('Camera started — follow the pose instructions', 'var(--accent)');
  } catch(e) {
    setStatus('Camera access denied: ' + e.message, 'var(--danger)');
  }
}

/* ── Start registration (RACE CONDITION FIXED) ── */
/* ── Start registration (100% Instant Camera Fix) ── */
async function startRegistration() {
  const empId   = document.getElementById('inpId').value.trim();
  const empName = document.getElementById('inpName').value.trim();
  const outlet  = document.getElementById('inpOutlet').value.trim();

  if (!empId || !empName) {
    toast('Employee ID and Name are required!');
    return;
  }

  // 1. කැමරාව මුලින්ම ඔන් කිරීම (සර්වර් එකට යන්න කලින් මේක වෙන නිසා කිසිම ප්‍රමාදයක් නෑ)
  await startCamera();

  currentPose = 0;
  poseStates  = POSES.map(() => 'pending');
  capturing   = false;

  ['inpId','inpName','inpOutlet'].forEach(id =>
    document.getElementById(id).disabled = true);
  document.getElementById('btnStart').disabled   = true;
  document.getElementById('btnCapture').disabled = false;
  document.getElementById('btnSkip').disabled    = false;
  document.getElementById('successBanner').style.display = 'none';

  refreshPoses();

  // 2. කැමරාව ඔන් වුණාට පස්සේ, ID එක කලින් තියෙනවද බලනවා
  try {
    const res  = await fetch(`${API}/check_id?user_id=${encodeURIComponent(empId)}`);
    const data = await res.json();
    if (data.exists) {
      if (!confirm(`ID '${empId}' is already registered. Overwrite?`)) {
          doReset();
          return;
      }
    }
  } catch(e) { 
      console.error("ID Check error", e);
  }

  // 3. අනිවාර්යයෙන්ම await භාවිතා කර දත්ත යැවීම (දත්ත මැකීම වැළැක්වීමට)
  try {
    await fetch(`${API}/reset`, { method:'POST' });
    await fetch(`${API}/set_meta`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ 
          company_id: <?php echo isset($_SESSION['company_id']) ? $_SESSION['company_id'] : 'null'; ?>,
          name: empName, 
          user_id: empId, 
          outlet: outlet 
      }),
    });
  } catch(e) {
      console.error(e);
  }
}
/* ── Capture pose ── */
async function capturePose() {
  if (capturing || currentPose >= POSES.length) return;
  capturing = true;
  document.getElementById('btnCapture').disabled = true;
  document.getElementById('btnSkip').disabled    = true;
  showSpinner(true);
  setStatus('🔄  DeepFace processing… hold still', 'var(--warning)');

  const vid    = document.getElementById('videoEl');
  const canvas = document.createElement('canvas');
  canvas.width  = vid.videoWidth  || 640;
  canvas.height = vid.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(vid, 0, 0);
  const imageData = canvas.toDataURL('image/jpeg', 0.92);

  try {
    const res  = await fetch(`${API}/capture`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ image:imageData, pose:POSES[currentPose].key }),
    });
    const data = await res.json();

    if (data.success) {
      if (data.face_boxes) faceBoxes = data.face_boxes;
      poseStates[currentPose] = 'done';
      toast(`✅ Captured: ${POSES[currentPose].key.replace(/_/g,' ').toUpperCase()}`);
      setStatus(`✅  Captured: ${POSES[currentPose].key.replace(/_/g,' ').toUpperCase()}`, 'var(--success)');
      currentPose++;
      refreshPoses();

      if (currentPose >= POSES.length) {
        await finishRegistration();
      } else {
        document.getElementById('btnCapture').disabled = false;
        document.getElementById('btnSkip').disabled    = false;
      }
    } else {
      setStatus(`⚠  ${data.message}`, 'var(--danger)');
      toast(data.message);
      document.getElementById('btnCapture').disabled = false;
      document.getElementById('btnSkip').disabled    = false;
    }
  } catch(e) {
    setStatus('Backend unreachable — is backend.py running?', 'var(--danger)');
    toast('Cannot reach Python backend!');
    document.getElementById('btnCapture').disabled = false;
    document.getElementById('btnSkip').disabled    = false;
  } finally {
    capturing = false;
    showSpinner(false);
  }
}

/* ── Skip pose ── */
async function skipPose() {
  if (currentPose >= POSES.length) return;
  const key = POSES[currentPose].key;
  poseStates[currentPose] = 'skipped';
  toast(`⏭ Skipped: ${key.replace(/_/g,' ').toUpperCase()}`);
  setStatus(`⏭  Skipped: ${key.replace(/_/g,' ').toUpperCase()}`, 'var(--warning)');
  currentPose++;
  refreshPoses();
  if (currentPose >= POSES.length) await finishRegistration();
}

/* ── Finish: call backend /save ── */
async function finishRegistration() {
  document.getElementById('btnCapture').disabled = true;
  document.getElementById('btnSkip').disabled    = true;
  setStatus('Saving profile to database…', 'var(--accent)');

  const done = poseStates.filter(s => s === 'done').length;
  if (done === 0) {
    alert('No poses captured. Cannot save profile.');
    doReset();
    return;
  }

  try {
    const res  = await fetch(`${API}/save`, { method:'POST' });
    const data = await res.json();

    if (data.success) {
      registeredCount = data.total_registered || registeredCount + 1;
      refreshBadge();

      const empName = document.getElementById('inpName').value;
      const empId   = document.getElementById('inpId').value;
      const outlet  = document.getElementById('inpOutlet').value;
      const banner  = document.getElementById('successBanner');
      banner.style.display = 'block';
      banner.innerHTML =
        `✓ REGISTRATION COMPLETE\n` +
        `Employee ID : ${empId}\n` +
        `Name        : ${empName}\n` +
        `Outlet      : ${outlet || '—'}\n` +
        `Poses saved : ${done} / ${POSES.length}`
          .split('\n').join('<br>');

      setStatus('✅  Profile saved successfully!', 'var(--success)');
      toast('Profile saved!');

      document.getElementById('btnStart').disabled = false;
    } else {
      setStatus('Save failed: ' + data.message, 'var(--danger)');
    }
  } catch(e) {
    setStatus('Save request failed — backend offline?', 'var(--danger)');
  }
}

/* ── Reset ── */
function doReset() {
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }
  stopDot();
  
  if (liveDetectInterval) clearInterval(liveDetectInterval);
  
  faceBoxes = [];
  currentPose = 0;
  poseStates  = POSES.map(() => 'pending');
  capturing   = false;

  const vid = document.getElementById('videoEl');
  vid.srcObject = null;
  vid.style.display = 'none';
  document.getElementById('idleScreen').style.display = 'flex';
  document.getElementById('successBanner').style.display = 'none';
  showSpinner(false);

  ['inpId','inpName','inpOutlet'].forEach(id => {
    const el = document.getElementById(id);
    el.disabled = false;
    el.value    = '';
  });

  document.getElementById('btnStart').disabled   = false;
  document.getElementById('btnCapture').disabled = true;
  document.getElementById('btnSkip').disabled    = true;
  document.getElementById('instrText').textContent   = 'Camera feed will appear after START';
  document.getElementById('counterText').textContent = '0 / 5';

  refreshPoses();
  setStatus('Enter employee details and click START', '');

  fetch(`${API}/reset`, { method:'POST' }).catch(() => {});
}

/* ── Keyboard shortcuts ── */
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  if (e.key === 'c' || e.key === 'C') capturePose();
  if (e.key === 's' || e.key === 'S') skipPose();
  if (e.key === 'r' || e.key === 'R') doReset();
});

/* ── Init badge from backend ── */
(async () => {
  try {
    const res  = await fetch(`${API}/health`);
    const data = await res.json();
    registeredCount = data.registered_count || 0;
    refreshBadge();
  } catch(e) {}
})();

refreshPoses();
</script>
</body>
</html>