# Library Management System — CI/CD (Лабораторная работа №1)

Небольшая система учёта библиотеки: Авторы / Книги / Читатели / Выдачи.
Двухзвенная архитектура: **клиент** (статичный SPA на HTML/JS, папка `static/`)
↔ **сервер + БД** (Flask REST API поверх SQLite, `app.py` + `db.py`).

20 CRUD-операций = 4 сущности × (list, get, create, update, delete).

```
library-app/
├── app.py              # Flask-приложение, все роуты
├── db.py                # доступ к SQLite (без ORM)
├── requirements.txt
├── Jenkinsfile          # pipeline CI/CD (без Docker)
├── static/              # фронтенд (index.html, script.js, style.css)
└── tests/
    └── test_api.py      # автотесты (unittest, запускаются через pytest)
```

> Вариант без Docker: сборка и запуск идут напрямую на агенте Jenkins —
> virtualenv + `waitress` (WSGI-сервер, работающий на Windows; `gunicorn`
> для Windows не подходит, это Unix-only библиотека). Ничего
> контейнеризировать не нужно.

## 1. Локальный запуск

Windows / PowerShell:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py                 # http://localhost:5000
```

Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Тесты:

```
pytest tests/ -v
```

---

## 2. Репозиторий и ветки на GitHub

1. Создать репозиторий на GitHub, например `library-cicd-lab`.
2. Инициализировать и запушить код:

   ```bash
   git init
   git add .
   git commit -m "Initial commit: library management app"
   git branch -M main
   git remote add origin https://github.com/<user>/library-cicd-lab.git
   git push -u origin main
   ```

3. Создать ветку разработки `dev` от `main`:

   ```bash
   git checkout -b dev
   git push -u origin dev
   ```

4. Для каждой новой функции/бага — отдельная ветка от `dev`, например:

   ```bash
   git checkout -b feature/loans-endpoint dev
   # ... правки, коммиты ...
   git push -u origin feature/loans-endpoint
   # затем Pull Request feature/... -> dev, после проверки dev -> main
   ```

   Итоговая схема веток: `main` (продакшн, стабильный код) ← `dev` (интеграция)
   ← `feature/*` (разработка отдельных фич).

---

## 3. Установка Jenkins

### Вариант А — Docker (проще всего для лабораторной)

```bash
docker volume create jenkins_home
docker run -d --name jenkins \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins/jenkins:lts
```

Открыть `http://localhost:8080`, получить начальный пароль:

```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### Вариант Б — пакет для Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install -y openjdk-17-jre
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key | sudo tee \
  /usr/share/keyrings/jenkins-keyring.asc > /dev/null
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
  https://pkg.jenkins.io/debian-stable binary/" | sudo tee \
  /etc/apt/sources.list.d/jenkins.list > /dev/null
sudo apt update
sudo apt install -y jenkins
sudo systemctl enable --now jenkins
```

Пароль: `sudo cat /var/lib/jenkins/secrets/initialAdminPassword`.

### Вариант В — Windows

Скачать `.msi` с [jenkins.io](https://www.jenkins.io/download/), установить,
Jenkins запустится как служба на `http://localhost:8080`.

### Первый запуск (одинаково для всех вариантов)

1. Ввести начальный пароль.
2. "Install suggested plugins".
3. Создать первого администратора.
4. Дополнительно поставить плагины (Manage Jenkins → Plugins):
   - **Git plugin** (обычно уже есть)
   - **GitHub Integration / GitHub Branch Source**
   - **Pipeline**

   Docker не используется — все стадии выполняются в обычном virtualenv,
   поэтому на агенте Jenkins достаточно установленных `python3` и `pip`
   (Manage Jenkins → Tools, либо просто убедиться, что `python3` есть в PATH
   на машине, где работает Jenkins agent).

---

## 4. Настройка Job в Jenkins

Рекомендуется **Multibranch Pipeline** — он сам находит `Jenkinsfile`
в каждой ветке и создаёт под-задачу на каждую ветку/PR.

1. Jenkins → New Item → имя `library-cicd-lab` → тип **Multibranch Pipeline**.
2. Branch Sources → **GitHub** (или Git) → указать URL репозитория и
   добавить credentials (GitHub Personal Access Token: Settings →
   Developer settings → Personal access tokens, права `repo`).
3. Build Configuration → Mode: `by Jenkinsfile`, Script Path: `Jenkinsfile`.
4. Scan Multibranch Pipeline Triggers → включить
   **"Scan by webhook"** (или periodic scan раз в минуту для лабы без
   публичного адреса).
5. Save — Jenkins сразу просканирует репозиторий и запустит pipeline
   для `main` и `dev`.

### Webhook на GitHub (получение push-события)

Репозиторий на GitHub → Settings → Webhooks → Add webhook:

- Payload URL: `http://<адрес-jenkins>:8080/github-webhook/`
- Content type: `application/json`
- Events: `Just the push event`

Если Jenkins локальный и недоступен снаружи — пробросить туннель
(например `ngrok http 8080`) и указать сгенерированный URL в webhook,
либо использовать периодический опрос (`Poll SCM`) вместо вебхука.

---

## 5. Как устроен pipeline (`Jenkinsfile`)

Declarative Pipeline (выбран за читаемость и удобный `post{}`-блок для
публикации отчётов о тестах) с тремя стадиями, без Docker.
Все шаги — через `bat` (Windows batch), так как Jenkins-агент на Windows.

| Стадия    | Что делает                                                             | Когда выполняется |
|-----------|--------------------------------------------------------------------------|--------------------|
| Checkout  | Забирает код текущей ветки                                               | всегда |
| Setup     | Создаёт venv (через полный путь к `python.exe`), ставит зависимости      | всегда |
| Test      | Прогоняет `pytest`, публикует JUnit-отчёт (`junit` step)                  | всегда — это стадия **CI** |
| Deploy    | Останавливает старый `waitress-serve.exe`, запускает новый через `schtasks`, проверяет `/api/health` | только `main` — это стадия **CD** |

Таким образом push в `feature/*` и `dev` запускает только CI
(установка зависимостей + тесты), а push в `main` дополнительно
выполняет CD — перезапуск приложения через `waitress` прямо на
машине, где работает Jenkins.

**Важный нюанс про Windows**: путь к `python.exe` захардкожен в
`environment { PYTHON = '...' }` в начале `Jenkinsfile`, потому что
служба Jenkins на Windows не всегда наследует системный PATH. Если
запускаешь проект на другой машине — поменяй этот путь под своего
пользователя (узнать его: `where.exe python` в обычном PowerShell).

Деплой сделан через `schtasks` (планировщик задач Windows), а не
через простой `start /B`, — потому что Jenkins по умолчанию убивает
всё дерево процессов шага сразу после его завершения, и обычный
фоновый процесс тоже "умер" бы вместе с шагом. Задача в планировщике
живёт независимо от Jenkins.

---

## 6. Демонстрация работы

1. Сделать изменение в ветке `feature/...`, закоммитить и запушить —
   в Jenkins автоматически появляется новый билд этой ветки, выполняются
   стадии Checkout/Setup/Test.
2. Смёржить `feature/...` → `dev` — Jenkins прогоняет pipeline для `dev`
   (Checkout/Setup/Test).
3. Смёржить `dev` → `main` — выполняется стадия Deploy: старый процесс
   `waitress-serve.exe` останавливается, новый запускается через
   `schtasks`; приложение обновляется на `http://localhost:5000`.
4. В интерфейсе Jenkins открыть билд → "Test Result" — видно количество
   пройденных/упавших тестов (JUnit-отчёт из стадии Test).
5. Проверить руками, что задача в планировщике реально создана и
   выполнена:
   ```powershell
   schtasks /Query /TN LibraryAppDeploy
   ```

---

## 7. Как альтернативно оформить Deploy (только для Linux-хостов)

Если Jenkins/приложение крутятся не на Windows, а на Linux-сервере,
и там уже настроен systemd-юнит для приложения (создаётся один раз
вручную, не через Jenkins), стадию `Deploy` можно упростить до:

```groovy
stage('Deploy') {
    when { branch 'main' }
    steps {
        sh 'sudo systemctl restart library-app'
    }
}
```

Пример unit-файла `/etc/systemd/system/library-app.service`:

```ini
[Unit]
Description=Library Management App
After=network.target

[Service]
WorkingDirectory=/opt/library-app
ExecStart=/opt/library-app/venv/bin/gunicorn -b 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## 8. Возможные доработки

- Добавить стадию `Lint` (flake8/ruff) перед тестами.
- Добавить staging-окружение: `dev` деплоится на отдельный порт (staging),
  `main` — на production-порт.
- Настроить деплой на удалённый сервер через SSH-плагин Jenkins
  (Publish Over SSH), если Jenkins и приложение работают на разных машинах.
