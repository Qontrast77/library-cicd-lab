"""genre-service: микросервис определения жанра книги по аннотации.

Загружает из MLflow Model Registry модель с алиасом "champion" (её назначает
конвейер Jenkins после проверки качества) и отдаёт предсказания через gateway.

  GET  /api/genre/model     - какая версия модели сейчас работает
  POST /api/genre/predict   - {"title": "...", "summary": "..."} -> жанр
  POST /api/genre/reload    - перечитать champion из MLflow (вызывает Jenkins)
"""
import os
import socket
import threading

import mlflow
import mlflow.sklearn
import pandas as pd
from flask import Flask, jsonify, request
from mlflow import MlflowClient

MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.environ.get("MODEL_NAME", "book-genre-classifier")
ALIAS = os.environ.get("MODEL_ALIAS", "champion")

mlflow.set_tracking_uri(MLFLOW_URI)
app = Flask(__name__)
_lock = threading.Lock()
state = {"model": None, "version": None, "error": None}


def load_model():
    """Загружает champion; при недоступности MLflow запоминает ошибку, а не падает."""
    try:
        mv = MlflowClient().get_model_version_by_alias(MODEL_NAME, ALIAS)
        model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}/{mv.version}")
    except Exception as e:  # модели ещё нет или MLflow не запущен
        state["error"] = f"{type(e).__name__}: {e}"
        app.logger.warning("model is not loaded: %s", state["error"])
        return False
    with _lock:
        state.update(model=model, version=mv.version, error=None,
                     tags=dict(mv.tags or {}), run_id=mv.run_id)
    app.logger.warning("loaded %s v%s", MODEL_NAME, mv.version)
    return True


def ensure_model():
    if state["model"] is None:
        load_model()
    return state["model"] is not None


@app.after_request
def add_pod_header(resp):
    resp.headers["X-Served-By"] = socket.gethostname()
    return resp


@app.get("/health")
def health():
    return jsonify(status="ok", pod=socket.gethostname())


@app.get("/api/genre/model")
def model_info():
    ensure_model()
    return jsonify(model=MODEL_NAME, alias=ALIAS, version=state["version"],
                   loaded=state["model"] is not None, error=state["error"],
                   tags=state.get("tags"), mlflow=MLFLOW_URI)


@app.post("/api/genre/reload")
def reload_model():
    ok = load_model()
    return (jsonify(reloaded=True, version=state["version"]) if ok
            else (jsonify(reloaded=False, error=state["error"]), 503))


@app.post("/api/genre/predict")
def predict():
    d = request.get_json(force=True)
    text = f"{d.get('title', '')}. {d.get('summary', '')}".strip(". ")
    if not text:
        return jsonify(error="нужно передать title и/или summary"), 400
    if not ensure_model():
        return jsonify(error="модель ещё не обучена или MLflow недоступен", detail=state["error"]), 503
    with _lock:
        model, version = state["model"], state["version"]
    X = pd.DataFrame({"text": [text]})
    proba = model.predict_proba(X)[0]
    ranked = sorted(zip(model.classes_, proba), key=lambda t: -t[1])
    return jsonify(genre=ranked[0][0], confidence=round(float(ranked[0][1]), 4),
                   top3=[{"genre": g, "p": round(float(p), 4)} for g, p in ranked[:3]],
                   model_version=version)


load_model()
