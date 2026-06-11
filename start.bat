@echo off
start cmd /k "python app.py"
timeout /t 5
start cmd /k "python Display-v2.py"