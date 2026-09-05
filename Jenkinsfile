// Declarative Pipeline выбран вместо Scripted, так как:
//  - структура стадий читается сразу (проще для отчёта/поддержки);
//  - встроенный блок post{} удобен для отчётов о тестах и уведомлений;
//  - меньше кода, достаточно гибкости для наших нужд (build+test [+deploy]).
//
// Без Docker: приложение собирается и запускается прямо на агенте Jenkins
// через virtualenv + gunicorn.
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        VENV = "venv"
        APP_PORT = "5000"
        PID_FILE = "app.pid"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                sh 'echo "Branch: $BRANCH_NAME" || true'
            }
        }

        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv ${VENV}
                    . ${VENV}/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    . ${VENV}/bin/activate
                    mkdir -p reports
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
            // Останавливаем старый процесс (если есть) и запускаем новый
            // через gunicorn в фоне, PID сохраняем в файл для следующей остановки.
            when {
                branch 'main'
            }
            steps {
                sh '''
                    . ${VENV}/bin/activate
                    if [ -f ${PID_FILE} ] && kill -0 $(cat ${PID_FILE}) 2>/dev/null; then
                        kill $(cat ${PID_FILE})
                        sleep 2
                    fi
                    nohup gunicorn -b 0.0.0.0:${APP_PORT} app:app > gunicorn.log 2>&1 &
                    echo $! > ${PID_FILE}
                    sleep 2
                    curl -sf http://localhost:${APP_PORT}/api/health
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
