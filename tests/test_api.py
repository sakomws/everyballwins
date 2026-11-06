"""Tests for the everyballwins simple API service.

Run with:
    python3 -m unittest discover -s tests -v
"""

import unittest

from fastapi.testclient import TestClient

from app.main import app, reset_store


class ApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        # Each test gets a fresh, empty in-memory store.
        reset_store()
        self.client = TestClient(app)

    # -- helpers -----------------------------------------------------------
    def create_item(self, **overrides) -> dict:
        payload = {"name": "Ball", "price": 9.99, "description": "A ball", "tags": ["sports"]}
        payload.update(overrides)
        response = self.client.post("/items", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    # -- meta endpoints ----------------------------------------------------
    def test_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["service"], "everyballwins API")
        self.assertIn("version", body)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    # -- item CRUD ---------------------------------------------------------
    def test_create_item(self):
        item = self.create_item(name="Basketball", price=19.5)
        self.assertEqual(item["name"], "Basketball")
        self.assertEqual(item["price"], 19.5)
        self.assertEqual(item["description"], "A ball")
        self.assertEqual(item["tags"], ["sports"])
        self.assertGreaterEqual(item["id"], 1)

    def test_create_item_minimal_payload(self):
        response = self.client.post("/items", json={"name": "Tennis ball", "price": 3})
        self.assertEqual(response.status_code, 201)
        item = response.json()
        self.assertIsNone(item["description"])
        self.assertEqual(item["tags"], [])

    def test_create_item_validation_error(self):
        # Missing required "price" field.
        response = self.client.post("/items", json={"name": "No price"})
        self.assertEqual(response.status_code, 422)
        # Negative price is rejected.
        response = self.client.post("/items", json={"name": "Bad", "price": -1})
        self.assertEqual(response.status_code, 422)

    def test_list_items_empty(self):
        response = self.client.get("/items")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_items_and_filter(self):
        self.create_item(name="Basketball")
        self.create_item(name="Football")
        self.create_item(name="Tennis racket")

        response = self.client.get("/items")
        self.assertEqual(len(response.json()), 3)

        response = self.client.get("/items", params={"q": "ball"})
        names = {item["name"] for item in response.json()}
        self.assertEqual(names, {"Basketball", "Football"})

        response = self.client.get("/items", params={"limit": 1, "offset": 1})
        self.assertEqual(len(response.json()), 1)

    def test_get_item(self):
        created = self.create_item()
        response = self.client.get(f"/items/{created['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), created)

    def test_get_item_not_found(self):
        response = self.client.get("/items/999999")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"])

    def test_update_item(self):
        created = self.create_item()
        response = self.client.put(
            f"/items/{created['id']}", json={"price": 4.99, "tags": ["sale"]}
        )
        self.assertEqual(response.status_code, 200)
        updated = response.json()
        self.assertEqual(updated["price"], 4.99)
        self.assertEqual(updated["tags"], ["sale"])
        # Untouched fields are preserved.
        self.assertEqual(updated["name"], created["name"])
        self.assertEqual(updated["id"], created["id"])

    def test_update_item_not_found(self):
        response = self.client.put("/items/999999", json={"price": 1})
        self.assertEqual(response.status_code, 404)

    def test_delete_item(self):
        created = self.create_item()
        response = self.client.delete(f"/items/{created['id']}")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get(f"/items/{created['id']}").status_code, 404)

    def test_delete_item_not_found(self):
        response = self.client.delete("/items/999999")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
