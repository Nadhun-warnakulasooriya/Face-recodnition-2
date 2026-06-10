# Face Recognition Attendance System

A complete, production-ready attendance management system that integrates with your existing face recognition engine. Automatic clock-in on first detection, pending clock-out modal with admin confirmation, real-time WebSocket updates, and MJPEG camera feed on the dashboard.

**Shift:** 9 AM – 10 PM  
**Location:** Front Door  
**Database:** SQLite (auto-created)  
**Backend:** Flask + Flask-SocketIO  

---

## Quick Start (3 Steps)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Backend
```bash
python app.py
```
Server runs on `http://localhost:5000`

### 3. Integrate with Your Recognition Engine
See [Integration Guide](#integration) below.

---

## System Files

### Backend
- **`app.py`** (450 lines)
  - Flask REST API server with 7 endpoints
  - WebSocket event broadcasting
  - SQLite database management
  - MJPEG camera stream generation
  - Runs on port 5000

- **`event_logger.py`** (200 lines)
  - Plugs into your recognition.py
  - Non-blocking HTTP event sending (background thread)
  - Daily state tracking (prevents duplicate clock-ins)
  - Automatic snapshot saving
  - Auto-detects clock-in vs clock-out based on time

- **`dashboard.html`** (600 lines)
  - Real-time attendance dashboard
  - Live MJPEG camera feed
  - Currently clocked-in staff list
  - Today's attendance table with export
  - Clock-out confirmation modal (auto-triggered via WebSocket)
  - Responsive design (works on desktop & mobile)

### Configuration
- **`requirements.txt`** – Python dependencies
- **`INTEGRATION_GUIDE.py`** – Complete setup & integration documentation
- **`test_system.py`** – Automated test suite to verify system is working

---

## Integration with Your Recognition Code

### Option A: Minimal (Copy-Paste)

At the top of your `recognition.py`:
```python
from event_logger import AttendanceEventLogger
event_logger = AttendanceEventLogger(backend_url="http://localhost:5000")
```

Inside your recognition worker, after getting a match:
```python
if name != "Unknown Person":
    event_logger.log_event(
        employee_id=face_key,      # or f"emp_{person_id}"
        name=name,
        dept=dept,
        confidence=conf,
        frame_bgr=roi_bgr,         # Face crop
        event_type='auto'          # Auto-detects clock-in vs out
    )
```

### Option B: Full Setup
See `INTEGRATION_GUIDE.py` for detailed examples with:
- Daily state reset at 9 AM
- Error handling
- Custom employee ID schemes
- Testing with curl

---

## Database Schema

### `attendance_records` Table
| Column | Type | Notes |
|--------|------|-------|
| id | INT (PK) | Auto-increment |
| employee_id | TEXT | Unique identifier |
| name | TEXT | Display name |
| outlet | TEXT | "Front Door" |
| date | DATE | YYYY-MM-DD |
| clock_in_time | TIME | HH:MM:SS |
| clock_out_time | TIME | NULL until clocked out |
| duration_mins | INT | Auto-calculated |
| clock_in_conf | REAL | 0.0–1.0 confidence |
| clock_out_conf | REAL | NULL until clock-out |
| clock_in_snapshot | TEXT | File path |
| clock_out_snapshot | TEXT | File path |
| status | TEXT | `clocked_in` \| `completed` |
| created_at | TIMESTAMP | Auto |

### `pending_clockouts` Table
| Column | Type | Notes |
|--------|------|-------|
| id | INT (PK) | Auto-increment |
| employee_id | TEXT | Employee ID |
| name | TEXT | Name |
| detected_at | TIMESTAMP | When detected |
| confidence | REAL | Match confidence |
| snapshot_path | TEXT | File path |
| attendance_record_id | INT | FK to attendance_records |

---

## API Reference

### REST Endpoints

**`POST /api/event`** – Log clock-in/out event
```json
{
  "employee_id": "emp_001",
  "name": "John Doe",
  "dept": "Engineering",
  "confidence": 0.92,
  "snapshot_path": "snapshots/emp_001_clock_in_20250607_090000_123456.jpg",
  "event_type": "clock_in"
}
```

**`GET /api/attendance/today`** – Get today's records
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "John Doe",
      "clock_in_time": "09:15:30",
      "clock_out_time": null,
      "status": "clocked_in"
    }
  ]
}
```

**`GET /api/staff/clocked-in`** – Currently clocked-in staff

**`POST /api/clockout/confirm/<pending_id>`** – Admin confirms clock-out

**`GET /api/pending-clockouts`** – Get pending clock-outs

**`GET /api/snapshot/<filename>`** – Retrieve snapshot image

**`GET /video_feed`** – MJPEG stream of camera

### WebSocket Events

**From Server:**
- `initial_data` – Sent on connection
- `clock_in_event` – New clock-in
- `clock_out_pending` – Triggers dashboard modal
- `clock_out_confirmed` – Clock-out approved

---

## Shift & Rules

- **Shift Window:** 9 AM – 10 PM
- **Clock-In:** Anytime (first detection → auto clock-in)
- **Clock-Out:** Only after 9 PM (requires admin confirmation)
- **Daily Reset:** Tracking resets at 9 AM (optional, can be manual)
- **One Clock-In Per Day:** Duplicate clock-ins rejected (409 Conflict)

---

## Testing

Run the automated test suite:
```bash
python test_system.py
```

Tests:
1. Backend connection
2. Video feed
3. Clock-in event
4. Get attendance records
5. Clocked-in staff list
6. Clock-out event (if after 9 PM)
7. Pending clock-outs
8. Clock-out confirmation
9. Dashboard accessibility

---

## File Structure

```
attendance-system/
├── app.py                          ← Flask server (start this first)
├── event_logger.py                 ← Import into your recognition.py
├── dashboard.html                  ← Open in browser
├── requirements.txt                ← pip install -r requirements.txt
├── test_system.py                  ← python test_system.py
├── INTEGRATION_GUIDE.py            ← Detailed setup docs
├── attendance.db                   ← SQLite (auto-created)
├── attendance.log                  ← System logs
└── snapshots/                      ← Face photos (auto-created)
    ├── emp_001_clock_in_20250607_090000_123456.jpg
    ├── emp_001_clock_out_20250607_210000_789012.jpg
    └── ...
