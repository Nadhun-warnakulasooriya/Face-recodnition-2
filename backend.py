"""
Employee Face Registration — Flask Backend
==========================================
Replaces the Tkinter app's logic layer.
"""

import os
import base64
import pickle
import urllib.request

import numpy as np
import cv2
from flask import Flask, request, jsonify
from flask_cors import CORS
from deepface import DeepFace

# ── App ───────────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

DB_FILE = "deepface_database.pkl"

# ── Model weights (DNN face detector) ────────────────────────────────────────
PROTOTXT_PATH   = "deploy.prototxt"
CAFFEMODEL_PATH = "res10_300x300_ssd_iter_140000.caffemodel"
PROTOTXT_URL    = (
    "https://raw.githubusercontent.com/opencv/opencv/master/"
    "samples/dnn/face_detector/deploy.prototxt"
)
CAFFEMODEL_URL  = (
    "https://raw.githubusercontent.com/opencv/opencv_3rdparty/"
    "dnn_samples_face_detector_20170830/"
    "res10_300x300_ssd_iter_140000.caffemodel"
)

def download_if_missing(path: str, url: str) -> None:
    if not os.path.exists(path):
        print(f"[INFO] Downloading {os.path.basename(path)}...")
        urllib.request.urlretrieve(url, path)
        print(f"[INFO] Saved: {path}")

download_if_missing(PROTOTXT_PATH,   PROTOTXT_URL)
download_if_missing(CAFFEMODEL_PATH, CAFFEMODEL_URL)

dnn_net              = cv2.dnn.readNetFromCaffe(PROTOTXT_PATH, CAFFEMODEL_PATH)
CONFIDENCE_THRESHOLD = 0.6

# ── Database helpers ──────────────────────────────────────────────────────────
def load_database() -> dict:
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"[WARNING] Could not load DB: {e}")
    return {}

def save_database(db: dict) -> None:
    with open(DB_FILE, "wb") as f:
        pickle.dump(db, f)

# ── In-memory registration session ───────────────────────────────────────────
_session: dict = {
    "name":       "",
    "user_id":    "",
    "outlet":     "",
    "embeddings": [],
}

def reset_session() -> None:
    _session["name"]      = ""
    _session["user_id"]   = ""
    _session["outlet"]    = ""
    _session["embeddings"].clear()

# ── Utilities ─────────────────────────────────────────────────────────────────
def b64_to_bgr(b64_str: str):
    """Decode a base64 data-URL or raw base64 JPEG to a BGR numpy array."""
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    try:
        np_arr = np.frombuffer(base64.b64decode(b64_str), dtype=np.uint8)
        return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    except Exception:
        return None

def detect_faces_dnn(bgr) -> list:
    """
    Run the OpenCV DNN face detector and return a list of face dicts:
        { x, y, w, h, conf }   (pixel coords in the original frame)
    """
    h, w = bgr.shape[:2]
    blob = cv2.dnn.blobFromImage(
        cv2.resize(bgr, (300, 300)),
        scalefactor=1.0,
        size=(300, 300),
        mean=(104.0, 177.0, 123.0),
    )
    dnn_net.setInput(blob)
    detections = dnn_net.forward()

    faces = []
    for i in range(detections.shape[2]):
        conf = float(detections[0, 0, i, 2])
        if conf < CONFIDENCE_THRESHOLD:
            continue
        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
        x1, y1, x2, y2 = box.astype(int)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        faces.append({
            "x":    int(x1),
            "y":    int(y1),
            "w":    int(x2 - x1),
            "h":    int(y2 - y1),
            "conf": f"{conf:.0%}",
        })
    return faces

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    db = load_database()
    return jsonify(status="ok", registered_count=len(db))

@app.route("/check_id", methods=["GET"])
def check_id():
    uid = request.args.get("user_id", "").strip()
    db  = load_database()
    return jsonify(exists=uid in db)

