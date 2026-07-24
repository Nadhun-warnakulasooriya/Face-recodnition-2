import os
import sys
import sqlite3
import threading
import json
import time
import queue
import urllib.request
from collections import deque
from datetime import datetime
import requests
import cv2
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
from PIL import Image, ImageTk
import customtkinter as ctk
from deepface import DeepFace

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG & PATHS
# ═══════════════════════════════════════════════════════════════════════════════
os.environ["DEEPFACE_HOME"] = os.path.abspath(".")
cv2.setNumThreads(0)
os.environ["OMP_NUM_THREADS"] = "8"

SERVER_URL = "http://127.0.0.1:5000" # VPS එකට දමන විට IP එක වෙනස් කරන්න
DB_FILE = "local_edge_data.db"
YUNET_MODEL = "face_detection_yunet_2023mar.onnx"
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

# AI Settings
COSINE_THRESHOLD = 0.35
DETECT_CONF = 0.20
MIN_FACE_PX = 30
SMOOTH_WINDOW = 10
RECOG_EVERY_N = 10
TRACK_RADIUS = 90
STALE_AFTER = 60
NUM_WORKERS = 2
PING_INTERVAL = 300 # තත්පර 300 (විනාඩි 5කට වරක් Activity Ping යවයි)

# ═══════════════════════════════════════════════════════════════════════════════
#  LOCAL DATABASE & OFFLINE QUEUE
# ═══════════════════════════════════════════════════════════════════════════════
def init_local_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
                    emp_id TEXT PRIMARY KEY, name TEXT, dept TEXT, embeddings TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS event_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, payload TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def save_setting(key, value):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def queue_event(event_type, payload):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO event_queue (event_type, payload) VALUES (?, ?)", (event_type, json.dumps(payload)))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  BACKGROUND SYNC WORKER (Internet නැති විට ක්‍රියාත්මක වීමට)
# ═══════════════════════════════════════════════════════════════════════════════
def background_sync_worker(app_instance):
    while True:
        time.sleep(5)
        api_key = get_setting("api_key")
        if not api_key:
            continue

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, event_type, payload FROM event_queue ORDER BY id ASC LIMIT 5")
        rows = c.fetchall()
        conn.close()

        for row in rows:
            event_id, event_type, payload_str = row
            payload = json.loads(payload_str)
            payload["api_key"] = api_key

            try:
                endpoint = "/api/event" if event_type == "attendance" else "/api/activity_ping"
                resp = requests.post(f"{SERVER_URL}{endpoint}", json=payload, timeout=5)
                
                if resp.status_code in [200, 201, 400, 409]:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("DELETE FROM event_queue WHERE id=?", (event_id,))
                    conn.commit()
                    conn.close()
                    if resp.status_code in [200, 201]:
                        app_instance.after(0, lambda e=event_type, p=payload: app_instance.log_msg(f"Synced {e} for {p.get('name', 'User')}"))
                    else:
                        app_instance.after(0, lambda e=event_type, p=payload, c=resp.status_code: app_instance.log_msg(f"Discarded {e} for {p.get('name', 'User')} (Error {c})"))
                else:
                    break 
            except Exception as e:
                break 

