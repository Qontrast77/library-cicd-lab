from flask import request, jsonify
from common import create_base_app, query

SCHEMA = """
CREATE TABLE IF NOT EXISTS authors (
    id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    country TEXT
);"""
app = create_base_app(SCHEMA)


def nf():
    return jsonify(error="Author not found"), 404


@app.get("/api/authors")
def list_authors():
    return jsonify(query("SELECT * FROM authors ORDER BY id"))


@app.get("/api/authors/<int:aid>")
def get_author(aid):
    row = query("SELECT * FROM authors WHERE id=%s", (aid,), one=True)
    return jsonify(row) if row else nf()


@app.post("/api/authors")
def create_author():
    d = request.get_json(force=True)
    row = query(
        "INSERT INTO authors (full_name, country) VALUES (%s, %s) RETURNING *",
        (d["full_name"], d.get("country")), one=True)
    return jsonify(row), 201


@app.put("/api/authors/<int:aid>")
def update_author(aid):
    d = request.get_json(force=True)
    row = query(
        """UPDATE authors SET full_name=COALESCE(%s, full_name),
                              country=COALESCE(%s, country)
           WHERE id=%s RETURNING *""",
        (d.get("full_name"), d.get("country"), aid), one=True)
    return jsonify(row) if row else nf()


@app.delete("/api/authors/<int:aid>")
def delete_author(aid):
    row = query("DELETE FROM authors WHERE id=%s RETURNING id", (aid,), one=True)
    return jsonify(deleted=aid) if row else nf()
