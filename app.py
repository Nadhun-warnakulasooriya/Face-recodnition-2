#!/usr/bin/env python3
"""
Face Recognition Attendance System — Multi-Tenant SaaS Backend
Database: MySQL (face_attendance)
"""

import os
import threading
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
import cv2
import numpy as np
import base64
import json
import urllib.request # මේක අලුතින් එකතු කළා (ෆයිල් ඩවුන්ලෝඩ් කිරීමට)
from deepface import DeepFace
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room



# ═══════════════════════════════════════════════════════════════════════════════
#  ADD THESE TWO LINES TO FIX THE NAMEERROR
# ═══════════════════════════════════════════════════════════════════════════════
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
OUTLET         = "Front Door"
SHIFT_START    = 9    
SHIFT_END      = 22   

# ── MySQL credentials ──────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":       "127.0.0.1",
    "port":       3306,
    "user":       "root",   # ඔයාගේ සර්වර් එකේ user
    "password":   "",       
    "database":   "face_attendance",
    "charset":    "utf8mb4",
    "autocommit": False,
}

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
    raise SystemExit(1)

def get_db():
    return db_pool.get_connection()

# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE HELPERS & MULTI-TENANT LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
def rows_as_dicts(cursor):
    cols = [d[0] for d in cursor.description]
    out = []
    for row in cursor.fetchall():
        d = {}
        for i, val in enumerate(row):
            if isinstance(val, timedelta):
                d[cols[i]] = str(val) 
            elif isinstance(val, (datetime, date)):
                d[cols[i]] = val.isoformat() 
            else:
                d[cols[i]] = val
        out.append(d)
    return out

def get_company_by_api_key(api_key):
    """API Key එක හරහා සමාගම හඳුනාගැනීම"""
    if not api_key:
        return None
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, company_name FROM companies WHERE api_key = %s", (api_key,))
    res = c.fetchone()
    conn.close()
    return res

def get_today_attendance(company_id):
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
        WHERE DATE(a.check_in) = %s AND a.company_id = %s
        ORDER BY a.check_in DESC
    """, (OUTLET, today, company_id))
    result = rows_as_dicts(c)
    conn.close()
    return result

def get_clocked_in_staff(company_id):
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
        WHERE DATE(a.check_in) = %s AND a.company_id = %s
          AND a.check_out IS NULL
          AND COALESCE(a.att_status, a.status) = 'clocked_in'
        ORDER BY a.check_in DESC
    """, (today, company_id))
    result = rows_as_dicts(c)
    conn.close()
    return result

# ═══════════════════════════════════════════════════════════════════════════════
#  FLASK + SOCKETIO SETUP
# ═══════════════════════════════════════════════════════════════════════════════
app = Flask(__name__)
app.config['SECRET_KEY'] = 'saas-attendance-secret'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


# ═══════════════════════════════════════════════════════════════════════════════
#  WEB REGISTRATION (DASHBOARD) ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
registration_session = {
    'company_id': None,
    'emp_id': '',
    'name': '',
    'outlet': '',
    'embeddings': []
}

# [NEW] ඉතාමත් සැහැල්ලු සහ වේගවත් Face Detector එක (Download වීම් අනවශ්‍යයි)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
# --- AI PRE-WARMING (මෙයින් බොත්තම එබූ පසු හිරවීම වළක්වයි) ---
logger.info("Pre-warming DeepFace Facenet512 Model. Please wait...")
try:
    _dummy_img = np.zeros((160, 160, 3), dtype=np.uint8)
    DeepFace.represent(img_path=_dummy_img, model_name="Facenet512", detector_backend="opencv", enforce_detection=False)
    logger.info("DeepFace Model loaded to RAM successfully!")
except Exception as e:
    logger.warning(f"DeepFace pre-warm failed: {e}")
@app.route('/set_meta', methods=['POST'])
def set_meta():
    global registration_session
    data = request.get_json(force=True, silent=True) or {}
    registration_session['company_id'] = data.get('company_id') 
    registration_session['emp_id'] = data.get('user_id', '').strip()
    registration_session['name'] = data.get('name', '').strip()
    registration_session['outlet'] = data.get('outlet', '').strip()
    registration_session['embeddings'] = []
    return jsonify({"success": True})

@app.route('/reset', methods=['POST'])
def reset_reg():
    global registration_session
    registration_session = {'company_id': None, 'emp_id': '', 'name': '', 'outlet': '', 'embeddings': []}
    return jsonify({"success": True})

