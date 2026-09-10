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
            //
            // Все системные команды вызываются по полному пути
            // (C:\Windows\System32\...), а не по голому имени — служба
            // Jenkins на этой машине не видит даже базовые команды Windows
            // через PATH (та же история, что была с python.exe).
            //
            // /ST 23:59 — заведомо время в будущем