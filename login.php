<?php
include 'connectin.php';
session_start();

// දැනටමත් ලොග් වී ඇත්නම් කෙලින්ම Dashboard එකට යැවීම
if (isset($_SESSION['company_id'])) {
    header("Location: dashboard.php");
    exit();
}

$error = "";

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $user = trim($_POST['username']);
    $pass = trim($_POST['password']);

    if (!empty($user) && !empty($pass)) {
        // SQL Injection වලින් ආරක්ෂා වීමට Prepared Statements භාවිතය
        $stmt = $conn->prepare("SELECT id, company_name, api_key, password FROM companies WHERE username = ?");
        $stmt->bind_param("s", $user);
        $stmt->execute();
        $result = $stmt->get_result();

        if ($result->num_rows === 1) {
            $row = $result->fetch_assoc();
            
            // දැනට සරල පාස්වර්ඩ් පරීක්ෂාව (පසුව Password Hash කළ හැක)
            if ($pass === $row['password']) {
                $_SESSION['company_id']   = $row['id'];
                $_SESSION['company_name'] = $row['company_name'];
                $_SESSION['api_key']      = $row['api_key'];

                header("Location: dashboard.php");
                exit();
            } else {
                $error = "වැරදි මුද්‍රිත පදයක් (Invalid Password)!";
            }
        } else {
            $error = "එවැනි සමාගමක් ලියාපදිංචි වී නැත!";
        }
        $stmt->close();
    } else {
        $error = "කරුණාකර සියලුම කොටස් සම්පූර්ණ කරන්න!";
    }
}
$conn->close();
?>

<!DOCTYPE html>
<html lang="si">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SaaS Attendance - Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #1e1e38 0%, #0d0d1a 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Segoe UI', sans-serif;
            color: white;
        }
        .login-card {
            background: #131326;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 420px;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
        }
        .form-control {
            background: #1a1a35;
            border: 1px solid rgba(255,255,255,0.1);
            color: white;
        }
        .form-control:focus {
            background: #1a1a35;
            color: white;
            border-color: #667eea;
            box-shadow: none;
        }
    </style>
</head>
<body>

<div class="login-card">
    <h3 class="text-center mb-4" style="font-weight: 700;">SaaS Attendance Login</h3>
    <p class="text-center text-muted small mb-4">ඔබේ සමාගමේ ගිණුමට ඇතුල් වන්න</p>

    <?php if(!empty($error)): ?>
        <div class="alert alert-danger py-2 small text-center"><?php echo $error; ?></div>
    <?php endif; ?>

    <form method="POST" action="login.php">
        <div class="mb-3">
            <label class="form-label small">Username</label>
            <input type="text" name="username" class="form-control" placeholder="e.g. keells" required>
        </div>
        <div class="mb-4">
            <label class="form-label small">Password</label>
            <input type="password" name="password" class="form-control" placeholder="••••••••" required>
        </div>
        <button type="submit" class="btn btn-primary w-100 py-2 font-weight-bold">Log In</button>
    </form>
</div>

</body>
</html>