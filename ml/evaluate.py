"""Шаг 4: проверка качества новой модели (quality gate).

Новая модель (алиас "candidate") и текущая рабочая (алиас "champion") проверяются
на одной и той же эталонной тестовой выборке data/books_test.csv. Если новая модель
хуже - выбрасывается исключение ModelQualityError, скрипт завершается с ошибкой,
и этап конвейера Jenkins падает. Иначе новая модель становится "champion".

Запуск: python ml/evaluate.py [--min-delta 0.0]
"""
import argparse
import time

import mlflow
import mlflow.sklearn
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from sklearn.metrics import accuracy_score, f1_score

from common import (CANDIDATE, CHAMPION, MLFLOW_URI, MODEL_NAME, TEST_FILE, fix_console,
                    load_dataset, model_text, read_report, write_report)


class ModelQualityError(Exception):
    """Новая модель работает хуже предыдущей."""


def load(uri, attempts=3):
    """Загрузка модели из MLflow с повтором: большой model.pkl иногда обрывается."""
    for i in range(1, attempts + 1):
        try:
            return mlflow.sklearn.load_model(uri)
        except MlflowException as e:
            if i == attempts:
                raise
            print(f"Загрузка {uri} не удалась (попытка {i}): {str(e)[:120]}... повтор через 5 с")
            time.sleep(5)


def evaluate(uri, X, y):
    pred = load(uri).predict(X)
    # float(): sklearn возвращает numpy-типы, а json не умеет их сохранять
    return {"f1_macro": float(f1_score(y, pred, average="macro")), "accuracy": float(accuracy_score(y, pred))}


def main():
    fix_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-delta", type=float, default=0.0,
                    help="на сколько новая модель может быть хуже без ошибки (по умолчанию 0)")
    a = ap.parse_args()

    mlflow.set_tracking_uri(MLFLOW_URI)
    client = MlflowClient()
    cand = read_report("candidate.json")
    version = str(cand["version"])

    test = load_dataset(TEST_FILE)
    X, y = model_text(test), test["genre"]

    new = evaluate(f"models:/{MODEL_NAME}/{version}", X, y)
    print(f"Новая модель    v{version}: f1_macro={new['f1_macro']:.4f} accuracy={new['accuracy']:.4f}")

    try:
        champ = client.get_model_version_by_alias(MODEL_NAME, CHAMPION)
    except MlflowException:
        champ = None

    old = None
    if champ is not None and str(champ.version) != version:
        old = evaluate(f"models:/{MODEL_NAME}/{champ.version}", X, y)
        print(f"Текущая модель  v{champ.version}: f1_macro={old['f1_macro']:.4f} accuracy={old['accuracy']:.4f}")
    else:
        print("Рабочей модели ещё нет - новая модель будет назначена первой.")

    passed = bool(old is None or new["f1_macro"] >= old["f1_macro"] - a.min_delta)
    result = {"candidate_version": version, "candidate": new,
              "champion_version": str(champ.version) if champ else None, "champion": old,
              "min_delta": a.min_delta, "passed": passed}
    write_report("quality_gate.json", result)

    with mlflow.start_run(run_id=cand["run_id"]):
        mlflow.log_metrics({"gate_candidate_f1": new["f1_macro"],
                            **({"gate_champion_f1": old["f1_macro"]} if old else {})})
        mlflow.set_tag("quality_gate", "passed" if passed else "failed")
    client.set_model_version_tag(MODEL_NAME, version, "quality_gate", "passed" if passed else "failed")

    if not passed:
        client.delete_registered_model_alias(MODEL_NAME, CANDIDATE)
        raise ModelQualityError(
            f"Новая модель v{version} хуже текущей v{champ.version}: "
            f"f1_macro {new['f1_macro']:.4f} < {old['f1_macro']:.4f}. "
            f"Модель не выпущена, в работе остаётся v{champ.version}.")

    client.set_registered_model_alias(MODEL_NAME, CHAMPION, version)
    print(f"\nПроверка пройдена: v{version} назначена '{CHAMPION}'.")


if __name__ == "__main__":
    main()
