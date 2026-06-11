import cv2
from deepface import DeepFace
import pickle
import os
import numpy as np
import threading
import queue
import time
import urllib.request
from collections import deque
from event_logger import AttendanceEventLogger

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG  — tuned for i5 12th-gen CPU-only
# ═══════════════════════════════════════════════════════════════════════════════
DB_FILE          = "deepface_database.pkl"
YUNET_MODEL      = "face_detection_yunet_2023mar.onnx"
YUNET_URL        = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
FRAME_W, FRAME_H = 640, 480

# --- Accuracy knobs ---
COSINE_THRESHOLD  = 0.25   # Tightened from 0.30 → fewer false positives
DETECT_CONF       = 0.75   # Raised from 0.70 → ignore weak detections
MIN_FACE_PX       = 60     # NEW: skip faces smaller than 60×60 px (blurry/far)
SMOOTH_WINDOW     = 10     # Slightly wider smoothing window

# --- Performance knobs (CPU-only) ---
RECOG_EVERY_N     = 10     # Raised from 4 → run DeepFace every 10 frames
TRACK_RADIUS      = 90     # px — how far a face can move and still match cache
STALE_AFTER       = 60     # frames before a vanished face track is evicted
NUM_WORKERS       = 2      # NEW: two recognition threads = use both P-cores

# ── Use all physical cores OpenCV is allowed to see ──────────────────────────
# i5-12th-gen has P-cores and E-cores; let numpy/OpenCV use them
cv2.setNumThreads(0)        # 0 = auto (uses all logical cores)
os.environ["OMP_NUM_THREADS"]      = "8"   # adjust to your core count
os.environ["OPENBLAS_NUM_THREADS"] = "8"

# ═══════════════════════════════════════════════════════════════════════════════
#  ATTENDANCE EVENT LOGGER INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════
event_logger = AttendanceEventLogger(backend_url="http://localhost:5000")
print("[OK] Event logger initialized - sending events to http://localhost:5000")

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

# Pre-normalise all embeddings once — matching becomes a single matmul
emb_matrix        = np.array(raw_embeddings, dtype=np.float32)
norms             = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
emb_matrix_normed = emb_matrix / norms      # shape: (N, 512)

print(f"[OK] Loaded {len(database)} people  |  {len(raw_embeddings)} embeddings")

# ═══════════════════════════════════════════════════════════════════════════════
#  PRE-WARM DeepFace model — load weights once, not on first detection
#  This eliminates the first-frame 2-second stall.
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
    """Returns (name, dept, confidence, color) for the best database match."""
    q = query_emb.astype(np.float32)
    norm = np.linalg.norm(q)
    if norm == 0:
        return "Unknown Person", "Access Denied", 0.0, (0, 0, 220)
    q /= norm
    sims      = emb_matrix_normed @ q          # (N,) cosine similarities
    distances = 1.0 - sims                     # (N,) cosine distances
    best_idx  = int(np.argmin(distances))
    best_dist = float(distances[best_idx])

    if best_dist <= COSINE_THRESHOLD:
        p    = known_profiles[best_idx]
        conf = max(0.0, min(1.0, 1.0 - best_dist / COSINE_THRESHOLD))
        return p["name"], p.get("dept", "Verified"), conf, (0, 220, 0)
    return "Unknown Person", "Access Denied", 0.0, (0, 0, 220)

# ═══════════════════════════════════════════════════════════════════════════════
#  BACKGROUND RECOGNITION WORKERS  (NUM_WORKERS threads)
#  Two threads = both recognition tasks run in parallel on P-cores.
# ═══════════════════════════════════════════════════════════════════════════════
recog_queue  = queue.Queue(maxsize=6)
result_lock  = threading.Lock()
result_store = {}   # face_key → {name, dept, conf, color, cx, cy, last_frame, history}

def recognition_worker():
    while True:
        item = recog_queue.get()
        if item is None:
            break

        face_key, cx, cy, roi_bgr = item

        try:
            # Resize crop to exactly what Facenet512 needs — avoids internal resize overhead
            roi_resized = cv2.resize(roi_bgr, (160, 160), interpolation=cv2.INTER_LINEAR)
            rgb_roi = cv2.cvtColor(roi_resized, cv2.COLOR_BGR2RGB)

            resp = DeepFace.represent(
                img_path=rgb_roi,
                model_name="Facenet512",
                detector_backend="skip",
                enforce_detection=False,
            )
            emb = np.array(resp[0]["embedding"], dtype=np.float32)
            name, dept, conf, color = match_embedding(emb)

        except Exception as e:
            name, dept, conf, color = "Unknown Person", "Access Denied", 0.0, (0, 0, 220)

        with result_lock:
            existing = result_store.get(face_key, {})
            history  = existing.get("history", deque(maxlen=SMOOTH_WINDOW))

            if name != "Unknown Person":
                history.append(conf)
                smooth_conf = float(np.mean(history))
            else:
                # FIX: Don't immediately reset — decay slowly so a single bad
                # frame doesn't wipe a confirmed identity
                if len(history) > 0:
                    history.append(0.0)          # penalise but don't clear
                smooth_conf = float(np.mean(history)) if history else 0.0
                if smooth_conf < 0.15:           # only flip to Unknown below threshold
                    name  = "Unknown Person"
                    dept  = "Access Denied"
                    color = (0, 0, 220)
                else:                            # still confident enough → keep last ID
                    prev  = result_store.get(face_key, {})
                    name  = prev.get("name", "Unknown Person")
                    dept  = prev.get("dept", "Access Denied")
                    color = prev.get("color", (0, 0, 220))

            result_store[face_key] = {
                "name": name, "dept": dept,
                "conf": smooth_conf, "color": color,
                "cx": cx, "cy": cy,
                "history": history,
                "last_frame": result_store.get(face_key, {}).get("last_frame", 0),
            }

            # ── NEW: LOG ATTENDANCE EVENT ──────────────────────────────────────
            # Send to attendance backend if person is recognized
            if name != "Unknown Person":
                event_logger.log_event(
                    employee_id=face_key,
                    name=name,
                    dept=dept,
                    confidence=smooth_conf,
                    frame_bgr=roi_bgr,
                    event_type='auto'  # auto-detects clock-in vs clock-out
                )

        recog_queue.task_done()

