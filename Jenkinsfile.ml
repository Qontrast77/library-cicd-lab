// ЛР №5. Декларативный конвейер Continuous Training (CT):
// изменение набора данных в GitHub -> переобучение -> проверка качества -> выпуск модели.
//
// Job в Jenkins: New Item -> Pipeline -> "Pipeline script from SCM" (Git, ветка main),
// Script Path: Jenkinsfile.ml. Перед запуском должен работать сервер MLflow:
//   docker compose up -d
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    // Шаг 9. Триггер: Jenkins каждые 2 минуты опрашивает GitHub. Новая сборка
    // появляется только при новом коммите, а обучение запускается только если
    // в коммите изменён набор данных (см. when ниже).
    triggers {
        pollSCM('H/2 * * * *')
    }

    parameters {
        booleanParam(name: 'FORCE_TRAIN', defaultValue: false,
                     description: 'Обучить модель, даже если набор данных не менялся')
        string(name: 'MIN_DELTA', defaultValue: '0.01',
               description: 'Допустимое ухудшение f1_macro новой модели относительно текущей (0 - строго не хуже)')
    }

    environment {
        PYTHON = 'C:/Users/Qontrast77/AppData/Local/Programs/Python/Python312/python.exe'
        PY = 'venv-ml\\Scripts\\python.exe'
        MLFLOW_TRACKING_URI = 'http://localhost:5000'
        MLFLOW_EXPERIMENT = 'book-genre'
        MODEL_NAME = 'book-genre-classifier'
        GATEWAY_URL = 'http://localhost:8081'
        PYTHONUNBUFFERED = '1'       // вывод Python сразу попадает в лог сборки
        GIT_PYTHON_REFRESH = 'quiet' // mlflow не ищет git в PATH службы Jenkins
        PYTHONIOENCODING = 'utf-8'   // русский текст в логе Jenkins (лог читается как UTF-8)
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.TRIGGER = currentBuild.getBuildCauses()*.shortDescription.join('; ')
                }
                echo "Причина запуска: ${env.TRIGGER}"
            }
        }

        stage('Dataset changed') {
            when { changeset 'data/**' }
            steps {
                echo 'В коммите изменён набор данных (data/**) - запускается переобучение модели'
            }
        }

        stage('Continuous Training') {
            when {
                anyOf {
                    changeset 'data/**'
                    changeset 'ml/params.json'
                    expression { params.FORCE_TRAIN }
                    triggeredBy 'UserIdCause'
                }
            }
            stages {

                stage('Setup ML env') {
                    steps {
                        bat 'scripts\\ml_setup.bat'
                    }
                }

                stage('Check MLflow') {
                    steps {
                        bat '%PY% -c "import urllib.request, os; u = os.environ[\'MLFLOW_TRACKING_URI\']; urllib.request.urlopen(u + \'/health\', timeout=10); print(\'MLflow OK:\', u)"'
                    }
                }

                stage('Validate data') {
                    steps {
                        bat '%PY% ml\\data_tool.py validate'
                        bat '%PY% ml\\data_tool.py stats'
                    }
                }

                stage('Train') {
                    steps {
                        bat '%PY% ml\\train.py --build %BUILD_NUMBER%'
                    }
                }

                // Шаг 4. evaluate.py выбрасывает ModelQualityError, если новая
                // модель хуже текущей - этап и вся сборка завершаются с ошибкой
                stage('Quality gate') {
                    steps {
                        bat "%PY% ml\\evaluate.py --min-delta ${params.MIN_DELTA}"
                    }
                }

                stage('Deploy model') {
                    steps {
                        catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                            bat '%PY% -c "import urllib.request, os; r = urllib.request.urlopen(urllib.request.Request(os.environ[\'GATEWAY_URL\'] + \'/api/genre/reload\', method=\'POST\'), timeout=120); print(r.read().decode())"'
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/ml/*.json', allowEmptyArchive: true
        }
        success {
            echo "Сборка ${env.BUILD_NUMBER} завершена. MLflow: ${env.MLFLOW_TRACKING_URI}"
        }
        failure {
            echo 'Конвейер завершился с ошибкой. Если упал этап Quality gate - новая модель хуже текущей и не выпущена.'
        }
    }
}
