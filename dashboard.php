<?php
date_default_timezone_set('Asia/Colombo');
include 'connectin.php';
session_start();

if (!isset($_SESSION['company_id'])) {
    header("Location: login.php");
    exit();
}
$current_company_id = $_SESSION['company_id'];
$current_company_name = $_SESSION['company_name'];

$flash_msg = '';
$flash_type = '';
if (isset($_SESSION['msg'])) {
    $flash_msg = $_SESSION['msg'];
    $flash_type = $_SESSION['msg_type'];
    unset($_SESSION['msg']);
    unset($_SESSION['msg_type']);
}

// ── 1. EMPLOYEE DELETE HANDLER ────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['delete_emp_id'])) {
    $emp_id_to_delete = trim($_POST['delete_emp_id']);
    // Optional: Send delete request to flask API if you have one, or delete locally
    $stmt = $conn->prepare("DELETE FROM employees WHERE emp_id = ? AND company_id = ?");
    $stmt->bind_param("si", $emp_id_to_delete, $current_company_id);
    if ($stmt->execute()) {
        $_SESSION['msg'] = "Employee deleted successfully!";
        $_SESSION['msg_type'] = "success";
    } else {
        $_SESSION['msg'] = "Failed to delete employee.";
        $_SESSION['msg_type'] = "error";
    }
    header("Location: " . $_SERVER['PHP_SELF']);
    exit();
}

// ── 2. ADD TRACKING PERIOD ────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['add_period'])) {
    $p_name = $_POST['period_name'];
    $p_start = $_POST['start_time'];
    $p_end = $_POST['end_time'];
    $stmt = $conn->prepare("INSERT INTO tracking_periods (company_id, period_name, start_time, end_time) VALUES (?, ?, ?, ?)");
    $stmt->bind_param("isss", $current_company_id, $p_name, $p_start, $p_end);
    if ($stmt->execute()) {
        $_SESSION['msg'] = "Tracking period added successfully!";
        $_SESSION['msg_type'] = "success";
    } else {
        $_SESSION['msg'] = "Failed to add tracking period.";
        $_SESSION['msg_type'] = "error";
    }
    header("Location: " . $_SERVER['PHP_SELF']);
    exit();
}

// ── 3. DELETE TRACKING PERIOD ────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['delete_period_id'])) {
    $del_id = $_POST['delete_period_id'];
    $stmt = $conn->prepare("DELETE FROM tracking_periods WHERE id = ? AND company_id = ?");
    $stmt->bind_param("ii", $del_id, $current_company_id);
    if ($stmt->execute()) {
        $_SESSION['msg'] = "Tracking period deleted successfully!";
        $_SESSION['msg_type'] = "success";
    } else {
        $_SESSION['msg'] = "Failed to delete tracking period.";
        $_SESSION['msg_type'] = "error";
    }
    header("Location: " . $_SERVER['PHP_SELF']);
    exit();
}

// ── 4. AJAX HANDLER FOR MODAL (Dynamic Reports) ────────────────
if (isset($_GET['ajax_tracking_emp'])) {
    $emp_id = $_GET['ajax_tracking_emp'];

    // සමාගමට අදාළ සියලුම Tracking Periods ලබාගැනීම
    $stmt_p = $conn->prepare("SELECT * FROM tracking_periods WHERE company_id = ? ORDER BY start_time ASC");
    $stmt_p->bind_param("i", $current_company_id);
    $stmt_p->execute();
    $res = $stmt_p->get_result();
    $periods = [];

    while ($r = $res->fetch_assoc()) {
        $st = $r['start_time'];
        $et = $r['end_time'];

        // අද දින අදාළ Time Window එක ඇතුළත ඇති Pings ගණන සෙවීම
        // Join with employees to ensure the emp belongs to current company
        $stmt = $conn->prepare("SELECT COUNT(a.id) as pings FROM activity_logs a JOIN employees e ON a.emp_id = e.emp_id WHERE a.emp_id = ? AND e.company_id = ? AND DATE(a.log_time) = CURDATE() AND TIME(a.log_time) BETWEEN ? AND ?");
        $stmt->bind_param("siss", $emp_id, $current_company_id, $st, $et);
        $stmt->execute();
        $ping_count = $stmt->get_result()->fetch_assoc()['pings'];

        // 1 Ping = 5 Minutes (Edge PC එකේ Throttling එකට අනුව)
        $mins = $ping_count * 5;

        $r['pings'] = $ping_count;
        $r['mins'] = $mins;

        // Status logic
        $current_time = date('H:i:s');
        if ($current_time < $st) {
            $r['status'] = 'upcoming';
        } elseif ($current_time >= $st && $current_time <= $et) {
            $r['status'] = 'active';
        } else {
            $r['status'] = 'completed';
        }

        $periods[] = $r;
    }

    header('Content-Type: application/json');
    echo json_encode($periods);
    exit();
}

