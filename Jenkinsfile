// Declarative Pipeline: сборка образов микросервисов, развёртывание в
// одноузловой Kubernetes (minikube), сквозной smoke-тест через gateway.
// Требования к Jenkins-агенту: Windows, установлены minikube, kubectl, Docker,
// кластер запущен (minikube start), у пользователя службы Jenkins доступен kubeconfig.
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        PYTHON = 'C:/Users/Qontrast77/AppData/Local/Programs/Python/Python312/python.exe'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        // при необходимости укажите путь к kubeconfig пользователя:
        // KUBECONFIG = 'C:/Users/Qontrast77/.kube/config'
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
                bat 'scripts/setup.bat'
            }
        }

        stage('Build images') {
            when { branch 'main' }
            steps {
                bat 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1 -Tag %IMAGE_TAG%'
            }
        }

        stage('Deploy to Kubernetes') {
            when { branch 'main' }
            steps {
                bat 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy.ps1 -Tag %IMAGE_TAG%'
            }
        }

        stage('Smoke test') {
            when { branch 'main' }
            steps {
                bat 'scripts/test.bat'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/results.xml'
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline finished OK for branch ${env.BRANCH_NAME}"
        }
        failure {
            echo "Pipeline failed on branch ${env.BRANCH_NAME} - check logs and smoke-test report"
            bat(returnStatus: true, script: 'kubectl get pods -n library')
        }
    }
}
