import os
import socket
import time

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "postgres"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=3,
    )


def query(sql, params=(), one=False):
    """Запрос в отдельной транзакции; коммит при выходе из with."""
    conn = get_conn()
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if cur.description is None:
                return None
            return cur.fetchone() if one else cur.fetchall()
    finally:
        conn.close()


def init_schema(schema_sql, retries=30):
    """Ждёт PostgreSQL и создаёт таблицы. Advisory-lock защищает от гонки реплик."""
    for _ in range(retries):
        try:
            conn = get_conn()
            with conn, conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(42)")
                cur.execute(schema_sql)
            conn.close()
            return
        except psycopg2.OperationalError:
            time.sleep(2)
    raise RuntimeError("database is not available")


def create_base_app(schema_sql):
    app = Flask(__name__)
    init_schema(schema_sql)

    @app.after_request
    def add_pod_header(resp):
        resp.headers["X-Served-By"] = socket.gethostname()
        return resp

    @app.errorhandler(KeyError)
    def missing_field(e):
        return jsonify(error=f"missing field {e}"), 400

    @app.route("/health")   # liveness
    def health():
        return jsonify(status="ok", pod=socket.gethostname())

    @app.route("/ready")    # readiness
    def ready():
        try:
            query("SELECT 1")
            return jsonify(status="ready")
        except Exception:
            return jsonify(status="db unavailable"), 503

    return app
