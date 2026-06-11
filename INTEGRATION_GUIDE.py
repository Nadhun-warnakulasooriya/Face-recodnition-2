#!/usr/bin/env python3
"""
FACE RECOGNITION ATTENDANCE SYSTEM
Complete Integration & Setup Guide

This guide walks through:
1. Installation & setup
2. Integrating event_logger into your existing recognition.py
3. Running the system end-to-end
4. Troubleshooting
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  QUICK START
# ═══════════════════════════════════════════════════════════════════════════════
"""
STEP 1: Install dependencies
    pip install -r requirements.txt

STEP 2: Start the Flask backend (in terminal 1)
    python app.py
    → Server will run on http://localhost:5000
    → Logs to attendance.log

STEP 3: Modify your recognition.py (see Integration Example below)

STEP 4: Start your recognition engine (in terminal 2)
    python recognition.py

STEP 5: Open dashboard in browser
    http://localhost:5000/dashboard.html
    or
    http://<your-pc-ip>:5000/dashboard.html (from another device)

DONE! System is live.
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  DIRECTORY STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════
"""
your-project-folder/
├── app.py                          ← Flask backend
├── event_logger.py                 ← Event logger module
├── dashboard.html                  ← Web dashboard (access at /dashboard.html)
├── requirements.txt                ← Python dependencies
├── recognition.py                  ← YOUR EXISTING recognition code (modified)
├── attendance.db                   ← SQLite database (auto-created)
├── attendance.log                  ← System logs
├── snapshots/                      ← Employee snapshots (auto-created)
│   ├── emp_001_clock_in_20250607_090000_123456.jpg
│   ├── emp_001_clock_out_20250607_210000_789012.jpg
│   └── ...
├── deepface_database.pkl           ← Your existing face embeddings
└── face_detection_yunet_2023mar.onnx ← YuNet model
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  INTEGRATION: Add event_logger to your recognition.py
# ═══════════════════════════════════════════════════════════════════════════════
"""
Here's the minimal changes needed to your existing recognition.py:

────────────────────────────────────────────────────────────────────────────────
AT THE TOP OF recognition.py (after other imports):

    from event_logger import AttendanceEventLogger
    
    # Initialize the event logger
    event_logger = AttendanceEventLogger(
        backend_url="http://localhost:5000",
        snapshots_dir="snapshots"
    )

────────────────────────────────────────────────────────────────────────────────
INSIDE recognition_worker(), after matching a face:

    # This is the section where you call match_embedding() and get:
    # name, dept, conf, color
    
    if name != "Unknown Person":
        # Send the detection to the attendance backend
        event_logger.log_event(
            employee_id=f"emp_{cached_key}",  # Or however you identify them
            name=name,
            dept=dept,
            confidence=conf,
            frame_bgr=roi_bgr,                # The face crop frame
            event_type='auto'                 # 'auto' = auto-detect in/out
        )

────────────────────────────────────────────────────────────────────────────────
OPTIONAL: Reset daily tracking at 9 AM

    In your main loop, add (before the camera capture loop):
    
    from datetime import datetime
    
    last_reset_hour = None
    
    while True:
        ret, frame = cam.read()
        
        # Reset daily state at 9 AM
        now_hour = datetime.now().hour
        if now_hour == 9 and last_reset_hour != 9:
            event_logger.reset_daily_state()
            last_reset_hour = 9
        elif now_hour != 9:
            last_reset_hour = None
        
        # ... rest of your loop

────────────────────────────────────────────────────────────────────────────────
COMPLETE MINIMAL EXAMPLE (simplified recognition.py structure):

    # recognition.py
    import cv2
    import threading
    import queue
    from event_logger import AttendanceEventLogger
    from datetime import datetime
    
    # Initialize event logger
    event_logger = AttendanceEventLogger(
        backend_url="http://localhost:5000",
        snapshots_dir="snapshots"
    )
    
    # ... your existing setup code ...
    
    # Background worker for recognition
    def recognition_worker():
        while True:
            item = recog_queue.get()
            # ... existing recognition code ...
            
            # After getting match result:
            name, dept, conf, color = match_embedding(emb)
            
            if name != "Unknown Person":
                # NEW: Log the event for attendance
                event_logger.log_event(
                    employee_id=face_key,
                    name=name,
                    dept=dept,
                    confidence=conf,
                    frame_bgr=roi_bgr,
                    event_type='auto'
                )
    
    # ... rest of your code ...
    
    # In main loop:
    last_reset_hour = None
    while True:
        ret, frame = cam.read()
        
        # Reset at 9 AM
        now_hour = datetime.now().hour
        if now_hour == 9 and last_reset_hour != 9:
            event_logger.reset_daily_state()
            last_reset_hour = 9
        elif now_hour != 9:
            last_reset_hour = None
        
        # ... your existing detection + recognition loop ...
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

