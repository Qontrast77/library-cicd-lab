@echo off
"C:/Windows/System32/taskkill.exe" /F /IM waitress-serve.exe /T 2>nul
"%PYTHON%" scripts/deploy_start.py
"C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" -NoProfile -Command "Start-Sleep -Seconds 5"
"C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:%APP_PORT%/api/health' | Out-Null; Write-Host 'Health check OK' } catch { Write-Host 'Health check FAILED'; exit 1 }"