$host = $_SERVER['SERVER_NAME'] ?? '127.0.0.1';
$protocol = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || (isset($_SERVER['SERVER_PORT']) && $_SERVER['SERVER_PORT'] == 443) ? "https://" : "http://";
$FLASK_URL = $protocol . $host . ":5000";
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
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 20px;
        }

        .container-main {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            padding: 20px 30px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            margin: 0;
            color: #333;
            font-weight: 700;
            font-size: 28px;
        }

        .header-info {
            display: flex;
            gap: 30px;
            align-items: center;
            font-size: 14px;
        }

        .header-info .info-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }

        .status-connected {
            background: #10b981;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {

            0%,
            100% {
                opacity: 1;
            }

            50% {
                opacity: 0.5;
            }
        }

        .custom-tabs {
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
            margin-bottom: 20px;
        }

        .custom-tabs .nav-link {
            color: white;
            opacity: 0.7;
            border: none;
            font-weight: 600;
            padding: 12px 25px;
            border-radius: 10px 10px 0 0;
            font-size: 15px;
            transition: all 0.3s;
        }

        .custom-tabs .nav-link:hover {
            opacity: 1;
            border-color: transparent;
            isolation: isolate;
        }

        .custom-tabs .nav-link.active {
            color: #667eea;
            background: white;
            opacity: 1;
            box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.05);
        }

        .grid-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin-bottom: 25px;
        }

        @media (max-width: 1024px) {
            .grid-container {
                grid-template-columns: 1fr;
            }
        }

        .card-custom {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            margin-bottom: 25px;
        }

        .card-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            font-size: 18px;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card-body {
            padding: 20px;
            flex: 1;
            overflow-y: auto;
            max-height: 500px;
        }

        #video-feed {
            width: 100%;
            height: 100%;
            object-fit: cover;
            background: #000;
            border-radius: 0;
            display: block;
        }

        .staff-list {
            list-style: none;
        }

        .staff-item {
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .staff-name {
            font-weight: 600;
            color: #333;
            font-size: 15px;
        }

        .staff-time {
            color: #999;
            font-size: 13px;
        }

        .btn-checkout-inline {
            background: #ef4444;
            color: white;
            border: none;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .btn-checkout-inline:hover {
            background: #dc2626;
        }

        .confidence-badge {
            display: inline-block;
            background: #10b981;
            color: white;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }

        .confidence-badge.low {
            background: #f59e0b;
        }

        .attendance-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        .attendance-table thead {
            background: #f5f5f5;
            position: sticky;
            top: 0;
            z-index: 1;
        }

        .attendance-table th {
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #ddd;
        }

        .attendance-table td {
            padding: 12px;
            border-bottom: 1px solid #eee;
        }

        .clickable-row {
            cursor: pointer;
            transition: background 0.2s;
        }

        .clickable-row:hover {
            background-color: #f0fdf4 !important;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
        }

        .status-badge.clocked-in {
            background: #dbeafe;
            color: #1e40af;
        }

        .status-badge.completed {
            background: #dcfce7;
            color: #166534;
        }

        .status-badge.pending {
            background: #fef3c7;
            color: #92400e;
        }

        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #999;
        }

        .action-buttons {
            display: flex;
            gap: 10px;
            padding: 15px 20px;
            border-top: 1px solid #f0f0f0;
        }

        .btn-export {
            flex: 1;
            background: #f0f0f0;
            border: 1px solid #ddd;
            color: #333;
            padding: 10px;
            border-radius: 6px;
            font-weight: 500;
            cursor: pointer;
        }

        .btn-export:hover {
            background: #e5e5e5;
        }

        .toast-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
        }

        .toast-notification {
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            margin-bottom: 10px;
            animation: slideIn 0.3s;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }

            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        .toast-success {
            border-left: 4px solid #10b981;
            color: #10b981;
        }

        .toast-info {
            border-left: 4px solid #3b82f6;
            color: #3b82f6;
        }

        .toast-error {
            border-left: 4px solid #ef4444;
            color: #ef4444;
        }
    </style>