```

---

## Configuration

Edit these values in `app.py` if needed:

```python
SHIFT_START          = 9       # 9 AM
SHIFT_END            = 22      # 10 PM
OUTLET               = "Front Door"
CAMERA_INDEX         = 0       # 0 = default camera
CAMERA_W, CAMERA_H   = 640, 480
```

---

## Troubleshooting

### "Cannot reach backend"
- Is `app.py` running? Check for `Running on http://0.0.0.0:5000`
- Port 5000 in use? Check: `lsof -i :5000` (Mac/Linux) or Task Manager (Windows)
- Using different machine? Use IP instead: `http://192.168.1.100:5000`

### "Dashboard not connecting"
- Hard refresh browser: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
- Check browser console (F12) for JavaScript errors
- Verify WebSocket: Open DevTools → Network → Filter "WS"

### "Events not being logged"
- Is `event_logger.log_event()` being called from recognition.py?
- Check `attendance.log` for error messages
- Verify `employee_id` and `name` are not empty

### "Camera feed blank"
- Try different `CAMERA_INDEX` (0, 1, 2...)
- Check if camera is in use by another app
- Test camera manually: `python -c "import cv2; cap=cv2.VideoCapture(0); print(cap.isOpened())"`

See full troubleshooting in `INTEGRATION_GUIDE.py`.

---

## Performance Notes

- **CPU-Only:** Optimized for i5 12th-gen without GPU (your current setup)
- **Recognition:** Every 10 frames (non-blocking background threads)
- **Dashboard:** 30 FPS MJPEG stream (uses ~5-10% CPU)
- **Database:** SQLite handles up to 1000+ records easily

---

## Production Checklist

- [ ] Change `SECRET_KEY` in `app.py`
- [ ] Set up database backups
- [ ] Configure log rotation
- [ ] Test with multiple faces simultaneously
- [ ] Monitor disk space for snapshots
- [ ] Set up automated 9 AM reset (optional)
- [ ] Configure CORS for your domain
- [ ] Test clock-out after 9 PM

---

## License

This system is part of your FYP. Modify freely for your needs.

---

## Support

Check:
1. `attendance.log` for errors
2. Browser console (F12) for client-side issues
3. `INTEGRATION_GUIDE.py` for detailed docs
4. `test_system.py` to diagnose problems

---

**Ready to integrate?** Start with:
```bash
python app.py
```
Then modify `recognition.py` using the [Integration Guide](#integration) above.
