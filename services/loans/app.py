import os
import requests
from flask import request, jsonify
from common import create_base_app, query

BOOKS_URL = os.environ.get("BOOKS_URL", "http://books-service")
MEMBERS_URL = os.environ.get("MEMBERS_URL", "http://members-service")

SCHEMA = """
CREATE TABLE IF NOT EXISTS loans (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    returned_at TIMESTAMPTZ
);"""
app = create_base_app(SCHEMA)


def nf():
    return jsonify(error="Loan not found"), 404


def release_copy(book_id):
    try:
        requests.post(f"{BOOKS_URL}/api/books/{book_id}/release", timeout=3)
    except requests.RequestException:
        app.logger.error("could not release copy of book %s", book_id)


@app.get("/api/loans")
def list_loans():
    return jsonify(query("SELECT * FROM loans ORDER BY id"))


@app.get("/api/loans/<int:lid>")
def get_loan(lid):
    row = query("SELECT * FROM loans WHERE id=%s", (lid,), one=True)
    return jsonify(row) if row else nf()


@app.post("/api/loans")
def create_loan():
    d = request.get_json(force=True)
    book_id, member_id = d["book_id"], d["member_id"]
    try:
        m = requests.get(f"{MEMBERS_URL}/api/members/{member_id}", timeout=3)
        if m.status_code == 404:
            return jsonify(error="Member not found"), 400
        r = requests.post(f"{BOOKS_URL}/api/books/{book_id}/reserve", timeout=3)
    except requests.RequestException:
        return jsonify(error="dependent service unavailable"), 503
    if r.status_code in (404, 409):
        return jsonify(error="No copies available"), 400
    if r.status_code != 200:
        return jsonify(error="books-service error"), 503
    try:
        row = query(
            "INSERT INTO loans (book_id, member_id) VALUES (%s, %s) RETURNING *",
            (book_id, member_id), one=True)
    except Exception:
        release_copy(book_id)   # компенсирующая операция
        raise
    return jsonify(row), 201


@app.put("/api/loans/<int:lid>")
def update_loan(lid):
    d = request.get_json(force=True)
    if not query("SELECT id FROM loans WHERE id=%s", (lid,), one=True):
        return nf()
    if d.get("returned"):
        upd = query(
            """UPDATE loans SET returned_at=now()
               WHERE id=%s AND returned_at IS NULL RETURNING *""", (lid,), one=True)
        if upd:
            release_copy(upd["book_id"])
    return jsonify(query("SELECT * FROM loans WHERE id=%s", (lid,), one=True))


@app.delete("/api/loans/<int:lid>")
def delete_loan(lid):
    row = query("DELETE FROM loans WHERE id=%s RETURNING id", (lid,), one=True)
    return jsonify(deleted=lid) if row else nf()
