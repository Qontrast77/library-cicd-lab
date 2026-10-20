"""Шаги 3 и 7: обучение нейронной сети с фиксацией гиперпараметров в MLflow,
выбор лучшей модели и её сохранение в MLflow Model Registry.

Модель - многослойный перцептрон (sklearn MLPClassifier) поверх TF-IDF признаков
текста "название + аннотация". Задача - определить жанр книги (10 классов).

Каждая комбинация гиперпараметров из ml/params.json - отдельный вложенный (nested)
run. Лучший по macro-F1 на валидации регистрируется как новая версия модели
и получает алиас "candidate". Решение о выпуске принимает ml/evaluate.py.

Запуск: python ml/train.py [--build 12]
"""
import argparse
import itertools
import json
import os
import time

import mlflow
import mlflow.sklearn
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

from common import (CANDIDATE, EXPERIMENT, MLFLOW_URI, MODEL_NAME, PARAMS_FILE, TEST_FILE,
                    TRAIN_FILE, file_md5, fix_console, load_dataset, model_text, write_report)


def build_model(p):
    tfidf = TfidfVectorizer(max_features=p["max_features"], ngram_range=tuple(p["ngram_range"]),
                            min_df=p["min_df"], sublinear_tf=True, stop_words="english")
    mlp = MLPClassifier(hidden_layer_sizes=tuple(p["hidden_layer_sizes"]), alpha=p["alpha"],
                        learning_rate_init=p["learning_rate_init"], batch_size=p["batch_size"],
                        max_iter=p["max_iter"], early_stopping=True, n_iter_no_change=5,
                        random_state=p["random_state"])
    # ColumnTransformer берёт колонку "text" из DataFrame - модель принимает
    # таблицу с одной колонкой text, это же записывается в сигнатуру модели
    return Pipeline([
        ("features", ColumnTransformer([("tfidf", tfidf, "text")])),
        ("mlp", mlp),
    ])


def param_grid(cfg):
    keys = list(cfg["grid"])
    for values in itertools.product(*(cfg["grid"][k] for k in keys)):
        yield {**cfg["fixed"], **dict(zip(keys, values))}


def flat(p):
    """Значения-списки -> строки, чтобы они нормально отображались в MLflow UI."""
    return {k: (str(tuple(v)) if isinstance(v, list) else v) for k, v in p.items()}


def scores(model, X, y, prefix):
    pred = model.predict(X)
    return {f"{prefix}_accuracy": accuracy_score(y, pred),
            f"{prefix}_f1_macro": f1_score(y, pred, average="macro")}, pred


