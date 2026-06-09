import cv2
from deepface import DeepFace
import pickle
import os
import numpy as np
import threading
import queue
import time
import urllib.request
import requests
from collections import deque

# ── Attendance integration ─────────────────────────────────────────────────────
from event_logger import AttendanceEventLogger
event_logger = AttendanceEventLogger(backend_url="http://localhost:5000")

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG — i5 12th-gen CPU සඳහා උපරිම Accuracy ලැබෙන සේ සකසා ඇත
# ═══════════════════════════════════════════════════════════════════════════════
DB_FILE          = "deepface_database.pkl"
YUNET_MODEL      = "face_detection_yunet_2023mar.onnx"
YUNET_URL        = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

# [UPGRADED] 720p Resolution - ඈත තියෙන මුහුණු පැහැදිලිව හඳුනාගැනීමට
FRAME_W, FRAME_H = 640, 480

# --- Accuracy knobs ---
COSINE_THRESHOLD  = 0.35   
DETECT_CONF       = 0.55   # [FIXED] 0.75 සිට 0.55 දක්වා අඩු කරන්න. (එවිට දුර නිසා ඇතිවන දුර්වල මුහුණු ද අසුකර ගනී)
MIN_FACE_PX       = 25     # [FIXED] 60 සිට 25 දක්වා අඩු කරන්න. (දුර සිටින විට මූණ කුඩාවට පික්සල් 25-30ක් වුවද අත්නොහරියි)
SMOOTH_WINDOW     = 7       # Slightly wider smoothing window

# --- Performance knobs (i5 Balanced Zone) ---
RECOG_EVERY_N     = 5      # [OPTIMIZED] හැම Frame 5කටම වරක් AI පරීක්ෂා කරයි (Accuracy වැඩි වේ)
TRACK_RADIUS      = 120    # [ADJUSTED] Resolution එක වැඩි නිසා Radius එක 120 දක්වා වැඩි කරන ලදී
STALE_AFTER       = 60     # frames before a vanished face track is evicted
NUM_WORKERS       = 3      # [OPTIMIZED] Threads 3ක් භාවිතයෙන් CPU එක හිර නොවී වේගවත් වැඩ කරයි

# ── Attendance logging threshold ───────────────────────────────────────────────
LOG_CONF_THRESHOLD = 0.2

# ── Use all physical cores OpenCV is allowed to see ──────────────────────────
cv2.setNumThreads(0)
os.environ["OMP_NUM_THREADS"]      = "8"
os.environ["OPENBLAS_NUM_THREADS"] = "8"

# ═══════════════════════════════════════════════════════════════════════════════
#  DOWNLOAD YUNET MODEL
# ═══════════════════════════════════════════════════════════════════════════════
if not os.path.exists(YUNET_MODEL):
    print("[INFO] Downloading YuNet model (~350 KB)...")
    urllib.request.urlretrieve(YUNET_URL, YUNET_MODEL)
    print("[INFO] Done.")

# ═══════════════════════════════════════════════════════════════════════════════
#  LOAD DATABASE
# ═══════════════════════════════════════════════════════════════════════════════
if not os.path.exists(DB_FILE):
    print("[CRITICAL] Database missing. Run manual_data_collection.py first.")
    exit()

with open(DB_FILE, "rb") as f:
    database = pickle.load(f)

raw_embeddings = []
known_profiles = []
for profile in database.values():
    for emb in profile["embeddings"]:
        raw_embeddings.append(emb)
        known_profiles.append(profile)

if len(raw_embeddings) == 0:
    print("[WARNING] Database is completely empty! Please register someone first.")
    emb_matrix_normed = np.empty((0, 512), dtype=np.float32)
else:
    # Pre-normalise all embeddings once
    emb_matrix        = np.array(raw_embeddings, dtype=np.float32)
    norms             = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    emb_matrix_normed = emb_matrix / norms      # shape: (N, 512)

print(f"[OK] Loaded {len(database)} people  |  {len(raw_embeddings)} embeddings")

# ═══════════════════════════════════════════════════════════════════════════════
#  PRE-WARM DeepFace model
# ═══════════════════════════════════════════════════════════════════════════════
print("[INFO] Pre-warming Facenet512 model (one-time, ~3 s)...")
_dummy = np.zeros((160, 160, 3), dtype=np.uint8)
try:
    DeepFace.represent(
        img_path=_dummy,
        model_name="Facenet512",
        detector_backend="skip",
        enforce_detection=False,
    )
