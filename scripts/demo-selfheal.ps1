# Демонстрация самовосстановления. Порт-форвард должен быть запущен в другом окне:
#   kubectl port-forward -n library svc/gateway 8081:80
# В третьем окне: kubectl get pods -n library -w
$B = "http://localhost:8081"

function Step($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan; Read-Host "Enter для запуска" | Out-Null }

Step "Сценарий 1: удаление одного пода books-service"
$p = kubectl get pods -n library -l app=books-service -o name | Select-Object -First 1
kubectl delete -n library $p
Start-Sleep 5
kubectl get pods -n library -l app=books-service

Step "Сценарий 2: падение контейнера (перезапуск kubelet, растёт RESTARTS)"
$pod = kubectl get pods -n library -l app=books-service -o jsonpath="{.items[0].metadata.name}"
minikube ssh -- "sudo crictl ps --label io.kubernetes.pod.name=$pod -q | xargs sudo crictl stop"
Start-Sleep 5
kubectl get pods -n library -l app=books-service

Step "Сценарий 3: удаление всех реплик books-service"
kubectl delete pod -n library -l app=books-service
Start-Sleep 15
kubectl get pods -n library -l app=books-service

Step "Сценарий 4: масштабирование до 5 и обратно до 3"
kubectl scale deployment/books-service -n library --replicas=5
Start-Sleep 8
kubectl get pods -n library -l app=books-service
kubectl scale deployment/books-service -n library --replicas=3

Step "Сценарий 5: падение БД, данные сохраняются (PVC)"
kubectl delete pod postgres-0 -n library
kubectl rollout status statefulset/postgres -n library --timeout=120s
Start-Sleep 10
Invoke-RestMethod "$B/api/books"

Write-Host "`nСобытия:" -ForegroundColor Cyan
kubectl get events -n library --sort-by=.lastTimestamp | Select-Object -Last 20