def main():
    fix_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default=os.environ.get("BUILD_NUMBER", "local"))
    ap.add_argument("--val-size", type=float, default=0.15)
    a = ap.parse_args()

    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT)
    client = MlflowClient()

    df = load_dataset(TRAIN_FILE)
    test = load_dataset(TEST_FILE)
    tr, val = train_test_split(df, test_size=a.val_size, stratify=df["genre"], random_state=42)
    X_tr, X_val, X_test = model_text(tr), model_text(val), model_text(test)
    data_md5 = file_md5(TRAIN_FILE)
    cfg = json.loads(PARAMS_FILE.read_text(encoding="utf-8"))
    combos = list(param_grid(cfg))

    print(f"MLflow: {MLFLOW_URI}, эксперимент '{EXPERIMENT}'")
    print(f"Данные: {len(df)} строк (train {len(tr)}, val {len(val)}), эталонный тест {len(test)}, md5 {data_md5}")
    print(f"Комбинаций гиперпараметров: {len(combos)}\n")

    with mlflow.start_run(run_name=f"build-{a.build}") as parent:
        mlflow.set_tags({
            "jenkins_build": a.build,
            "git_commit": os.environ.get("GIT_COMMIT", "local"),
            "trigger": os.environ.get("TRIGGER", "manual"),
            "data_md5": data_md5,
        })
        mlflow.log_params({"data_rows": len(df), "data_md5": data_md5, "train_rows": len(tr),
                           "val_rows": len(val), "test_rows": len(test),
                           "n_genres": df["genre"].nunique(), "n_trials": len(combos)})
        mlflow.log_artifact(str(PARAMS_FILE))
        mlflow.log_dict(df["genre"].value_counts().to_dict(), "data/genre_distribution.json")

        best = None
        for i, p in enumerate(combos, 1):
            with mlflow.start_run(run_name=f"build-{a.build}-trial-{i}", nested=True) as run:
                mlflow.log_params(flat(p))
                t0 = time.time()
                model = build_model(p).fit(X_tr, tr["genre"])
                m, _ = scores(model, X_val, val["genre"], "val")
                m["train_time_sec"] = time.time() - t0
                m["epochs"] = model.named_steps["mlp"].n_iter_
                m["final_loss"] = model.named_steps["mlp"].loss_
                mlflow.log_metrics(m)
                for epoch, loss in enumerate(model.named_steps["mlp"].loss_curve_, 1):
                    mlflow.log_metric("loss", loss, step=epoch)
                varying = {k: flat(p)[k] for k in cfg["grid"]}
                print(f"[{i}/{len(combos)}] {varying}  val_f1={m['val_f1_macro']:.4f} "
                      f"acc={m['val_accuracy']:.4f} epochs={m['epochs']} {m['train_time_sec']:.1f}s")
                if best is None or m["val_f1_macro"] > best["metrics"]["val_f1_macro"]:
                    best = {"run_id": run.info.run_id, "trial": i, "params": p, "metrics": m, "model": model}

        # ---- лучшая модель: оценка на эталонном тесте, сохранение и регистрация ----
        model = best["model"]
        test_m, pred = scores(model, X_test, test["genre"], "test")
        mlflow.log_params({f"best_{k}": v for k, v in flat(best["params"]).items()})
        mlflow.log_metrics({"best_val_f1_macro": best["metrics"]["val_f1_macro"],
                            "best_val_accuracy": best["metrics"]["val_accuracy"], **test_m})
        mlflow.set_tag("best_trial_run_id", best["run_id"])
        client.set_tag(best["run_id"], "best_in_build", "true")
        labels = sorted(test["genre"].unique())
        mlflow.log_dict(classification_report(test["genre"], pred, output_dict=True, zero_division=0),
                        "eval/classification_report.json")
        mlflow.log_dict({"labels": labels,
                         "matrix": confusion_matrix(test["genre"], pred, labels=labels).tolist()},
                        "eval/confusion_matrix.json")

        example = X_test.head(3)
        info = mlflow.sklearn.log_model(model, artifact_path="model", input_example=example,
                                        signature=infer_signature(example, model.predict(example)))
        mv = mlflow.register_model(info.model_uri, MODEL_NAME)
        client.set_registered_model_alias(MODEL_NAME, CANDIDATE, mv.version)
        for k, v in {"jenkins_build": a.build, "data_md5": data_md5,
                     "val_f1_macro": f"{best['metrics']['val_f1_macro']:.4f}",
                     "test_f1_macro": f"{test_m['test_f1_macro']:.4f}"}.items():
            client.set_model_version_tag(MODEL_NAME, mv.version, k, v)
        client.update_model_version(MODEL_NAME, mv.version, description=(
            f"Сборка {a.build}. Лучшая из {len(combos)} комбинаций (trial {best['trial']}): "
            f"{flat(best['params'])}"))

    report = {"model_name": MODEL_NAME, "version": mv.version, "run_id": parent.info.run_id,
              "best_trial_run_id": best["run_id"], "build": a.build, "data_md5": data_md5,
              "params": best["params"], "val_metrics": best["metrics"], "test_metrics": test_m}
    write_report("candidate.json", report)
    write_report("best_params.json", best["params"])

    print(f"\nЛучшая модель: trial {best['trial']}, val_f1={best['metrics']['val_f1_macro']:.4f}, "
          f"test_f1={test_m['test_f1_macro']:.4f}")
    print(f"Зарегистрирована: {MODEL_NAME} v{mv.version} (алиас '{CANDIDATE}')")


if __name__ == "__main__":
    main()