# ═══════════════════════════════════════════════════════════════════════════════
#  MODERN GUI & AI INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class OfficeTerminalApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SaaS Attendance - AI Edge Terminal")
        self.geometry("1000x650")
        self.minsize(900, 600)
        
        self.camera_running = False
        self.cap = None
        self.detector = None
        self.emb_matrix_normed = np.empty((0, 512), dtype=np.float32)
        self.known_profiles = []
        
        self.recog_queue = queue.Queue(maxsize=6)
        self.result_store = {}
        self.result_lock = threading.Lock()
        self.frame_count = 0
        self.face_counter = 0
        self.workers = []

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.create_left_panel()
        self.create_right_panel()

        threading.Thread(target=background_sync_worker, args=(self,), daemon=True).start()

    def create_left_panel(self):
        self.left_frame = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.left_frame.grid(row=0, column=0, sticky="nsew")
        self.left_frame.grid_propagate(False)
        
        self.title_label = ctk.CTkLabel(self.left_frame, text="AI Attendance", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=(30, 10), padx=20, anchor="w")
        
        self.status_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20, pady=(0, 20))
        self.status_dot = ctk.CTkLabel(self.status_frame, text="●", text_color="orange", font=ctk.CTkFont(size=18))
        self.status_dot.pack(side="left")
        self.status_text = ctk.CTkLabel(self.status_frame, text=" System Standby", text_color="gray")
        self.status_text.pack(side="left", padx=(5, 0))
        
        ctk.CTkLabel(self.left_frame, text="API Key:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20)
        self.api_entry = ctk.CTkEntry(self.left_frame, placeholder_text="Enter API Key")
        self.api_entry.pack(fill="x", padx=20, pady=(5, 15))
        self.api_entry.insert(0, get_setting("api_key"))
        
        self.btn_sync = ctk.CTkButton(self.left_frame, text="🔄 Sync Employees", command=self.sync_data, fg_color="#f59e0b", hover_color="#d97706")
        self.btn_sync.pack(fill="x", padx=20, pady=5)
        
        self.btn_start = ctk.CTkButton(self.left_frame, text="▶ Start Scanner", command=self.toggle_camera, fg_color="#10b981", hover_color="#059669")
        self.btn_start.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(self.left_frame, text="Activity Log:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        self.log_textbox = ctk.CTkTextbox(self.left_frame, height=200, font=ctk.CTkFont(size=11))
        self.log_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.log_textbox.insert("0.0", "Terminal initialized...\n")

    def create_right_panel(self):
        self.right_frame = ctk.CTkFrame(self, corner_radius=10)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.right_frame.pack_propagate(False)
        
        self.video_label = ctk.CTkLabel(self.right_frame, text="Camera Offline", font=ctk.CTkFont(size=20), text_color="gray")
        self.video_label.pack(expand=True, fill="both", padx=10, pady=10)

    def log_msg(self, msg):
        time_str = datetime.now().strftime("%H:%M:%S")
        self.log_textbox.insert("end", f"[{time_str}] {msg}\n")
        self.log_textbox.see("end")

    def sync_data(self):
        api_key = self.api_entry.get().strip()
        if not api_key:
            self.log_msg("Error: API Key is empty!")
            return
            
        save_setting("api_key", api_key)
        self.btn_sync.configure(state="disabled", text="Syncing...")
        self.log_msg("Downloading faces from server...")
        threading.Thread(target=self._perform_sync, args=(api_key,), daemon=True).start()

    def _perform_sync(self, api_key):
        try:
            resp = requests.post(f"{SERVER_URL}/api/sync_faces", json={"api_key": api_key}, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("database", {})
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("DELETE FROM employees")
                for emp_id, info in data.items():
                    c.execute("INSERT INTO employees (emp_id, name, dept, embeddings) VALUES (?, ?, ?, ?)",
                              (emp_id, info.get("name"), info.get("dept", ""), json.dumps(info.get("embeddings", []))))
                conn.commit()
                conn.close()
                self.after(0, lambda d=len(data): self.log_msg(f"Sync successful! {d} employees loaded."))
            else:
                self.after(0, lambda: self.log_msg("Sync Failed: Invalid API Key"))
        except Exception as e:
            self.after(0, lambda: self.log_msg("Sync Error: Server offline"))
        self.after(0, lambda: self.btn_sync.configure(state="normal", text="🔄 Sync Employees"))

    def load_ai_models(self):
        self.after(0, lambda: self.log_msg("Loading AI Models..."))
        if not os.path.exists(YUNET_MODEL):
            self.after(0, lambda: self.log_msg("Downloading face detection model (YuNet)..."))
            urllib.request.urlretrieve(YUNET_URL, YUNET_MODEL)
            
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT emp_id, name, dept, embeddings FROM employees")
        rows = c.fetchall()
        conn.close()

        raw_embeddings = []
        self.known_profiles = []
        for row in rows:
            embs = json.loads(row[3])
            for emb in embs:
                raw_embeddings.append(emb)
                self.known_profiles.append({"id": row[0], "name": row[1], "dept": row[2]})

        if raw_embeddings:
            emb_matrix = np.array(raw_embeddings, dtype=np.float32)
            norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
            self.emb_matrix_normed = emb_matrix / norms
        
        try:
            DeepFace.represent(np.zeros((160, 160, 3), dtype=np.uint8), model_name="Facenet512", detector_backend="skip", enforce_detection=False)
        except: pass

        self.detector = cv2.FaceDetectorYN.create(YUNET_MODEL, "", (640, 480), score_threshold=DETECT_CONF, nms_threshold=0.30, top_k=5000)

    def match_embedding(self, query_emb):
        if len(self.emb_matrix_normed) == 0: return "Unknown", "Access Denied", None, 0.0, (220, 0, 0)
        q = query_emb.astype(np.float32)
        norm = np.linalg.norm(q)
        if norm == 0: return "Unknown", "Access Denied", None, 0.0, (220, 0, 0)
        q /= norm
        sims = self.emb_matrix_normed @ q
        distances = 1.0 - sims
        best_idx = int(np.argmin(distances))
        best_dist = float(distances[best_idx])
        if best_dist <= COSINE_THRESHOLD:
            p = self.known_profiles[best_idx]
            conf = max(0.0, min(1.0, 1.0 - best_dist / COSINE_THRESHOLD))
            return p["name"], p["dept"], p["id"], conf, (0, 220, 0)
        return "Unknown", "Access Denied", None, 0.0, (220, 0, 0)

    def recognition_worker(self):
        while self.camera_running:
            try:
                item = self.recog_queue.get(timeout=1)
            except queue.Empty:
                continue
                
            if item is None: break
            face_key, cx, cy, roi_bgr = item
            try:
                rgb_roi = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
                resp = DeepFace.represent(rgb_roi, model_name="Facenet512", detector_backend="skip", enforce_detection=False)
                emb = np.array(resp[0]["embedding"], dtype=np.float32)
                name, dept, emp_id, conf, color = self.match_embedding(emb)
            except:
                name, dept, emp_id, conf, color = "Unknown", "Error", None, 0.0, (220, 0, 0)

            with self.result_lock:
                existing = self.result_store.get(face_key, {})
                history = existing.get("history", deque(maxlen=SMOOTH_WINDOW))
                
                if name != "Unknown":
                    history.append(conf)
                    smooth_conf = float(np.mean(history))
                else:
                    if len(history) > 0: history.append(0.0)
                    smooth_conf = float(np.mean(history)) if history else 0.0
                    if smooth_conf < 0.15:
                        name, dept, emp_id, color = "Unknown", "Denied", None, (220, 0, 0)
                    else:
                        name = existing.get("name", "Unknown")
                        emp_id = existing.get("emp_id", None)
                        color = existing.get("color", (220, 0, 0))

                # Throttling Logic (විනාඩි 5කට වරක් පමණක් Ping යැවීම)
                current_time = time.time()
                last_ping = existing.get("last_ping", 0)
                
                if name != "Unknown" and emp_id and smooth_conf >= 0.70:
                    if not existing.get("logged"):
                        # පළමු වරට (Attendance Mark)
                        queue_event("attendance", {"employee_id": emp_id, "name": name, "confidence": smooth_conf})
                        self.log_msg(f"Attendance queued for {name}")
                        existing["logged"] = True
                        existing["last_ping"] = current_time
                    elif current_time - last_ping > PING_INTERVAL:
                        # විනාඩි 5කට පසුව (Activity Tracking)
                        queue_event("activity_ping", {"emp_id": emp_id, "name": name, "confidence": smooth_conf})
                        existing["last_ping"] = current_time

                self.result_store[face_key] = {
                    "name": name, "dept": dept, "emp_id": emp_id,
                    "conf": smooth_conf, "color": color, "cx": cx, "cy": cy,
                    "history": history, "last_frame": existing.get("last_frame", 0),
                    "logged": existing.get("logged", False),
                    "last_ping": existing.get("last_ping", 0)
                }

    def toggle_camera(self):
        if not self.camera_running:
            self.btn_start.configure(state="disabled", text="Starting...")
            self.log_msg("Initializing scanner... please wait.")
            threading.Thread(target=self._init_scanner_thread, daemon=True).start()
        else:
            self.camera_running = False
            self.btn_start.configure(text="▶ Start Scanner", fg_color="#10b981", hover_color="#059669")
            self.status_dot.configure(text_color="orange")
            self.status_text.configure(text=" System Standby", text_color="gray")
            self.log_msg("Scanner stopped.")
            if self.cap: self.cap.release()
            self.video_label.configure(image=None, text="Camera Offline")

    def _init_scanner_thread(self):
        self.load_ai_models()
        
        # CCTV සඳහා මෙතැනට RTSP Link එක ලබාදෙන්න (උදා: "rtsp://admin:pass@192.168.1.100/stream")
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        if not self.cap.isOpened():
            self.after(0, lambda: self.log_msg("Error: Camera not found!"))
            self.after(0, lambda: self.btn_start.configure(state="normal", text="▶ Start Scanner"))
            return
            
        self.camera_running = True
        
        self.workers = [t for t in self.workers if t.is_alive()]
        while len(self.workers) < NUM_WORKERS:
            t = threading.Thread(target=self.recognition_worker, daemon=True)
            t.start()
            self.workers.append(t)
            
        self.after(0, self._on_scanner_ready)

    def _on_scanner_ready(self):
        self.btn_start.configure(state="normal", text="■ Stop Scanner", fg_color="#ef4444", hover_color="#dc2626")
        self.status_dot.configure(text_color="#10b981")
        self.status_text.configure(text=" Camera Active", text_color="#10b981")
        self.log_msg("Scanner initialized and ready.")
        self.update_camera_frame()

    def find_cached_result(self, cx, cy):
        best_key, best_dist = None, TRACK_RADIUS
        for k, v in self.result_store.items():
            d = abs(cx - v["cx"]) + abs(cy - v["cy"])
            if d < best_dist: best_dist, best_key = d, k
        return best_key

    def update_camera_frame(self):
        if self.camera_running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.frame_count += 1
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                self.detector.setInputSize((w, h))
                _, faces = self.detector.detect(frame)

                if faces is not None:
                    for face in faces:
                        x, y, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                        if fw < MIN_FACE_PX or fh < MIN_FACE_PX: continue

                        x1, y1 = max(0, x), max(0, y)
                        x2, y2 = min(w, x+fw), min(h, y+fh)
                        cx, cy = (x1+x2)//2, (y1+y2)//2

                        with self.result_lock:
                            cached_key = self.find_cached_result(cx, cy)
                        if cached_key is None:
                            self.face_counter += 1
                            cached_key = f"face_{self.face_counter}"

                        with self.result_lock:
                            if cached_key in self.result_store:
                                self.result_store[cached_key]["cx"] = cx
                                self.result_store[cached_key]["cy"] = cy
                                self.result_store[cached_key]["last_frame"] = self.frame_count

                        if self.frame_count % RECOG_EVERY_N == 0:
                            pad = max(20, int(fw * 0.30))
                            rx1, ry1 = max(0, x1 - pad), max(0, y1 - pad)
                            rx2, ry2 = min(w, x2 + pad), min(h, y2 + pad)
                            roi = frame[ry1:ry2, rx1:rx2]
                            if roi.size > 0:
                                try:
                                    self.recog_queue.put_nowait((cached_key, cx, cy, roi.copy()))
                                except queue.Full: pass

                        with self.result_lock:
                            res = self.result_store.get(cached_key)

                        if res:
                            label = f"{res['name']} ({res['conf']:.0%})" if res['conf'] > 0 else "Identifying..."
                            color = res["color"]
                        else:
                            label, color = "Identifying...", (255, 165, 0) # BGR Format in OpenCV drawing

                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        bar_y1 = min(y2, h - 36)
                        cv2.rectangle(frame, (x1, bar_y1), (x2, bar_y1 + 35), color, cv2.FILLED)
                        cv2.putText(frame, label, (x1 + 6, bar_y1 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

                with self.result_lock:
                    stale = [k for k, v in list(self.result_store.items()) if self.frame_count - v.get("last_frame", 0) > STALE_AFTER]
                    for k in stale: del self.result_store[k]

                cv2_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(cv2_img)
                
                label_w = self.right_frame.winfo_width() - 20
                label_h = self.right_frame.winfo_height() - 20
                if label_w > 0 and label_h > 0:
                    pil_img = pil_img.resize((label_w, label_h))
                
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(label_w, label_h))
                self.video_label.configure(image=ctk_img, text="")
                
            self.after(15, self.update_camera_frame)

if __name__ == "__main__":
    init_local_db()
    app = OfficeTerminalApp()
    app.mainloop()