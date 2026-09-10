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
            // CD stage: only on main. Stops old waitress process, starts new one via schtasks
            // (schtasks breaks the process fully away from Jenkins, so it survives after this step ends).
            // All system commands use full paths because the Jenkins service does not see PATH properly.
            // ST 23:59 is just "some time later today" - the actual value does not matter since
            // we run the task immediately with /Run right after creating it.
            when {
                branch 'main'
            }
            steps {
                bat '''
                    "C:\\Windows\\System32\\taskkill.exe" /F /IM waitress-serve.exe /T 2>nul
                    "C:\\Windows\\System32\\schtasks.exe" /Create /TN LibraryAppDeploy /TR "\\"%WORKSPACE%\\venv\\Scripts\\waitress-serve.exe\\" --host=0.0.0.0 --port=%APP_PORT% app:app" /SC ONCE /ST 23:59 /F
                    "C:\\Windows\\System32\\schtasks.exe" /Run /TN LibraryAppDeploy
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