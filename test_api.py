#!/usr/bin/env python3
"""Tests for the simple Python API (api.py).

Run with:
    python3 -m unittest -v
"""

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request

from api import ApiHandler, ItemStore, create_server


def request(
    method: str, url: str, payload: dict | None = None, raw_body: bytes | None = None
) -> tuple[int, dict]:
    """Make an HTTP request and return (status_code, parsed_json_body)."""
    data = raw_body
    if data is None and payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = json.loads(exc.read().decode("utf-8"))
        exc.close()
        return exc.code, body


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = create_server("127.0.0.1", 0)  # ephemeral port
        cls.port = cls.server.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self) -> None:
        # Isolate each test with a fresh store.
        ApiHandler.store = ItemStore()

    # -- basic endpoints -------------------------------------------------

    def test_root_returns_service_info(self) -> None:
        status, body = request("GET", f"{self.base}/")
        self.assertEqual(status, 200)
        self.assertEqual(body["service"], "everyballwins")
        self.assertIn("version", body)

    def test_health(self) -> None:
        status, body = request("GET", f"{self.base}/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_unknown_route_returns_404(self) -> None:
        status, body = request("GET", f"{self.base}/nope")
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    # -- items CRUD ------------------------------------------------------

    def test_list_items_empty(self) -> None:
        status, body = request("GET", f"{self.base}/api/items")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"items": []})

    def test_create_item(self) -> None:
        status, body = request("POST", f"{self.base}/api/items", {"name": "ball"})
        self.assertEqual(status, 201)
        self.assertEqual(body, {"id": 1, "name": "ball"})

    def test_create_and_get_item(self) -> None:
        _, created = request("POST", f"{self.base}/api/items", {"name": "trophy"})
        status, body = request("GET", f"{self.base}/api/items/{created['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(body, created)

    def test_create_item_missing_name(self) -> None:
        status, body = request("POST", f"{self.base}/api/items", {})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_create_item_empty_body(self) -> None:
        status, body = request("POST", f"{self.base}/api/items", raw_body=b"")
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_create_item_invalid_json(self) -> None:
        status, body = request("POST", f"{self.base}/api/items", raw_body=b"not json")
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_get_missing_item(self) -> None:
        status, body = request("GET", f"{self.base}/api/items/999")
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_delete_item(self) -> None:
        _, created = request("POST", f"{self.base}/api/items", {"name": "gone"})
        status, body = request("DELETE", f"{self.base}/api/items/{created['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"deleted": created["id"]})
        status, _ = request("GET", f"{self.base}/api/items/{created['id']}")
        self.assertEqual(status, 404)

    def test_delete_missing_item(self) -> None:
        status, _ = request("DELETE", f"{self.base}/api/items/999")
        self.assertEqual(status, 404)

    def test_items_are_listed_in_order(self) -> None:
        request("POST", f"{self.base}/api/items", {"name": "a"})
        request("POST", f"{self.base}/api/items", {"name": "b"})
        status, body = request("GET", f"{self.base}/api/items")
        self.assertEqual(status, 200)
        self.assertEqual([i["name"] for i in body["items"]], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
