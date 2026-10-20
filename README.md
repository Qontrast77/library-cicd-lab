# Library — ЛР №5 «Основы MLOps» (Continuous Training)

Микросервисная система «Библиотека» из ЛР №3, запущенная **без Kubernetes**
(docker compose), дополнена процессом непрерывного обучения модели:
MLflow + Jenkins + Docker + GitHub.

**Задача модели:** определить жанр книги по названию и аннотации (10 жанров).
**Данные:** [azlan8289/Book_Genre](https://huggingface.co/datasets/azlan8289/Book_Genre)
(Hugging Face, копия Kaggle *Book Genre Prediction*), 4657 книг.
**Модель:** своя нейронная сеть — многослойный перцептрон (sklearn `MLPClassifier`)
поверх TF-IDF признаков текста.

## Что где (пункты методички)

| № | Пункт задания | Реализация |
|---|---|---|
| 1 | Модель нейронной сети | `ml/train.py` → `build_model()` (TF-IDF + MLP) |
| 2 | Набор данных | `ml/prepare_data.py` → `data/books.csv`, `data/books_test.csv` |
| 3 | Обучение с mlflow, гиперпараметры, выбор лучшей | `ml/train.py`, сетка в `ml/params.json` |
| 4 | Проверка качества, exception | `ml/evaluate.py` → `ModelQualityError` |
| 5 | Сервер mlflow | сервис `mlflow` в `docker-compose.yml`, http://localhost:5000 |
| 6 | Декларативный конвейер | `Jenkinsfile.ml` |
| 7 | Сохранение моделей и гиперпараметров | MLflow Model Registry (`book-genre-classifier`), артефакты сборки `reports/ml/*.json` |
| 8 | Консольное приложение для изменения данных | `ml/data_tool.py` |
| 9 | Триггер на изменение данных | `pollSCM` + `when { changeset 'data/**' }` в `Jenkinsfile.ml` |
| + | Использование модели в системе | микросервис `services/genre` (`/api/genre/*`), блок «Определить жанр» в UI |

```
docker-compose.yml        postgres + 4 сервиса + gateway + mlflow + genre-service
Jenkinsfile.ml            конвейер CT (старый Jenkinsfile из ЛР №3/4 не изменён)
compose/postgres-init.sql создание БД сервисов
gateway/compose.conf      маршруты nginx для docker compose (+ /api/genre)
data/books.csv            обучающий набор (меняется data_tool.py, лежит в git)
data/books_test.csv       эталонная тестовая выборка (не меняется)
ml/common.py              общие настройки
ml/prepare_data.py        загрузка датасета с Hugging Face и разбиение
ml/params.json            сетка гиперпараметров
ml/train.py               обучение + MLflow + регистрация лучшей модели
ml/evaluate.py            quality gate: сравнение с текущей моделью
ml/data_tool.py           консольное приложение для изменения набора данных
services/genre/           микросервис предсказания жанра
scripts/ml_setup.bat      venv для ML-части (используется в Jenkins)
```

## Запуск

```bat
:: 0. Kubernetes для этой работы не нужен - освобождаем память
minikube stop

:: 1. Система + сервер MLflow
docker compose up -d --build
::    приложение http://localhost:8081, MLflow UI http://localhost:5000

:: 2. ML-окружение и набор данных (один раз)
set PYTHON=C:/Users/Qontrast77/AppData/Local/Programs/Python/Python312/python.exe
scripts\ml_setup.bat
venv-ml\Scripts\python.exe ml\prepare_data.py
git add . && git commit -m "ЛР5: MLOps" && git push

:: 3. Ручная проверка без Jenkins (необязательно)
venv-ml\Scripts\python.exe ml\train.py
venv-ml\Scripts\python.exe ml\evaluate.py
```

**Jenkins:** New Item → *Pipeline* → «library-ml» → Pipeline script from SCM →
Git `https://github.com/Qontrast77/library-cicd-lab.git`, ветка `*/main`,
Script Path `Jenkinsfile.ml`. Первый раз запустить вручную (*Build Now*) —
после этого Jenkins регистрирует триггер `pollSCM` и параметры сборки.

## Сценарий демонстрации (для отчёта)

```bat
:: успешное переобучение: добавили книгу -> push -> Jenkins сам запускает сборку
venv-ml\Scripts\python.exe ml\data_tool.py add --title "Dune" --genre science ^
    --summary "On the desert planet Arrakis young Paul Atreides ..." --push

:: ухудшение данных -> новая модель хуже -> ModelQualityError, сборка красная
venv-ml\Scripts\python.exe ml\data_tool.py noise --fraction 0.5 --push

:: вернуть данные
git revert --no-edit HEAD && git push
```

Остальные команды: `python ml\data_tool.py -h` (stats, list, show, add, edit,
delete, import, remove-genre, sample, noise, validate).

---

## Предыдущая версия README

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

приветулики