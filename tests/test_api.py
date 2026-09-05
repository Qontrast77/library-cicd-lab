"""
Тесты API. Написаны через unittest (стандартная библиотека),
но полностью совместимы с автозапуском через pytest в Jenkins:
    pytest tests/ --junitxml=reports/results.xml
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app


class LibraryApiTestCase(unittest.TestCase):

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp()
        os.close(fd)
        os.remove(self.db_path)  # init_db creates it fresh
        app = create_app(db_path=self.db_path)
        app.config["TESTING"] = True
        self.client = app.test_client()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_health(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "ok")

    def test_author_crud(self):
        resp = self.client.post("/api/authors", json={"full_name": "Лев Толстой", "country": "RU"})
        self.assertEqual(resp.status_code, 201)
        author_id = resp.get_json()["id"]

        resp = self.client.get("/api/authors")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()), 1)

        resp = self.client.get(f"/api/authors/{author_id}")
        self.assertEqual(resp.get_json()["full_name"], "Лев Толстой")

        resp = self.client.put(f"/api/authors/{author_id}", json={"country": "Russia"})
        self.assertEqual(resp.get_json()["country"], "Russia")

        resp = self.client.delete(f"/api/authors/{author_id}")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(f"/api/authors/{author_id}")
        self.assertEqual(resp.status_code, 404)

    def test_book_crud(self):
        author_id = self.client.post(
            "/api/authors", json={"full_name": "Автор", "country": "RU"}
        ).get_json()["id"]

        resp = self.client.post(
            "/api/books",
            json={"title": "Война и мир", "year": 1869, "copies_total": 3, "author_id": author_id},
        )
        self.assertEqual(resp.status_code, 201)
        book = resp.get_json()
        self.assertEqual(book["copies_available"], 3)
        book_id = book["id"]

        resp = self.client.get(f"/api/books/{book_id}")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.put(f"/api/books/{book_id}", json={"year": 1870})
        self.assertEqual(resp.get_json()["year"], 1870)

        resp = self.client.delete(f"/api/books/{book_id}")
        self.assertEqual(resp.status_code, 200)

    def test_member_crud(self):
        resp = self.client.post("/api/members", json={"full_name": "Иван Иванов", "email": "ivan@example.com"})
        self.assertEqual(resp.status_code, 201)
        member_id = resp.get_json()["id"]

        resp = self.client.get(f"/api/members/{member_id}")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.put(f"/api/members/{member_id}", json={"full_name": "Иван Петров"})
        self.assertEqual(resp.get_json()["full_name"], "Иван Петров")

        resp = self.client.delete(f"/api/members/{member_id}")
        self.assertEqual(resp.status_code, 200)

    def test_loan_flow(self):
        author_id = self.client.post("/api/authors", json={"full_name": "Автор2"}).get_json()["id"]
        book_id = self.client.post(
            "/api/books", json={"title": "Книга", "copies_total": 1, "author_id": author_id}
        ).get_json()["id"]
        member_id = self.client.post(
            "/api/members", json={"full_name": "Читатель", "email": "reader@example.com"}
        ).get_json()["id"]

        resp = self.client.post("/api/loans", json={"book_id": book_id, "member_id": member_id})
        self.assertEqual(resp.status_code, 201)
        loan_id = resp.get_json()["id"]

        # копий больше не осталось
        resp = self.client.post("/api/loans", json={"book_id": book_id, "member_id": member_id})
        self.assertEqual(resp.status_code, 400)

        resp = self.client.get(f"/api/loans/{loan_id}")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.put(f"/api/loans/{loan_id}", json={"returned": True})
        self.assertIsNotNone(resp.get_json()["returned_at"])

        book_resp = self.client.get(f"/api/books/{book_id}").get_json()
        self.assertEqual(book_resp["copies_available"], 1)

        resp = self.client.delete(f"/api/loans/{loan_id}")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
