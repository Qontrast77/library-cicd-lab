"""Шаг 2: загрузка набора данных с Hugging Face и разбиение на обучающую и эталонную
тестовую части.

Набор: azlan8289/Book_Genre (копия Kaggle-датасета athu1105/book-genre-prediction),
4657 книг, поля: title, genre (10 жанров), summary. Лицензия Apache-2.0.

Запуск (один раз):  python ml/prepare_data.py
Если интернета нет:  python ml/prepare_data.py --source путь/к/data.csv
"""
import argparse

import pandas as pd
from sklearn.model_selection import train_test_split

from common import COLUMNS, DATA_DIR, TEST_FILE, TRAIN_FILE, file_md5, save_dataset

HF_URL = "https://huggingface.co/datasets/azlan8289/Book_Genre/resolve/main/data.csv"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", default=HF_URL, help="URL или путь к исходному CSV")
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--force", action="store_true", help="перезаписать существующие файлы")
    a = p.parse_args()

    if TRAIN_FILE.exists() and not a.force:
        raise SystemExit(f"{TRAIN_FILE} уже существует. Используйте --force для перезаписи.")

    print(f"Загрузка {a.source} ...")
    raw = pd.read_csv(a.source)
    print(f"Получено строк: {len(raw)}, колонки: {list(raw.columns)}")

    df = raw.rename(columns={"index": "id"})
    if "id" not in df.columns:
        df.insert(0, "id", range(len(df)))
    df = df[COLUMNS].copy()
    df["title"] = df["title"].astype(str).str.strip()
    df["genre"] = df["genre"].astype(str).str.strip().str.lower()
    df["summary"] = df["summary"].astype(str).str.strip()
    df = df[(df["summary"].str.len() > 20) & (df["title"] != "")]
    df = df.drop_duplicates(subset=["title", "summary"])
    df["id"] = range(1, len(df) + 1)

    train, test = train_test_split(df, test_size=a.test_size, stratify=df["genre"], random_state=42)
    DATA_DIR.mkdir(exist_ok=True)
    save_dataset(train.sort_values("id"), TRAIN_FILE)
    save_dataset(test.sort_values("id"), TEST_FILE)

    print(f"\nОбучающий набор:  {TRAIN_FILE.relative_to(DATA_DIR.parent)}  ({len(train)} строк)")
    print(f"Эталонный тест:   {TEST_FILE.relative_to(DATA_DIR.parent)}  ({len(test)} строк)")
    print(f"md5 обучающего набора: {file_md5(TRAIN_FILE)}")
    print("\nРаспределение жанров:")
    print(df["genre"].value_counts().to_string())


if __name__ == "__main__":
    main()
