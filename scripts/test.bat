@echo off
call venv/Scripts/activate.bat
if not exist reports mkdir reports
pytest tests/ --junitxml=reports/results.xml
