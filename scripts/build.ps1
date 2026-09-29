# Сборка образов внутри Docker-демона minikube (кластер увидит их без registry).
# Использование: .\scripts\build.ps1 [-Tag v1]
param([string]$Tag = "v1")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

& minikube -p minikube docker-env --shell powershell | Invoke-Expression

foreach ($n in "authors", "books", "members", "loans") {
    docker build -f services/Dockerfile --build-arg SERVICE=$n -t "library/$n-service:$Tag" services
    if ($LASTEXITCODE -ne 0) { throw "build of $n failed" }
}
docker build -t "library/gateway:$Tag" gateway
if ($LASTEXITCODE -ne 0) { throw "build of gateway failed" }
Write-Host "Images built with tag $Tag"
