#!/usr/bin/env python3
"""
Face Recognition Attendance System — Flask Backend + WebSocket (Zero-Lag)
Database: MySQL (face_attendance)
Shift: 9 AM – 10 PM | Location: Front Door
"""

import os
import threading
import logging
from datetime import datetime
from pathlib import Path
import cv2
import numpy as np
import base64
import json
import pickle
from deepface import DeepFace
from flask import Flask, jsonify, request, Response, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import mysql.connector
from mysql.connector import pooling

# ═══════════════════════════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('attendance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
SNAPSHOTS_DIR  = "snapshots"
CAMERA_INDEX   = 0
CAMERA_W       = 640
CAMERA_H       = 480
OUTLET         = "Front Door"
SHIFT_START    = 9    # 9 AM
SHIFT_END      = 22   # 10 PM

# ── MySQL credentials ──────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":       "127.0.0.1",
    "port":       3306,
    "user":       "root",   
    "password":   "",       
    "database":   "face_attendance",
    "charset":    "utf8mb4",
    "autocommit": False,
}

Path(SNAPSHOTS_DIR).mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  CONNECTION POOL
# ═══════════════════════════════════════════════════════════════════════════════
try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="attendance_pool",
        pool_size=5,
        **DB_CONFIG
    )
    logger.info("MySQL connection pool ready.")
except mysql.connector.Error as e:
    logger.critical(f"Cannot connect to MySQL: {e}")
    logger.critical("Make sure XAMPP MySQL is running and DB_CONFIG is correct.")
    raise SystemExit(1)


def get_db():
    """Return a connection from the pool."""
    return db_pool.get_connection()


# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE INITIALISATION
# ═══════════════════════════════════════════════════════════════════════════════
def _add_column(cursor, conn, table, col_name, col_def):
    try:
        cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{col_name}` {col_def}")
        conn.commit()
        logger.info(f"  + {table}.{col_name}")
    except mysql.connector.Error as e:
        conn.rollback()
        if e.errno != 1060:   
            logger.warning(f"  Cannot add {table}.{col_name}: {e}")


def init_db():
    conn = get_db()
    c    = conn.cursor()

    attendance_extras = [
        ("outlet",             "VARCHAR(50) DEFAULT 'Front Door'"),
        ("clock_in_time",      "TIME DEFAULT NULL"),
        ("clock_out_time",     "TIME DEFAULT NULL"),
        ("duration_mins",      "INT DEFAULT NULL"),
        ("clock_in_conf",      "FLOAT DEFAULT NULL"),
        ("clock_out_conf",     "FLOAT DEFAULT NULL"),
        ("clock_in_snapshot",  "TEXT DEFAULT NULL"),
        ("clock_out_snapshot", "TEXT DEFAULT NULL"),
        ("att_status",         "ENUM('clocked_in','completed') DEFAULT 'clocked_in'"),
    ]
    for col, defn in attendance_extras:
        _add_column(c, conn, "attendance", col, defn)

    c.execute("""
        CREATE TABLE IF NOT EXISTS `pending_clockouts` (
            `id`            INT AUTO_INCREMENT PRIMARY KEY,
            `emp_id`        VARCHAR(20)  NOT NULL,
            `name`          VARCHAR(100) NOT NULL,
            `detected_at`   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            `confidence`    FLOAT        NOT NULL,
            `snapshot_path` TEXT         NOT NULL,
            `attendance_id` INT          NOT NULL,
            FOREIGN KEY (`emp_id`) REFERENCES `employees`(`emp_id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    conn.close()
    logger.info("Database check complete (face_attendance / MySQL).")

init_db()

# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def rows_as_dicts(cursor):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

def get_today_attendance():
    conn = get_db()
    c    = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("""
        SELECT
            a.id, a.emp_id AS employee_id, e.name,
            COALESCE(a.outlet, %s) AS outlet,
            COALESCE(a.clock_in_time,  TIME(a.check_in)) AS clock_in_time,
            COALESCE(a.clock_out_time, TIME(a.check_out)) AS clock_out_time,
            a.duration_mins, a.clock_in_conf, a.clock_out_conf,
            COALESCE(a.att_status, a.status) AS status
        FROM attendance a
        JOIN employees e ON a.emp_id = e.emp_id
        WHERE DATE(a.check_in) = %s
        ORDER BY a.check_in DESC
    """, (OUTLET, today))
    result = rows_as_dicts(c)
    conn.close()
    return result