# Spawn NUM_WORKERS threads
workers = []
for _ in range(NUM_WORKERS):
    t = threading.Thread(target=recognition_worker, daemon=True)
    t.start()
    workers.append(t)

# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER — O(n) nearest cached track, but n is tiny (≤ 5 faces)
# ═══════════════════════════════════════════════════════════════════════════════
def find_cached_result(cx, cy):
    best_key, best_dist = None, TRACK_RADIUS
    for k, v in result_store.items():
        d = abs(cx - v["cx"]) + abs(cy - v["cy"])   # Manhattan — faster than hypot
        if d < best_dist:
            best_dist, best_key = d, k
    return best_key

# ═══════════════════════════════════════════════════════════════════════════════
#  CAMERA
# ═══════════════════════════════════════════════════════════════════════════════
cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # NEW: reduce capture buffer → fresher frames

frame_count  = 0
face_counter = 0
fps_times    = deque(maxlen=30)

print("Recognition dashboard live — press 'q' to quit")

while True:
    ret, frame = cam.read()
    if not ret:
        print("[ERROR] Camera lost.")
        break

    t0 = time.perf_counter()
    frame_count += 1
    frame = cv2.flip(frame, 1)

    # ── YuNet Detection ───────────────────────────────────────────────────────
    _, faces = detector.detect(frame)

    if faces is not None:
        for face in faces:
            x,  y  = int(face[0]), int(face[1])
            fw, fh = int(face[2]), int(face[3])
            det_conf = float(face[14])

            # ── NEW: skip tiny / far-away faces ──────────────────────────────
            if fw < MIN_FACE_PX or fh < MIN_FACE_PX:
                continue

            x1 = max(0, x);         y1 = max(0, y)
            x2 = min(FRAME_W, x+fw); y2 = min(FRAME_H, y+fh)
            cx, cy = (x1+x2)//2,    (y1+y2)//2

            # ── Find or create track ──────────────────────────────────────────
            with result_lock:
                cached_key = find_cached_result(cx, cy)

            if cached_key is None:
                face_counter += 1
                cached_key = f"face_{face_counter}"

            # Update centroid + last_frame every frame (cheap)
            with result_lock:
                if cached_key in result_store:
                    result_store[cached_key]["cx"]         = cx
                    result_store[cached_key]["cy"]         = cy
                    result_store[cached_key]["last_frame"] = frame_count

            # ── Submit crop every RECOG_EVERY_N frames ────────────────────────
            if frame_count % RECOG_EVERY_N == 0:
                pad  = max(10, int(fw * 0.12))      # slightly smaller pad
                rx1  = max(0, x1 - pad);       ry1 = max(0, y1 - pad)
                rx2  = min(FRAME_W, x2 + pad); ry2 = min(FRAME_H, y2 + pad)
                roi  = frame[ry1:ry2, rx1:rx2]
                if roi.size > 0:
                    try:
                        recog_queue.put_nowait((cached_key, cx, cy, roi.copy()))
                    except queue.Full:
                        pass   # never stall the display loop

            # ── Fetch cached label ────────────────────────────────────────────
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
            else:
                color = (0, 165, 255)
                label = "Identifying..."

            # ── Draw bounding box ─────────────────────────────────────────────
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Info bar — clamp so it never goes off the bottom edge
            bar_y1 = min(y2, FRAME_H - 36)
            cv2.rectangle(frame, (x1, bar_y1), (x2, bar_y1 + 35), color, cv2.FILLED)
            cv2.putText(frame, label, (x1 + 6, bar_y1 + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            # Detection confidence (top-right corner of box)
            cv2.putText(frame, f"{det_conf:.0%}", (x2 - 42, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1, cv2.LINE_AA)

            # 5 facial landmarks
            lms = face[4:14].reshape(5, 2)
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

    n_faces   = 0 if faces is None else sum(
        1 for f in faces if int(f[2]) >= MIN_FACE_PX and int(f[3]) >= MIN_FACE_PX
    )
    queue_sz  = recog_queue.qsize()

    cv2.putText(frame,
                f"Faces: {n_faces}   FPS: {fps:.0f}   Queue: {queue_sz}   Workers: {NUM_WORKERS}",
                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 200, 255), 2, cv2.LINE_AA)
    cv2.putText(frame,
                f"YuNet + Facenet512 | threshold: {COSINE_THRESHOLD} | min-face: {MIN_FACE_PX}px",
                (15, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1, cv2.LINE_AA)

    cv2.imshow("Multi-Face Live Recognition Dashboard", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ── Shutdown ──────────────────────────────────────────────────────────────────
for _ in workers:
    recog_queue.put(None)
for t in workers:
    t.join()
cam.release()
cv2.destroyAllWindows()
print("[INFO] Closed.")
