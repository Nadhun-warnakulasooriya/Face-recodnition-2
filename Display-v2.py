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

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
DB_FILE          = "deepface_database.pkl"
YUNET_MODEL      = "face_detection_yunet_2023mar.onnx"
YUNET_URL        = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
FRAME_W, FRAME_H = 640, 480

COSINE_THRESHOLD  = 0.30   # Lower = stricter match. Range: 0.20–0.40
DETECT_CONF       = 0.70   # YuNet minimum confidence to draw a box
RECOG_EVERY_N     = 4      # Run DeepFace every N frames (raise for more FPS)
TRACK_RADIUS      = 80     # px — how far a face can move and still match cached result
SMOOTH_WINDOW     = 8      # frames to average confidence over
STALE_AFTER       = 45     # frames — drop cached result if face disappears

# ═══════════════════════════════════════════════════════════════════════════════
#  DOWNLOAD YUNET MODEL
# ═══════════════════════════════════════════════════════════════════════════════
if not os.path.exists(YUNET_MODEL):
    print("[INFO] Downloading YuNet model (~350KB)...")
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

# Pre-normalise all embeddings once so matching is just a dot product
emb_matrix = np.array(raw_embeddings, dtype=np.float32)
emb_norms  = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
emb_matrix_normed = emb_matrix / emb_norms          # shape: (N, 512)

print(f"[OK] Loaded {len(database)} people  |  {len(raw_embeddings)} embeddings")