────────────────────────────────────────────────────────────────────────────────
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  API REFERENCE
# ═══════════════════════════════════════════════════════════════════════════════
"""
REST API Endpoints:

1. POST /api/event
   Send a clock-in or clock-out event
   Payload:
   {
       "employee_id": "emp_001",
       "name": "John Doe",
       "dept": "Engineering",
       "confidence": 0.92,
       "snapshot_path": "snapshots/emp_001_clock_in_20250607_090000_123456.jpg",
       "event_type": "clock_in" | "clock_out"
   }
   Response:
   {
       "success": true,
       "record_id": 5,
       "event": "clock_in"
   }

2. GET /api/attendance/today
   Get all attendance records for today
   Response:
   {
       "success": true,
       "data": [
           {
               "id": 1,
               "name": "John Doe",
               "clock_in_time": "09:15:30",
               "clock_out_time": "21:45:00",
               "duration_mins": 750,
               "status": "completed",
               "clock_in_conf": 0.92,
               "clock_out_conf": 0.88
           },
           ...
       ]
   }

3. GET /api/staff/clocked-in
   Get currently clocked-in staff
   Response:
   {
       "success": true,
       "data": [
           {
               "id": 2,
               "employee_id": "emp_002",
               "name": "Jane Smith",
               "clock_in_time": "09:30:00",
               "clock_in_conf": 0.95
           },
           ...
       ]
   }

4. POST /api/clockout/confirm/<pending_id>
   Admin confirms a pending clock-out
   Response:
   {
       "success": true,
       "message": "Jane Smith clocked out",
       "duration_mins": 720
   }

5. GET /api/pending-clockouts
   Get all pending clock-outs (awaiting admin)
   Response:
   {
       "success": true,
       "data": [
           {
               "id": 1,
               "employee_id": "emp_002",
               "name": "Jane Smith",
               "detected_at": "2025-06-07 21:45:30",
               "confidence": 0.88,
               "snapshot_path": "snapshots/emp_002_clock_out_20250607_214530.jpg"
           }
       ]
   }

6. GET /api/snapshot/<filename>
   Get snapshot image by filename
   Returns: JPEG image

7. GET /video_feed
   MJPEG stream of live camera feed
   Returns: multipart/x-mixed-replace MJPEG stream

WebSocket Events:

From Server to Client:
  - initial_data: {attendance_today, clocked_in_staff, pending_clockouts}
  - clock_in_event: {employee_id, name, dept, time, confidence, snapshot_path}
  - clock_out_pending: {pending_id, employee_id, name, dept, time, confidence}
  - clock_out_confirmed: {employee_id, name, time, confidence, duration_mins}
  - attendance_update: {data, clocked_in, timestamp}

From Client to Server:
  - request_attendance: (no payload)
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
"""
Backend Configuration (in app.py):

SHIFT_START = 9       # 9 AM (clock-in window opens)
SHIFT_END = 22        # 10 PM (clock-out window opens)
OUTLET = "Front Door" # Location identifier
CAMERA_INDEX = 0      # 0 for default, 1+ for other cameras
CAMERA_W = 640        # Camera width
CAMERA_H = 480        # Camera height

Event Logger Configuration (in event_logger.py):

SHIFT_END_HOUR = 22   # Must match backend