@app.route('/live_detect', methods=['POST'])
def live_detect():
    try:
        data = request.get_json()
        img_b64 = data.get('image', '').split(',')[1]
        img_data = base64.b64decode(img_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        face_boxes = []
        # අලුත් සැහැල්ලු ක්‍රමයට Bounding Box ඇඳීම
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        for (x, y, w, h) in faces:
            face_boxes.append({
                "x": int(x), "y": int(y), "w": int(w), "h": int(h),
                "conf": "100%"
            })
        return jsonify({"face_boxes": face_boxes})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/capture', methods=['POST'])
def capture_pose():
    global registration_session
    try:
        data = request.get_json()
        img_b64 = data.get('image', '').split(',')[1]
        img_data = base64.b64decode(img_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # [FIXED] retinaface වෙනුවට opencv යොදා ඇත. (VPS එක Crash නොවේ)
        results = DeepFace.represent(img_path=rgb_img, model_name="Facenet512", detector_backend="opencv", enforce_detection=True)

        if len(results) == 1:
            emb = results[0]["embedding"]
            registration_session['embeddings'].append(emb)
            area = results[0].get('facial_area', {})
            box = [{"x": area.get('x'), "y": area.get('y'), "w": area.get('w'), "h": area.get('h'), "conf": "100%"}] if area else []
            return jsonify({"success": True, "face_boxes": box})
        elif len(results) > 1:
            return jsonify({"success": False, "message": "Multiple faces detected! Please stand alone."})
        else:
            return jsonify({"success": False, "message": "No face detected."})

    except ValueError:
        return jsonify({"success": False, "message": "Face not detected. Adjust lighting."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/save', methods=['POST'])
def save_registration():
    global registration_session
    try:
        company_id = registration_session.get('company_id')
        emp_id = registration_session.get('emp_id')
        name = registration_session.get('name')
        outlet = registration_session.get('outlet', 'Unassigned')
        embeddings = registration_session.get('embeddings')

        if not emp_id or not name or not embeddings or not company_id:
            return jsonify({"success": False, "message": "Missing data or Company ID."}), 400

        conn = get_db()
        c = conn.cursor()
        
        clean_embeddings = [[float(val) for val in emb] for emb in embeddings]
        emb_json = json.dumps(clean_embeddings)

        c.execute("""
            INSERT INTO employees (emp_id, company_id, name, outlet, face_embeddings)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            name=VALUES(name), outlet=VALUES(outlet), face_embeddings=VALUES(face_embeddings)
        """, (emp_id, company_id, name, outlet, emb_json))
        
        conn.commit()
        conn.close()

        registration_session = {'company_id': None, 'emp_id': '', 'name': '', 'outlet': '', 'embeddings': []}
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ═══════════════════════════════════════════════════════════════════════════════
#  EDGE PC ENDPOINTS (SYNC & ATTENDANCE)
# ═══════════════════════════════════════════════════════════════════════════════
@app.route('/api/sync_faces', methods=['POST'])
def sync_faces():
    """Edge PC එක විවෘත වන විට මූණු දත්ත ඩවුන්ලෝඩ් කිරීමට"""
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        company = get_company_by_api_key(api_key)
        
        if not company:
            return jsonify({"error": "Invalid API Key"}), 401
            
        company_id = company[0]
        company_name = company[1]

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT emp_id, name, outlet, face_embeddings FROM employees WHERE company_id = %s", (company_id,))
        
        employees_data = {}
        for row in c.fetchall():
            emp_id, name, outlet, emb_str = row
            if emb_str:
                employees_data[emp_id] = {
                    "id": emp_id,
                    "name": name,
                    "dept": outlet,
                    "embeddings": json.loads(emb_str)
                }
        conn.close()
        
        return jsonify({"success": True, "company_name": company_name, "database": employees_data}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/event', methods=['POST'])
def log_event():
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        company = get_company_by_api_key(api_key)
        
        if not company:
            return jsonify({'error': 'Unauthorized API Key'}), 401
            
        company_id = company[0]

        emp_id     = data.get('employee_id') or data.get('emp_id')
        name       = data.get('name')
        dept       = data.get('dept', 'Unassigned')
        conf       = float(data.get('confidence', 0.0))
        event_type = data.get('event_type', 'auto') 

        if not emp_id or not name:
            return jsonify({'error': 'Missing employee_id or name'}), 400

        conn     = get_db()
        c        = conn.cursor()
        now_dt   = datetime.now()
        now_time = now_dt.strftime("%H:%M:%S")

        c.execute("""
            SELECT id, check_in FROM attendance
            WHERE emp_id = %s AND company_id = %s AND check_out IS NULL
            ORDER BY check_in DESC LIMIT 1
        """, (emp_id, company_id))
        active_session = c.fetchone()

        if event_type == 'auto':
            if not active_session:
                event_type = 'clock_in'
            else:
                if now_dt.hour >= SHIFT_END: 
                    event_type = 'clock_out'
                else:
                    conn.close()
                    return jsonify({'message': f'{name} already clocked in.'}), 200

        if event_type == 'clock_in':
            if active_session:
                 conn.close()
                 return jsonify({'error': 'Already clocked in today'}), 409

            c.execute("""
                INSERT INTO attendance
                    (company_id, emp_id, check_in, status,
                     outlet, clock_in_time, clock_in_conf, att_status)
                VALUES (%s, %s, %s, 'present', %s, %s, %s, 'clocked_in')
            """, (company_id, emp_id, now_dt, OUTLET, now_time, conf))
            conn.commit()
            conn.close()

            logger.info(f"[{company[1]}] Clock-in: {name} ({emp_id})")
            socketio.emit('clock_in_event', {
                'employee_id': emp_id, 'name': name, 'dept': dept, 'time': now_time
            }, room=f"company_{company_id}")

            return jsonify({'success': True, 'event': 'clock_in'}), 201

        elif event_type == 'clock_out':
            if not active_session:
                conn.close()
                return jsonify({'error': 'Not clocked in today'}), 409
                
            attendance_id = active_session[0]
            check_in_dt   = active_session[1]
            duration_mins = int((now_dt - check_in_dt).total_seconds() / 60) if check_in_dt else None

            c.execute("""
                UPDATE attendance
                SET check_out = %s, clock_out_time = %s, clock_out_conf = %s,
                    duration_mins = %s, att_status = 'completed'
                WHERE id = %s AND company_id = %s
            """, (now_dt, now_time, conf, duration_mins, attendance_id, company_id))
            conn.commit()
            conn.close()

            logger.info(f"[{company[1]}] Clock-out: {name} ({emp_id})")
            socketio.emit('clock_out_confirmed', {
                'employee_id': emp_id, 'name': name, 'time': now_time, 'duration_mins': duration_mins
            }, room=f"company_{company_id}")

            return jsonify({'success': True, 'event': 'clock_out_confirmed'}), 201

    except Exception as e:
        logger.error(f"/api/event error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/engine_settings', methods=['GET'])
def dummy_engine_settings():
    # පරණ Dashboard එකෙන් එන Request වලට Dummy උත්තරයක් දීම
    return jsonify({"is_active": True, "camera_source": "0"})

@app.route('/api/video_frame', methods=['POST'])
def api_video_frame():
    try:
        api_key = request.headers.get('X-API-Key')
        company = get_company_by_api_key(api_key)
        if company:
            data = request.data
            if data:
                b64 = base64.b64encode(data).decode('utf-8')
                socketio.emit('video_stream', {'frame': b64}, room=f"company_{company[0]}")
        return '', 204
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    try:
        api_key = request.headers.get('X-API-Key')
        company = get_company_by_api_key(api_key)
        if company:
            data = request.data
            if data:
                b64 = base64.b64encode(data).decode('utf-8')
                socketio.emit('video_stream', {'frame': b64}, room=f"company_{company[0]}")
        return '', 204
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD DATA ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
@app.route('/api/attendance/monthly', methods=['GET'])
def get_monthly_attendance():
    try:
        company_id = request.args.get('company_id')
        if not company_id: return jsonify({'error': 'Company ID required'}), 400
        
        conn = get_db()
        c = conn.cursor()
        current_month = datetime.now().strftime("%Y-%m")
        
        c.execute("""
            SELECT a.id, a.emp_id, e.name, DATE(a.check_in) as date,
                   COALESCE(a.clock_in_time, TIME(a.check_in)) AS clock_in_time,
                   a.clock_out_time, a.duration_mins, a.outlet,
                   COALESCE(a.att_status, a.status) AS status
            FROM attendance a
            JOIN employees e ON a.emp_id = e.emp_id
            WHERE DATE_FORMAT(a.check_in, '%Y-%m') = %s AND a.company_id = %s
            ORDER BY a.check_in ASC
        """, (current_month, company_id))
        
        result = rows_as_dicts(c)
        conn.close()
        return jsonify({'success': True, 'data': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════════════════════════════════════
#  WEBSOCKET EVENTS (MULTI-TENANT ROOMS)
# ═══════════════════════════════════════════════════════════════════════════════
@socketio.on('connect')
def handle_connect():
    company_id = request.args.get('company_id')
    if company_id:
        room_name = f"company_{company_id}"
        join_room(room_name)
        logger.info(f"Dashboard connected to Room: {room_name}")
        
        emit('initial_data', {
            'attendance_today': get_today_attendance(company_id),
            'clocked_in_staff': get_clocked_in_staff(company_id)
        }, to=room_name)


@socketio.on('request_attendance')
def handle_attendance_request(data=None):  # [FIXED] data=None කිරීමෙන් හිස් දත්ත ආවත් Crash නොවේ
    company_id = data.get('company_id') if isinstance(data, dict) else None
    if company_id:
        room_name = f"company_{company_id}"
        emit('attendance_update', {
            'data':       get_today_attendance(company_id),
            'clocked_in': get_clocked_in_staff(company_id),
        }, to=room_name)

if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("SaaS Face Recognition API Started")
    logger.info("=" * 80)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)