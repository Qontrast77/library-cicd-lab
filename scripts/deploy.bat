@echo off
"C:/Windows/System32/net.exe" stop LibraryApp 2>nul
"C:/Windows/System32/net.exe" start LibraryApp
"C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" -NoProfile -Command "Start-Sleep -Seconds 3"
"C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:%APP_PORT%/api/health' | Out-Null; Write-Host 'Health check OK' } catch { Write-Host 'Health check FAILED'; exit 1 }"