def get_pending_clockouts():
    conn = get_db()
    c    = conn.cursor()
    c.execute("""
        SELECT id, emp_id AS employee_id, name,
               detected_at, confidence, snapshot_path, attendance_id
        FROM pending_clockouts
        ORDER BY detected_at DESC
    """)
    result = rows_as_dicts(c)
    conn.close()
    return result

def get_clocked_in_staff():
    conn  = get_db()
    c     = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("""
        SELECT
            a.id, a.emp_id AS employee_id, e.name,
            COALESCE(a.clock_in_time, TIME(a.check_in)) AS clock_in_time,
            a.clock_in_conf
        FROM attendance a
        JOIN employees e ON a.emp_id = e.emp_id
        WHERE DATE(a.check_in) = %s
          AND a.check_out IS NULL
          AND COALESCE(a.att_status, a.status) = 'clocked_in'
        ORDER BY a.check_in DESC
    """, (today,))
    result = rows_as_dicts(c)
    conn.close()
    return result

def log_activity(emp_id, confidence, status='active'):
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute("""
            INSERT INTO activity_logs (emp_id, activity_status, confidence_score)
            VALUES (%s, %s, %s)
        """, (emp_id, status, confidence))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"activity_logs insert failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  FLASK + SOCKETIO SETUP
# ═══════════════════════════════════════════════════════════════════════════════
app = Flask(__name__)
app.config['SECRET_KEY'] = 'attendance-secret-key-change-in-prod'
CORS(app)

# --- වෙනස් කළ කොටස: async_mode='threading' හරහා කාර්යක්ෂමතාවය වැඩි කර ඇත ---
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ═══════════════════════════════════════════════════════════════════════════════
#  NEW: EMPLOYEE REGISTRATION API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
# Temporary session to hold data during the 5 poses
registration_session = {
    'emp_id': '',
    'name': '',
    'outlet': '',
    'embeddings': []
}

# Load OpenCV DNN for fast live detection bounding boxes on the website
dnn_net = None
PROTOTXT_PATH = "deploy.prototxt"
CAFFEMODEL_PATH = "res10_300x300_ssd_iter_140000.caffemodel"
try:
    if os.path.exists(PROTOTXT_PATH) and os.path.exists(CAFFEMODEL_PATH):
        dnn_net = cv2.dnn.readNetFromCaffe(PROTOTXT_PATH, CAFFEMODEL_PATH)
        logger.info("OpenCV DNN loaded for web registration live view.")