@app.route("/set_meta", methods=["POST"])
def set_meta():
    """Store employee metadata for the current session."""
    payload = request.get_json(force=True)
    _session["name"]    = payload.get("name",    "").strip()
    _session["user_id"] = payload.get("user_id", "").strip()
    _session["outlet"]  = payload.get("outlet",  "").strip()
    print(f"[META] Session started for {_session['name']} ({_session['user_id']})")
    return jsonify(success=True)

@app.route("/live_detect", methods=["POST"])
def live_detect():
    """Fast endpoint just to get bounding boxes for the live feed."""
    payload = request.get_json(force=True)
    b64_img = payload.get("image", "")
    
    if not b64_img:
        return jsonify(face_boxes=[])

    bgr = b64_to_bgr(b64_img)
    if bgr is None:
        return jsonify(face_boxes=[])

    # Run the fast OpenCV DNN check
    faces = detect_faces_dnn(bgr)
    return jsonify(face_boxes=faces)

@app.route("/capture", methods=["POST"])
def capture():
    """
    Receive a base64 video frame from the browser, run DeepFace on it, and
    return the result + face bounding boxes for the overlay canvas.
    """
    payload   = request.get_json(force=True)
    b64_img   = payload.get("image", "")
    pose      = payload.get("pose", "unknown")

    if not b64_img:
        return jsonify(success=False, message="No image received"), 400

    bgr = b64_to_bgr(b64_img)
    if bgr is None:
        return jsonify(success=False, message="Could not decode image"), 400

    # Fast DNN pre-check
    faces = detect_faces_dnn(bgr)
    if len(faces) == 0:
        return jsonify(success=False, message="No face detected — adjust angle/lighting",
                       face_boxes=[])
    if len(faces) > 1:
        return jsonify(success=False, message="Multiple faces detected — please stand alone",
                       face_boxes=faces)

    # DeepFace embedding (accurate)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    try:
        results = DeepFace.represent(
            img_path          = rgb,
            model_name        = "Facenet512",
            detector_backend  = "retinaface",
            enforce_detection = True,
        )
    except ValueError:
        return jsonify(success=False,
                       message="DeepFace could not lock onto face — try again",
                       face_boxes=faces)

    if len(results) == 0:
        return jsonify(success=False, message="No face found by DeepFace",
                       face_boxes=faces)
    if len(results) > 1:
        return jsonify(success=False, message=f"Multiple faces detected ({len(results)})",
                       face_boxes=faces)

    embedding = results[0]["embedding"]
    _session["embeddings"].append(embedding)

    print(f"[OK] Pose '{pose}' captured for {_session['user_id']} "
          f"-- total: {len(_session['embeddings'])}")

    return jsonify(
        success        = True,
        message        = f"Pose '{pose}' captured",
        total_captured = len(_session["embeddings"]),
        face_boxes     = faces,
    )

@app.route("/save", methods=["POST"])
def save():
    """Persist the session embeddings to the pickle database."""
    name    = _session["name"]
    user_id = _session["user_id"]
    outlet  = _session["outlet"]

    if not name or not user_id:
        return jsonify(success=False,
                       message="Missing employee metadata — call /set_meta first"), 400
    if not _session["embeddings"]:
        return jsonify(success=False, message="No embeddings captured"), 400

    db = load_database()
    db[user_id] = {
        "name":       name,
        "id":         user_id,
        "outlet":     outlet,
        "embeddings": list(_session["embeddings"]),
        "num_poses":  len(_session["embeddings"]),
    }
    save_database(db)

    n = len(_session["embeddings"])
    print(f"[SAVED] {name} ({user_id}) -- {n} embeddings -> {DB_FILE}")

    reset_session()
    return jsonify(success=True, message=f"Profile saved: {n} embeddings",
                   total_registered=len(db))

@app.route("/reset", methods=["POST"])
def reset():
    """Clear the in-memory session (does NOT touch the database)."""
    reset_session()
    print("[RESET] Session cleared")
    return jsonify(success=True)

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Employee Registration Backend")
    print("  http://localhost:5000")
    print("  Open index.html in your browser")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)