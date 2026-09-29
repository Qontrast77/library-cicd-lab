"""
Сквозной smoke-тест микросервисного приложения через API Gateway.
Запуск: BASE_URL=http://localhost:8080 pytest tests/ --junitxml=reports/results.xml
"""
import os
import unittest

import requests

BASE = os.environ.get("BASE_URL", "http://localhost:8080")
T = 10


def post(path, **body):
    return requests.post(f"{BASE}{path}", json=body, timeout=T)


class LibrarySmokeTest(unittest.TestCase):

    def test_health(self):
        r = requests.get(f"{BASE}/api/health", timeout=T)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_author_crud(self):
        r = post("/api/authors", full_name="Лев Толстой", country="RU")
        self.assertEqual(r.status_code, 201)
        aid = r.json()["id"]
        self.assertEqual(requests.get(f"{BASE}/api/authors/{aid}", timeout=T).status_code, 200)
        r = requests.put(f"{BASE}/api/authors/{aid}", json={"country": "Russia"}, timeout=T)
        self.assertEqual(r.json()["country"], "Russia")
        self.assertEqual(requests.delete(f"{BASE}/api/authors/{aid}", timeout=T).status_code, 200)
        self.assertEqual(requests.get(f"{BASE}/api/authors/{aid}", timeout=T).status_code, 404)

    def test_book_requires_existing_author(self):
        r = post("/api/books", title="Ghost", author_id=999999)
        self.assertEqual(r.status_code, 400)

    def test_member_crud(self):
        r = post("/api/members", full_name="Иван Иванов", email="ivan@example.com")
        self.assertEqual(r.status_code, 201)
        mid = r.json()["id"]
        r = requests.put(f"{BASE}/api/members/{mid}", json={"full_name": "Иван Петров"}, timeout=T)
        self.assertEqual(r.json()["full_name"], "Иван Петров")
        self.assertEqual(requests.delete(f"{BASE}/api/members/{mid}", timeout=T).status_code, 200)

    def test_loan_flow_across_services(self):
        aid = post("/api/authors", full_name="Автор2").json()["id"]
        book = post("/api/books", title="Книга", copies_total=1, author_id=aid).json()
        self.assertEqual(book["copies_available"], 1)
        mid = post("/api/members", full_name="Читатель", email="r@example.com").json()["id"]

        r = post("/api/loans", book_id=book["id"], member_id=mid)
        self.assertEqual(r.status_code, 201)
        lid = r.json()["id"]

        # копий не осталось
        self.assertEqual(post("/api/loans", book_id=book["id"], member_id=mid).status_code, 400)
        b = requests.get(f"{BASE}/api/books/{book['id']}", timeout=T).json()
        self.assertEqual(b["copies_available"], 0)

        # возврат
        r = requests.put(f"{BASE}/api/loans/{lid}", json={"returned": True}, timeout=T)
        self.assertIsNotNone(r.json()["returned_at"])
        b = requests.get(f"{BASE}/api/books/{book['id']}", timeout=T).json()
        self.assertEqual(b["copies_available"], 1)

        self.assertEqual(requests.delete(f"{BASE}/api/loans/{lid}", timeout=T).status_code, 200)

    def test_loan_unknown_member(self):
        aid = post("/api/authors", full_name="Автор3").json()["id"]
        book = post("/api/books", title="Книга3", author_id=aid).json()
        r = post("/api/loans", book_id=book["id"], member_id=999999)
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
