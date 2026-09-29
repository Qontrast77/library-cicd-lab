# Развёртывание в Kubernetes.
# Использование: .\scripts\deploy.ps1 [-Tag v1]
param([string]$Tag = "v1")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-postgres.yaml
kubectl rollout status statefulset/postgres -n library --timeout=180s

$tpl = Get-Content k8s/service.tpl.yaml -Raw
foreach ($n in "authors", "books", "members", "loans") {
    $tpl.Replace("__NAME__", $n).Replace("__TAG__", $Tag) | kubectl apply -f -
}
(Get-Content k8s/20-gateway.yaml -Raw).Replace("__TAG__", $Tag) | kubectl apply -f -

foreach ($d in "authors-service", "books-service", "members-service", "loans-service", "gateway") {
    kubectl rollout status deployment/$d -n library --timeout=180s
    if ($LASTEXITCODE -ne 0) { throw "rollout of $d failed" }
}
kubectl get all -n library
