@echo off
"%DOCKER%" compose build
"%DOCKER%" compose up -d
"C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" -NoProfile -Command "Start-Sleep -Seconds 5"
"C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost/api/health' | Out-Null; Write-Host 'Health check OK' } catch { Write-Host 'Health check FAILED'; exit 1 }"
