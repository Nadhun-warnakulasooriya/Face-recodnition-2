import cv2
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from deepface import DeepFace
import pickle
import os
import urllib.request
import threading

# ── Model File Paths & Download URLs ─────────────────────────────────────────
DB_FILE        = "deepface_database.pkl"
PROTOTXT_PATH  = "deploy.prototxt"
CAFFEMODEL_PATH = "res10_300x300_ssd_iter_140000.caffemodel"
PROTOTXT_URL   = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
CAFFEMODEL_URL = "https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"

def download_if_missing(path, url):
    if not os.path.exists(path):
        print(f"[INFO] Downloading {os.path.basename(path)}...")
        urllib.request.urlretrieve(url, path)
        print(f"[INFO] Saved: {path}")

download_if_missing(PROTOTXT_PATH,    PROTOTXT_URL)
download_if_missing(CAFFEMODEL_PATH,  CAFFEMODEL_URL)

net = cv2.dnn.readNetFromCaffe(PROTOTXT_PATH, CAFFEMODEL_PATH)
CONFIDENCE_THRESHOLD = 0.6

# ── Pose Configuration ────────────────────────────────────────────────────────
POSE_ORDER = ["straight", "slight_left", "slight_right", "slight_up", "slight_down"]
POSE_LABELS = {
    "straight":     "Look STRAIGHT at camera",
    "slight_left":  "Turn head slightly LEFT",
    "slight_right": "Turn head slightly RIGHT",
    "slight_up":    "Look slightly UP",
    "slight_down":  "Look slightly DOWN",
}

# ── Colour Palette ────────────────────────────────────────────────────────────
BG_DARK   = "#0d0d1a"
BG_PANEL  = "#131326"
BG_CARD   = "#1a1a35"
ACCENT    = "#4f8ef7"
ACCENT2   = "#7c3aed"
SUCCESS   = "#22c55e"
WARNING   = "#f59e0b"
DANGER    = "#ef4444"
TEXT_PRI  = "#e8e8ff"
TEXT_SEC  = "#7878a8"
BORDER    = "#2a2a50"
ENTRY_BG  = "#0d0d2a"


class EmployeeRegistrationApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Employee Face Registration")
        self.root.geometry("1100x680")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(False, False)

        # State
        self.cam              = None
        self.running          = False
        self.current_frame    = None
        self.current_pose_idx = 0
        self.user_embeddings  = []
        self.capturing        = False

        # Load database
        self.database = {}
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "rb") as f:
                    self.database = pickle.load(f)
            except Exception as e:
                print(f"[WARNING] Could not load DB: {e}")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────────────────────────────────────
    # UI CONSTRUCTION
    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Top Header ────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=BG_PANEL, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="◈  Employee Face Registration System",
                 font=("Consolas", 15, "bold"), fg=ACCENT, bg=BG_PANEL
                 ).place(x=24, y=14)
        tk.Label(hdr, text="DeepFace · Facenet512 · RetinaFace",
                 font=("Consolas", 8), fg=TEXT_SEC, bg=BG_PANEL
                 ).place(x=26, y=40)

        # DB count badge
        self.badge_var = tk.StringVar()
        self._refresh_badge()
        tk.Label(hdr, textvariable=self.badge_var,
                 font=("Consolas", 9, "bold"), fg=ACCENT2, bg=BG_PANEL
                 ).place(relx=1.0, x=-20, y=22, anchor="ne")

        # Separator line
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # ── Main Body ─────────────────────────────────────────────────────────
        body = tk.Frame(self.root, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=18, pady=14)

        # Left: form panel
        left = tk.Frame(body, bg=BG_PANEL, width=320, bd=0)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)
        self._build_left_panel(left)

        # Right: camera panel
        right = tk.Frame(body, bg=BG_CARD, bd=0)
        right.pack(side="left", fill="both", expand=True)
        self._build_camera_panel(right)

    def _build_left_panel(self, parent):
        # ── Section: Employee Details ─────────────────────────────────────────
        self._section_label(parent, "EMPLOYEE DETAILS")

        form = tk.Frame(parent, bg=BG_PANEL)
        form.pack(fill="x", padx=16, pady=(0, 10))

        self.entries: dict[str, tk.Entry] = {}
        fields = [
            ("Employee ID",   "emp_id",   "e.g. EMP-001"),
            ("Employee Name", "emp_name", "Full name"),
            ("Outlet",        "outlet",   "Branch / location"),
        ]
        for label, key, placeholder in fields:
            tk.Label(form, text=label, font=("Consolas", 9, "bold"),
                     fg=TEXT_SEC, bg=BG_PANEL, anchor="w"
                     ).pack(fill="x", pady=(10, 2))
            e = tk.Entry(form, font=("Consolas", 11),
                         bg=ENTRY_BG, fg=TEXT_PRI, insertbackground=ACCENT,
                         relief="flat", bd=0, highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=BORDER)
            e.pack(fill="x", ipady=7)
            e.insert(0, placeholder)
            e.config(fg=TEXT_SEC)
            e.bind("<FocusIn>",  lambda ev, w=e, ph=placeholder: self._clear_ph(ev, w, ph))
            e.bind("<FocusOut>", lambda ev, w=e, ph=placeholder: self._restore_ph(ev, w, ph))
            self.entries[key] = e

        # ── Section: Pose Progress ────────────────────────────────────────────
        self._section_label(parent, "POSE PROGRESS")

        self.pose_labels: dict[str, tuple[tk.Label, tk.Label]] = {}
        pose_frame = tk.Frame(parent, bg=BG_PANEL)
        pose_frame.pack(fill="x", padx=16, pady=(0, 10))

        for pose in POSE_ORDER:
            row = tk.Frame(pose_frame, bg=BG_PANEL)
            row.pack(fill="x", pady=3)
            dot = tk.Label(row, text="○", font=("Consolas", 13),
                           fg=TEXT_SEC, bg=BG_PANEL, width=2)
            dot.pack(side="left")
            lbl = tk.Label(row, text=POSE_LABELS[pose],
                           font=("Consolas", 9), fg=TEXT_SEC, bg=BG_PANEL, anchor="w")
            lbl.pack(side="left", padx=4)
            self.pose_labels[pose] = (dot, lbl)

        # Progress bar
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Reg.Horizontal.TProgressbar",
                        troughcolor=ENTRY_BG, background=ACCENT,
                        bordercolor=BORDER, lightcolor=ACCENT,
                        darkcolor=ACCENT2, thickness=5)
        self.progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(parent, variable=self.progress_var,
                         maximum=len(POSE_ORDER), length=288,
                         style="Reg.Horizontal.TProgressbar"
                         ).pack(padx=16, pady=(0, 12))

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_frame = tk.Frame(parent, bg=BG_PANEL)
        btn_frame.pack(fill="x", padx=16, pady=(0, 10))

        self.btn_start = self._make_btn(btn_frame, "▶  START REGISTRATION",
                                        ACCENT, "white", self._start_registration)
        self.btn_start.pack(fill="x", pady=(0, 6))

        self.btn_capture = self._make_btn(btn_frame, "📸  CAPTURE POSE",
                                          SUCCESS, "white", self._capture_pose,
                                          state="disabled")
        self.btn_capture.pack(fill="x", pady=(0, 6))

        row2 = tk.Frame(btn_frame, bg=BG_PANEL)
        row2.pack(fill="x")
        self.btn_skip = self._make_btn(row2, "⏭ SKIP",
                                       BG_CARD, TEXT_SEC, self._skip_pose,
                                       state="disabled", font_size=9)
        self.btn_skip.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._make_btn(row2, "🔄 RESET",
                       BG_CARD, TEXT_SEC, self._reset,
                       font_size=9).pack(side="left", fill="x", expand=True)

        # ── Status Message ────────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Enter employee details and click START")
        self.status_lbl = tk.Label(parent, textvariable=self.status_var,
                                   font=("Consolas", 8), fg=TEXT_SEC, bg=BG_PANEL,
                                   wraplength=285, justify="center")
        self.status_lbl.pack(pady=6, padx=10)

    def _build_camera_panel(self, parent):
        # Camera label + live indicator
        top = tk.Frame(parent, bg=BG_CARD)
        top.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(top, text="LIVE FEED", font=("Consolas", 10, "bold"),
                 fg=TEXT_PRI, bg=BG_CARD).pack(side="left")
        self.live_dot = tk.Label(top, text="●", font=("Consolas", 10),
                                 fg=BORDER, bg=BG_CARD)
        self.live_dot.pack(side="left", padx=6)

        # Canvas
        self.canvas = tk.Canvas(parent, width=640, height=470,
                                bg="#050510", highlightthickness=1,
                                highlightbackground=BORDER)
        self.canvas.pack(padx=14, pady=(0, 8))
        self._draw_idle_screen()

        # Instruction + counter row
        bottom = tk.Frame(parent, bg=BG_CARD)
        bottom.pack(fill="x", padx=14, pady=(0, 10))
        self.instr_var = tk.StringVar(value="Camera feed will appear after START")
        tk.Label(bottom, textvariable=self.instr_var,
                 font=("Consolas", 10, "bold"), fg=SUCCESS, bg=BG_CARD,
                 anchor="w").pack(side="left")
        self.counter_var = tk.StringVar(value="0 / 5")
        tk.Label(bottom, textvariable=self.counter_var,
                 font=("Consolas", 10, "bold"), fg=ACCENT2, bg=BG_CARD,
                 anchor="e").pack(side="right")

    # ─────────────────────────────────────────────────────────────────────────
    # HELPER WIDGETS
    # ─────────────────────────────────────────────────────────────────────────
    def _section_label(self, parent, text):
        f = tk.Frame(parent, bg=BG_PANEL)
        f.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(f, text=text, font=("Consolas", 8, "bold"),
                 fg=ACCENT2, bg=BG_PANEL).pack(side="left")
        tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x",
                                              expand=True, padx=(8, 0), pady=6)

    def _make_btn(self, parent, text, bg, fg, cmd, state="normal",
                  font_size=10):
        return tk.Button(parent, text=text,
                         font=("Consolas", font_size, "bold"),
                         bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                         relief="flat", bd=0, padx=8, pady=8,
                         cursor="hand2", command=cmd, state=state)

    def _draw_idle_screen(self):
        self.canvas.delete("all")
        self.canvas.create_text(320, 235, text="◈",
                                font=("Consolas", 60), fill=BORDER)
        self.canvas.create_text(320, 310,
                                text="Camera starts after registration begins",
                                font=("Consolas", 11), fill=TEXT_SEC)

    def _refresh_badge(self):
        n = len(self.database)
        self.badge_var.set(f"Registered: {n} employee{'s' if n!=1 else ''}")

    # ── Placeholder helpers ───────────────────────────────────────────────────
    def _clear_ph(self, _, widget, placeholder):
        if widget.get() == placeholder:
            widget.delete(0, tk.END)
            widget.config(fg=TEXT_PRI)

    def _restore_ph(self, _, widget, placeholder):
        if not widget.get():
            widget.insert(0, placeholder)
            widget.config(fg=TEXT_SEC)

    # ─────────────────────────────────────────────────────────────────────────
    # REGISTRATION FLOW
    # ─────────────────────────────────────────────────────────────────────────
    def _start_registration(self):
        placeholders = {"e.g. EMP-001", "Full name", "Branch / location"}

        emp_id   = self.entries["emp_id"].get().strip()
        emp_name = self.entries["emp_name"].get().strip()
        outlet   = self.entries["outlet"].get().strip()

        # Strip placeholder text if still present
        if emp_id   in placeholders: emp_id   = ""
        if emp_name in placeholders: emp_name = ""
        if outlet   in placeholders: outlet   = ""

        if not emp_id or not emp_name:
            messagebox.showerror("Missing Fields",
                                 "Employee ID and Employee Name are required.")
            return

        if emp_id in self.database:
            if not messagebox.askyesno("ID Already Exists",
                    f"Employee ID  '{emp_id}'  is already registered.\n"
                    "Overwrite existing record?"):
                return

        self.emp_id   = emp_id
        self.emp_name = emp_name
        self.outlet   = outlet

        self.current_pose_idx = 0
        self.user_embeddings  = []

        # Lock form
        for e in self.entries.values():
            e.config(state="disabled")
        self.btn_start.config(state="disabled")
        self.btn_capture.config(state="normal")
        self.btn_skip.config(state="normal")

        # Start camera
        self.cam = cv2.VideoCapture(0)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.running = True
        self._set_status("Camera started — follow the pose instructions", ACCENT)
        self._update_pose_ui()
        self._update_camera()

    def _update_pose_ui(self):
        for i, pose in enumerate(POSE_ORDER):
            dot, lbl = self.pose_labels[pose]
            if i < self.current_pose_idx:
                dot.config(text="✓", fg=SUCCESS)
                lbl.config(fg=SUCCESS)
            elif i == self.current_pose_idx:
                dot.config(text="►", fg=ACCENT)
                lbl.config(fg=TEXT_PRI)
            else:
                dot.config(text="○", fg=TEXT_SEC)
                lbl.config(fg=TEXT_SEC)

        self.progress_var.set(self.current_pose_idx)
        self.counter_var.set(f"{self.current_pose_idx} / {len(POSE_ORDER)}")

        if self.current_pose_idx < len(POSE_ORDER):
            pose = POSE_ORDER[self.current_pose_idx]
            self.instr_var.set(
                f"[{self.current_pose_idx+1}/{len(POSE_ORDER)}]  {POSE_LABELS[pose]}"
            )
        else:
            self.instr_var.set("✅  All poses captured — saving profile…")

    def _update_camera(self):
        if not self.running:
            return

        ret, frame = self.cam.read()
        if not ret:
            self._set_status("[ERROR] Camera read failed!", DANGER)
            self.root.after(100, self._update_camera)
            return

        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]

        # DNN face detection overlay
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0)
        )
        net.setInput(blob)
        detections = net.forward()

        for i in range(detections.shape[2]):
            conf = detections[0, 0, i, 2]
            if conf < CONFIDENCE_THRESHOLD:
                continue
            box        = detections[0, 0, i, 3:7] * [w, h, w, h]
            x1, y1, x2, y2 = box.astype(int)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            colour = (80, 200, 120) if not self.capturing else (80, 120, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), colour, 2)
            cv2.putText(frame, f"{conf:.0%}", (x1, max(y1 - 6, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, colour, 1)

        self.current_frame = frame.copy()

        # Render to canvas
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img   = Image.fromarray(rgb).resize((640, 470))
        imgtk = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(0, 0, anchor="nw", image=imgtk)
        self.canvas._ref = imgtk          # prevent GC

        # Blink live dot
        self.live_dot.config(fg=SUCCESS if int(self.root.tk.call(
            "clock", "clicks", "-milliseconds")) % 1200 < 600 else BORDER)

        self.root.after(30, self._update_camera)

    # ─────────────────────────────────────────────────────────────────────────
    # CAPTURE / SKIP / FINISH
    # ─────────────────────────────────────────────────────────────────────────
    def _capture_pose(self):
        if self.capturing or self.current_frame is None:
            return
        if self.current_pose_idx >= len(POSE_ORDER):
            return

        self.capturing = True
        self.btn_capture.config(state="disabled")
        self.btn_skip.config(state="disabled")
        self._set_status("🔄  DeepFace processing… hold still", WARNING)

        frame_copy = self.current_frame.copy()
        pose_name  = POSE_ORDER[self.current_pose_idx]

        def _infer():
            try:
                results = DeepFace.represent(
                    img_path=cv2.cvtColor(frame_copy, cv2.COLOR_BGR2RGB),
                    model_name="Facenet512",
                    detector_backend="retinaface",
                    enforce_detection=True,
                )
                if len(results) == 1:
                    self.root.after(0, self._on_success, results[0]["embedding"], pose_name)
                elif len(results) > 1:
                    self.root.after(0, self._on_error, "Multiple faces detected — stand alone")
                else:
                    self.root.after(0, self._on_error, "No face found — adjust angle/lighting")
            except ValueError:
                self.root.after(0, self._on_error, "Face not detected — try again")
            except Exception as ex:
                self.root.after(0, self._on_error, f"Error: {str(ex)[:55]}")

        threading.Thread(target=_infer, daemon=True).start()

    def _on_success(self, embedding, pose_name):
        self.capturing = False
        self.user_embeddings.append(embedding)
        self.current_pose_idx += 1
        self._update_pose_ui()
        self._set_status(f"✅  Captured: {pose_name.replace('_', ' ').upper()}", SUCCESS)

        if self.current_pose_idx >= len(POSE_ORDER):
            self.root.after(400, self._finish_registration)
        else:
            self.btn_capture.config(state="normal")
            self.btn_skip.config(state="normal")

    def _on_error(self, msg):
        self.capturing = False
        self._set_status(f"⚠  {msg}", DANGER)
        self.btn_capture.config(state="normal")
        self.btn_skip.config(state="normal")

    def _skip_pose(self):
        if self.current_pose_idx >= len(POSE_ORDER):
            return
        skipped = POSE_ORDER[self.current_pose_idx].replace("_", " ").upper()
        self.current_pose_idx += 1
        self._update_pose_ui()
        self._set_status(f"⏭  Skipped: {skipped}", WARNING)

        if self.current_pose_idx >= len(POSE_ORDER):
            self.root.after(300, self._finish_registration)
        else:
            self.btn_capture.config(state="normal")
            self.btn_skip.config(state="normal")

    def _finish_registration(self):
        self.btn_capture.config(state="disabled")
        self.btn_skip.config(state="disabled")

        if not self.user_embeddings:
            messagebox.showerror("Registration Failed",
                                 "No poses captured. Cannot save profile.")
            self._reset()
            return

        self.database[self.emp_id] = {
            "name":       self.emp_name,
            "id":         self.emp_id,
            "outlet":     self.outlet,
            "embeddings": self.user_embeddings,
            "num_poses":  len(self.user_embeddings),
        }
        with open(DB_FILE, "wb") as f:
            pickle.dump(self.database, f)

        self._refresh_badge()

        messagebox.showinfo("Registration Complete",
            f"Employee registered successfully!\n\n"
            f"  Employee ID  :  {self.emp_id}\n"
            f"  Name         :  {self.emp_name}\n"
            f"  Outlet       :  {self.outlet or '—'}\n"
            f"  Poses saved  :  {len(self.user_embeddings)} / {len(POSE_ORDER)}")
        self._reset()

    # ─────────────────────────────────────────────────────────────────────────
    # RESET / CLOSE
    # ─────────────────────────────────────────────────────────────────────────
    def _reset(self):
        self.running = False
        if self.cam:
            self.cam.release()
            self.cam = None

        self.current_pose_idx = 0
        self.user_embeddings  = []
        self.capturing        = False

        # Unlock form
        placeholders = {
            "emp_id":   "e.g. EMP-001",
            "emp_name": "Full name",
            "outlet":   "Branch / location",
        }
        for key, e in self.entries.items():
            e.config(state="normal")
            e.delete(0, tk.END)
            e.insert(0, placeholders[key])
            e.config(fg=TEXT_SEC)

        self.btn_start.config(state="normal")
        self.btn_capture.config(state="disabled")
        self.btn_skip.config(state="disabled")

        for pose in POSE_ORDER:
            dot, lbl = self.pose_labels[pose]
            dot.config(text="○", fg=TEXT_SEC)
            lbl.config(fg=TEXT_SEC)

        self.progress_var.set(0)
        self.counter_var.set("0 / 5")
        self.instr_var.set("Camera feed will appear after START")
        self.live_dot.config(fg=BORDER)
        self._draw_idle_screen()
        self._set_status("Enter employee details and click START", TEXT_SEC)

    def _set_status(self, text, colour=TEXT_SEC):
        self.status_var.set(text)
        self.status_lbl.config(fg=colour)

    def _on_close(self):
        self.running = False
        if self.cam:
            self.cam.release()
        self.root.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = EmployeeRegistrationApp(root)
    root.mainloop()
