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
├── Dockerfile
├── Jenkinsfile          # pipeline CI/CD
├── static/              # фронтенд (index.html, script.js, style.css)
└── tests/
    └── test_api.py      # автотесты (unittest, запускаются через pytest)
```

## 1. Локальный запуск

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                 # http://localhost:5000
```

Тесты:

```bash
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
   - **Docker Pipeline** (если деплой через Docker)

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
публикации отчётов о тестах) с четырьмя стадиями:

| Стадия       | Что делает                                                  | Когда выполняется |
|--------------|--------------------------------------------------------------|--------------------|
| Checkout     | Забирает код текущей ветки                                    | всегда |
| Setup        | Создаёт venv, ставит зависимости из `requirements.txt`        | всегда |
| Test         | Прогоняет `pytest`, публикует JUnit-отчёт (`junit` step)       | всегда — это стадия **CI** |
| Build image  | `docker build` образа приложения                              | только `main`, `dev` |
| Deploy       | Останавливает старый контейнер и поднимает новый               | только `main` — это стадия **CD** |

Таким образом push в `feature/*` запускает только CI (сборка+тесты),
а push в `main` дополнительно выполняет CD (сборка образа и деплой).

---

## 6. Демонстрация работы

1. Сделать изменение в ветке `feature/...`, закоммитить и запушить —
   в Jenkins автоматически появляется новый билд этой ветки, выполняются
   стадии Checkout/Setup/Test.
2. Смёржить `feature/...` → `dev` — Jenkins прогоняет pipeline для `dev`
   (плюс сборку Docker-образа).
3. Смёржить `dev` → `main` — выполняются все стадии, включая деплой;
   приложение обновляется на `http://<host>:5000`.
4. В интерфейсе Jenkins открыть билд → "Test Result" — видно количество
   пройденных/упавших тестов (JUnit-отчёт из стадии Test).

---

## 7. Возможные доработки

- Добавить стадию `Lint` (flake8/ruff) перед тестами.
- Добавить staging-окружение: `dev` деплоится на staging-порт,
  `main` — на production.
- Push собранного образа в Docker Hub / приватный registry вместо
  локального `docker run`.
