"""Общие настройки и функции ML-части проекта (ЛР №5, основы MLOps)."""
import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TRAIN_FILE = DATA_DIR / "books.csv"        # редактируемый набор для обучения
TEST_FILE = DATA_DIR / "books_test.csv"    # эталонная (неизменяемая) тестовая выборка
REPORTS_DIR = ROOT / "reports" / "ml"
PARAMS_FILE = Path(__file__).resolve().parent / "params.json"

COLUMNS = ["id", "title", "genre", "summary"]

MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT = os.environ.get("MLFLOW_EXPERIMENT", "book-genre")
MODEL_NAME = os.environ.get("MODEL_NAME", "book-genre-classifier")
CHAMPION = "champion"      # алиас рабочей (лучшей) модели в Model Registry
CANDIDATE = "candidate"    # алиас модели, обученной в текущей сборке


def fix_console():
    """В Windows-консоли и логе Jenkins (cp1251/cp866) нет эмодзи, которые печатает
    mlflow, - заменяем неподдерживаемые символы, чтобы скрипт не падал."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass


def load_dataset(path=TRAIN_FILE):
    df = pd.read_csv(path, encoding="utf-8")
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}: нет колонок {sorted(missing)}")
    return df[COLUMNS]


def save_dataset(df, path=TRAIN_FILE):
    df[COLUMNS].to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def file_md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def model_text(df):
    """Текст, по которому модель определяет жанр: название + аннотация."""
    return pd.DataFrame({"text": (df["title"].fillna("") + ". " + df["summary"].fillna(""))})


def write_report(name, data):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_report(name):
    return json.loads((REPORTS_DIR / name).read_text(encoding="utf-8"))
