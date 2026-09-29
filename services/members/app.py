from flask import request, jsonify
from common import create_base_app, query

SCHEMA = """
CREATE TABLE IF NOT EXISTS members (
    id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL
);"""
app = create_base_app(SCHEMA)


def nf():
    return jsonify(error="Member not found"), 404


@app.get("/api/members")
def list_members():
    return jsonify(query("SELECT * FROM members ORDER BY id"))


@app.get("/api/members/<int:mid>")
def get_member(mid):
    row = query("SELECT * FROM members WHERE id=%s", (mid,), one=True)
    return jsonify(row) if row else nf()


@app.post("/api/members")
def create_member():
    d = request.get_json(force=True)
    row = query(
        "INSERT INTO members (full_name, email) VALUES (%s, %s) RETURNING *",
        (d["full_name"], d["email"]), one=True)
    return jsonify(row), 201


@app.put("/api/members/<int:mid>")
def update_member(mid):
    d = request.get_json(force=True)
    row = query(
        """UPDATE members SET full_name=COALESCE(%s, full_name),
                              email=COALESCE(%s, email)
           WHERE id=%s RETURNING *""",
        (d.get("full_name"), d.get("email"), mid), one=True)
    return jsonify(row) if row else nf()


@app.delete("/api/members/<int:mid>")
def delete_member(mid):
    row = query("DELETE FROM members WHERE id=%s RETURNING id", (mid,), one=True)
    return jsonify(deleted=mid) if row else nf()