Attendance Rules:
- Clock-in can happen anytime (no time restriction)
- Clock-out only after 9 PM (SHIFT_END hour)
- Only one clock-in per employee per day
- Clock-out requires admin confirmation (shows modal on dashboard)
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════
"""
Table: attendance_records
┌─────────────────────────────────────────────────────────────────────┐
│ id (int, PK)        │ Auto-increment record ID                      │
│ employee_id (text)  │ Unique identifier (e.g., "emp_001")           │
│ name (text)         │ Display name                                  │
│ outlet (text)       │ Location ("Front Door")                       │
│ date (date)         │ YYYY-MM-DD                                    │
│ clock_in_time (time)│ HH:MM:SS                                      │
│ clock_out_time (time, NULL) │ HH:MM:SS or NULL if not clocked out   │
│ duration_mins (int, NULL)   │ Calculated when clocked out           │
│ clock_in_conf (real)│ Confidence 0.0-1.0                            │
│ clock_out_conf (real, NULL) │ Confidence when clocking out          │
│ clock_in_snapshot (text)    │ Path to snapshot file                 │
│ clock_out_snapshot (text, NULL) │ Path to snapshot file             │
│ status (text)       │ 'clocked_in' | 'completed'                   │
│ created_at (timestamp) │ When record was created                    │
└─────────────────────────────────────────────────────────────────────┘

Table: pending_clockouts
┌─────────────────────────────────────────────────────────────────────┐
│ id (int, PK)        │ Auto-increment ID                             │
│ employee_id (text)  │ Who is clocking out                           │
│ name (text)         │ Display name                                  │
│ detected_at (timestamp) │ When the face was detected               │
│ confidence (real)    │ Match confidence                              │
│ snapshot_path (text) │ Path to the detection snapshot               │
│ attendance_record_id (int, FK) │ References attendance_records     │
└─────────────────────────────────────────────────────────────────────┘
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  FLOW DIAGRAM
# ═══════════════════════════════════════════════════════════════════════════════
"""
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLOCK-IN FLOW (9 AM - 10 PM)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Recognition Engine         Event Logger              Flask Backend          │
│  ───────────────           ─────────────              ─────────────           │
│                                                                               │
│  1. Detect face ──→                                                          │
│                                                                               │
│  2. Match embedding ──→                                                      │
│                                                                               │
│  3. Get result      ──→ log_event()                                          │
│     (name, dept,        ├─ Check if already clocked in                      │
│      conf)              ├─ Save snapshot                                    │
│                         └─ Queue for HTTP send                              │
│                                                                               │
│  4. Display on         (async background)                                    │
│     screen        ←──── HTTP POST /api/event ────→ Create attendance_record  │
│                         (non-blocking)              (status: clocked_in)      │
│                                                                               │
│                                              ←──── JSON response ────        │
│                                                                               │
│                                     Emit WebSocket broadcast                 │
│                                     (to all connected dashboards)            │
│                                                                               │
│                         Dashboard receives 'clock_in_event'                  │
│                         ├─ Add to "Currently Clocked In" list               │
│                         └─ Update attendance table                          │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    CLOCK-OUT FLOW (After 9 PM Only)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Recognition Engine         Event Logger              Flask Backend          │
│  ───────────────           ─────────────              ─────────────           │
│                                                                               │
│  1. Detect same face ──→                                                     │
│     after 9 PM                                                               │
│                                                                               │
│  2. log_event()   ───────→ Create pending_clockout                           │
│     (event='auto'          (awaiting admin confirmation)                     │
│      detects after 9pm)                                                      │
│                                                                               │
│  3. HTTP POST     ────────→ /api/event with 'clock_out'                      │
│     /api/event                                                               │
│                            ├─ Verify it's after 9 PM                         │
│                            ├─ Check employee is clocked in                   │
│                            ├─ Create pending_clockout record                 │
│                            └─ Emit WebSocket 'clock_out_pending'             │
│                                                                               │
│                         Dashboard receives 'clock_out_pending'               │
│                         ├─ Modal popup shows:                                │
│                         │  • Employee snapshot                               │
│                         │  • Name, confidence, time                          │
│                         │  • "Confirm Clock-Out" button                      │
│                         └─ Wait for admin click                              │
│                                                                               │
│                         Admin clicks "Confirm Clock-Out" ──→                 │
│                                                                               │
│                         POST /api/clockout/confirm/<pending_id>              │
│                         ├─ Update attendance_record:                        │
│                         │  • Set clock_out_time                              │
│                         │  • Calculate duration_mins                         │
│                         │  • Set status='completed'                          │
│                         ├─ Delete pending_clockout record                    │
│                         └─ Emit 'clock_out_confirmed'                        │
│                                                                               │
│                         Dashboard receives 'clock_out_confirmed'             │
│                         ├─ Remove from "Currently Clocked In"               │
│                         ├─ Update attendance table                          │
│                         └─ Show toast: "Jane clocked out"                   │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  TROUBLESHOOTING
# ═══════════════════════════════════════════════════════════════════════════════
"""
Problem: "Cannot reach backend at http://localhost:5000"
Solution:
  - Is app.py running? Check terminal for "Running on http://0.0.0.0:5000"
  - Port 5000 in use? Change in app.py: socketio.run(..., port=5001)
  - Firewall blocking? Check Windows Defender / OS firewall settings
  - Running from different machines? Use IP instead:
    AttendanceEventLogger(backend_url="http://192.168.1.100:5000")

Problem: Dashboard not showing up
Solution:
  - Browser cache? Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
  - Check browser console (F12) for JavaScript errors
  - Verify /video_feed is working: http://localhost:5000/video_feed in new tab

Problem: Events are not being logged
Solution:
  - Check attendance.log for errors
  - Verify event_logger.log_event() is being called from recognition.py
  - Check that employee_id and name are not empty strings
  - WebSocket connected? Check dashboard connection status

Problem: Clock-out modal not appearing
Solution:
  - Only appears after 9 PM (22:00)
  - Employee must be clocked in (status='clocked_in')
  - Check browser console for WebSocket errors
  - Try manual test: curl -X POST http://localhost:5000/api/event \
      -H "Content-Type: application/json" \
      -d '{
        "employee_id":"test_emp",
        "name":"Test User",
        "dept":"Test",
        "confidence":0.9,
        "snapshot_path":"snapshots/test.jpg",
        "event_type":"clock_out"
      }'

Problem: Database locked
Solution:
  - Only one app.py instance should run
  - Close all Python processes: pkill -f python
  - Restart app.py

Problem: Camera feed not showing
Solution:
  - Check CAMERA_INDEX in app.py (try 0, 1, 2)
  - Verify camera is not in use by another app
  - Try: python -c "import cv2; cap=cv2.VideoCapture(0); print(cap.isOpened())"

Problem: High CPU usage
Solution:
  - Reduce MJPEG frame rate (increase delay in dashboard)
  - Reduce camera resolution
  - Close unnecessary browser tabs
  - On multi-monitor setup, minimizing dashboard helps
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  PRODUCTION CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════
"""
Before deploying to production:

