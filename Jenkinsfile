// Declarative Pipeline выбран вместо Scripted, так как:
//  - структура стадий читается сразу (проще для отчёта/поддержки);
//  - встроенный блок post{} удобен для отчётов о тестах и уведомлений;
//  - меньше кода, достаточно гибкости для наших нужд (build+test [+deploy]).
//
// Без Docker, для Windows-агента: сборка и запуск идут прямо на машине,
// где крутится Jenkins, через virtualenv + waitress (WSGI-сервер для
// Windows — gunicorn на Windows не запускается, это Unix-only).
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        // Полный путь к python.exe — не полагаемся на системный PATH,
        // так как служба Jenkins на Windows часто его не наследует.
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
            // CD-стадия: выполняется только при пуше в main (production).
            // Старый процесс waitress останавливается по имени образа,
            // новый запускается в фоне через schtasks (чтобы Jenkins не
            // прибил процесс сразу после завершения стадии — при обычном
            // "start /B" Jenkins по умолчанию убивает всё дерево процессов
            // шага, как только тот завершится).
            when {
                branch 'main'
            }
            steps {
                bat '''
                    taskkill /F /IM waitress-serve.exe /T 2>nul
                    schtasks /Create /TN LibraryAppDeploy /TR "\\"%WORKSPACE%\\venv\\Scripts\\waitress-serve.exe\\" --host=0.0.0.0 --port=%APP_PORT% app:app" /SC ONCE /ST 00:00 /F
                    schtasks /Run /TN LibraryAppDeploy
                    timeout /t 3 /nobreak
                    curl -sf http://localhost:%APP_PORT%/api/health
                '''
            }
        }
    }

    post {
        success {
            echo "Pipeline завершён успешно для ветки ${env.BRANCH_NAME}"
        }
        failure {
            echo "Pipeline упал на ветке ${env.BRANCH_NAME} — проверьте отчёт о тестах"
        }
    }
}
