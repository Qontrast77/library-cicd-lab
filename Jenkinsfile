// Declarative Pipeline: simple stage structure, post{} block for test reports.
// Setup/Test run natively via venv (no Docker needed for CI).
// Build & Push (main only) builds a versioned Docker image and pushes it to
// Docker Hub - this is the artifact-versioning requirement.
// Deploy (main only) runs the app as a container behind nginx via
// docker-compose - see docker-compose.yml.
// All Windows-specific commands live in scripts/*.bat so this file has no
// backslash escaping to worry about (forward slashes work fine on Windows).
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
        // TODO: replace with your own Docker Hub username/repo
        IMAGE_NAME = 'YOUR_DOCKERHUB_USERNAME/library-cicd-lab'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        // Required for the Dockerfile's "RUN --mount=type=cache" to work -
        // that syntax needs BuildKit, not the older classic builder.
        DOCKER_BUILDKIT = '1'
        COMPOSE_DOCKER_CLI_BUILD = '1'
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

        stage('Build & Push image') {
            // Builds a versioned Docker image (tagged with the Jenkins build
            // number) and pushes it to Docker Hub for versioning/artifact
            // storage purposes. Only on main.
            when {
                branch 'main'
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKERHUB_USER',
                    passwordVariable: 'DOCKERHUB_PASS'
                )]) {
                    bat 'scripts/build_push.bat'
                }
            }
        }

        stage('Deploy') {
            // CD stage: only on main. (Re)starts the app plus nginx via
            // docker-compose, reusing the image built in the previous stage.
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

