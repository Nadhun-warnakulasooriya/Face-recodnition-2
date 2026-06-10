@echo off
chcp 65001 >nul
echo ═══════════════════════════════════════════════════════════
echo     Clean Installation ඉතිරි කරමින්...
echo ═══════════════════════════════════════════════════════════

taskkill /F /IM python.exe 2>nul
taskkill /F /IM code.exe 2>nul

echo.
echo [Step 1] pip upgrade කරමින්...
python -m pip install --upgrade pip setuptools wheel

echo.
echo [Step 2] pip cache purge කරමින්...
pip cache purge

echo.
echo [Step 3] numpy + protobuf පළමුවෙන්ම install කරමින්...
pip install --user --no-cache-dir numpy==1.24.3 protobuf==4.25.3

echo.
echo [Step 4] TensorFlow + Keras (compatible versions)...
pip install --user --no-cache-dir tensorflow==2.13.0 keras==2.13.1 gast==0.4.0

echo.
echo [Step 5] OpenCV + Computer Vision libraries...
pip install --user --no-cache-dir opencv-python==4.8.1.78 pillow==11.0.0

echo.
echo [Step 6] DeepFace + අනෙකුත් dependencies...
pip install --user --no-cache-dir deepface requests scipy scikit-learn

echo.
echo [Step 7] CustomTkinter (GUI)...
pip install --user --no-cache-dir customtkinter

echo.
echo [Step 8] PyTorch (CPU version)...
pip install --user torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

echo.
echo [Step 9] PyInstaller (EXE බිම්බිම් සඳහා)...
pip install --user pyinstaller

echo.
echo [Step 10] YuNet Model download කරමින්...
python -c "import urllib.request; urllib.request.urlretrieve('https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx', 'face_detection_yunet_2023mar.onnx'); print('✓ YuNet Model downloaded!')"

echo.
echo ═══════════════════════════════════════════════════════════
echo ✓ සියලුම libraries නිවුතුවා සිදු වුණා!
echo ═══════════════════════════════════════════════════════════
echo.
echo Python version check කරමින්...
python --version
pip list | findstr tensorflow

echo.
echo ✓ Ready! Build කිරීමට build.bat double-click කරන්න
pause