<?php
$userName   = "root";
$password   = "";
$database   = "face_attendance";
$servername = "localhost";

$conn = new mysqli($servername, $userName, $password, $database);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// ── Flask backend URL ─────────────────────────
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
        .header-info .info-item strong { color: #667eea; }
        .status-indicator { width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 6px; }
        .status-connected { background: #10b981; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-bottom: 25px; }
        @media (max-width: 1024px) { .grid-container { grid-template-columns: 1fr; } }
        .card-custom { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; display: flex; flex-direction: column; }
        .card-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; font-size: 18px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
        .card-body { padding: 20px; flex: 1; overflow-y: auto; max-height: 500px; }
        #video-feed { width: 100%; height: 100%; object-fit: cover; background: #000; border-radius: 0; display: block; }
        .staff-list { list-style: none; }
        .staff-item { padding: 15px; border-bottom: 1px solid #f0f0f0; display: flex; justify-content: space-between; align-items: center; transition: background 0.2s; }
        .staff-item:hover { background: #f9f9f9; }
        .staff-item:last-child { border-bottom: none; }
        .staff-name { font-weight: 600; color: #333; font-size: 15px; }
        .staff-time { color: #999; font-size: 13px; }
        .confidence-badge { display: inline-block; background: #10b981; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 500; }
        .confidence-badge.low { background: #f59e0b; }
        .table-container { overflow-x: auto; }
        .attendance-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .attendance-table thead { background: #f5f5f5; position: sticky; top: 0; }
        .attendance-table th { padding: 12px; text-align: left; font-weight: 600; color: #333; border-bottom: 2px solid #ddd; }
        .attendance-table td { padding: 12px; border-bottom: 1px solid #eee; }
        .attendance-table tbody tr:hover { background: #f9f9f9; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 500; }
        .status-badge.clocked-in { background: #dbeafe; color: #1e40af; }
        .status-badge.completed  { background: #dcfce7; color: #166534; }
        .modal-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; }
        .modal-header .btn-close { filter: brightness(0) invert(1); }
        .clock-out-snapshot { width: 100%; height: 300px; object-fit: cover; border-radius: 8px; margin: 20px 0; background: #f0f0f0; }
        .clock-out-info { background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 15px 0; display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .clock-out-info-item { text-align: center; }
        .clock-out-info-item label { display: block; font-size: 12px; color: #999; margin-bottom: 5px; font-weight: 500; }
        .clock-out-info-item value { display: block; font-size: 16px; font-weight: 600; color: #333; }
        .btn-confirm { background: linear-gradient(135deg, #10b981 0%, #059669 100%); border: none; color: white; padding: 12px 30px; border-radius: 6px; font-weight: 600; font-size: 16px; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; width: 100%; margin-top: 20px; }
        .btn-confirm:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(16,185,129,0.3); color: white; }
        .btn-cancel { background: #e5e7eb; border: none; color: #333; padding: 12px 30px; border-radius: 6px; font-weight: 600; font-size: 16px; cursor: pointer; width: 100%; margin-top: 10px; }
        .empty-state { text-align: center; padding: 40px 20px; color: #999; }
        .empty-state i { font-size: 48px; margin-bottom: 15px; opacity: 0.5; }
        .action-buttons { display: flex; gap: 10px; padding: 15px 20px; border-top: 1px solid #f0f0f0; }
        .btn-export { flex: 1; background: #f0f0f0; border: 1px solid #ddd; color: #333; padding: 10px; border-radius: 6px; font-weight: 500; cursor: pointer; transition: background 0.2s; }
        .btn-export:hover { background: #e5e5e5; }
        .toast-container { position: fixed; bottom: 20px; right: 20px; z-index: 9999; }
        .toast-notification { background: white; padding: 15px 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); margin-bottom: 10px; animation: slideIn 0.3s; display: flex; align-items: center; gap: 10px; }
        @keyframes slideIn { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .toast-success { border-left: 4px solid #10b981; color: #10b981; }
        .toast-info    { border-left: 4px solid #3b82f6; color: #3b82f6; }
        .toast-error   { border-left: 4px solid #ef4444; color: #ef4444; }
        .loading-spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #f3f3f3; border-top: 2px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .db-badge { background: rgba(255,255,255,0.2); border-radius: 6px; padding: 3px 10px; font-size: 12px; margin-left: 8px; }
    </style>
</head>
<body>
<div class="container-main">

    <div class="header">
        <h1><i class="bi bi-camera-video"></i> Attendance Dashboard
            <span class="db-badge" style="background:#667eea;color:white;font-size:13px;">PHP + MySQL</span>
        </h1>
        <div class="header-info">
            <a href="index.php" class="btn" style="background:#10b981; color:white; padding:8px 15px; border-radius:6px; text-decoration:none; font-weight:600; font-size:14px; display:flex; align-items:center; gap:6px;">
                <i class="bi bi-person-plus-fill"></i> Register User
            </a>
            <div class="info-item">
                <span class="status-indicator status-connected"></span>
                <span>WebSocket: <strong id="connection-status">Connecting...</strong></span>
            </div>
            <div class="info-item">
                DB: <strong style="color:#10b981;">
                    <?php echo $conn->stat() ? 'Connected' : 'Error'; ?>
                </strong>
            </div>
            <div class="info-item">
                Time: <strong id="current-time">00:00:00</strong>
            </div>
        </div>
    </div>

    <div class="grid-container">

        <div>
            <div class="card-custom" style="margin-bottom:25px; height:400px;">
                <div class="card-header">
                    <span>Live Camera Feed</span>
                    <span style="font-size:12px;font-weight:400;">Front Door</span>
                </div>
                <div class="card-body" style="padding:0; position:relative; flex:1; overflow:hidden; background:#000; border-radius:0 0 12px 12px; height:345px;">
                    <img id="video-feed"
                         src="" 
                         alt="Camera feed"
                         style="width:100%; height:100%; object-fit:cover; display:block; position:absolute; top:0; left:0;"
                         onerror="this.style.display='none'; document.getElementById('feed-offline').style.display='flex';">
                    <div id="feed-offline"
                         style="display:none; color:#aaa; text-align:center; font-size:14px;
                                position:absolute; top:0; left:0; width:100%; height:100%;
                                flex-direction:column; align-items:center; justify-content:center; gap:8px;">
                        <span style="font-size:32px;">📷</span>
                        <span>Waiting for camera...</span>
                        <small style="color:#666;">Make sure Display-v2.py is running</small>
                    </div>
                </div>
            </div>

            <div class="card-custom">
                <div class="card-header">
                    <span>Currently Clocked In</span>
                    <span id="staff-count" style="font-size:14px;font-weight:400;">
                        <?php
                        $today = date('Y-m-d');
                        $res   = $conn->query("SELECT COUNT(*) AS cnt FROM attendance WHERE DATE(check_in)='$today' AND check_out IS NULL AND COALESCE(att_status, status)='clocked_in'");
                        $cnt = $res ? $res->fetch_assoc()['cnt'] : 0;
                        echo $cnt . ' staff';
                        ?>
                    </span>
                </div>
                <div class="card-body">
                    <ul class="staff-list" id="staff-list">
                        <?php
                        $today  = date('Y-m-d');
                        $sql    = "SELECT a.emp_id, e.name, COALESCE(a.clock_in_time, TIME(a.check_in)) AS clock_in_time, a.clock_in_conf FROM attendance a JOIN employees  e ON a.emp_id = e.emp_id WHERE DATE(a.check_in)='$today' AND a.check_out IS NULL AND COALESCE(a.att_status, a.status)='clocked_in' ORDER BY a.check_in DESC";
                        $result = $conn->query($sql);
                        if ($result && $result->num_rows > 0) {
                            while ($row = $result->fetch_assoc()) {
                                $conf      = floatval($row['clock_in_conf']);
                                $confPct   = round($conf * 100);
                                $lowClass  = $conf < 0.8 ? 'low' : '';
                                $name      = htmlspecialchars($row['name']);
                                $clockIn   = htmlspecialchars($row['clock_in_time']);
                                echo "<li class='staff-item'><div><div class='staff-name'>$name</div><div class='staff-time'>In: $clockIn</div></div><div class='confidence-badge $lowClass'>{$confPct}%</div></li>";
                            }
                        } else {
                            echo "<div class='empty-state'><i class='bi bi-person-slash'></i><p>No staff clocked in</p></div>";
                        }
                        ?>
                    </ul>
                </div>
            </div>
        </div>

        <div class="card-custom">
            <div class="card-header">
                <span>Today's Attendance</span>
                <span id="attendance-count" style="font-size:14px;font-weight:400;">
                    <?php
                    $today = date('Y-m-d');
                    $res   = $conn->query("SELECT COUNT(*) AS cnt FROM attendance WHERE DATE(check_in)='$today'");
                    $cnt = $res ? $res->fetch_assoc()['cnt'] : 0;
                    echo $cnt . ' records';
                    ?>
                </span>
            </div>
            <div class="table-container" style="padding:0; overflow-y:auto; max-height:500px;">
                <table class="attendance-table">
                    <thead><tr><th>Name</th><th>Clock In</th><th>Clock Out</th><th>Duration</th><th>Status</th></tr></thead>
                    <tbody id="attendance-table-body">
                        <?php
                        $today  = date('Y-m-d');
                        $sql    = "SELECT e.name, COALESCE(a.clock_in_time,  TIME(a.check_in))  AS clock_in_time, COALESCE(a.clock_out_time, TIME(a.check_out)) AS clock_out_time, a.duration_mins, COALESCE(a.att_status, a.status) AS status FROM attendance a JOIN employees  e ON a.emp_id = e.emp_id WHERE DATE(a.check_in)='$today' ORDER BY a.check_in DESC";
                        $result = $conn->query($sql);
                        if ($result && $result->num_rows > 0) {
                            while ($row = $result->fetch_assoc()) {
                                $name      = htmlspecialchars($row['name']);
                                $clockIn   = htmlspecialchars($row['clock_in_time'] ?? '—');
                                $clockOut  = htmlspecialchars($row['clock_out_time'] ?? '—');
                                $duration  = $row['duration_mins'] ? $row['duration_mins'] . ' min' : '—';
                                $status    = $row['status'] === 'clocked_in' ? 'Clocked In' : 'Completed';
                                $statusCls = $row['status'] === 'clocked_in' ? 'clocked-in' : 'completed';
                                echo "<tr><td>$name</td><td>$clockIn</td><td>$clockOut</td><td>$duration</td><td><span class='status-badge $statusCls'>$status</span></td></tr>";
                            }
                        } else {
                            echo "<tr><td colspan='5' style='text-align:center;padding:40px;'><i class='bi bi-inbox' style='font-size:32px;color:#ddd;'></i><p style='color:#999;margin-top:10px;'>No attendance records yet</p></td></tr>";
                        }
                        ?>
                    </tbody>
                </table>
            </div>
            <div class="action-buttons">
                <button class="btn-export" onclick="exportToCSV()"><i class="bi bi-download"></i> Export CSV</button>
                <button class="btn-export" onclick="location.reload()"><i class="bi bi-arrow-clockwise"></i> Refresh</button>
            </div>
        </div>

    </div> 
    
    <div class="card-custom" style="margin-bottom:25px;">
        <div class="card-header">
            <span><i class="bi bi-people-fill"></i> All Registered Employees</span>
            <span style="font-size:14px;font-weight:400;">
                <?php
                $res_emps = $conn->query("SELECT COUNT(*) AS cnt FROM employees");
                $total_emps = $res_emps ? $res_emps->fetch_assoc()['cnt'] : 0;
                echo $total_emps . ' Employees';
                ?>
            </span>
        </div>
        <div class="table-container" style="padding:0; overflow-y:auto; max-height:400px;">
            <table class="attendance-table">
                <thead><tr><th>Employee ID</th><th>Name</th><th>Outlet</th><th>Registered Date</th></tr></thead>
                <tbody>
                    <?php
                    $emp_sql = "SELECT emp_id, name, outlet, created_at FROM employees ORDER BY created_at DESC";
                    $emp_result = $conn->query($emp_sql);
                    if ($emp_result && $emp_result->num_rows > 0) {
                        while ($row = $emp_result->fetch_assoc()) {
                            $e_id = htmlspecialchars($row['emp_id']);
                            $e_name = htmlspecialchars($row['name']);
                            $e_outlet = htmlspecialchars($row['outlet'] ?? 'Unassigned');
                            $e_date = htmlspecialchars($row['created_at']);
                            echo "<tr><td><strong>$e_id</strong></td><td>$e_name</td><td>$e_outlet</td><td style='color:#666; font-size:13px;'>$e_date</td></tr>";
                        }
                    } else {
                        echo "<tr><td colspan='4' style='text-align:center;padding:40px;'><i class='bi bi-person-x' style='font-size:32px;color:#ddd;'></i><p style='color:#999;margin-top:10px;'>No registered employees found in the database.</p></td></tr>";
                    }
                    ?>
                </tbody>
            </table>
        </div>
    </div>

</div> 

<div class="modal fade" id="clockOutModal" tabindex="-1" data-bs-backdrop="static" data-bs-keyboard="false">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title"><i class="bi bi-clock-history"></i> Confirm Clock-Out</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <img id="modal-snapshot" class="clock-out-snapshot" src="" alt="Employee snapshot">
                <div class="clock-out-info">
                    <div class="clock-out-info-item"><label>Name</label><value id="modal-name">—</value></div>
                    <div class="clock-out-info-item"><label>Confidence</label><value id="modal-confidence">—</value></div>
                    <div class="clock-out-info-item"><label>Time</label><value id="modal-time">—</value></div>
                    <div class="clock-out-info-item"><label>Department</label><value id="modal-dept">—</value></div>
                </div>
                <p style="color:#666;font-size:14px;text-align:center;">Confirm this employee's clock-out?</p>
                <button class="btn-confirm" id="confirm-btn" onclick="confirmClockOut()"><i class="bi bi-check-circle"></i> Confirm Clock-Out</button>
                <button class="btn-cancel" onclick="dismissModal()">Cancel</button>
            </div>
        </div>
    </div>
</div>

<div class="toast-container" id="toast-container"></div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<script>
    const FLASK = 'http://localhost:5000';

    // ── වෙනස් කළ කොටස: 'polling' ඉවත් කර 100% websocket පමණක් යොදා ඇත ──
    const socket = io(FLASK, {
        transports: ['websocket'], 
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        timeout: 5000,
    });

    let shiftEndHour  = 22;
    let pendingClockOut = null;

    socket.on('connect', () => {
        updateConnectionStatus('Connected', true);
        showToast('WebSocket connected', 'success');
    });

    socket.on('disconnect', () => {
        updateConnectionStatus('Disconnected', false);
    });

    socket.on('connect_error', (err) => {
        updateConnectionStatus('Error — is app.py running?', false);
    });

    socket.on('video_stream', (data) => {
        if (data && data.frame) {
            const img = document.getElementById('video-feed');
            img.src = 'data:image/jpeg;base64,' + data.frame;
            img.style.display = 'block';
            document.getElementById('feed-offline').style.display = 'none';
        }
    });

    socket.on('initial_data', (data) => {
        shiftEndHour = data.shift_end_hour || 22;
        renderStaffList(data.clocked_in_staff || []);
        renderAttendanceTable(data.attendance_today || []);
    });

    socket.on('clock_in_event', (data) => {
        showToast(`✓ ${data.name} clocked in at ${data.time}`, 'success');
        socket.emit('request_attendance'); 
    });

    socket.on('clock_out_pending', (data) => {
        pendingClockOut = data;
        showClockOutModal(data);
    });

    socket.on('clock_out_confirmed', (data) => {
        showToast(`✓ ${data.name} clocked out`, 'success');
        socket.emit('request_attendance');
    });

    socket.on('attendance_update', (data) => {
        renderStaffList(data.clocked_in || []);
        renderAttendanceTable(data.data || []);
    });

    function renderStaffList(staff) {
        const list  = document.getElementById('staff-list');
        const count = document.getElementById('staff-count');
        if (!staff.length) {
            list.innerHTML = `<div class="empty-state"><i class="bi bi-person-slash"></i><p>No staff clocked in</p></div>`;
            count.textContent = '0 staff';
            return;
        }
        list.innerHTML = staff.map(s => {
            const pct = Math.round((s.clock_in_conf || 0) * 100);
            const low = (s.clock_in_conf || 0) < 0.8 ? 'low' : '';
            return `<li class="staff-item"><div><div class="staff-name">${s.name}</div><div class="staff-time">In: ${s.clock_in_time}</div></div><div class="confidence-badge ${low}">${pct}%</div></li>`;
        }).join('');
        count.textContent = `${staff.length} staff`;
    }

    function renderAttendanceTable(records) {
        const tbody = document.getElementById('attendance-table-body');
        const count = document.getElementById('attendance-count');
        if (!records.length) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:40px;"><i class="bi bi-inbox" style="font-size:32px;color:#ddd;"></i><p style="color:#999;margin-top:10px;">No attendance records yet</p></td></tr>`;
            count.textContent = '0 records';
            return;
        }
        tbody.innerHTML = records.map(r => {
            const dur    = r.duration_mins ? r.duration_mins + ' min' : '—';
            const status = r.status === 'clocked_in' ? 'Clocked In' : 'Completed';
            const cls    = r.status === 'clocked_in' ? 'clocked-in' : 'completed';
            return `<tr><td>${r.name}</td><td>${r.clock_in_time || '—'}</td><td>${r.clock_out_time || '—'}</td><td>${dur}</td><td><span class="status-badge ${cls}">${status}</span></td></tr>`;
        }).join('');
        count.textContent = `${records.length} records`;
    }

    function showClockOutModal(data) {
        const filename = data.snapshot_path ? data.snapshot_path.split(/[\\/]/).pop() : '';
        document.getElementById('modal-snapshot').src = filename ? `${FLASK}/api/snapshot/${filename}` : '';
        document.getElementById('modal-name').textContent       = data.name;
        document.getElementById('modal-confidence').textContent = Math.round(data.confidence * 100) + '%';
        document.getElementById('modal-time').textContent       = data.time;
        document.getElementById('modal-dept').textContent       = data.dept || 'Unassigned';
        document.getElementById('confirm-btn').dataset.pendingId = data.pending_id;
        new bootstrap.Modal(document.getElementById('clockOutModal')).show();
    }

    function confirmClockOut() {
        if (!pendingClockOut) return;
        const btn = document.getElementById('confirm-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="loading-spinner"></span> Confirming...';

        fetch(`${FLASK}/api/clockout/confirm/${pendingClockOut.pending_id}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }
        })
        .then(r => r.json())
        .then(data => {
            dismissModal();
            showToast(`✓ ${data.message}`, 'success');
            socket.emit('request_attendance');
        })
        .catch(e => {
            showToast('Confirm failed: ' + e, 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle"></i> Confirm Clock-Out';
        });
    }

    function dismissModal() {
        const m = bootstrap.Modal.getInstance(document.getElementById('clockOutModal'));
        if (m) m.hide();
        pendingClockOut = null;
    }

    function updateConnectionStatus(text, ok) {
        const el  = document.getElementById('connection-status');
        el.textContent = text;
        const dot = el.closest('.info-item').querySelector('.status-indicator');
        dot.className = 'status-indicator' + (ok ? ' status-connected' : '');
    }

    function showToast(msg, type = 'info') {
        const c     = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'x-circle' : 'info-circle';
        toast.innerHTML = `<i class="bi bi-${icon}"></i><span>${msg}</span>`;
        c.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    function exportToCSV() {
        const rows  = document.querySelectorAll('#attendance-table-body tr');
        const heads = ['Name','Clock In','Clock Out','Duration','Status'];
        let csv     = heads.join(',') + '\n';
        rows.forEach(row => {
            const cells = [...row.querySelectorAll('td')].map(td => `"${td.textContent.trim()}"`);
            if (cells.length === 5) csv += cells.join(',') + '\n';
        });
        const a    = document.createElement('a');
        a.href     = 'data:text/csv,' + encodeURIComponent(csv);
        a.download = `attendance_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        showToast('Exported to CSV', 'success');
    }

    setInterval(() => {
        document.getElementById('current-time').textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
    }, 1000);

    socket.emit('request_attendance');
</script>
</body>
</html>
<?php $conn->close(); ?>