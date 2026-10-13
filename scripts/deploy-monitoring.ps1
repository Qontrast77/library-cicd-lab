# Развёртывание мониторинга (Prometheus + node-exporter + cAdvisor + Grafana)
# Запуск из корня проекта: .\scripts\deploy-monitoring.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

kubectl apply -f monitoring/

foreach ($d in "deployment/prometheus", "deployment/grafana", "daemonset/node-exporter", "daemonset/cadvisor") {
    kubectl rollout status $d -n monitoring --timeout=300s
    if ($LASTEXITCODE -ne 0) { throw "rollout of $d failed" }
}
kubectl get all -n monitoring -o wide

Write-Host ""
Write-Host "Открой два отдельных окна PowerShell и оставь их работать:" -ForegroundColor Cyan
Write-Host "  kubectl port-forward -n monitoring svc/prometheus 9090:9090   -> http://localhost:9090"
Write-Host "  kubectl port-forward -n monitoring svc/grafana    3000:3000   -> http://localhost:3000 (admin / admin)"