[ ] Change SECRET_KEY in app.py (not 'attendance-secret-key-change-in-prod')
[ ] Set debug=False in socketio.run() (already set, confirm)
[ ] Configure CORS allowed_origins to specific domain(s)
[ ] Set up SSL/HTTPS if accessing from different network
[ ] Configure backup of SQLite database (attendance.db)
[ ] Set up log rotation for attendance.log (gets large over time)
[ ] Test with multiple faces simultaneously
[ ] Test clock-out confirmation under various network conditions
[ ] Verify snapshots are saving correctly
[ ] Set up automated daily reset of tracking (9 AM)
[ ] Monitor disk space for snapshots directory
[ ] Create database export/reporting queries for management

Database Backup:
  cp attendance.db attendance.db.backup

Export Attendance Reports:
  sqlite3 attendance.db "SELECT * FROM attendance_records WHERE date = '2025-06-07' ORDER BY clock_in_time"

Log Monitoring:
  tail -f attendance.log
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  EXAMPLE CRON JOBS (Linux/Mac)
# ═══════════════════════════════════════════════════════════════════════════════
"""
Run these to keep the system healthy:

# Start attendance system at boot
@reboot cd /home/user/attendance-system && python app.py >> app.log 2>&1

# Backup database daily at 11 PM
0 23 * * * cp /home/user/attendance-system/attendance.db \
            /home/user/attendance-system/backups/attendance_$(date +\%Y\%m\%d).db

# Clear old snapshots (older than 30 days)
0 2 * * * find /home/user/attendance-system/snapshots -type f -mtime +30 -delete

# Restart if crashed (check every 5 minutes)
*/5 * * * * pgrep -f "python app.py" || \
            (cd /home/user/attendance-system && python app.py >> app.log 2>&1 &)
"""

print("Integration guide loaded. See comments above for detailed setup instructions.")
