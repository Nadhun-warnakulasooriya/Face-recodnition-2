#!/usr/bin/env python3
"""
Test Script for Face Recognition Attendance System
Use this to verify the backend is running and accepting events.

Usage:
    python test_system.py
"""

import requests
import json
import time
import sys
from datetime import datetime
from pathlib import Path

# Configuration
BACKEND_URL = "http://localhost:5000"
SNAPSHOTS_DIR = "snapshots"

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_backend_alive():
    """Check if Flask backend is running."""
    print_section("TEST 1: Backend Connection")
    try:
        response = requests.get(f"{BACKEND_URL}/api/attendance/today", timeout=5)
        if response.status_code == 200:
            print("✓ Backend is running and responding")
            return True
        else:
            print(f"✗ Backend returned {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot reach {BACKEND_URL}")
        print("  Is app.py running? Start it with: python app.py")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_video_feed():
    """Check if MJPEG feed is available."""
    print_section("TEST 2: Video Feed")
    try:
        response = requests.head(f"{BACKEND_URL}/video_feed", timeout=5)
        if response.status_code == 200:
            print("✓ Video feed is available")
            print(f"  Access at: {BACKEND_URL}/video_feed")
            return True
        else:
            print(f"✗ Video feed returned {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_clock_in(emp_id="test_emp_001", name="Test User", dept="Engineering"):
    """Test clock-in event."""
    print_section(f"TEST 3: Clock-In Event")
    
    # Create dummy snapshot
    Path(SNAPSHOTS_DIR).mkdir(exist_ok=True)
    dummy_snapshot = f"{SNAPSHOTS_DIR}/test_clock_in_dummy.jpg"
    with open(dummy_snapshot, 'w') as f:
        f.write("dummy")  # Placeholder
    
    payload = {
        "employee_id": emp_id,
        "name": name,
        "dept": dept,
        "confidence": 0.92,
        "snapshot_path": dummy_snapshot,
        "event_type": "clock_in"
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/event",
            json=payload,
            timeout=5
        )
        
        result = response.json()
        
        if response.status_code in [200, 201]:
            print("✓ Clock-in event recorded successfully")
            print(f"  Record ID: {result.get('record_id')}")
            print(f"  Time: {datetime.now().strftime('%H:%M:%S')}")
            print(f"  Employee: {name}")
            return result.get('record_id')
        else:
            print(f"✗ Clock-in failed: {response.status_code}")
            print(f"  Response: {result}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return None

def test_get_attendance():
    """Fetch today's attendance records."""
    print_section("TEST 4: Get Attendance Records")
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/attendance/today",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            records = data.get('data', [])
            
            print(f"✓ Retrieved {len(records)} attendance record(s)")
            
            if records:
                for rec in records:
                    print(f"\n  Name: {rec['name']}")
                    print(f"  Clock In: {rec['clock_in_time']}")
                    if rec['clock_out_time']:
                        print(f"  Clock Out: {rec['clock_out_time']}")
                        print(f"  Duration: {rec.get('duration_mins', '—')} mins")
                    else:
                        print(f"  Status: Currently clocked in")
            return True
        else:
            print(f"✗ Failed to get attendance: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_clocked_in_staff():
    """Fetch currently clocked-in staff."""
    print_section("TEST 5: Currently Clocked-In Staff")
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/staff/clocked-in",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            staff = data.get('data', [])
            
            print(f"✓ Retrieved {len(staff)} clocked-in staff")
            
            for person in staff:
                print(f"\n  {person['name']}")
                print(f"    Clock In: {person['clock_in_time']}")
                print(f"    Confidence: {person['clock_in_conf']:.0%}")
            
            return staff
        else:
            print(f"✗ Failed to get staff: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return []

def test_clock_out(record_id, emp_id="test_emp_001", name="Test User"):
    """Test clock-out event (only after 9 PM)."""
    print_section("TEST 6: Clock-Out Event (Pending)")
    
    now = datetime.now()
    if now.hour < 22:
        print(f"⊘ Clock-out window not open yet")
        print(f"  Current time: {now.strftime('%H:%M:%S')}")
        print(f"  Clock-out available after: 22:00:00")
        print(f"  Run this test again after 10 PM")
        return None
    
    # Create dummy snapshot
    Path(SNAPSHOTS_DIR).mkdir(exist_ok=True)
    dummy_snapshot = f"{SNAPSHOTS_DIR}/test_clock_out_dummy.jpg"
    with open(dummy_snapshot, 'w') as f:
        f.write("dummy")
    
    payload = {
        "employee_id": emp_id,
        "name": name,
        "dept": "Engineering",
        "confidence": 0.88,
        "snapshot_path": dummy_snapshot,
        "event_type": "clock_out"
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/event",
            json=payload,
            timeout=5
        )
        
        result = response.json()
        
        if response.status_code in [200, 201]:
            print("✓ Clock-out event recorded (pending confirmation)")
            print(f"  Pending ID: {result.get('pending_id')}")
            print(f"  Status: Awaiting admin confirmation on dashboard")
            return result.get('pending_id')
        else:
            print(f"✗ Clock-out failed: {response.status_code}")
            print(f"  Response: {result}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return None

def test_pending_clockouts():
    """Get pending clock-outs."""
    print_section("TEST 7: Pending Clock-Outs")
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/pending-clockouts",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            pendings = data.get('data', [])
            
            print(f"✓ Retrieved {len(pendings)} pending clock-out(s)")
            
            for p in pendings:
                print(f"\n  ID: {p['id']}")
                print(f"  Employee: {p['name']}")
                print(f"  Detected: {p['detected_at']}")
                print(f"  Confidence: {p['confidence']:.0%}")
            
            return pendings
        else:
            print(f"✗ Failed to get pending: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return []

def test_confirm_clockout(pending_id):
    """Test clock-out confirmation (admin approves)."""
    print_section("TEST 8: Confirm Clock-Out")
    
    if not pending_id:
        print("⊘ No pending clock-out to confirm")
        print("  Run TEST 6 (clock-out) first")
        return False
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/clockout/confirm/{pending_id}",
            timeout=5
        )
        
        result = response.json()
        
        if response.status_code == 200:
            print("✓ Clock-out confirmed successfully")
            print(f"  Message: {result.get('message')}")
            print(f"  Duration: {result.get('duration_mins', 'N/A')} minutes")
            return True
        else:
            print(f"✗ Confirmation failed: {response.status_code}")
            print(f"  Response: {result}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def test_dashboard():
    """Check if dashboard is accessible."""
    print_section("TEST 9: Dashboard")
    try:
        response = requests.get(
            f"{BACKEND_URL}/dashboard.html",
            timeout=5
        )
        
        if response.status_code == 200:
            print("✓ Dashboard is accessible")
            print(f"  Open in browser: {BACKEND_URL}/dashboard.html")
            return True
        else:
            print(f"✗ Dashboard returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def main():
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║         FACE RECOGNITION ATTENDANCE SYSTEM - TEST SUITE                    ║")
    print("║                                                                            ║")
    print(f"║  Backend URL: {BACKEND_URL:<55} ║")
    print("║                                                                            ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    
    # Run tests
    passed = 0
    total = 9
    
    # Test 1: Backend
    if test_backend_alive():
        passed += 1
    else:
        print("\n⚠ Cannot continue without backend. Start app.py and try again.")
        sys.exit(1)
    
    # Test 2: Video Feed
    if test_video_feed():
        passed += 1
    
    # Test 3: Clock-In
    record_id = test_clock_in()
    if record_id:
        passed += 1
    
    # Test 4: Get Attendance
    if test_get_attendance():
        passed += 1
    
    # Test 5: Clocked-In Staff
    staff = test_clocked_in_staff()
    if staff is not None:
        passed += 1
    
    # Test 6: Clock-Out
    pending_id = test_clock_out(record_id)
    if pending_id:
        passed += 1
    else:
        pending_id = None  # Might fail if not after 10 PM
    
    # Test 7: Pending Clock-Outs
    if test_pending_clockouts():
        passed += 1
    
    # Test 8: Confirm Clock-Out (only if we have a pending)
    if pending_id:
        if test_confirm_clockout(pending_id):
            passed += 1
    else:
        print_section("TEST 8: Confirm Clock-Out")
        print("⊘ Skipped (requires TEST 6 to succeed)")
    
    # Test 9: Dashboard
    if test_dashboard():
        passed += 1
    
    # Summary
    print_section("SUMMARY")
    print(f"Tests Passed: {passed}/9")
    
    if passed == 9:
        print("\n✓ All tests passed! System is ready to integrate.")
        print("\nNext steps:")
        print("  1. Modify your recognition.py to use event_logger")
        print("  2. Import: from event_logger import AttendanceEventLogger")
        print("  3. Call: event_logger.log_event() when faces are matched")
        print("  4. Open dashboard: " + BACKEND_URL + "/dashboard.html")
    elif passed >= 7:
        print("\n⚠ Most tests passed. Some features may be limited.")
        print("  Review failures above and check app.py logs.")
    else:
        print("\n✗ Multiple test failures. Check app.py is running correctly.")
    
    print("\n")

if __name__ == "__main__":
    main()
