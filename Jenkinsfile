pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        PYTHON = 'C:/Users/Qontrast77/AppData/Local/Programs/Python/Python312/python.exe'
        DOCKER = 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
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
                bat 'scripts/setup.bat'
            }
        }

        stage('Test') {
            steps {
                bat 'scripts/test.bat'
            }
            post {
                always {
                    junit 'reports/results.xml'
                }
            }
        }

        stage('Deploy') {
            // CD stage: only on main. Builds the app image and (re)starts
            // it plus nginx via docker-compose - see scripts/deploy.bat.
            when {
                branch 'main'
            }
            steps {
                bat 'scripts/deploy.bat'
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

