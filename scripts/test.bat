@echo off
call venv/Scripts/activate.bat
if not exist reports mkdir reports
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke.ps1
