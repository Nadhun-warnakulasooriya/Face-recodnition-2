<?php
include 'connectin.php';
session_start();
if (!isset($_SESSION['company_id'])) {
    header("Location: login.php");
    exit();
}
$current_company_id = $_SESSION['company_id'];
$current_company_name = $_SESSION['company_name'];

// ── 1. EMPLOYEE DELETE HANDLER ────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['delete_emp_id'])) {
    $emp_id_to_delete = trim($_POST['delete_emp_id']);
    
    $url = "http://localhost:5000/api/employee/" . urlencode($emp_id_to_delete);
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "DELETE");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    curl_close($ch);

    header("Location: " . $_SERVER['PHP_SELF']);
    exit();
}

$FLASK_URL = "http://localhost:5000";
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Face Recognition Attendance Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; }
        .container-main { max-width: 1400px; margin: 0 auto; }
        
        .header { background: white; padding: 20px 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { margin: 0; color: #333; font-weight: 700; font-size: 28px; }
        .header-info { display: flex; gap: 30px; align-items: center; font-size: 14px; }
        .header-info .info-item { display: flex; align-items: center; gap: 8px; }
        
        .status-indicator { width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 6px; }
        .status-connected { background: #10b981; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        
        .custom-tabs { border-bottom: 2px solid rgba(255,255,255,0.2); margin-bottom: 20px; }
        .custom-tabs .nav-link { color: white; opacity: 0.7; border: none; font-weight: 600; padding: 12px 25px; border-radius: 10px 10px 0 0; font-size: 15px; transition: all 0.3s; }
        .custom-tabs .nav-link:hover { opacity: 1; border-color: transparent; isolation: isolate; }
        .custom-tabs .nav-link.active { color: #667eea; background: white; opacity: 1; box-shadow: 0 -4px 12px rgba(0,0,0,0.05); }
        
        .grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-bottom: 25px; }
        @media (max-width: 1024px) { .grid-container { grid-template-columns: 1fr; } }
        
        .card-custom { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; display: flex; flex-direction: column; margin-bottom: 25px;}
        .card-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; font-size: 18px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
        .card-body { padding: 20px; flex: 1; overflow-y: auto; max-height: 500px; }
        
        #video-feed { width: 100%; height: 100%; object-fit: cover; background: #000; border-radius: 0; display: block; }
        .staff-list { list-style: none; }
        .staff-item { padding: 15px; border-bottom: 1px solid #f0f0f0; display: flex; justify-content: space-between; align-items: center; }
        .staff-name { font-weight: 600; color: #333; font-size: 15px; }
        .staff-time { color: #999; font-size: 13px; }
        
        /* New buttons and badges */
        .btn-checkout-inline { background: #ef4444; color: white; border: none; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.2s; display: flex; align-items: center; gap: 5px; }
        .btn-checkout-inline:hover { background: #dc2626; }
        .confidence-badge { display: inline-block; background: #10b981; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 500; }
        .confidence-badge.low { background: #f59e0b; }

        .attendance-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .attendance-table thead { background: #f5f5f5; position: sticky; top: 0; z-index: 1; }
        .attendance-table th { padding: 12px; text-align: left; font-weight: 600; color: #333; border-bottom: 2px solid #ddd; }
        .attendance-table td { padding: 12px; border-bottom: 1px solid #eee; }
        
        .clickable-row { cursor: pointer; transition: background 0.2s; }
        .clickable-row:hover { background-color: #f0fdf4 !important; }
        
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 500; }
        .status-badge.clocked-in { background: #dbeafe; color: #1e40af; }
        .status-badge.completed   { background: #dcfce7; color: #166534; }
        .status-badge.pending     { background: #fef3c7; color: #92400e; }
        
        .empty-state { text-align: center; padding: 40px 20px; color: #999; }
        .action-buttons { display: flex; gap: 10px; padding: 15px 20px; border-top: 1px solid #f0f0f0; }
        .btn-export { flex: 1; background: #f0f0f0; border: 1px solid #ddd; color: #333; padding: 10px; border-radius: 6px; font-weight: 500; cursor: pointer; }
        .btn-export:hover { background: #e5e5e5; }
        
        .toast-container { position: fixed; bottom: 20px; right: 20px; z-index: 9999; }
        .toast-notification { background: white; padding: 15px 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); margin-bottom: 10px; animation: slideIn 0.3s; display: flex; align-items: center; gap: 10px; }
        @keyframes slideIn { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .toast-success { border-left: 4px solid #10b981; color: #10b981; }
        .toast-info    { border-left: 4px solid #3b82f6; color: #3b82f6; }
        .toast-error   { border-left: 4px solid #ef4444; color: #ef4444; }
    </style>
</head>
<body>
<div class="container-main">

    <div class="header">
        <h1><i class="bi bi-camera-video"></i> Attendance Dashboard</h1>
        <div class="header-info">
            
            <div class="engine-controls" style="background: #f8fafc; padding: 6px 15px; border-radius: 8px; display: flex; gap: 10px; align-items: center; border: 1px solid #e2e8f0; margin-right: 15px;">
                <label for="camDropdown" style="font-size: 13px; font-weight: 600; color: #475569; margin: 0;">
                    <i class="bi bi-camera-video"></i> Camera:
                </label>
                <select id="camDropdown" class="form-select form-select-sm" style="width: auto; font-size: 13px; font-weight: 500; cursor: pointer; border-color: #cbd5e1;" onchange="updateEngineSettings()">
                    <option value="OFF" style="color: #ef4444; font-weight: 600;">🔴 OFF (Release Camera)</option>
                    <option value="0">🟢 Local Webcam 1 (Default)</option>
                    <option value="1">🟢 Local Webcam 2 (USB)</option>
                    <option value="rtsp://admin:password@192.168.1.100:554/stream1">🔵 Front Door (IP Camera)</option>
                    <option value="rtsp://admin:password@192.168.1.101:554/stream1">🔵 Back Door (IP Camera)</option>
                </select>
            </div>

            <a href="index.php" class="btn" style="background:#10b981; color:white; padding:8px 15px; border-radius:6px; text-decoration:none; font-weight:600; font-size:14px; display:flex; align-items:center; gap:6px;">
                <i class="bi bi-person-plus-fill"></i> Register User
            </a>
            <div class="info-item">
                <span class="status-indicator status-connected"></span>
                <span>WebSocket: <strong id="connection-status">Connecting...</strong></span>
            </div>
            <div class="info-item">
                Time: <strong id="current-time">00:00:00</strong>
            </div>
        </div>
    </div>

    <ul class="nav nav-tabs custom-tabs" id="dashboardTabs" role="tablist">
        <li class="nav-item" role="presentation">
            <button class="nav-link active" id="live-tab" data-bs-toggle="tab" data-bs-target="#live-pane" type="button" role="tab" aria-selected="true">
                <i class="bi bi-broadcast"></i> Live Dashboard
            </button>
        </li>
        <li class="nav-item" role="presentation">
            <button class="nav-link" id="attendance-tab" data-bs-toggle="tab" data-bs-target="#attendance-pane" type="button" role="tab" aria-selected="false">
                <i class="bi bi-list-check"></i> Today's Attendance
            </button>
        </li>
        <li class="nav-item" role="presentation">
            <button class="nav-link" id="employees-tab" data-bs-toggle="tab" data-bs-target="#employees-pane" type="button" role="tab" aria-selected="false">
                <i class="bi bi-people"></i> Employee Management
            </button>
        </li>
    </ul>

    <div class="tab-content" id="dashboardTabsContent">
        
        <div class="tab-pane fade show active" id="live-pane" role="tabpanel" aria-labelledby="live-tab">
            <div class="grid-container">
                <div>
                    <div class="card-custom" style="height:400px;">
                        <div class="card-header">
                            <span>Live Camera Feed</span>
                            <span style="font-size:12px;font-weight:400;">Front Door</span>
                        </div>
                        <div class="card-body" style="padding:0; position:relative; overflow:hidden; background:#000;">
                            <img id="video-feed" src="" alt="Camera feed" onerror="this.style.display='none'; document.getElementById('feed-offline').style.display='flex';">
                            <div id="feed-offline" style="display:none; color:#aaa; text-align:center; position:absolute; top:0; left:0; width:100%; height:100%; flex-direction:column; align-items:center; justify-content:center; gap:8px;">
                                <span style="font-size:32px;">📷</span><span>Waiting for camera...</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div>
                    <div class="card-custom">
                        <div class="card-header">
                            <span>Currently Clocked In</span>
                            <span id="staff-count" style="font-size:14px;font-weight:400;">0 staff</span>
                        </div>
                        <div class="card-body">
                            <ul class="staff-list" id="staff-list">
                                <div class='empty-state'><i class='bi bi-person-slash'></i><p>Loading...</p></div>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="tab-pane fade" id="attendance-pane" role="tabpanel" aria-labelledby="attendance-tab">
            <div class="card-custom">
                <div class="card-header">
                    <span>Today's Attendance</span>
                    <span id="attendance-count" style="font-size:14px;font-weight:400;">0 records</span>
                </div>
                
                <div style="background: #e0f2fe; padding: 12px 20px; font-size: 14px; color: #0369a1; border-bottom: 1px solid #bae6fd;">
                    <i class="bi bi-info-circle-fill"></i> <strong>Tip:</strong> Click on any employee's row below to view their specific Recognition Time Windows.
                </div>

                <div class="card-body" style="padding:0; overflow-y:auto; max-height:500px;">
                    <table class="attendance-table">
                        <thead><tr><th>Name</th><th>Clock In</th><th>Clock Out</th><th>Duration</th><th>Status</th></tr></thead>
                        <tbody id="attendance-table-body">
                            <tr><td colspan="5" class="empty-state">Loading records...</td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="action-buttons">
    <button class="btn-export" onclick="exportToCSV()" title="Download today's attendance">
        <i class="bi bi-file-earmark-spreadsheet"></i> Today's Report
    </button>
    
    <button class="btn-export" style="background:#10b981; color:white; border:none; font-weight: 600;" onclick="downloadMonthlyCSV()">
        <i class="bi bi-calendar-check"></i> Monthly Report
    </button>
    
    <button type="button" class="btn-export" onclick="refreshData()">
        <i class="bi bi-arrow-clockwise"></i> Refresh
    </button>
</div>
            </div>
        </div>

        <div class="tab-pane fade" id="employees-pane" role="tabpanel" aria-labelledby="employees-tab">
            <div class="card-custom">
                <div class="card-header">
                    <span><i class="bi bi-people-fill"></i> All Registered Employees</span>
                    <span style="font-size:14px;font-weight:400;">
                        <?php
                        $res_emps = $conn->query("SELECT COUNT(*) AS cnt FROM employees WHERE company_id = $current_company_id");
                        $total_emps = $res_emps ? $res_emps->fetch_assoc()['cnt'] : 0;
                        echo $total_emps . ' Employees';
                        ?>
                    </span>
                </div>
                <div class="card-body" style="padding:0; overflow-y:auto; max-height:500px;">
                    <table class="attendance-table">
                        <thead><tr><th>Employee ID</th><th>Name</th><th>Outlet</th><th>Registered Date</th><th>Action</th></tr></thead>
                        <tbody>
                            <?php
                            // පෙන්වන්නේ අදාල සමාගමේ සේවකයින් පමණයි
                            $emp_sql = "SELECT emp_id, name, outlet, created_at FROM employees WHERE company_id = $current_company_id ORDER BY created_at DESC";
                            $emp_result = $conn->query($emp_sql);
                            if ($emp_result && $emp_result->num_rows > 0) {
                                while ($row = $emp_result->fetch_assoc()) {
                                    $e_id = htmlspecialchars($row['emp_id']);
                                    $e_name = htmlspecialchars($row['name']);
                                    $e_outlet = htmlspecialchars($row['outlet'] ?? 'Unassigned');
                                    $e_date = htmlspecialchars($row['created_at']);
                                    echo "<tr>
                                        <td><strong>$e_id</strong></td>
                                        <td>$e_name</td>
                                        <td>$e_outlet</td>
                                        <td style='color:#666; font-size:13px;'>$e_date</td>
                                        <td>
                                            <form method='POST' style='margin:0;' onsubmit='return confirm(\"Are you sure you want to delete this employee?\");'>
                                                <input type='hidden' name='delete_emp_id' value='$e_id'>
                                                <button type='submit' class='btn btn-danger btn-sm' style='padding:2px 8px; font-size:12px;'>Delete</button>
                                            </form>
                                        </td>
                                    </tr>";
                                }
                            } else {
                                echo "<tr><td colspan='5' class='empty-state'>No registered employees found.</td></tr>";
                            }
                            ?>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
    </div> </div> 

<div class="modal fade" id="timeWindowModal" tabindex="-1" aria-labelledby="timeWindowModalLabel" aria-hidden="true">
  <div class="modal-dialog modal-lg modal-dialog-centered">
    <div class="modal-content" style="border: none; border-radius: 12px; overflow: hidden;">
      <div class="modal-header" style="background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%); color: white; padding: 20px;">
        <h5 class="modal-title" id="timeWindowModalLabel" style="font-weight: 600;">
            <i class="bi bi-person-bounding-box"></i> Time Windows: <span id="modal-emp-name" style="text-decoration: underline;">Employee</span>
        </h5>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body" style="padding: 0;">
        <table class="attendance-table" style="margin: 0;">
            <thead>
                <tr style="background: #fff8f1;">
                    <th>Time Window</th>
                    <th>Requirement</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>08:00 AM – 12:00 PM</strong></td>
                    <td>Minimum 1 successful face recognition</td>
                    <td><span class="status-badge completed"><i class="bi bi-check-circle"></i> Checked</span></td>
                </tr>
                <tr>
                    <td><strong>12:00 PM – 04:00 PM</strong></td>
                    <td>Minimum 1 successful face recognition</td>
                    <td><span class="status-badge clocked-in"><i class="bi bi-camera-video"></i> Active Now</span></td>
                </tr>
                <tr>
                    <td><strong>04:00 PM – 10:00 PM</strong></td>
                    <td>Minimum 1 successful face recognition</td>
                    <td><span class="status-badge pending"><i class="bi bi-clock"></i> Upcoming</span></td>
                </tr>
            </tbody>
        </table>
        <div style="padding: 15px 20px; font-size: 13px; color: #666; background: #fafafa; border-top: 1px solid #eee;">
            <i class="bi bi-info-circle text-primary"></i> <b>Note:</b> The statuses above show the face recognition requirement for <strong><span id="modal-emp-name-footer"></span></strong>.
        </div>
      </div>
      <div class="modal-footer" style="background: #fff; padding: 10px 20px;">
        <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
      </div>
    </div>
  </div>
</div>

<div class="toast-container" id="toast-container"></div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<script>
    const FLASK = 'http://localhost:5000';
    
    // ── MULTI-TENANT SOCKET.IO CONNECTION ──
    const CURRENT_COMPANY_ID = "<?php echo isset($_SESSION['company_id']) ? $_SESSION['company_id'] : ''; ?>";

    const socket = io(FLASK, {
        query: { company_id: CURRENT_COMPANY_ID }
    });

    // තත්පර 5කට වරක් Auto-Refresh වීම
    setInterval(() => {
        if (CURRENT_COMPANY_ID) {
            socket.emit('request_attendance', { company_id: CURRENT_COMPANY_ID });
        }
    }, 5000);
    // ───────────────────────────────────────

    let timeWindowModal;
    document.addEventListener("DOMContentLoaded", function() {
        timeWindowModal = new bootstrap.Modal(document.getElementById('timeWindowModal'));
    });

    socket.on('connect', () => { 
        updateConnectionStatus('Connected', true); 
        if (CURRENT_COMPANY_ID) {
            socket.emit('request_attendance', { company_id: CURRENT_COMPANY_ID }); 
        }
    });
    
    socket.on('disconnect', () => updateConnectionStatus('Disconnected', false));
    
    socket.on('video_stream', (data) => {
        if (data && data.frame) {
            const img = document.getElementById('video-feed');
            img.src = 'data:image/jpeg;base64,' + data.frame;
            img.style.display = 'block';
            document.getElementById('feed-offline').style.display = 'none';
        }
    });

    socket.on('initial_data', (data) => {
        renderStaffList(data.clocked_in_staff || []);
        renderAttendanceTable(data.attendance_today || []);
    });

    socket.on('attendance_update', (data) => {
        renderStaffList(data.clocked_in || []);
        renderAttendanceTable(data.data || []);
    });

    socket.on('clock_out_confirmed', (data) => {
        showToast(`✓ ${data.name} clocked out successfully`, 'success');
        if (CURRENT_COMPANY_ID) {
            socket.emit('request_attendance', { company_id: CURRENT_COMPANY_ID });
        }
    });

    function downloadMonthlyCSV() {
        showToast('Preparing Monthly Report...', 'info');
        
        // PHP හරහා Company ID එක යැවීම
        fetch(`${FLASK}/api/attendance/monthly?company_id=${CURRENT_COMPANY_ID}`)
            .then(r => r.json())
            .then(res => {
                if (res.success && res.data.length > 0) {
                    let csv = 'Record ID,Employee ID,Name,Date,Clock In,Clock Out,Duration (Mins),Outlet,Status\n';
                    
                    res.data.forEach(r => {
                        const id = r.id;
                        const emp_id = r.emp_id || '—';
                        const name = `"${r.name}"`;
                        const date = r.date;
                        const cIn = r.clock_in_time || '—';
                        const cOut = r.clock_out_time || '—';
                        const dur = r.duration_mins || '0';
                        const outlet = r.outlet || '—';
                        const status = r.status === 'clocked_in' ? 'Clocked In' : 'Completed';
                        
                        csv += `${id},${emp_id},${name},${date},${cIn},${cOut},${dur},${outlet},${status}\n`;
                    });
                    
                    const currentMonth = new Date().toISOString().slice(0,7);
                    const a = document.createElement('a');
                    a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
                    a.download = `Monthly_Attendance_${currentMonth}.csv`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    
                    showToast('Monthly report downloaded successfully!', 'success');
                } else if (res.success && res.data.length === 0) {
                    showToast('No records found for this month.', 'warning');
                } else {
                    showToast(res.error || 'Failed to fetch data', 'error');
                }
            })
            .catch(e => showToast('Connection Error: ' + e, 'error'));
    }

   function renderStaffList(staff) {
        const list = document.getElementById('staff-list');
        const count = document.getElementById('staff-count');
        if (!staff.length) {
            list.innerHTML = `<div class="empty-state"><i class="bi bi-person-slash"></i><p>No staff clocked in</p></div>`;
            count.textContent = '0 staff'; return;
        }
        list.innerHTML = staff.map(s => {
            const pct = Math.round((s.clock_in_conf || 0) * 100);
            const low = (s.clock_in_conf || 0) < 0.8 ? 'low' : '';
            const empId = s.employee_id || s.emp_id || s.id || '';
            
            return `
            <li class="staff-item">
                <div>
                    <div class="staff-name">${s.name}</div>
                    <div class="staff-time">In: ${s.clock_in_time}</div>
                </div>
                <div style="display: flex; align-items: center; gap: 15px;">
                    ${s.clock_in_conf !== undefined ? `<div class="confidence-badge ${low}">${pct}%</div>` : ''}
                    <button class="btn-checkout-inline" onclick="manualClockOut('${empId}', '${s.name}', this)">
                        <i class="bi bi-box-arrow-right"></i> Check Out
                    </button>
                </div>
            </li>`;
        }).join('');
        count.textContent = `${staff.length} staff`;
    }

    function manualClockOut(empId, empName, btnElement) {
        if (!empId) {
            showToast('Error: Employee ID is missing!', 'error');
            return;
        }

        if (!confirm(`Are you sure you want to clock out ${empName}?`)) {
            return;
        }

        if (btnElement) {
            btnElement.disabled = true;
            btnElement.innerHTML = `<i class="bi bi-hourglass-split"></i> Processing...`;
        }

        fetch(`${FLASK}/api/event`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_key: "<?php echo isset($_SESSION['api_key']) ? $_SESSION['api_key'] : ''; ?>", // [ADDED] API Key
                employee_id: empId,
                name: empName,
                event_type: 'clock_out'
            })
        })
        .then(r => r.json())
        .then(data => {
            if(data.success || data.event === 'clock_out_confirmed') {
                if (CURRENT_COMPANY_ID) {
                    socket.emit('request_attendance', { company_id: CURRENT_COMPANY_ID });
                }
            } else {
                showToast(data.error || 'Clock out failed', 'error');
                if (btnElement) {
                    btnElement.disabled = false;
                    btnElement.innerHTML = `<i class="bi bi-box-arrow-right"></i> Check Out`;
                }
            }
        })
        .catch(e => {
            showToast('Connection error: ' + e, 'error');
            if (btnElement) {
                btnElement.disabled = false;
                btnElement.innerHTML = `<i class="bi bi-box-arrow-right"></i> Check Out`;
            }
        });
    }

    function renderAttendanceTable(records) {
        const tbody = document.getElementById('attendance-table-body');
        const count = document.getElementById('attendance-count');
        if (!records.length) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No attendance records yet</td></tr>`;
            count.textContent = '0 records'; return;
        }
        
        tbody.innerHTML = records.map(r => {
            const dur = r.duration_mins ? r.duration_mins + ' min' : '—';
            const status = r.status === 'clocked_in' ? 'Clocked In' : 'Completed';
            const cls = r.status === 'clocked_in' ? 'clocked-in' : 'completed';
            
            return `<tr class="clickable-row" onclick="openTimeWindowModal('${r.name}')" title="Click to view time windows for ${r.name}">
                        <td><strong>${r.name}</strong></td>
                        <td>${r.clock_in_time || '—'}</td>
                        <td>${r.clock_out_time || '—'}</td>
                        <td>${dur}</td>
                        <td><span class="status-badge ${cls}">${status}</span></td>
                    </tr>`;
        }).join('');
        count.textContent = `${records.length} records`;
    }

    function openTimeWindowModal(employeeName) {
        document.getElementById('modal-emp-name').textContent = employeeName;
        document.getElementById('modal-emp-name-footer').textContent = employeeName;
        timeWindowModal.show();
    }

    function updateConnectionStatus(text, ok) {
        const el = document.getElementById('connection-status'); el.textContent = text;
        const dot = el.closest('.info-item').querySelector('.status-indicator');
        dot.className = 'status-indicator' + (ok ? ' status-connected' : '');
    }

    function showToast(msg, type = 'info') {
        const c = document.getElementById('toast-container');
        const toast = document.createElement('div'); toast.className = `toast-notification toast-${type}`;
        const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'x-circle' : 'info-circle';
        toast.innerHTML = `<i class="bi bi-${icon}"></i><span>${msg}</span>`;
        c.appendChild(toast); setTimeout(() => toast.remove(), 4000);
    }

    function exportToCSV() {
        const rows = document.querySelectorAll('#attendance-table-body tr');
        let csv = 'Name,Clock In,Clock Out,Duration,Status\n';
        rows.forEach(row => {
            const cells = [...row.querySelectorAll('td')].map(td => `"${td.textContent.trim()}"`);
            if (cells.length === 5) csv += cells.join(',') + '\n';
        });
        const a = document.createElement('a'); a.href = 'data:text/csv,' + encodeURIComponent(csv);
        a.download = `attendance_${new Date().toISOString().split('T')[0]}.csv`; a.click();
    }

    function refreshData() {
        showToast('Fetching latest data...', 'info');
        setTimeout(() => { window.location.href = window.location.pathname + '?refresh=' + new Date().getTime(); }, 800);
    }

    // ── AI Engine Camera Switcher Settings Logic ──
    fetch(`${FLASK}/api/engine_settings`)
        .then(r => r.json())
        .then(data => {
            const dropdown = document.getElementById('camDropdown');
            if (!data.is_active) {
                dropdown.value = "OFF";
            } else {
                let exists = Array.from(dropdown.options).some(opt => opt.value === data.camera_source);
                if (!exists) {
                    const newOption = new Option(`Custom: ${data.camera_source}`, data.camera_source);
                    dropdown.add(newOption);
                }
                dropdown.value = data.camera_source;
            }
        })
        .catch(e => console.log('Engine settings API not ready or reachable yet.'));

    function updateEngineSettings() {
        const dropdown = document.getElementById('camDropdown');
        const selectedValue = dropdown.value;
        
        let isActive = true;
        let camSource = selectedValue;

        if (selectedValue === "OFF") {
            isActive = false;
            camSource = "0"; 
            showToast('Shutting down AI Engine & Releasing Camera...', 'warning');
        } else {
            showToast('Switching Camera Feed...', 'info');
        }

        fetch(`${FLASK}/api/engine_settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: isActive, camera_source: camSource })
        })
        .then(r => r.json())
        .then(data => {
            if(data.success) {
                if(isActive) {
                    showToast('Camera connected successfully!', 'success');
                } else {
                    showToast('Camera is now OFF', 'success');
                }
            }
        })
        .catch(e => showToast('Error updating settings', 'error'));
    }

    setInterval(() => {
        document.getElementById('current-time').textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
    }, 1000);
</script>
</body>
</html>