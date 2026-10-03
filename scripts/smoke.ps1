# Поднимает port-forward к gateway, запускает smoke-тест и закрывает port-forward.
# pytest должен быть в PATH (активированный venv).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path reports)) { New-Item -ItemType Directory reports | Out-Null }

$pf = Start-Process kubectl -ArgumentList "port-forward -n library svc/gateway 8081:80" `
      -PassThru -WindowStyle Hidden
try {
    $ok = $false
    foreach ($i in 1..30) {
        try { Invoke-WebRequest -UseBasicParsing http://localhost:8081/api/health | Out-Null; $ok = $true; break }
        catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ok) { throw "gateway is not reachable on localhost:8081" }

    $env:BASE_URL = "http://localhost:8081"
    pytest tests/ --junitxml=reports/results.xml
    $code = $LASTEXITCODE
}
finally {
    Stop-Process -Id $pf.Id -Force -ErrorAction SilentlyContinue
}
exit $code

