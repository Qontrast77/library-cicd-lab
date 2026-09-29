import os
import requests
from flask import request, jsonify
from common import create_base_app, query

AUTHORS_URL = os.environ.get("AUTHORS_URL", "http://authors-service")

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    year INTEGER,
    copies_total INTEGER NOT NULL DEFAULT 1,
    copies_available INTEGER NOT NULL DEFAULT 1,
    author_id INTEGER NOT NULL
);"""
app = create_base_app(SCHEMA)


def nf():
    return jsonify(error="Book not found"), 404


def author_exists(author_id):
    """True/False, либо None если authors-service недоступен."""
    try:
        r = requests.get(f"{AUTHORS_URL}/api/authors/{author_id}", timeout=3)
    except requests.RequestException:
        return None
    return r.status_code == 200


@app.get("/api/books")
def list_books():
    return jsonify(query("SELECT * FROM books ORDER BY id"))


@app.get("/api/books/<int:bid>")
def get_book(bid):
    row = query("SELECT * FROM books WHERE id=%s", (bid,), one=True)
    return jsonify(row) if row else nf()


@app.post("/api/books")
def create_book():
    d = request.get_json(force=True)
    exists = author_exists(d["author_id"])
    if exists is None:
        return jsonify(error="authors-service unavailable"), 503
    if not exists:
        return jsonify(error="Author not found"), 400
    copies = int(d.get("copies_total", 1))
    row = query(
        """INSERT INTO books (title, year, copies_total, copies_available, author_id)
           VALUES (%s, %s, %s, %s, %s) RETURNING *""",
        (d["title"], d.get("year"), copies, copies, d["author_id"]), one=True)
    return jsonify(row), 201


@app.put("/api/books/<int:bid>")
def update_book(bid):
    d = request.get_json(force=True)
    row = query(
        """UPDATE books SET title=COALESCE(%s, title), year=COALESCE(%s, year),
               copies_total=COALESCE(%s, copies_total),
               copies_available=COALESCE(%s, copies_available),
               author_id=COALESCE(%s, author_id)
           WHERE id=%s RETURNING *""",
        (d.get("title"), d.get("year"), d.get("copies_total"),
         d.get("copies_available"), d.get("author_id"), bid), one=True)
    return jsonify(row) if row else nf()


@app.delete("/api/books/<int:bid>")
def delete_book(bid):
    row = query("DELETE FROM books WHERE id=%s RETURNING id", (bid,), one=True)
    return jsonify(deleted=bid) if row else nf()


# ---- операции для loans-service (атомарные) ----
@app.post("/api/books/<int:bid>/reserve")
def reserve(bid):
    row = query(
        """UPDATE books SET copies_available = copies_available - 1
           WHERE id=%s AND copies_available > 0 RETURNING *""", (bid,), one=True)
    if row:
        return jsonify(row)
    exists = query("SELECT id FROM books WHERE id=%s", (bid,), one=True)
    return (jsonify(error="No copies available"), 409) if exists else nf()


@app.post("/api/books/<int:bid>/release")
def release(bid):
    row = query(
        """UPDATE books SET copies_available = LEAST(copies_total, copies_available + 1)
           WHERE id=%s RETURNING *""", (bid,), one=True)
    return jsonify(row) if row else nf()
