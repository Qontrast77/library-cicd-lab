pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        PYTHON = 'C:\\Users\\Qontrast77\\AppData\\Local\\Programs\\Python\\Python312\\python.exe'
        APP_PORT = '5000'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                bat 'echo Branch: %BRANCH_NAME%'
            }
        }

        stage('Setup') {
            steps {
                bat '''
                    "%PYTHON%" -m venv venv
                    call venv\\Scripts\\activate.bat
                    python -m pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Test') {
            steps {
                bat '''
                    call venv\\Scripts\\activate.bat
                    if not exist reports mkdir reports
                    pytest tests/ --junitxml=reports/results.xml
                '''
            }
            post {
                always {
                    junit 'reports/results.xml'
                }
            }
        }

        stage('Deploy') {
            // CD stage: only on main. Stops old waitress process, starts new one via WMIC
            // process create - this makes the new process a child of the WMI provider host,
            // fully detached from Jenkins, so it survives after this step ends. Switched away
            // from schtasks because it needs "Log on as a batch job" rights the Jenkins
            // service account does not have here.
            // All system commands use full paths because the Jenkins service does not see PATH properly.
            when {
                branch 'main'
            }
            steps {
                bat '''
                    "C:\\Windows\\System32\\taskkill.exe" /F /IM waitress-serve.exe /T 2>nul
                   "C:\Windows\System32\wbem\WMIC.exe" process call create "\"%WORKSPACE%\venv\Scripts\waitress-serve.exe\" --host=0.0.0.0 --port=%APP_PORT% app:app", "%WORKSPACE%"
                    "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -Command "Start-Sleep -Seconds 5"
                    "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:%APP_PORT%/api/health' | Out-Null; Write-Host 'Health check OK' } catch { Write-Host 'Health check FAILED'; exit 1 }"
                '''
            }
        }
    }

    post {
        success {
            echo "Pipeline finished OK for branch ${env.BRANCH_NAME}"
        }
        failure {
            echo "Pipeline failed on branch ${env.BRANCH_NAME} - check test report"
        }
    }
}