except Exception:
    pass
print("[INFO] Model warm-up complete.")

# ═══════════════════════════════════════════════════════════════════════════════
#  YUNET DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════
detector = cv2.FaceDetectorYN.create(
    YUNET_MODEL, "", (FRAME_W, FRAME_H),
    score_threshold=DETECT_CONF,
    nms_threshold=0.30,
    top_k=5000,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  FAST VECTORISED COSINE MATCH
# ═══════════════════════════════════════════════════════════════════════════════
def match_embedding(query_emb: np.ndarray):
    if len(emb_matrix_normed) == 0:
        return "Unknown Person", "Access Denied", 0.0, (0, 0, 220)
        
    q = query_emb.astype(np.float32)
    norm = np.linalg.norm(q)
    if norm == 0:
        return "Unknown Person", "Access Denied", None, 0.0, (0, 0, 220)
    q /= norm
    sims      = emb_matrix_normed @ q
    distances = 1.0 - sims
    best_idx  = int(np.argmin(distances))
    best_dist = float(distances[best_idx])

    if best_dist <= COSINE_THRESHOLD:
        p      = known_profiles[best_idx]
        conf   = max(0.0, min(1.0, 1.0 - best_dist / COSINE_THRESHOLD))
        emp_id = p.get("emp_id") or p.get("id") or p["name"].lower().replace(" ", "_")
        return p["name"], p.get("dept", "Verified"), emp_id, conf, (0, 220, 0)
    return "Unknown Person", "Access Denied", None, 0.0, (0, 0, 220)

# ═══════════════════════════════════════════════════════════════════════════════
#  BACKGROUND RECOGNITION WORKERS (With Face Alignment)
# ═══════════════════════════════════════════════════════════════════════════════
recog_queue  = queue.Queue(maxsize=6)
result_lock  = threading.Lock()
result_store = {}   

def recognition_worker():
    while True:
        item = recog_queue.get()
        if item is None:
            break

        # [NEW] roi_lms (Landmarks) ද දැන් Queue එක හරහා Worker ට ලැබේ
        face_key, cx, cy, roi_bgr, roi_lms = item

        try:
            # ─── [NEW] FACE ALIGNMENT (මුහුණ කෙලින් කිරීම) ───
            # ඇස් දෙකෙහි පිහිටීම අනුව මුහුණ ඇලවී ඇති කෝණය (Angle) ගණනය කරයි
            left_eye = roi_lms[0]
            right_eye = roi_lms[1]
            dY = right_eye[1] - left_eye[1]
            dX = right_eye[0] - left_eye[0]
            angle = np.degrees(np.arctan2(dY, dX))
            
            # ඇස් දෙක මැද ලක්ෂ්‍යය වටා රූපය කැරකවීමට Matrix එක ලබා ගනී
            eye_center = (float((left_eye[0] + right_eye[0]) / 2), float((left_eye[1] + right_eye[1]) / 2))
            M = cv2.getRotationMatrix2D(eye_center, angle, 1.0)
            
            # රූපය Rotate කර මුහුණ තිරස් අතට කෙලින් කරගනී (Using INTER_CUBIC for high quality)
            h, w = roi_bgr.shape[:2]
            rotated_roi = cv2.warpAffine(roi_bgr, M, (w, h), flags=cv2.INTER_CUBIC)

            # [UPGRADED] INTER_LINEAR වෙනුවට INTER_CUBIC භාවිතයෙන් Sharpness එක වැඩි කරයි
            roi_resized = cv2.resize(rotated_roi, (160, 160), interpolation=cv2.INTER_CUBIC)
            rgb_roi     = cv2.cvtColor(roi_resized, cv2.COLOR_BGR2RGB)

            resp = DeepFace.represent(
                img_path=rgb_roi,
                model_name="Facenet512",
                detector_backend="skip",
                enforce_detection=False,
            )
            emb = np.array(resp[0]["embedding"], dtype=np.float32)
            name, dept, emp_id, conf, color = match_embedding(emb)

        except Exception:
            name, dept, emp_id, conf, color = "Unknown Person", "Access Denied", None, 0.0, (0, 0, 220)

        with result_lock:
            existing = result_store.get(face_key, {})
            history  = existing.get("history", deque(maxlen=SMOOTH_WINDOW))

            if name != "Unknown Person":
                history.append(conf)
                smooth_conf = float(np.mean(history))
            else:
                if len(history) > 0:
                    history.append(0.0)
                smooth_conf = float(np.mean(history)) if history else 0.0
                if smooth_conf < 0.15:
                    name   = "Unknown Person"
                    dept   = "Access Denied"
                    emp_id = None
                    color  = (0, 0, 220)
                else:
                    prev   = result_store.get(face_key, {})
                    name   = prev.get("name", "Unknown Person")
                    dept   = prev.get("dept", "Access Denied")
                    emp_id = prev.get("emp_id")
                    color  = prev.get("color", (0, 0, 220))

            result_store[face_key] = {
                "name":       name,
                "dept":       dept,
                "emp_id":     emp_id,
                "conf":       smooth_conf,
                "color":      color,
                "cx":         cx,
                "cy":         cy,
                "history":    history,
                "last_frame": result_store.get(face_key, {}).get("last_frame", 0),
                "roi_bgr":    roi_bgr,
            }

            already_logged = existing.get("logged_event", False)
            if (
                name != "Unknown Person"
                and emp_id is not None
                and smooth_conf >= LOG_CONF_THRESHOLD
                and not already_logged
            ):
                result_store[face_key]["logged_event"] = True
                threading.Thread(
                    target=_fire_attendance_event,
                    args=(emp_id, name, dept, smooth_conf, roi_bgr.copy()),
                    daemon=True
                ).start()

        recog_queue.task_done()


def _fire_attendance_event(emp_id, name, dept, conf, roi_bgr):
    try:
        event_logger.log_event(
            employee_id=emp_id,
            name=name,
            dept=dept,
            confidence=conf,
            frame_bgr=roi_bgr,
            event_type='auto',
        )
    except Exception as e:
        print(f"[ATTENDANCE] Event send error: {e}")


# Spawn NUM_WORKERS threads
workers = []
for _ in range(NUM_WORKERS):
    t = threading.Thread(target=recognition_worker, daemon=True)
    t.start()
    workers.append(t)

# ═══════════════════════════════════════════════════════════════════════════════
#  FLASK DASHBOARD — Streaming Config (ලැග් වීම වැළැක්වීමට මුල් අගයන්ම තබා ඇත)
# ═══════════════════════════════════════════════════════════════════════════════
FLASK_URL      = "http://localhost:5000"
STREAM_EVERY_N = 4      
STREAM_QUALITY = 45     
STREAM_W       = 480   
STREAM_H       = 300    

stream_queue   = deque(maxlen=1)
_sess          = requests.Session()   

def flask_stream_worker():
    while True:
        if not stream_queue:
            time.sleep(0.005)
            continue
            
        data = stream_queue.popleft()
        if data is None:
            break
            
        try:
            _sess.post(
                f"{FLASK_URL}/api/video_frame",
                data=data,
                headers={"Content-Type": "application/octet-stream"},
                timeout=0.1, 
            )
        except Exception:
            pass

stream_thread = threading.Thread(target=flask_stream_worker, daemon=True)
stream_thread.start()
print(f"[STREAM] Pushing frames → {FLASK_URL}  (WebSocket → dashboard)")

# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER — nearest cached track
# ═══════════════════════════════════════════════════════════════════════════════
def find_cached_result(cx, cy):
    best_key, best_dist = None, TRACK_RADIUS
    for k, v in result_store.items():
        d = abs(cx - v["cx"]) + abs(cy - v["cy"])
        if d < best_dist:
            best_dist, best_key = d, k
    return best_key


# ═══════════════════════════════════════════════════════════════════════════════
#  ZERO-LAG CAMERA STREAM THREAD 
# ═══════════════════════════════════════════════════════════════════════════════
class CameraStream:
    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
        self.grabbed, self.frame = self.stream.read()
        self.stopped = False
        self.lock = threading.Lock()

    def start(self):
        t = threading.Thread(target=self.update, daemon=True)
        t.start()
        return self

    def update(self):
        while not self.stopped:
            grabbed, frame = self.stream.read()
            with self.lock:
                self.grabbed = grabbed
                self.frame = frame

    def read(self):
        with self.lock:
            if self.frame is not None:
                return self.grabbed, self.frame.copy()
            return self.grabbed, None

    def stop(self):
        self.stopped = True
        self.stream.release()

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════════
engine_active = True
current_source = "0"

def parse_source(src):
    return int(src) if str(src).isdigit() else src

cam = CameraStream(parse_source(current_source)).start()
time.sleep(1.0) 

frame_count  = 0
face_counter = 0
fps_times    = deque(maxlen=30)
last_settings_check = time.time()

print("Recognition dashboard live — press 'q' to quit")
print(f"[ATTENDANCE] Logging to {FLASK_URL}  |  conf threshold: {LOG_CONF_THRESHOLD:.0%}")

_last_reset_hour = -1
detector_size_set = False

while True:
    # 1. Check Dashboard Settings Every 2 Seconds
    if time.time() - last_settings_check > 2.0:
        try:
            resp = requests.get(f"{FLASK_URL}/api/engine_settings", timeout=1).json()
            new_active = resp.get("is_active", True)
            new_source = resp.get("camera_source", "0")

            if new_active != engine_active or new_source != current_source:
                print(f"[ENGINE] Settings changed -> Active: {new_active}, Source: {new_source}")
                engine_active = new_active
                current_source = new_source

                # Release current camera lock
                cam.stop()
                
                if engine_active:
                    time.sleep(1.0) # Give OS time to fully release hardware
                    cam = CameraStream(parse_source(current_source)).start()
                    detector_size_set = False # Needs reset for new camera resolution
                    
        except Exception:
            pass # Backend might be temporarily offline
        last_settings_check = time.time()

    # 2. If Engine is OFF, send Standby Screen to Dashboard
    if not engine_active:
        standby = np.zeros((STREAM_H, STREAM_W, 3), dtype=np.uint8)
        cv2.putText(standby, "AI ENGINE OFFLINE", (STREAM_W//2 - 90, STREAM_H//2 - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(standby, "Camera Released. Use Dashboard to turn ON.", (STREAM_W//2 - 150, STREAM_H//2 + 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        _, jpeg = cv2.imencode('.jpg', standby, [cv2.IMWRITE_JPEG_QUALITY, 50])
        stream_queue.append(jpeg.tobytes())
        
        time.sleep(0.5)
        continue

    # 3. Normal camera reading (Engine is ON)
    ret, frame = cam.read()
    if not ret or frame is None:
        time.sleep(0.01)
        continue

    # [SAFETY] කැමරාව 720p support නොකර වෙනත් resolution එකක් ලබා දුන්නද කේතය crash වීම වළක්වයි
    if not detector_size_set:
        h_actual, w_actual = frame.shape[:2]
        detector.setInputSize((w_actual, h_actual))
        detector_size_set = True

    t0 = time.perf_counter()
    
    # --- මින් පහළට ඇති ඔබගේ පැරණි කේතය එලෙසම තබන්න (frame_count += 1, ආදිය) ---
    frame_count += 1
    frame = cv2.flip(frame, 1)

    # ── Daily reset at 9 AM ───────────────────────────────────────────────────
    current_hour = time.localtime().tm_hour
    if current_hour == 9 and _last_reset_hour != 9:
        event_logger.reset_daily_state()
        with result_lock:
            for v in result_store.values():
                v["logged_event"] = False
        _last_reset_hour = 9
        print("[ATTENDANCE] Daily state reset at 9 AM.")
    elif current_hour != 9:
        _last_reset_hour = current_hour

    # ── YuNet Detection ───────────────────────────────────────────────────────
    _, faces = detector.detect(frame)

    if faces is not None:
        for face in faces:
            x,  y  = int(face[0]), int(face[1])
            fw, fh = int(face[2]), int(face[3])
            det_conf = float(face[14])

            if fw < MIN_FACE_PX or fh < MIN_FACE_PX:
                continue

            h_actual, w_actual = frame.shape[:2]
            x1 = max(0, x);          y1 = max(0, y)
            x2 = min(w_actual, x+fw); y2 = min(h_actual, y+fh)
            cx, cy = (x1+x2)//2,     (y1+y2)//2

            with result_lock:
                cached_key = find_cached_result(cx, cy)

            if cached_key is None:
                face_counter += 1
                cached_key = f"face_{face_counter}"

            with result_lock:
                if cached_key in result_store:
                    result_store[cached_key]["cx"]         = cx
                    result_store[cached_key]["cy"]         = cy
                    result_store[cached_key]["last_frame"] = frame_count

            # Landmarks කලින්ම ලබා ගනී (For Alignment)
            lms = face[4:14].reshape(5, 2)

            if frame_count % RECOG_EVERY_N == 0:
                # [ADJUSTED] Padding එක මඳක් වැඩි කරන ලදී (මුහුණ කැරකැවීමේදී Black corners කැපී යාමට)
                pad  = max(10, int(fw * 0.12))
                rx1  = max(0, x1 - pad);       ry1 = max(0, y1 - pad)
                rx2  = min(w_actual, x2 + pad); ry2 = min(h_actual, y2 + pad)
                roi  = frame[ry1:ry2, rx1:rx2]
                
                if roi.size > 0:
                    # Landmarks ටික Crop කරගන්නා ROI එකට සාපේක්ෂව (Relative) වෙනස් කරයි
                    roi_lms = lms.copy()
                    roi_lms[:, 0] -= rx1
                    roi_lms[:, 1] -= ry1
                    
                    try:
                        # [UPDATED] roi_lms ද Worker thread එකට ලබාදේ
                        recog_queue.put_nowait((cached_key, cx, cy, roi.copy(), roi_lms))
                    except queue.Full:
                        pass

            with result_lock:
                res = result_store.get(cached_key)

            if res:
                name  = res["name"]
                dept  = res["dept"]
                conf  = res["conf"]
                color = res["color"]
                label = f"{name}  |  {dept}"
                if conf > 0:
                    label += f"  ({conf:.0%})"
                if res.get("logged_event"):
                    label += "  ✓"
            else:
                color = (0, 165, 255)
                label = "Identifying..."

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            bar_y1 = min(y2, h_actual - 36)
            cv2.rectangle(frame, (x1, bar_y1), (x2, bar_y1 + 35), color, cv2.FILLED)
            cv2.putText(frame, label, (x1 + 6, bar_y1 + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            cv2.putText(frame, f"{det_conf:.0%}", (x2 - 42, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1, cv2.LINE_AA)

            for lx, ly in lms:
                cv2.circle(frame, (int(lx), int(ly)), 3, (0, 200, 255), -1)

    # ── Evict stale tracks ────────────────────────────────────────────────────
    with result_lock:
        stale = [k for k, v in result_store.items()
                 if frame_count - v.get("last_frame", 0) > STALE_AFTER]
        for k in stale:
            del result_store[k]

    # ── HUD overlay ───────────────────────────────────────────────────────────
    fps_times.append(time.perf_counter() - t0)
    fps = 1.0 / (sum(fps_times) / len(fps_times)) if fps_times else 0

    n_faces  = 0 if faces is None else sum(
        1 for f in faces if int(f[2]) >= MIN_FACE_PX and int(f[3]) >= MIN_FACE_PX
    )
    queue_sz = recog_queue.qsize()

    logger_status = event_logger.get_status()
    att_queue     = logger_status.get("queue_size", 0)
    clocked_in    = len(logger_status.get("clocked_in_today", []))

    cv2.putText(frame,
                f"Faces: {n_faces}   FPS: {fps:.0f}   Queue: {queue_sz}   Workers: {NUM_WORKERS}",
                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 200, 255), 2, cv2.LINE_AA)
    cv2.putText(frame,
                f"YuNet + Facenet512 | Aligned Mode | threshold: {COSINE_THRESHOLD}",
                (15, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.putText(frame,
                f"Attendance: {clocked_in} clocked in today  |  pending: {att_queue}",
                (15, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 220, 120), 1, cv2.LINE_AA)

    # ── Push to Flask dashboard (Downsampled to original size for Zero-Lag) ──
    if frame_count % STREAM_EVERY_N == 0:
        small = cv2.resize(frame, (STREAM_W, STREAM_H), interpolation=cv2.INTER_LINEAR)
        _, jpeg = cv2.imencode('.jpg', small, [cv2.IMWRITE_JPEG_QUALITY, STREAM_QUALITY])
        data = jpeg.tobytes()
        stream_queue.append(data)

    cv2.imshow("Multi-Face Live Recognition Dashboard", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ── Shutdown ──────────────────────────────────────────────────────────────────
for _ in workers:
    recog_queue.put(None)
for t in workers:
    t.join()
    
stream_queue.append(None)
stream_thread.join(timeout=2)

cam.stop() 
cv2.destroyAllWindows()
print("[INFO] Closed.")