@echo off
"C:/Windows/System32/taskkill.exe" /F /IM waitress-serve.exe /T 2>nul
"C:/Windows/System32/wbem/WMIC.exe" process call create "\"%WORKSPACE%/venv/Scripts/waitress-serve.exe\" --host=0.0.0.0 --port=%APP_PORT% app:app", "%WORKSPACE%"
"C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" -NoProfile -Command "Start-Sleep -Seconds 5"
"C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:%APP_PORT%/api/health' | Out-Null; Write-Host 'Health check OK' } catch { Write-Host 'Health check FAILED'; exit 1 }"
