// Declarative Pipeline выбран вместо Scripted, так как:
//  - структура стадий читается сразу (проще для отчёта/поддержки);
//  - встроенный блок post{} удобен для отчётов о тестах и уведомлений;
//  - меньше кода, достаточно гибкости для наших нужд (build+test [+deploy]).
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        VENV = "venv"
        IMAGE_NAME = "library-app"
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

        stage('Build image') {
            when {
                // сборка образа — только для main/dev, чтобы feature-ветки
                // не гоняли лишний Docker build
                anyOf { branch 'main'; branch 'dev' }
            }
            steps {
                sh 'docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .'
            }
        }

        stage('Deploy') {
            // CD-стадия: выполняется только при пуше в main (production)
            when {
                branch 'main'
            }
            steps {
                sh '''
                    docker stop ${IMAGE_NAME} || true
                    docker rm ${IMAGE_NAME} || true
                    docker run -d --name ${IMAGE_NAME} -p 5000:5000 ${IMAGE_NAME}:${BUILD_NUMBER}
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
