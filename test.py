import os
import time
import queue
import pickle
import urllib.request
import threading
from collections import deque
import cv2
import numpy as np
import requests
import customtkinter as ctk
from deepface import DeepFace

def ensure_files():
    # 1. YUNET Model එක නැත්නම් ඩවුන්ලෝඩ් කරන්න
    if not os.path.exists(YUNET_MODEL):
        print(f"[INFO] {YUNET_MODEL} not found. Downloading...")
        try:
            urllib.request.urlretrieve(YUNET_URL, YUNET_MODEL)
            print("[SUCCESS] Model downloaded successfully.")
        except Exception as e:
            print(f"[ERROR] Download failed: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG & SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
SERVER_URL       = "http://localhost:5000"
DB_FILE          = "deepface_database.pkl"
YUNET_MODEL      = "face_detection_yunet_2023mar.onnx"
YUNET_URL        = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
FRAME_W, FRAME_H = 640, 480

COSINE_THRESHOLD  = 0.25   
DETECT_CONF       = 0.75   
MIN_FACE_PX       = 60     
SMOOTH_WINDOW     = 10     
RECOG_EVERY_N     = 10     
TRACK_RADIUS      = 90     
STALE_AFTER       = 60     
NUM_WORKERS       = 4      

cv2.setNumThreads(0)
os.environ["OMP_NUM_THREADS"]      = "8"
os.environ["OPENBLAS_NUM_THREADS"] = "8"

# ═══════════════════════════════════════════════════════════════════════════════
#  DESKTOP APPLICATION GUI (CustomTkinter)
# ═══════════════════════════════════════════════════════════════════════════════
class AttendanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("600x450")
        self.title("SaaS Attendance - Office Terminal")
        self.camera_running = False
        
        # --- UI Design ---
        self.title_label = ctk.CTkLabel(self, text="Office Face Scanner", font=("Arial", 24, "bold"))
        self.title_label.pack(pady=(30, 10))
        
        self.desc_label = ctk.CTkLabel(self, text="Enter your Company API Key to sync and start.", text_color="gray")
        self.desc_label.pack(pady=(0, 20))
        
        # API Key Input
        self.api_entry = ctk.CTkEntry(self, width=300, placeholder_text="e.g. KEY_KEELLS_7712", justify="center")
        self.api_entry.pack(pady=10)
        
        # Sync Button
        self.btn_sync = ctk.CTkButton(self, text="1. Sync Employees", fg_color="#f59e0b", hover_color="#d97706", command=self.sync_database)
        self.btn_sync.pack(pady=10)
        
        # Start Camera Button
        self.btn_start = ctk.CTkButton(self, text="2. Start Scanner", fg_color="#10b981", hover_color="#059669", command=self.start_camera_thread)
        self.btn_start.pack(pady=10)
        
        # Status Label
        self.status_label = ctk.CTkLabel(self, text="Status: Waiting...", font=("Arial", 12))
        self.status_label.pack(pady=20)

    def sync_database(self):
        api_key = self.api_entry.get().strip()
        if not api_key:
            self.status_label.configure(text="Status: Please enter API Key first!", text_color="red")
            return
            
        self.status_label.configure(text="Status: Syncing with server...", text_color="orange")
        self.update()
        
        try:
            response = requests.post(f"{SERVER_URL}/api/sync_faces", json={"api_key": api_key}, timeout=10)
            if response.status_code == 200:
                data = response.json().get("database", {})
                company_name = response.json().get("company_name", "Unknown")
                with open(DB_FILE, "wb") as f:
                    pickle.dump(data, f)
                self.status_label.configure(text=f"Status: Synced! Loaded {len(data)} employees for {company_name}.", text_color="green")
            else:
                self.status_label.configure(text=f"Status: Sync Failed! Invalid API Key.", text_color="red")
        except Exception as e:
            self.status_label.configure(text=f"Status: Server Offline or Error.", text_color="red")

    def start_camera_thread(self):
        api_key = self.api_entry.get().strip()
        if not api_key:
            self.status_label.configure(text="Status: Please enter API Key first!", text_color="red")
            return
            
        if not os.path.exists(DB_FILE):
            self.status_label.configure(text="Status: Please Sync Employees first!", text_color="red")
            return

        if self.camera_running:
            self.status_label.configure(text="Status: Camera is already running!", text_color="orange")
            return

        self.camera_running = True
        self.status_label.configure(text="Status: Camera Started. Check new window.", text_color="green")
        self.btn_start.configure(state="disabled")
        
        # Start AI in a separate background thread to prevent GUI freezing
        threading.Thread(target=self.run_ai_scanner, args=(api_key,), daemon=True).start()

    def run_ai_scanner(self, api_key):
        # ══════════════════════════════════════════════════════════════════
        #  AI SCANNER LOGIC (Runs in background thread)
        # ══════════════════════════════════════════════════════════════════
        if not os.path.exists(YUNET_MODEL):
            urllib.request.urlretrieve(YUNET_URL, YUNET_MODEL)

        with open(DB_FILE, "rb") as f:
            database = pickle.load(f)

        raw_embeddings = []
        known_profiles = []
        for profile in database.values():
            for emb in profile["embeddings"]:
                raw_embeddings.append(emb)
                known_profiles.append(profile)

        if len(raw_embeddings) == 0:
            print("[WARNING] Empty database.")
            emb_matrix_normed = np.empty((0, 512), dtype=np.float32)
        else:
            emb_matrix = np.array(raw_embeddings, dtype=np.float32)
            norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
            emb_matrix_normed = emb_matrix / norms

        print("[INFO] Warming up AI...")
        try:
            DeepFace.represent(np.zeros((160, 160, 3), dtype=np.uint8), model_name="Facenet512", detector_backend="skip", enforce_detection=False)
        except Exception:
            pass

        detector = cv2.FaceDetectorYN.create(YUNET_MODEL, "", (FRAME_W, FRAME_H), score_threshold=DETECT_CONF, nms_threshold=0.30, top_k=5000)

        def match_embedding(query_emb):
            if len(emb_matrix_normed) == 0: return "Unknown Person", "Access Denied", None, 0.0, (0, 0, 220)
            q = query_emb.astype(np.float32)
            norm = np.linalg.norm(q)
            if norm == 0: return "Unknown Person", "Access Denied", None, 0.0, (0, 0, 220)
            q /= norm
            sims = emb_matrix_normed @ q
            distances = 1.0 - sims
            best_idx = int(np.argmin(distances))
            best_dist = float(distances[best_idx])
            if best_dist <= COSINE_THRESHOLD:
                p = known_profiles[best_idx]
                conf = max(0.0, min(1.0, 1.0 - best_dist / COSINE_THRESHOLD))
                return p["name"], p.get("dept", "Verified"), p["id"], conf, (0, 220, 0)
            return "Unknown Person", "Access Denied", None, 0.0, (0, 0, 220)

        recog_queue = queue.Queue(maxsize=6)
        result_lock = threading.Lock()
        result_store = {}

        def recognition_worker():
            while True:
                item = recog_queue.get()
                if item is None: break
                face_key, cx, cy, roi_bgr = item
                try:
                    roi_resized = cv2.resize(roi_bgr, (160, 160), interpolation=cv2.INTER_LINEAR)
                    rgb_roi = cv2.cvtColor(roi_resized, cv2.COLOR_BGR2RGB)
                    resp = DeepFace.represent(rgb_roi, model_name="Facenet512", detector_backend="skip", enforce_detection=False)
                    emb = np.array(resp[0]["embedding"], dtype=np.float32)
                    name, dept, emp_id, conf, color = match_embedding(emb)
                except Exception:
                    name, dept, emp_id, conf, color = "Unknown Person", "Access Denied", None, 0.0, (0, 0, 220)

                with result_lock:
                    existing = result_store.get(face_key, {})
                    history = existing.get("history", deque(maxlen=SMOOTH_WINDOW))
                    if name != "Unknown Person":
                        history.append(conf)
                        smooth_conf = float(np.mean(history))
                    else:
                        if len(history) > 0: history.append(0.0)
                        smooth_conf = float(np.mean(history)) if history else 0.0
                        if smooth_conf < 0.15:
                            name, dept, emp_id, color = "Unknown Person", "Access Denied", None, (0, 0, 220)
                        else:
                            prev = result_store.get(face_key, {})
                            name = prev.get("name", "Unknown Person")
                            dept = prev.get("dept", "Access Denied")
                            emp_id = prev.get("emp_id", None)
                            color = prev.get("color", (0, 0, 220))

                    result_store[face_key] = {
                        "name": name, "dept": dept, "emp_id": emp_id,
                        "conf": smooth_conf, "color": color, "cx": cx, "cy": cy,
                        "history": history, "last_frame": existing.get("last_frame", 0),
                        "logged": existing.get("logged", False)
                    }

                    # --- ATTENDANCE LOGGING TO VPS ---
                    # --- ATTENDANCE LOGGING TO VPS ---
                    if name != "Unknown Person" and emp_id and smooth_conf >= 0.20 and not result_store[face_key]["logged"]:
                        result_store[face_key]["logged"] = True
                        try:
                            payload = {"api_key": api_key, "employee_id": emp_id, "name": name, "confidence": smooth_conf}
                            response = requests.post(f"{SERVER_URL}/api/event", json=payload, timeout=5)
                            
                            if response.status_code == 201:
                                print(f"[SUCCESS] {name} - Attendance Marked in Database!")
                            elif response.status_code == 200:
                                print(f"[INFO] {name} - {response.json().get('message', 'Already Clocked In.')}")
                            else:
                                print(f"[SERVER ERROR] API Rejected ({response.status_code}): {response.text}")
                                result_store[face_key]["logged"] = False # Error එකක් ආවොත් ආයෙත් යවන්න හදනවා
                        except Exception as e:
                            print(f"[NETWORK ERROR] Connection to VPS failed: {e}")
                            result_store[face_key]["logged"] = False
                

        workers = []
        for _ in range(NUM_WORKERS):
            t = threading.Thread(target=recognition_worker, daemon=True)
            t.start()
            workers.append(t)

        def find_cached_result(cx, cy):
            best_key, best_dist = None, TRACK_RADIUS
            for k, v in result_store.items():
                d = abs(cx - v["cx"]) + abs(cy - v["cy"])
                if d < best_dist: best_dist, best_key = d, k
            return best_key

        cam = cv2.VideoCapture(0)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
        
        frame_count = 0
        face_counter = 0

        while self.camera_running:
            ret, frame = cam.read()
            if not ret: break
            frame_count += 1
            frame = cv2.flip(frame, 1)

            _, faces = detector.detect(frame)
            if faces is not None:
                for face in faces:
                    x, y, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                    det_conf = float(face[14])
                    if fw < MIN_FACE_PX or fh < MIN_FACE_PX: continue

                    x1, y1 = max(0, x), max(0, y)
                    x2, y2 = min(FRAME_W, x+fw), min(FRAME_H, y+fh)
                    cx, cy = (x1+x2)//2, (y1+y2)//2

                    with result_lock:
                        cached_key = find_cached_result(cx, cy)
                    if cached_key is None:
                        face_counter += 1
                        cached_key = f"face_{face_counter}"

                    with result_lock:
                        if cached_key in result_store:
                            result_store[cached_key]["cx"] = cx
                            result_store[cached_key]["cy"] = cy
                            result_store[cached_key]["last_frame"] = frame_count

                    if frame_count % RECOG_EVERY_N == 0:
                        pad = max(10, int(fw * 0.12))
                        rx1, ry1 = max(0, x1 - pad), max(0, y1 - pad)
                        rx2, ry2 = min(FRAME_W, x2 + pad), min(FRAME_H, y2 + pad)
                        roi = frame[ry1:ry2, rx1:rx2]
                        if roi.size > 0:
                            try:
                                recog_queue.put_nowait((cached_key, cx, cy, roi.copy()))
                            except queue.Full: pass

                    with result_lock:
                        res = result_store.get(cached_key)

                    if res:
                        label = f"{res['name']} ({res['conf']:.0%})" if res['conf'] > 0 else "Identifying..."
                        color = res["color"]
                    else:
                        label, color = "Identifying...", (0, 165, 255)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    bar_y1 = min(y2, FRAME_H - 36)
                    cv2.rectangle(frame, (x1, bar_y1), (x2, bar_y1 + 35), color, cv2.FILLED)
                    cv2.putText(frame, label, (x1 + 6, bar_y1 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            with result_lock:
                stale = [k for k, v in result_store.items() if frame_count - v.get("last_frame", 0) > STALE_AFTER]
                for k in stale: del result_store[k]

            cv2.imshow("SaaS Attendance Scanner", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.camera_running = False
                break

        for _ in workers: recog_queue.put(None)
        cam.release()
        cv2.destroyAllWindows()
        self.btn_start.configure(state="normal")
        self.status_label.configure(text="Status: Camera Stopped.", text_color="orange")

# ═══════════════════════════════════════════════════════════════════════════════
#  START APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = AttendanceApp()
    app.mainloop()