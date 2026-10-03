param([string]$Tag = "v1")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$images = @()
foreach ($n in "authors", "books", "members", "loans") {
    docker build -f services/Dockerfile --build-arg SERVICE=$n -t "library/$n-service:$Tag" services
    if ($LASTEXITCODE -ne 0) { throw "build of $n failed" }
    $images += "library/$n-service:$Tag"
}
docker build -t "library/gateway:$Tag" gateway
if ($LASTEXITCODE -ne 0) { throw "build of gateway failed" }
$images += "library/gateway:$Tag"

foreach ($i in $images) {
    minikube image load $i
    if ($LASTEXITCODE -ne 0) { throw "image load of $i failed" }
}
Write-Host "Images built and loaded into minikube with tag $Tag"