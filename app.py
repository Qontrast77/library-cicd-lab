"""
Library Management System — REST API
Стек: Flask + sqlite3 (двухзвенная архитектура: клиент (SPA, static/) <-> сервер + БД)

Ресурсы и CRUD-операции (5 x 4 = 20):
  /api/authors   GET(list), GET(one), POST, PUT, DELETE
  /api/books     GET(list), GET(one), POST, PUT, DELETE
  /api/members   GET(list), GET(one), POST, PUT, DELETE
  /api/loans     GET(list), GET(one), POST, PUT, DELETE
"""
import os
from flask import Flask, request, jsonify, send_from_directory, g

from db import get_connection, init_db, row_to_dict, now_iso

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_app(db_path=None):
    app = Flask(__name__, static_folder="static")
    app.config["DB_PATH"] = db_path or os.path.join(BASE_DIR, "library.db")
    init_db(app.config["DB_PATH"])

    @app.teardown_appcontext
    def close_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def get_db():
        if "db" not in g:
            g.db = get_connection(app.config["DB_PATH"])
        return g.db

    register_routes(app, get_db)
    return app


def register_routes(app, get_db):

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    def not_found(name):
        return jsonify({"error": f"{name} not found"}), 404

    # ================= AUTHORS =================
    @app.route("/api/authors", methods=["GET"])
    def list_authors():
        rows = get_db().execute("SELECT * FROM authors").fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.route("/api/authors/<int:author_id>", methods=["GET"])
    def get_author(author_id):
        row = get_db().execute("SELECT * FROM authors WHERE id=?", (author_id,)).fetchone()
        return (jsonify(row_to_dict(row)), 200) if row else not_found("Author")

    @app.route("/api/authors", methods=["POST"])
    def create_author():
        data = request.get_json(force=True)
        db = get_db()
        cur = db.execute(
            "INSERT INTO authors (full_name, country) VALUES (?, ?)",
            (data["full_name"], data.get("country")),
        )
        db.commit()
        return jsonify(row_to_dict(db.execute("SELECT * FROM authors WHERE id=?", (cur.lastrowid,)).fetchone())), 201

    @app.route("/api/authors/<int:author_id>", methods=["PUT"])
    def update_author(author_id):
        db = get_db()
        row = db.execute("SELECT * FROM authors WHERE id=?", (author_id,)).fetchone()
        if not row:
            return not_found("Author")
        data = request.get_json(force=True)
        db.execute(
            "UPDATE authors SET full_name=?, country=? WHERE id=?",
            (data.get("full_name", row["full_name"]), data.get("country", row["country"]), author_id),
        )
        db.commit()
        return jsonify(row_to_dict(db.execute("SELECT * FROM authors WHERE id=?", (author_id,)).fetchone()))

    @app.route("/api/authors/<int:author_id>", methods=["DELETE"])
    def delete_author(author_id):
        db = get_db()
        row = db.execute("SELECT * FROM authors WHERE id=?", (author_id,)).fetchone()
        if not row:
            return not_found("Author")
        db.execute("DELETE FROM authors WHERE id=?", (author_id,))
        db.commit()
        return jsonify({"deleted": author_id})

    # ================= BOOKS =================
    @app.route("/api/books", methods=["GET"])
    def list_books():
        rows = get_db().execute("SELECT * FROM books").fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.route("/api/books/<int:book_id>", methods=["GET"])
    def get_book(book_id):
        row = get_db().execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return (jsonify(row_to_dict(row)), 200) if row else not_found("Book")

    @app.route("/api/books", methods=["POST"])
    def create_book():
        data = request.get_json(force=True)
        copies = int(data.get("copies_total", 1))
        db = get_db()
        cur = db.execute(
            "INSERT INTO books (title, year, copies_total, copies_available, author_id) VALUES (?, ?, ?, ?, ?)",
            (data["title"], data.get("year"), copies, copies, data["author_id"]),
        )
        db.commit()
        return jsonify(row_to_dict(db.execute("SELECT * FROM books WHERE id=?", (cur.lastrowid,)).fetchone())), 201

    @app.route("/api/books/<int:book_id>", methods=["PUT"])
    def update_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if not row:
            return not_found("Book")
        data = request.get_json(force=True)
        db.execute(
            """UPDATE books SET title=?, year=?, copies_total=?, copies_available=?, author_id=?
               WHERE id=?""",
            (
                data.get("title", row["title"]),
                data.get("year", row["year"]),
                data.get("copies_total", row["copies_total"]),
                data.get("copies_available", row["copies_available"]),
                data.get("author_id", row["author_id"]),
                book_id,
            ),
        )
        db.commit()
        return jsonify(row_to_dict(db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()))

    @app.route("/api/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        db = get_db()
        row = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if not row:
            return not_found("Book")
        db.execute("DELETE FROM books WHERE id=?", (book_id,))
        db.commit()
        return jsonify({"deleted": book_id})

    # ================= MEMBERS =================
    @app.route("/api/members", methods=["GET"])
    def list_members():
        rows = get_db().execute("SELECT * FROM members").fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.route("/api/members/<int:member_id>", methods=["GET"])
    def get_member(member_id):
        row = get_db().execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
        return (jsonify(row_to_dict(row)), 200) if row else not_found("Member")

    @app.route("/api/members", methods=["POST"])
    def create_member():
        data = request.get_json(force=True)
        db = get_db()
        cur = db.execute(
            "INSERT INTO members (full_name, email) VALUES (?, ?)",
            (data["full_name"], data["email"]),
        )
        db.commit()
        return jsonify(row_to_dict(db.execute("SELECT * FROM members WHERE id=?", (cur.lastrowid,)).fetchone())), 201

    @app.route("/api/members/<int:member_id>", methods=["PUT"])
    def update_member(member_id):
        db = get_db()
        row = db.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
        if not row:
            return not_found("Member")
        data = request.get_json(force=True)
        db.execute(
            "UPDATE members SET full_name=?, email=? WHERE id=?",
            (data.get("full_name", row["full_name"]), data.get("email", row["email"]), member_id),
        )
        db.commit()
        return jsonify(row_to_dict(db.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()))

    @app.route("/api/members/<int:member_id>", methods=["DELETE"])
    def delete_member(member_id):
        db = get_db()
        row = db.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
        if not row:
            return not_found("Member")
        db.execute("DELETE FROM members WHERE id=?", (member_id,))
        db.commit()
        return jsonify({"deleted": member_id})

    # ================= LOANS =================
    @app.route("/api/loans", methods=["GET"])
    def list_loans():
        rows = get_db().execute("SELECT * FROM loans").fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.route("/api/loans/<int:loan_id>", methods=["GET"])
    def get_loan(loan_id):
        row = get_db().execute("SELECT * FROM loans WHERE id=?", (loan_id,)).fetchone()
        return (jsonify(row_to_dict(row)), 200) if row else not_found("Loan")

    @app.route("/api/loans", methods=["POST"])
    def create_loan():
        data = request.get_json(force=True)
        db = get_db()
        book = db.execute("SELECT * FROM books WHERE id=?", (data["book_id"],)).fetchone()
        if not book or book["copies_available"] < 1:
            return jsonify({"error": "No copies available"}), 400
        db.execute(
            "UPDATE books SET copies_available = copies_available - 1 WHERE id=?",
            (book["id"],),
        )
        cur = db.execute(
            "INSERT INTO loans (book_id, member_id, issued_at, returned_at) VALUES (?, ?, ?, NULL)",
            (data["book_id"], data["member_id"], now_iso()),
        )
        db.commit()
        return jsonify(row_to_dict(db.execute("SELECT * FROM loans WHERE id=?", (cur.lastrowid,)).fetchone())), 201

    @app.route("/api/loans/<int:loan_id>", methods=["PUT"])
    def update_loan(loan_id):
        """Используется в т.ч. для возврата книги (returned=true)."""
        db = get_db()
        loan = db.execute("SELECT * FROM loans WHERE id=?", (loan_id,)).fetchone()
        if not loan:
            return not_found("Loan")
        data = request.get_json(force=True)
        if data.get("returned") and not loan["returned_at"]:
            db.execute("UPDATE loans SET returned_at=? WHERE id=?", (now_iso(), loan_id))
            db.execute(
                """UPDATE books SET copies_available = MIN(copies_total, copies_available + 1)
                   WHERE id=?""",
                (loan["book_id"],),
            )
        db.commit()
        return jsonify(row_to_dict(db.execute("SELECT * FROM loans WHERE id=?", (loan_id,)).fetchone()))

    @app.route("/api/loans/<int:loan_id>", methods=["DELETE"])
    def delete_loan(loan_id):
        db = get_db()
        row = db.execute("SELECT * FROM loans WHERE id=?", (loan_id,)).fetchone()
        if not row:
            return not_found("Loan")
        db.execute("DELETE FROM loans WHERE id=?", (loan_id,))
        db.commit()
        return jsonify({"deleted": loan_id})

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