# ═══════════════════════════════════════════════════════════════════════════════
#  YUNET DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════
detector = cv2.FaceDetectorYN.create(
    YUNET_MODEL, "", (FRAME_W, FRAME_H),
    score_threshold = DETECT_CONF,
    nms_threshold   = 0.30,
    top_k           = 5000,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  FAST VECTORISED COSINE DISTANCE
# ═══════════════════════════════════════════════════════════════════════════════
def match_embedding(query_emb: np.ndarray):
    """Returns (name, dept, confidence, color) for the best database match."""
    q = query_emb.astype(np.float32)
    q /= np.linalg.norm(q)                          # normalise query
    sims      = emb_matrix_normed @ q               # dot product = cosine similarity
    distances = 1.0 - sims                          # cosine distance
    best_idx  = int(np.argmin(distances))
    best_dist = float(distances[best_idx])

    if best_dist <= COSINE_THRESHOLD:
        p    = known_profiles[best_idx]
        conf = max(0.0, min(1.0, 1.0 - best_dist / COSINE_THRESHOLD))
        return p["name"], p.get("dept", "Verified"), conf, (0, 220, 0)
    return "Unknown Person", "Access Denied", 0.0, (0, 0, 220)

# ═══════════════════════════════════════════════════════════════════════════════
#  BACKGROUND RECOGNITION THREAD
#  The display loop runs at full camera FPS.
#  DeepFace runs in a separate thread so it never blocks the display.
# ═══════════════════════════════════════════════════════════════════════════════
recog_queue   = queue.Queue(maxsize=4)   # face crops waiting to be processed
result_lock   = threading.Lock()
result_store  = {}   # face_key -> {name, dept, conf, color, cx, cy, last_frame}

def recognition_worker():
    while True:
        item = recog_queue.get()
        if item is None:
            break

        face_key, cx, cy, roi_bgr = item

        try:
            rgb_roi = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
            resp    = DeepFace.represent(
                img_path         = rgb_roi,
                model_name       = "Facenet512",
                detector_backend = "skip",      # We already cropped the face
                enforce_detection= False,
            )
            emb = np.array(resp[0]["embedding"], dtype=np.float32)
            name, dept, conf, color = match_embedding(emb)

        except Exception:
            name, dept, conf, color = "Unknown Person", "Access Denied", 0.0, (0, 0, 220)

        with result_lock:
            existing = result_store.get(face_key, {})
            # Temporal smoothing: average confidence over last SMOOTH_WINDOW readings
            history = existing.get("history", deque(maxlen=SMOOTH_WINDOW))
            if name != "Unknown Person":
                history.append(conf)
                smooth_conf = float(np.mean(history))
            else:
                history.clear()
                smooth_conf = 0.0

            result_store[face_key] = {
                "name": name, "dept": dept,
                "conf": smooth_conf, "color": color,
                "cx": cx, "cy": cy,
                "history": history,
                "last_frame": result_store.get(face_key, {}).get("last_frame", 0),
            }

        recog_queue.task_done()

worker = threading.Thread(target=recognition_worker, daemon=True)
worker.start()

# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER — find cached result closest to this face center
# ═══════════════════════════════════════════════════════════════════════════════
def find_cached_result(cx, cy):
    best_key, best_dist = None, TRACK_RADIUS
    for k, v in result_store.items():
        d = np.hypot(cx - v["cx"], cy - v["cy"])
        if d < best_dist:
            best_dist, best_key = d, k
    return best_key

# ═══════════════════════════════════════════════════════════════════════════════
#  CAMERA
# ═══════════════════════════════════════════════════════════════════════════════
cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

frame_count  = 0
face_counter = 0          # unique key per new face track
fps_counter  = deque(maxlen=30)

print("Launching recognition dashboard...  press 'q' to quit")

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

    active_keys = set()

    if faces is not None:
        for face in faces:
            x,  y  = int(face[0]), int(face[1])
            fw, fh = int(face[2]), int(face[3])
            det_conf = float(face[14])

            x1 = max(0, x);        y1 = max(0, y)
            x2 = min(FRAME_W, x+fw); y2 = min(FRAME_H, y+fh)
            cx, cy = (x1+x2)//2, (y1+y2)//2

            # ── Find or create a track for this face ──────────────────────────
            with result_lock:
                cached_key = find_cached_result(cx, cy)

            if cached_key is None:
                face_counter += 1
                cached_key = f"face_{face_counter}"

            active_keys.add(cached_key)

            # Update centroid in store so tracking stays current
            with result_lock:
                if cached_key in result_store:
                    result_store[cached_key]["cx"] = cx
                    result_store[cached_key]["cy"] = cy
                    result_store[cached_key]["last_frame"] = frame_count

            # ── Submit crop for recognition every N frames ─────────────────────
            if frame_count % RECOG_EVERY_N == 0:
                pad  = max(10, int(fw * 0.15))
                rx1  = max(0, x1 - pad);      ry1 = max(0, y1 - pad)
                rx2  = min(FRAME_W, x2 + pad); ry2 = min(FRAME_H, y2 + pad)
                roi  = frame[ry1:ry2, rx1:rx2]
                if roi.size > 0:
                    try:
                        recog_queue.put_nowait((cached_key, cx, cy, roi.copy()))
                    except queue.Full:
                        pass   # drop frame — display never stalls

            # ── Retrieve cached result ─────────────────────────────────────────
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
                color = (0, 165, 255)   # orange = identifying
                label = "Identifying..."

            # ── Draw bounding box + info bar ───────────────────────────────────
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            bar_y1 = min(y2, FRAME_H - 36)
            cv2.rectangle(frame, (x1, bar_y1), (x2, bar_y1 + 35), color, cv2.FILLED)
            cv2.putText(frame, label, (x1 + 6, bar_y1 + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            # YuNet detection confidence (top-right of box)
            cv2.putText(frame, f"{det_conf:.0%}", (x2 - 42, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1, cv2.LINE_AA)

            # Draw 5 facial landmarks
            lms = face[4:14].reshape(5, 2)
            for lx, ly in lms:
                cv2.circle(frame, (int(lx), int(ly)), 3, (0, 200, 255), -1)

    # ── Evict stale face tracks ───────────────────────────────────────────────
    with result_lock:
        stale = [k for k, v in result_store.items()
                 if frame_count - v.get("last_frame", 0) > STALE_AFTER]
        for k in stale:
            del result_store[k]

    # ── HUD ───────────────────────────────────────────────────────────────────
    fps_counter.append(time.perf_counter() - t0)
    fps = 1.0 / (sum(fps_counter) / len(fps_counter)) if fps_counter else 0

    num_faces = 0 if faces is None else len(faces)
    queue_sz  = recog_queue.qsize()

    cv2.putText(frame, f"Faces: {num_faces}   FPS: {fps:.0f}   Queue: {queue_sz}", (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 200, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, f"YuNet + Facenet512 | Cosine tol: {COSINE_THRESHOLD}", (15, 58),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1, cv2.LINE_AA)

    cv2.imshow("Multi-Face Live Recognition Dashboard", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ── Shutdown ──────────────────────────────────────────────────────────────────
recog_queue.put(None)
cam.release()
cv2.destroyAllWindows()
print("[INFO] Closed.")