#!/usr/bin/env python3
"""
Event Logger Module for Face Recognition Attendance System
Plugs into your existing recognition.py to send events to the Flask backend.

Integration:
    1. Import this module into your recognition.py
    2. Create an AttendanceEventLogger instance
    3. Call logger.log_event() whenever a face is matched
"""

import os
import requests
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class AttendanceEventLogger:
    """
    Manages clock-in/out events and sends them to the Flask backend.
    Tracks daily state to avoid duplicate events.
    """

    def __init__(self, backend_url="http://localhost:5000", snapshots_dir="snapshots"):
        """
        Args:
            backend_url: URL of the Flask attendance backend
            snapshots_dir: Directory to save snapshots
        """
        self.backend_url = backend_url.rstrip('/')
        self.snapshots_dir = snapshots_dir
        Path(self.snapshots_dir).mkdir(exist_ok=True)

        # Track today's clock-ins (employee_id → clock_in_time)
        self.today_clocked_in = {}
        self.shift_end_hour = 22  # 10 PM

        # Background thread for HTTP requests (non-blocking)
        self.event_queue = []
        self.queue_lock = threading.Lock()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

        logger.info(f"[AttendanceEventLogger] Initialized | Backend: {self.backend_url}")

    def _worker(self):
        """Background thread to send events to backend without blocking recognition."""
        while True:
            time.sleep(0.5)  # Poll every 500ms
            event = None
            with self.queue_lock:
                if self.event_queue:
                    event = self.event_queue.pop(0)
            
            if event:
                self._send_event(event)

    def _send_event(self, event):
        """Send single event to Flask backend."""
        try:
            response = requests.post(
                f"{self.backend_url}/api/event",
                json=event,
                timeout=5
            )
            if response.status_code in [201, 200]:
                logger.info(
                    f"✓ {event['event_type'].upper()}: {event['name']} "
                    f"({event['employee_id']}) | conf={event['confidence']:.2f}"
                )
            elif response.status_code == 409:
                logger.warning(f"⊘ {event['name']}: {response.json().get('error', 'Conflict')}")
            else:
                logger.error(f"✗ Event send failed: {response.status_code} | {response.text}")
        except requests.exceptions.ConnectionError:
            logger.error(f"✗ Cannot reach backend at {self.backend_url}")
            # Re-queue the event for retry
            with self.queue_lock:
                self.event_queue.insert(0, event)
        except Exception as e:
            logger.error(f"✗ Error sending event: {str(e)}")

    def log_event(self, employee_id, name, dept, confidence, frame_bgr, event_type='auto'):
        """
        Log a face detection as a potential clock-in or clock-out.

        Args:
            employee_id (str): Unique identifier (e.g., "person_0", "EMP_001")
            name (str): Display name (e.g., "John Doe")
            dept (str): Department or role
            confidence (float): Match confidence (0.0-1.0)
            frame_bgr (ndarray): OpenCV BGR frame containing the face
            event_type (str): 'clock_in', 'clock_out', or 'auto' (auto-detects based on time)

        Returns:
            bool: True if event was queued, False if rejected (e.g., already clocked in)
        """
        import cv2
        
        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        current_hour = now.hour

        # Auto-detect event type based on shift window
        if event_type == 'auto':
            if employee_id not in self.today_clocked_in:
                event_type = 'clock_in'
            elif current_hour >= self.shift_end_hour:
                event_type = 'clock_out'
            else:
                # Employee is clocked in but not yet in clock-out window → skip
                return False

        # Save snapshot
        try:
            timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{employee_id}_{event_type}_{timestamp}.jpg"
            snapshot_path = os.path.join(self.snapshots_dir, filename)
            cv2.imwrite(snapshot_path, frame_bgr)
        except Exception as e:
            logger.error(f"Failed to save snapshot: {str(e)}")
            snapshot_path = None

        # Build event payload
        event = {
            'employee_id': employee_id,
            'name': name,
            'dept': dept,
            'confidence': float(confidence),
            'snapshot_path': snapshot_path,
            'event_type': event_type
        }

        # Queue for background send
        with self.queue_lock:
            self.event_queue.append(event)

        # Track clock-in locally to avoid duplicates
        if event_type == 'clock_in':
            self.today_clocked_in[employee_id] = now.strftime("%H:%M:%S")
        elif event_type == 'clock_out':
            # Don't remove from tracking yet — let backend confirm
            pass

        return True

    def reset_daily_state(self):
        """Call this once per day (e.g., at midnight or 9 AM) to reset tracking."""
        self.today_clocked_in.clear()
        logger.info("[AttendanceEventLogger] Daily state reset.")

    def get_status(self):
        """Return current logger status."""
        return {
            'backend_url': self.backend_url,
            'queue_size': len(self.event_queue),
            'clocked_in_today': list(self.today_clocked_in.keys()),
            'worker_alive': self.worker_thread.is_alive()
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  INTEGRATION EXAMPLE
# ═══════════════════════════════════════════════════════════════════════════════
"""
In your recognition.py, after the recognition worker gets a match:

    # At the top of recognition.py
    from event_logger import AttendanceEventLogger
    event_logger = AttendanceEventLogger(backend_url="http://localhost:5000")

    # Inside recognition_worker() or wherever you call match_embedding():
    # After getting name, dept, conf from the matched face:

    if name != "Unknown Person":
        event_logger.log_event(
            employee_id=f"emp_{person_id}",  # adjust to your ID scheme
            name=name,
            dept=dept,
            confidence=conf,
            frame_bgr=roi_bgr,  # or any face frame you have
            event_type='auto'   # auto-detects based on time
        )

    # Optional: Reset daily tracking at start of shift (9 AM)
    from datetime import datetime
    if datetime.now().hour == 9 and datetime.now().minute == 0:
        event_logger.reset_daily_state()
"""