</head>

<body>
    <div class="container-main">

        <div class="header">
            <h1><i class="bi bi-buildings"></i> <?php echo htmlspecialchars($current_company_name); ?> Dashboard</h1>
            <div class="header-info">

                <div class="engine-controls"
                    style="background: #f8fafc; padding: 6px 15px; border-radius: 8px; display: flex; gap: 10px; align-items: center; border: 1px solid #e2e8f0; margin-right: 15px;">
                    <label for="camDropdown" style="font-size: 13px; font-weight: 600; color: #475569; margin: 0;">
                        <i class="bi bi-camera-video"></i> Camera:
                    </label>
                    <select id="camDropdown" class="form-select form-select-sm"
                        style="width: auto; font-size: 13px; font-weight: 500; cursor: pointer; border-color: #cbd5e1;"
                        onchange="updateEngineSettings()">
                        <option value="OFF" style="color: #ef4444; font-weight: 600;">🔴 OFF (Release Camera)</option>
                        <option value="0">🟢 Local Edge PC 1</option>
                        <option value="1">🟢 Local Edge PC 2</option>
                    </select>
                </div>

                <a href="index.php" class="btn"
                    style="background:#10b981; color:white; padding:8px 15px; border-radius:6px; text-decoration:none; font-weight:600; font-size:14px; display:flex; align-items:center; gap:6px;">
                    <i class="bi bi-person-plus-fill"></i> Register User
                </a>
                <a href="logout.php" class="btn btn-outline-danger btn-sm px-3" style="font-weight: 600;">Logout</a>

                <div class="info-item ms-2">
                    <span class="status-indicator status-connected"></span>
                    <span>WS: <strong id="connection-status">Connecting...</strong></span>
                </div>
                <div class="info-item">
                    Time: <strong id="current-time">00:00:00</strong>
                </div>
            </div>
        </div>

        <ul class="nav nav-tabs custom-tabs" id="dashboardTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="live-tab" data-bs-target="#live-pane"
                    type="button" role="tab" aria-selected="true">
                    <i class="bi bi-broadcast"></i> Live Feed
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="attendance-tab" data-bs-target="#attendance-pane"
                    type="button" role="tab" aria-selected="false">
                    <i class="bi bi-list-check"></i> Attendance
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="employees-tab" data-bs-target="#employees-pane"
                    type="button" role="tab" aria-selected="false">
                    <i class="bi bi-people"></i> Employees
                </button>
            </li>
            <!-- [NEW TAB] Tracking Settings -->
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="settings-tab" data-bs-target="#settings-pane"
                    type="button" role="tab" aria-selected="false">
                    <i class="bi bi-gear"></i> Tracking Settings
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
                                <span style="font-size:12px;font-weight:400;">Main Entrance</span>
                            </div>
                            <div class="card-body"
                                style="padding:0; position:relative; overflow:hidden; background:#000;">
                                <img id="video-feed" src="" alt="Camera feed"
                                    onerror="this.style.display='none'; document.getElementById('feed-offline').style.display='flex';">
                                <div id="feed-offline"
                                    style="display:none; color:#aaa; text-align:center; position:absolute; top:0; left:0; width:100%; height:100%; flex-direction:column; align-items:center; justify-content:center; gap:8px;">
                                    <span style="font-size:32px;">📷</span><span>Waiting for Edge PC stream...</span>
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
                                    <div class='empty-state'><i class='bi bi-person-slash'></i>
                                        <p>Loading...</p>
                                    </div>
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

                    <div
                        style="background: #e0f2fe; padding: 12px 20px; font-size: 14px; color: #0369a1; border-bottom: 1px solid #bae6fd;">
                        <i class="bi bi-info-circle-fill"></i> <strong>Tip:</strong> Click on any employee's row below
                        to view their <b>Live Tracking Reports</b> for today.
                    </div>

                    <div class="card-body" style="padding:0; overflow-y:auto; max-height:500px;">
                        <table class="attendance-table">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Clock In</th>
                                    <th>Clock Out</th>
                                    <th>Duration</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody id="attendance-table-body">
                                <tr>
                                    <td colspan="5" class="empty-state">Loading records...</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="action-buttons">
                        <button class="btn-export" onclick="exportToCSV()" title="Download today's attendance">
                            <i class="bi bi-file-earmark-spreadsheet"></i> Today's Report
                        </button>

                        <button class="btn-export"
                            style="background:#10b981; color:white; border:none; font-weight: 600;"
                            onclick="downloadMonthlyCSV()">
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
                        <span><i class="bi bi-people-fill"></i> Registered Employees</span>
                    </div>
                    <div class="card-body" style="padding:0; overflow-y:auto; max-height:500px;">
                        <table class="attendance-table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Name</th>
                                    <th>Outlet</th>
                                    <th>Registered Date</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php
                                $emp_sql = "SELECT emp_id, name, outlet, created_at FROM employees WHERE company_id = ? ORDER BY created_at DESC";
                                $stmt_emp = $conn->prepare($emp_sql);
                                $stmt_emp->bind_param("i", $current_company_id);
                                $stmt_emp->execute();
                                $emp_result = $stmt_emp->get_result();
                                if ($emp_result && $emp_result->num_rows > 0) {
                                    while ($row = $emp_result->fetch_assoc()) {
                                        $e_id = htmlspecialchars($row['emp_id']);
                                        echo "<tr>
                                        <td><strong>$e_id</strong></td>
                                        <td>" . htmlspecialchars($row['name']) . "</td>
                                        <td>" . htmlspecialchars($row['outlet'] ?? '—') . "</td>
                                        <td style='color:#666; font-size:13px;'>" . htmlspecialchars($row['created_at']) . "</td>
                                        <td>
                                            <form method='POST' style='margin:0;' onsubmit='return confirm(\"Delete this employee?\");'>
                                                <input type='hidden' name='delete_emp_id' value='$e_id'>
                                                <button type='submit' class='btn btn-danger btn-sm' style='padding:2px 8px; font-size:12px;'>Delete</button>
                                            </form>
                                        </td>
                                    </tr>";
                                    }
                                } else {
                                    echo "<tr><td colspan='5' class='empty-state'>No employees found.</td></tr>";
                                }
                                ?>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- [NEW] TRACKING SETTINGS PANE -->
            <div class="tab-pane fade" id="settings-pane" role="tabpanel" aria-labelledby="settings-tab">
                <div class="row">
                    <div class="col-md-5">
                        <div class="card-custom">
                            <div class="card-header"><span>Add New Tracking Period</span></div>
                            <div class="card-body">
                                <form method="POST">
                                    <input type="hidden" name="add_period" value="1">
                                    <div class="mb-3">
                                        <label class="form-label text-muted small fw-bold">Period Name (e.g. Morning
                                            Shift)</label>
                                        <input type="text" name="period_name" class="form-control" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label text-muted small fw-bold">Start Time</label>
                                        <input type="time" name="start_time" class="form-control" required>
                                    </div>
                                    <div class="mb-4">
                                        <label class="form-label text-muted small fw-bold">End Time</label>
                                        <input type="time" name="end_time" class="form-control" required>
                                    </div>
                                    <button type="submit" class="btn w-100"
                                        style="background:#10b981; color:white; font-weight:bold;">
                                        <i class="bi bi-plus-circle"></i> Save Period
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-7">
                        <div class="card-custom">
                            <div class="card-header"><span>Active Tracking Periods</span></div>
                            <div class="card-body" style="padding:0;">
                                <table class="attendance-table">
                                    <thead>
                                        <tr>
                                            <th>Name</th>
                                            <th>Time Window</th>
                                            <th>Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <?php
                                        $p_sql = "SELECT id, period_name, start_time, end_time FROM tracking_periods WHERE company_id = ? ORDER BY start_time ASC";
                                        $stmt_p2 = $conn->prepare($p_sql);
                                        $stmt_p2->bind_param("i", $current_company_id);
                                        $stmt_p2->execute();
                                        $p_res = $stmt_p2->get_result();
                                        if ($p_res && $p_res->num_rows > 0) {
                                            while ($p = $p_res->fetch_assoc()) {
                                                $pid = $p['id'];
                                                echo "<tr>
                                                <td><strong>" . htmlspecialchars($p['period_name']) . "</strong></td>
                                                <td>" . date('h:i A', strtotime($p['start_time'])) . " - " . date('h:i A', strtotime($p['end_time'])) . "</td>
                                                <td>
                                                    <form method='POST' style='margin:0;' onsubmit='return confirm(\"Remove this period?\");'>
                                                        <input type='hidden' name='delete_period_id' value='$pid'>
                                                        <button type='submit' class='btn btn-outline-danger btn-sm border-0' title='Delete'><i class='bi bi-trash3-fill'></i></button>
                                                    </form>
                                                </td>
                                            </tr>";
                                            }
                                        } else {
                                            echo "<tr><td colspan='3' class='empty-state'>No tracking periods set. Add periods to track employee presence.</td></tr>";
                                        }
                                        ?>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <!-- DYNAMIC MODAL (AJAX Loaded) -->
    <div class="modal fade" id="timeWindowModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-lg modal-dialog-centered">
            <div class="modal-content" style="border: none; border-radius: 12px; overflow: hidden;">
                <div class="modal-header"
                    style="background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%); color: white; padding: 20px;">
                    <h5 class="modal-title" style="font-weight: 600;">
                        <i class="bi bi-person-bounding-box"></i> Live Tracking Report: <span id="modal-emp-name"
                            style="text-decoration: underline;">Employee</span>
                    </h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"
                        aria-label="Close"></button>
                </div>
                <div class="modal-body" style="padding: 0;">
                    <table class="attendance-table" style="margin: 0;">
                        <thead>
                            <tr style="background: #fff8f1;">
                                <th>Tracking Period</th>
                                <th>Time Present (Pings)</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="modal-tracking-body">
                            <tr>
                                <td colspan="3" class="empty-state">Loading data...</td>
                            </tr>
                        </tbody>
                    </table>
                    <div
                        style="padding: 15px 20px; font-size: 13px; color: #666; background: #fafafa; border-top: 1px solid #eee;">
                        <i class="bi bi-info-circle text-primary"></i> <b>Note:</b> Shows presence data for today. 1
                        Active Ping = 5 Mins of presence.
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
        setInterval(() => {
            const timeEl = document.getElementById('current-time');
            if (timeEl) timeEl.textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
        }, 1000);

        window.addEventListener('error', function (e) {
            const errEl = document.getElementById('connection-status');
            if (errEl) errEl.textContent = 'JS Error: ' + e.message;
        });

        const FLASK = '<?php echo $FLASK_URL; ?>';
        const CURRENT_COMPANY_ID = "<?php echo $current_company_id; ?>";
        const API_KEY = "<?php echo isset($_SESSION['api_key']) ? $_SESSION['api_key'] : ''; ?>";

        let socket;
        try {
            socket = io(FLASK, { query: { company_id: CURRENT_COMPANY_ID } });

            setInterval(() => {
                if (CURRENT_COMPANY_ID && socket) socket.emit('request_attendance', { company_id: CURRENT_COMPANY_ID });
            }, 5000);
        } catch (err) {
            console.error("SocketIO Initialization Error:", err);
            const errEl = document.getElementById('connection-status');
            if (errEl) errEl.textContent = 'Socket.io not loaded!';
        }

        let timeWindowModal;
        document.addEventListener("DOMContentLoaded", function () {
            timeWindowModal = new bootstrap.Modal(document.getElementById('timeWindowModal'));

            <?php if (!empty($flash_msg)): ?>
                showToast("<?php echo addslashes($flash_msg); ?>", "<?php echo addslashes($flash_type); ?>");
            <?php endif; ?>

            socket.on('connect', () => {
                updateConnectionStatus('Connected', true);
                socket.emit('request_attendance', { company_id: CURRENT_COMPANY_ID });
            });

            socket.on('disconnect', () => updateConnectionStatus('Disconnected', false));

            socket.on('connect_error', (error) => {
                updateConnectionStatus('Error: ' + error.message, false);
                console.error('Socket connection error:', error);
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
                renderStaffList(data.clocked_in_staff || []);
                renderAttendanceTable(data.attendance_today || []);
            });

            socket.on('attendance_update', (data) => {
                renderStaffList(data.clocked_in || []);
                renderAttendanceTable(data.data || []);
            });

            socket.on('clock_out_confirmed', (data) => {
                showToast(`✓ ${data.name} clocked out successfully`, 'success');
                socket.emit('request_attendance', { company_id: CURRENT_COMPANY_ID });
            });

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
                if (!empId) { showToast('Error: Employee ID is missing!', 'error'); return; }
                if (!confirm(`Are you sure you want to clock out ${empName}?`)) return;

                btnElement.disabled = true;
                btnElement.innerHTML = `<i class="bi bi-hourglass-split"></i>...`;

                fetch(`${FLASK}/api/event`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key: API_KEY, employee_id: empId, name: empName, event_type: 'clock_out' })
                })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success || data.event === 'clock_out_confirmed') {
                            socket.emit('request_attendance', { company_id: CURRENT_COMPANY_ID });
                        } else {
                            showToast(data.error || 'Clock out failed', 'error');
                            btnElement.disabled = false; btnElement.innerHTML = `Check Out`;
                        }
                    })
                    .catch(e => { showToast('Connection error', 'error'); btnElement.disabled = false; btnElement.innerHTML = `Check Out`; });
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
                    const empId = r.employee_id || r.emp_id || '';

                    // [NEW] Passes both Name and Emp ID to load dynamic data
                    return `<tr class="clickable-row" onclick="openTimeWindowModal('${r.name}', '${empId}')" title="View live tracking for ${r.name}">
                        <td><strong>${r.name}</strong></td>
                        <td>${r.clock_in_time || '—'}</td>
                        <td>${r.clock_out_time || '—'}</td>
                        <td>${dur}</td>
                        <td><span class="status-badge ${cls}">${status}</span></td>
                    </tr>`;
                }).join('');
                count.textContent = `${records.length} records`;
            }

            // [NEW] AJAX Fetch for Dynamic Reports
            function openTimeWindowModal(employeeName, empId) {
                document.getElementById('modal-emp-name').textContent = employeeName;
                const tbody = document.getElementById('modal-tracking-body');
                tbody.innerHTML = '<tr><td colspan="3" class="empty-state"><div class="spinner-border spinner-border-sm text-primary"></div> Loading tracking data...</td></tr>';
                timeWindowModal.show();

                fetch(`?ajax_tracking_emp=${encodeURIComponent(empId)}`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.length === 0) {
                            tbody.innerHTML = '<tr><td colspan="3" class="empty-state text-warning"><i class="bi bi-exclamation-triangle"></i> No tracking periods defined in Tracking Settings.</td></tr>';
                            return;
                        }

                        function formatTime(timeStr) {
                            const [h, m] = timeStr.split(':');
                            const d = new Date(); d.setHours(h, m);
                            return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
                        }

                        let html = '';
                        data.forEach(p => {
                            let badge = '';
                            if (p.status === 'upcoming') badge = '<span class="status-badge pending"><i class="bi bi-clock"></i> Upcoming</span>';
                            else if (p.status === 'active') badge = '<span class="status-badge clocked-in"><i class="bi bi-camera-video"></i> Active Now</span>';
                            else badge = '<span class="status-badge completed"><i class="bi bi-check-circle"></i> Completed</span>';

                            const pingsText = p.pings > 0 ? `<small class="text-muted ms-2">(${p.pings} active logs)</small>` : '';
                            const timeHighlight = p.mins > 0 ? `<strong>${p.mins} Mins</strong>` : `<span class="text-muted">0 Mins</span>`;

                            html += `<tr>
                        <td><strong>${p.period_name}</strong><br><small class="text-muted">${formatTime(p.start_time)} – ${formatTime(p.end_time)}</small></td>
                        <td style="vertical-align: middle;">${timeHighlight} ${pingsText}</td>
                        <td style="vertical-align: middle;">${badge}</td>
                    </tr>`;
                        });
                        tbody.innerHTML = html;
                    })
                    .catch(e => {
                        tbody.innerHTML = '<tr><td colspan="3" class="empty-state text-danger">Failed to load data.</td></tr>';
                    });
            }

            function updateConnectionStatus(text, ok) {
                const el = document.getElementById('connection-status'); el.textContent = text;
                const dot = el.closest('.info-item').querySelector('.status-indicator');
                dot.className = 'status-indicator' + (ok ? ' status-connected' : '');
            }

            function showToast(msg, type = 'info') {
                const c = document.getElementById('toast-container');
                const toast = document.createElement('div'); toast.className = `toast-notification toast-${type}`;
                toast.innerHTML = `<i class="bi bi-${type === 'success' ? 'check-circle' : 'info-circle'}"></i><span>${msg}</span>`;
                c.appendChild(toast); setTimeout(() => toast.remove(), 4000);
            }

            function updateEngineSettings() {
                const camDropdown = document.getElementById('camDropdown');
                const selectedCam = camDropdown.value;
                if (selectedCam === 'OFF') {
                    socket.emit('stop_camera', { company_id: CURRENT_COMPANY_ID });
                    showToast("Camera stopped (Local Edge)", "info");
                } else {
                    socket.emit('start_camera', { company_id: CURRENT_COMPANY_ID, camera_id: selectedCam });
                    showToast(`Camera ${selectedCam} activated`, "success");
                }
            }

            function downloadCSV(csv, filename) {
                let csvFile = new Blob([csv], { type: "text/csv" });
                let downloadLink = document.createElement("a");
                downloadLink.download = filename;
                downloadLink.href = window.URL.createObjectURL(csvFile);
                downloadLink.style.display = "none";
                document.body.appendChild(downloadLink);
                downloadLink.click();
            }

            function downloadMonthlyCSV() {
                showToast("Monthly export triggered", "info");
                // Fallback or navigate to export endpoint
                window.location.href = `export_monthly.php?company_id=${CURRENT_COMPANY_ID}`;
            }

            function exportToCSV() {
                let csv = [];
                const rows = document.querySelectorAll("#attendance-table-body tr:not(.empty-state)");
                if (rows.length === 0) {
                    showToast("No data to export", "error");
                    return;
                }
                csv.push("Name,Clock In,Clock Out,Duration,Status");
                for (let i = 0; i < rows.length; i++) {
                    let row = [], cols = rows[i].querySelectorAll("td");
                    for (let j = 0; j < cols.length; j++)
                        row.push('"' + cols[j].innerText.replace(/"/g, '""') + '"');
                    csv.push(row.join(","));
                }
                downloadCSV(csv.join("\\n"), "daily_attendance.csv");
            }

            function refreshData() { window.location.reload(); }

            setInterval(() => {
                document.getElementById('current-time').textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
            }, 1000);
        });
    </script>
    <script>
        document.addEventListener("DOMContentLoaded", function () {
            const tabs = document.querySelectorAll('#dashboardTabs .nav-link');
            const panes = document.querySelectorAll('.tab-content .tab-pane');
            
            tabs.forEach(tab => {
                tab.addEventListener('click', function (e) {
                    e.preventDefault();
                    tabs.forEach(t => t.classList.remove('active'));
                    panes.forEach(p => p.classList.remove('show', 'active'));
                    
                    this.classList.add('active');
                    const targetId = this.getAttribute('data-bs-target');
                    if(targetId) {
                        const targetPane = document.querySelector(targetId);
                        if(targetPane) targetPane.classList.add('show', 'active');
                    }
                });
            });
        });
    </script>
</body>

</html>