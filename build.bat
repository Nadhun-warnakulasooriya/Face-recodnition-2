@echo off
pyinstaller --onefile ^
  --windowed ^
  --name "Attendance-Scanner" ^
  --icon=icon.ico ^
  --add-data "face_detection_yunet_2023mar.onnx;." ^
  --hidden-import=cv2 ^
  --hidden-import=deepface ^
  --hidden-import=tensorflow ^
  --hidden-import=customtkinter ^
  test.py

echo Build complete! 
pause