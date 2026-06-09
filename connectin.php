<?php
$userName   = "root";
$password   = "";
$database   = "face_attendance";
$servername = "localhost";

$conn = new mysqli($servername, $userName, $password, $database);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}
?>