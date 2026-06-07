import cv2
from deepface import DeepFace
import pickle
import os
import urllib.request

DB_FILE = "deepface_database.pkl"

# ── OpenCV DNN Face Detector Setup ───────────────────────────────────────────
# Much more accurate than Haar Cascade — handles angles, lighting, partial faces
PROTOTXT_PATH = "deploy.prototxt"
CAFFEMODEL_PATH = "res10_300x300_ssd_iter_140000.caffemodel"

PROTOTXT_URL   = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
CAFFEMODEL_URL = "https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"

def download_if_missing(path, url):
    if not os.path.exists(path):
        print(f"[INFO] Downloading {os.path.basename(path)}...")
        urllib.request.urlretrieve(url, path)
        print(f"[INFO] Saved: {path}")

download_if_missing(PROTOTXT_PATH,   PROTOTXT_URL)
download_if_missing(CAFFEMODEL_PATH, CAFFEMODEL_URL)

net = cv2.dnn.readNetFromCaffe(PROTOTXT_PATH, CAFFEMODEL_PATH)
CONFIDENCE_THRESHOLD = 0.6   # Only draw boxes when DNN is ≥60% confident

# ── Initialize Database ───────────────────────────────────────────────────────
if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "rb") as f:
            database = pickle.load(f)
    except Exception as e:
        print(f"[WARNING] Failed to load database: {e}. Starting fresh.")
        database = {}
else:
    database = {}

print("=" * 70)
print("DEEPFACE MANUAL DATA COLLECTION - ULTRA HIGH ACCURACY")
print("=" * 70)
print("\nInstructions:")
print("1. Position your face in the center of the frame")
print("2. Follow the on-screen pose instructions")
print("3. Click the video window, then press 'c' to CAPTURE")
print("4. Press 'q' to quit, 's' to skip pose\n")

print("\n[STEP 1] Register New Person")
print("-" * 70)
name    = input("Enter Full Name: ").strip()
user_id = input("Enter Employee/Student ID: ").strip()
dept    = input("Enter Department: ").strip()

if not name or not user_id:
    print("[ERROR] Name and ID are required!")
    exit()

# ── Initialize Camera ─────────────────────────────────────────────────────────
cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

POSE_ORDER = ['straight', 'slight_left', 'slight_right', 'slight_up', 'slight_down']
instructions = {
    'straight':     'Look STRAIGHT at camera',
    'slight_left':  'Turn head slightly LEFT',
    'slight_right': 'Turn head slightly RIGHT',
    'slight_up':    'Look slightly UP',
    'slight_down':  'Look slightly DOWN'
}

current_pose_idx = 0
user_embeddings  = []

print(f"\n[STEP 2] Start Manual Registration")
print("-" * 70)
print(f"Registered: {name} ({user_id})")
print(f"Poses to capture: {len(POSE_ORDER)}\n")

message       = ""
message_timer = 0

while True:
    ret, frame = cam.read()
    if not ret:
        print("[ERROR] Camera failed!")
        break

    h, w, _ = frame.shape
    frame    = cv2.flip(frame, 1)   # selfie view

    # ── DNN Face Detection (live bounding box only) ───────────────────────────
    blob = cv2.dnn.blobFromImage(
        cv2.resize(frame, (300, 300)),  # DNN expects 300×300 input
        scalefactor=1.0,
        size=(300, 300),
        mean=(104.0, 177.0, 123.0)      # ImageNet mean subtraction
    )
    net.setInput(blob)
    detections = net.forward()

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence < CONFIDENCE_THRESHOLD:
            continue

        # Scale the box coordinates back to the original frame size
        box = detections[0, 0, i, 3:7] * [w, h, w, h]
        x1, y1, x2, y2 = box.astype(int)

        # Clamp to frame boundaries
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Show confidence score on the box
        cv2.putText(frame, f"{confidence:.0%}", (x1, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)

    # ── UI Overlays ───────────────────────────────────────────────────────────
    cv2.putText(frame, "DEEPFACE DATA COLLECTION", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)

    if current_pose_idx < len(POSE_ORDER):
        current_pose   = POSE_ORDER[current_pose_idx]
        pose_idx_text  = f"{current_pose_idx + 1}/{len(POSE_ORDER)}"

        cv2.putText(frame, f"[{pose_idx_text}] {instructions[current_pose]}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, "Click on window, then press 'c' to CAPTURE", (10, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    cv2.putText(frame, "Keys: 'c' = Capture | 's' = Skip | 'q' = Quit", (10, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    if message_timer > 0:
        color = (0, 0, 255) if "ERROR" in message else (255, 255, 0)
        cv2.putText(frame, message, (10, h - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        message_timer -= 1

    cv2.imshow("DeepFace Manual Collection", frame)

    # ── Key Controls ──────────────────────────────────────────────────────────
    key = cv2.waitKey(5) & 0xFF

    if key in [ord('q'), ord('Q')]:
        print("\n[CANCELLED] Exiting...")
        break

    elif key in [ord('s'), ord('S')]:
        print(f"\n[SKIPPED] Skipping {POSE_ORDER[current_pose_idx]}...")
        current_pose_idx += 1
        if current_pose_idx >= len(POSE_ORDER):
            break

    elif key in [ord('c'), ord('C')]:
        if current_pose_idx >= len(POSE_ORDER):
            break

        print(f"[INFO] Processing {POSE_ORDER[current_pose_idx].upper()} with DeepFace... freeze!")

        try:
            results = DeepFace.represent(
                img_path=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                model_name="Facenet512",
                detector_backend="retinaface",
                enforce_detection=True
            )

            if len(results) == 1:
                embedding = results[0]["embedding"]
                user_embeddings.append(embedding)

                print(f"✓ Captured: {POSE_ORDER[current_pose_idx].upper()}")
                message       = f"Captured {POSE_ORDER[current_pose_idx]}!"
                message_timer = 30
                current_pose_idx += 1

                if current_pose_idx >= len(POSE_ORDER):
                    print("\n[SUCCESS] All poses captured! Saving profile...")
                    cv2.imshow("DeepFace Manual Collection", frame)
                    cv2.waitKey(1000)
                    break

            elif len(results) > 1:
                print("[WARNING] Multiple faces detected! Please stand alone.")
                message       = "[ERROR] Multiple faces detected!"
                message_timer = 30

        except ValueError:
            print("[WARNING] DeepFace could not lock onto your face. Adjust lighting/angle.")
            message       = "[ERROR] Face lost during capture!"
            message_timer = 30

# ── Save Profile Database ─────────────────────────────────────────────────────
if len(user_embeddings) > 0:
    database[user_id] = {
        "name":       name,
        "id":         user_id,
        "dept":       dept,
        "embeddings": user_embeddings,
        "num_poses":  len(user_embeddings),
    }
    with open(DB_FILE, "wb") as f:
        pickle.dump(database, f)

    print(f"\n{'='*70}")
    print("[SUCCESS] DeepFace Profile saved!")
    print(f"{'='*70}")
    print(f"  Name:           {name}")
    print(f"  ID:             {user_id}")
    print(f"  Department:     {dept}")
    print(f"  Poses captured: {len(user_embeddings)}/{len(POSE_ORDER)}")
    print(f"  Saved to:       {DB_FILE}")
else:
    print("\n[ERROR] No faces captured. Profile not saved.")

# Cleanup
cam.release()
cv2.destroyAllWindows()