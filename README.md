# 📸 Face Recognition Attendance System

A robust, real-time face recognition attendance management system built with Python (Flask) and PHP. This system utilizes advanced AI models (`DeepFace`, `Facenet512`, `YuNet`) to detect and recognize employees, logging their attendance directly into a MySQL database with zero-lag live video streaming via WebSockets.

## ✨ Key Features

* **🧠 Advanced AI Recognition:** Uses OpenCV YuNet for high-speed face detection and DeepFace (Facenet512) for accurate facial recognition.
* **⚡ Zero-Lag Live Dashboard:** Real-time video stream pushing from the Python backend to the PHP dashboard using WebSockets (`Socket.IO`).
* **👥 Employee Registration:** Dedicated portal (`index.php`) to capture multiple face poses (Straight, Left, Right, Up, Down) for high accuracy.
* **🕒 Automated & Manual Attendance:** Auto clock-in/out based on shift times, plus manual override capabilities from the dashboard.
* **🎥 Multi-Camera Support:** Built-in AI Engine Switcher to easily toggle between Local Webcams and IP Cameras (RTSP) to save CPU/Bandwidth.
* **📊 Reporting:** Export daily and monthly attendance records directly to CSV.

## 🛠️ Tech Stack

* **Backend (AI & API):** Python 3, Flask, Flask-SocketIO, DeepFace, OpenCV
* **Frontend (Dashboard):** PHP, HTML5, Bootstrap 5, Vanilla JS, Socket.IO Client
* **Database:** MySQL (via XAMPP)

---

## 🚀 Installation & Setup

### 1. Prerequisites
* **Python 3.8+** installed on your machine.
* **XAMPP** (or any other local server with PHP and MySQL).
* A webcam or an RTSP IP Camera.

### 2. Database Setup
1. Open XAMPP and start **Apache** and **MySQL**.
2. Go to `http://localhost/phpmyadmin/`.
3. Create a new database named `face_attendance`.
4. Import the provided SQL file (`127_0_0_1 (1).sql`) into this database to create the necessary tables.

### 3. Python Environment Setup
Open your terminal/command prompt in the project directory and install the required Python libraries:

```bash
pip install flask flask-cors flask-socketio opencv-python numpy deepface mysql-connector-python requests
