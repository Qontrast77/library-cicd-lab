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