except Exception as e:
    logger.warning(f"Could not load OpenCV DNN: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    """Returns total registered count for the dashboard badge."""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM employees")
        count = c.fetchone()[0]
        conn.close()
        return jsonify({"status": "ok", "registered_count": count})
    except Exception:
        return jsonify({"status": "error", "registered_count": 0})

@app.route('/check_id', methods=['GET'])
def check_id():
    """Checks if employee ID is already taken."""
    user_id = request.args.get('user_id')
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT emp_id FROM employees WHERE emp_id = %s", (user_id,))
        exists = c.fetchone() is not None
        conn.close()
        return jsonify({"exists": exists})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/set_meta', methods=['POST'])
def set_meta():
    """Initializes a new registration session."""
    global registration_session
    data = request.get_json()
    registration_session['emp_id'] = data.get('user_id', '').strip()
    registration_session['name'] = data.get('name', '').strip()
    registration_session['outlet'] = data.get('outlet', '').strip()
    registration_session['embeddings'] = []
    return jsonify({"success": True})

@app.route('/reset', methods=['POST'])
def reset_reg():
    """Clears the ongoing registration session."""
    global registration_session
    registration_session = {'emp_id': '', 'name': '', 'outlet': '', 'embeddings': []}
    return jsonify({"success": True})

@app.route('/live_detect', methods=['POST'])
def live_detect():
    """Fast polling endpoint for the green bounding box on index.php."""
    try:
        data = request.get_json()
        img_b64 = data.get('image', '').split(',')[1]
        img_data = base64.b64decode(img_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        face_boxes = []
        if dnn_net is not None:
            h, w = img.shape[:2]
            blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
            dnn_net.setInput(blob)
            detections = dnn_net.forward()
            
            for i in range(detections.shape[2]):
                conf = detections[0, 0, i, 2]
                if conf > 0.6:  # 60% confidence threshold
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    x1, y1, x2, y2 = box.astype("int")
                    face_boxes.append({
                        "x": int(x1), "y": int(y1),
                        "w": int(x2-x1), "h": int(y2-y1),
                        "conf": f"{conf:.0%}"
                    })

        return jsonify({"face_boxes": face_boxes})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/capture', methods=['POST'])
def capture_pose():
    """Process high-res frame via DeepFace and extract Facenet512 embeddings."""
    global registration_session
    try:
        data = request.get_json()
        img_b64 = data.get('image', '').split(',')[1]
        img_data = base64.b64decode(img_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # DeepFace Processing (Retinaface + Facenet512)
        results = DeepFace.represent(
            img_path=rgb_img,
            model_name="Facenet512",
            detector_backend="retinaface",
            enforce_detection=True
        )

        if len(results) == 1:
            emb = results[0]["embedding"]
            registration_session['embeddings'].append(emb)

            area = results[0].get('facial_area', {})
            box = []
            if area:
                box = [{"x": area.get('x'), "y": area.get('y'), "w": area.get('w'), "h": area.get('h'), "conf": "100%"}]

            return jsonify({"success": True, "face_boxes": box})
        elif len(results) > 1:
            return jsonify({"success": False, "message": "Multiple faces detected! Please stand alone."})
        else:
            return jsonify({"success": False, "message": "No face detected."})

    except ValueError:
        return jsonify({"success": False, "message": "Face not detected. Adjust lighting/angle."})
    except Exception as e:
        logger.error(f"/capture error: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/save', methods=['POST'])
def save_registration():
    """Saves finalized embeddings to MySQL and Pickle file."""
    global registration_session
    try:
        emp_id = registration_session.get('emp_id')
        name = registration_session.get('name')
        outlet = registration_session.get('outlet', 'Unassigned')
        embeddings = registration_session.get('embeddings')

        if not emp_id or not name or not embeddings:
            return jsonify({"success": False, "message": "Missing data or no poses captured."}), 400

        # 1. Save to MySQL (Table: employees)
        conn = get_db()
        c = conn.cursor()
        emb_json = json.dumps(embeddings)

        c.execute("""
            INSERT INTO employees (emp_id, name, outlet, face_embeddings)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            name=VALUES(name), outlet=VALUES(outlet), face_embeddings=VALUES(face_embeddings)
        """, (emp_id, name, outlet, emb_json))
        conn.commit()
        
        # Get latest total count
        c.execute("SELECT COUNT(*) FROM employees")
        total_registered = c.fetchone()[0]
        conn.close()

        # 2. Save to Pickle File (for Display-v2.py)
        db_file = "deepface_database.pkl"
        db_data = {}
        if os.path.exists(db_file):
            with open(db_file, "rb") as f:
                db_data = pickle.load(f)

        db_data[emp_id] = {
            "name": name,
            "id": emp_id,
            "dept": outlet,
            "embeddings": embeddings,
            "num_poses": len(embeddings)
        }

        with open(db_file, "wb") as f:
            pickle.dump(db_data, f)

        # Clear session after successful save
        registration_session = {'emp_id': '', 'name': '', 'outlet': '', 'embeddings': []}

        logger.info(f"New Employee Registered: {name} ({emp_id})")
        return jsonify({"success": True, "total_registered": total_registered})

    except Exception as e:
        logger.error(f"/save error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
#  EXISTING REST API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.route('/api/event', methods=['POST'])
def log_event():
    """Receive clock-in / clock-out from recognition engine."""
    try:
        data       = request.get_json()
        emp_id     = data.get('employee_id')
        name       = data.get('name')
        dept       = data.get('dept', 'Unassigned')
        conf       = float(data.get('confidence', 0.0))
        snapshot   = data.get('snapshot_path')
        event_type = data.get('event_type', 'clock_in')

        if not emp_id or not name:
            return jsonify({'error': 'Missing employee_id or name'}), 400

        conn     = get_db()
        c        = conn.cursor()
        today    = datetime.now().strftime("%Y-%m-%d")
        now_dt   = datetime.now()
        now_time = now_dt.strftime("%H:%M:%S")

        # ── CLOCK-IN ──────────────────────────────────────────────────────────
        if event_type == 'clock_in':
            c.execute("""
                SELECT id FROM attendance
                WHERE emp_id = %s AND DATE(check_in) = %s AND check_out IS NULL
            """, (emp_id, today))
            if c.fetchone():
                conn.close()
                return jsonify({'error': 'Already clocked in today'}), 409

            c.execute("""
                INSERT INTO attendance
                    (emp_id, check_in, status,
                     outlet, clock_in_time, clock_in_conf,
                     clock_in_snapshot, att_status)
                VALUES (%s, %s, 'present', %s, %s, %s, %s, 'clocked_in')
            """, (emp_id, now_dt, OUTLET, now_time, conf, snapshot))
            conn.commit()
            record_id = c.lastrowid
            conn.close()

            threading.Thread(
                target=log_activity, args=(emp_id, conf, 'active'), daemon=True
            ).start()

            logger.info(f"Clock-in: {name} ({emp_id}) at {now_time} | conf={conf:.2f}")
            socketio.emit('clock_in_event', {
                'employee_id':  emp_id,
                'name':         name,
                'dept':         dept,
                'time':         now_time,
                'confidence':   conf,
                'snapshot_path': snapshot
            }, broadcast=True)

            return jsonify({'success': True, 'record_id': record_id,
                            'event': 'clock_in'}), 201

        # ── CLOCK-OUT ─────────────────────────────────────────────────────────
        elif event_type == 'clock_out':
            if now_dt.hour < SHIFT_END:
                conn.close()
                return jsonify({
                    'error': f'Clock-out window not open. Opens at {SHIFT_END}:00'
                }), 403

            c.execute("""
                SELECT id FROM attendance
                WHERE emp_id = %s AND DATE(check_in) = %s AND check_out IS NULL
            """, (emp_id, today))
            row = c.fetchone()
            if not row:
                conn.close()
                return jsonify({'error': 'Not clocked in today'}), 409

            attendance_id = row[0]

            c.execute("""
                INSERT INTO pending_clockouts
                    (emp_id, name, confidence, snapshot_path, attendance_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (emp_id, name, conf, snapshot, attendance_id))
            conn.commit()
            pending_id = c.lastrowid
            conn.close()

            threading.Thread(
                target=log_activity, args=(emp_id, conf, 'active'), daemon=True
            ).start()

            logger.info(f"Clock-out pending: {name} ({emp_id}) at {now_time} | conf={conf:.2f}")
            socketio.emit('clock_out_pending', {
                'pending_id':           pending_id,
                'employee_id':          emp_id,
                'name':                 name,
                'dept':                 dept,
                'time':                 now_time,
                'confidence':           conf,
                'snapshot_path':        snapshot,
                'attendance_record_id': attendance_id
            }, broadcast=True)

            return jsonify({'success': True, 'pending_id': pending_id,
                            'event': 'clock_out_pending'}), 201

        else:
            return jsonify({'error': 'Unknown event_type'}), 400

    except Exception as e:
        logger.error(f"/api/event error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/attendance/today', methods=['GET'])
def get_attendance_today():
    try:
        return jsonify({'success': True, 'data': get_today_attendance()}), 200
    except Exception as e:
        logger.error(f"/api/attendance/today: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/staff/clocked-in', methods=['GET'])
def get_clocked_in():
    try:
        return jsonify({'success': True, 'data': get_clocked_in_staff()}), 200
    except Exception as e:
        logger.error(f"/api/staff/clocked-in: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/clockout/confirm/<int:pending_id>', methods=['POST'])
def confirm_clockout(pending_id):
    try:
        conn = get_db()
        c    = conn.cursor()

        c.execute("""
            SELECT attendance_id, emp_id, name, confidence, snapshot_path
            FROM pending_clockouts WHERE id = %s
        """, (pending_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Pending clock-out not found'}), 404

        attendance_id, emp_id, name, conf, snapshot = row

        c.execute("SELECT check_in FROM attendance WHERE id = %s", (attendance_id,))
        ci_row = c.fetchone()
        now_dt       = datetime.now()
        now_time     = now_dt.strftime("%H:%M:%S")
        duration_mins = None
        if ci_row and ci_row[0]:
            try:
                duration_mins = int((now_dt - ci_row[0]).total_seconds() / 60)
            except Exception:
                pass

        c.execute("""
            UPDATE attendance
            SET check_out          = %s,
                clock_out_time     = %s,
                clock_out_conf     = %s,
                clock_out_snapshot = %s,
                duration_mins      = %s,
                att_status         = 'completed'
            WHERE id = %s
        """, (now_dt, now_time, conf, snapshot, duration_mins, attendance_id))

        c.execute("DELETE FROM pending_clockouts WHERE id = %s", (pending_id,))
        conn.commit()
        conn.close()

        threading.Thread(
            target=log_activity, args=(emp_id, conf, 'idle'), daemon=True
        ).start()

        logger.info(f"Clock-out confirmed: {name} ({emp_id}) at {now_time}")
        socketio.emit('clock_out_confirmed', {
            'employee_id':   emp_id,
            'name':          name,
            'time':          now_time,
            'confidence':    conf,
            'duration_mins': duration_mins
        }, broadcast=True)

        return jsonify({
            'success':       True,
            'message':       f'{name} clocked out',
            'duration_mins': duration_mins
        }), 200

    except Exception as e:
        logger.error(f"/api/clockout/confirm: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/pending-clockouts', methods=['GET'])
def get_pendings():
    try:
        return jsonify({'success': True, 'data': get_pending_clockouts()}), 200
    except Exception as e:
        logger.error(f"/api/pending-clockouts: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/snapshot/<path:filename>', methods=['GET'])
def get_snapshot(filename):
    try:
        filepath = os.path.join(SNAPSHOTS_DIR, filename)
        if os.path.exists(filepath):
            return send_file(filepath, mimetype='image/jpeg')
        return jsonify({'error': 'Snapshot not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
#  LIVE VIDEO FRAME RECEIVER FOR DASHBOARD (ZERO-LAG WEBSOCKET)
# ═══════════════════════════════════════════════════════════════════════════════
@app.route('/api/video_frame', methods=['POST'])
def api_video_frame():
    """Receive JPEG bytes → push INSTANTLY to browser via WebSockets."""
    try:
        data = request.data
        if data:
            # අලුතින් Background Task සාදමින් පෝලිම් ගැසීම වෙනුවට සෘජුවම emit කරයි
            b64 = base64.b64encode(data).decode('utf-8')
            socketio.emit('video_stream', {'frame': b64}, namespace='/')
            
        return '', 204
    except Exception as e:
        logger.error(f"/api/video_frame error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
@app.route('/dashboard.php')
def dashboard():
    dashboard_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard.php')
    if os.path.exists(dashboard_path):
        return send_file(dashboard_path)
    return (
        "<h2>dashboard.php not found</h2>"
        "<p>Make sure <b>dashboard.php</b> is in the same folder as <b>app.py</b>.</p>"
        f"<p>Expected location: <code>{dashboard_path}</code></p>"
    ), 404


@app.route('/api/employees', methods=['GET'])
def get_employees():
    try:
        conn = get_db()
        c    = conn.cursor()
        c.execute("SELECT emp_id, name, outlet FROM employees ORDER BY name")
        result = rows_as_dicts(c)
        conn.close()
        return jsonify({'success': True, 'data': result}), 200
    except Exception as e:
        logger.error(f"/api/employees: {e}")
        return jsonify({'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
#  WEBSOCKET EVENTS
# ═══════════════════════════════════════════════════════════════════════════════

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    emit('initial_data', {
        'attendance_today': get_today_attendance(),
        'clocked_in_staff': get_clocked_in_staff(),
        'pending_clockouts': get_pending_clockouts(),
        'shift_end_hour':   SHIFT_END
    })

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('request_attendance')
def handle_attendance_request():
    emit('attendance_update', {
        'data':       get_today_attendance(),
        'clocked_in': get_clocked_in_staff(),
        'timestamp':  datetime.now().isoformat()
    })

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("Face Recognition Attendance & Registration System  |  MySQL backend")
    logger.info(f"Shift    : {SHIFT_START}:00 AM — {SHIFT_END}:00")
    logger.info(f"Location : {OUTLET}")
    logger.info(f"Database : {DB_CONFIG['host']} / {DB_CONFIG['database']}")
    logger.info(f"Snapshots: {SNAPSHOTS_DIR}/")
    logger.info("=" * 80)

    socketio.run(app, host='0.0.0.0', port=5000, debug=False,
                 allow_unsafe_werkzeug=True)