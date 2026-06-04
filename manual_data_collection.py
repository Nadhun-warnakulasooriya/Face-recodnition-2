import cv2
from deepface import DeepFace
import pickle
import os

DB_FILE = "deepface_database.pkl" # Renamed so it doesn't conflict with your old dlib database

# Initialize Database
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

# Initialize Camera
cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Load a fast, lightweight OpenCV detector just for the live video feed bounding box
# (This prevents the video feed from lagging while you pose)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

POSE_ORDER = ['straight', 'slight_left', 'slight_right', 'slight_up', 'slight_down']
instructions = {
    'straight':     'Look STRAIGHT at camera',
    'slight_left':  'Turn head slightly LEFT',
    'slight_right': 'Turn head slightly RIGHT',
    'slight_up':    'Look slightly UP',
    'slight_down':  'Look slightly DOWN'
}

current_pose_idx = 0
user_embeddings = [] # DeepFace calls them embeddings instead of encodings

print(f"\n[STEP 2] Start Manual Registration")
print("-" * 70)
print(f"Registered: {name} ({user_id})")
print(f"Poses to capture: {len(POSE_ORDER)}\n")

# Variables for UI feedback
message = ""
message_timer = 0

while True:
    ret, frame = cam.read()

    if not ret:
        print("[ERROR] Camera failed!")
        break

    h, w, _ = frame.shape

    # Flip for selfie view 
    frame = cv2.flip(frame, 1)
    
    # Fast, lightweight face detection just for the live bounding box
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))

    # Draw bounding boxes (Live Feed)
    for (x, y, fw, fh) in faces:
        cv2.rectangle(frame, (x, y), (x+fw, y+fh), (0, 255, 0), 2)

    # ── UI Overlays ───────────────────────────────────────────────────────────
    cv2.putText(frame, "DEEPFACE DATA COLLECTION", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)

    if current_pose_idx < len(POSE_ORDER):
        current_pose = POSE_ORDER[current_pose_idx]
        pose_idx_text = f"{current_pose_idx + 1}/{len(POSE_ORDER)}"
        
        cv2.putText(frame, f"[{pose_idx_text}] {instructions[current_pose]}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, "Click on window, then press 'c' to CAPTURE", (10, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    cv2.putText(frame, "Keys: 'c' = Capture | 's' = Skip | 'q' = Quit", (10, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    # Show temporary success/error messages on screen
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
        
        # We need RGB for DeepFace
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        try:
            # ── THE MAGIC HAPPENS HERE ──
            # We use Facenet512 (highly accurate) and RetinaFace (finds faces at weird angles)
            results = DeepFace.represent(
                img_path=rgb_frame,
                model_name="Facenet512",
                detector_backend="retinaface",
                enforce_detection=True # Fails safely if no face is found
            )

            if len(results) == 1:
                # Extract the high-density mathematical face map
                embedding = results[0]["embedding"]
                user_embeddings.append(embedding)
                
                print(f"✓ Captured: {POSE_ORDER[current_pose_idx].upper()}")
                message = f"Captured {POSE_ORDER[current_pose_idx]}!"
                message_timer = 30
                current_pose_idx += 1
                
                if current_pose_idx >= len(POSE_ORDER):
                    print("\n[SUCCESS] All poses captured! Saving profile...")
                    cv2.imshow("DeepFace Manual Collection", frame)
                    cv2.waitKey(1000)
                    break
                    
            elif len(results) > 1:
                print("[WARNING] Multiple faces detected! Please stand alone.")
                message = "[ERROR] Multiple faces detected!"
                message_timer = 30

        except ValueError:
            # DeepFace throws a ValueError if enforce_detection=True and it can't find a face
            print("[WARNING] DeepFace could not lock onto your face. Adjust lighting/angle.")
            message = "[ERROR] Face lost during capture!"
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