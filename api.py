#!/usr/bin/env python3
"""everyballwins — simple Python API.

A tiny JSON REST API built only on the Python standard library.
No external dependencies required.

Endpoints
---------
GET    /                  Service info.
GET    /health            Health check.
GET    /api/items         List all items.
GET    /api/items/{id}    Get a single item.
POST   /api/items         Create an item. Body: {"name": "..."}.
DELETE /api/items/{id}    Delete an item.

Run:
    python3 api.py [--host 127.0.0.1] [--port 8000]
"""

from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 8000


class ItemStore:
    """Thread-safe in-memory store for items."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._items.values())

    def get(self, item_id: int) -> dict[str, Any] | None:
        with self._lock:
            return self._items.get(item_id)

    def create(self, name: str) -> dict[str, Any]:
        with self._lock:
            item = {"id": self._next_id, "name": name}
            self._items[self._next_id] = item
            self._next_id += 1
            return item

    def delete(self, item_id: int) -> bool:
        with self._lock:
            return self._items.pop(item_id, None) is not None


class ApiHandler(BaseHTTPRequestHandler):
    """Request handler for the simple API."""

    store = ItemStore()
    server_version = "SimplePyApi/1.0"

    # -- helpers ---------------------------------------------------------

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> tuple[dict[str, Any] | None, str | None]:
        """Return (data, error). Exactly one of the two is not None."""
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return None, "request body is required"
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None, "request body must be valid JSON"
        if not isinstance(data, dict):
            return None, "request body must be a JSON object"
        return data, None

    def _item_id_from_path(self, prefix: str) -> int | None:
        path = urlparse(self.path).path.rstrip("/")
        if not path.startswith(prefix + "/"):
            return None
        try:
            return int(path[len(prefix) + 1 :])
        except ValueError:
            return None

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Keep test/CLI output clean; override to re-enable logging.
        pass

    # -- routes ----------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path == "/":
            self._send_json(200, {"service": "everyballwins", "version": "1.0.0"})
            return

        if path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if path == "/api/items":
            self._send_json(200, {"items": self.store.list()})
            return

        item_id = self._item_id_from_path("/api/items")
        if item_id is not None:
            item = self.store.get(item_id)
            if item is None:
                self._send_json(404, {"error": "item not found"})
            else:
                self._send_json(200, item)
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path == "/api/items":
            data, error = self._read_json_body()
            if error:
                self._send_json(400, {"error": error})
                return
            name = data.get("name")
            if not isinstance(name, str) or not name.strip():
                self._send_json(400, {"error": "'name' must be a non-empty string"})
                return
            self._send_json(201, self.store.create(name.strip()))
            return

        self._send_json(404, {"error": "not found"})

    def do_DELETE(self) -> None:  # noqa: N802
        item_id = self._item_id_from_path("/api/items")
        if item_id is None:
            self._send_json(404, {"error": "not found"})
            return
        if self.store.delete(item_id):
            self._send_json(200, {"deleted": item_id})
        else:
            self._send_json(404, {"error": "item not found"})


def create_server(host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), ApiHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the simple Python API.")
    parser.add_argument("--host", default=HOST, help=f"bind host (default: {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"bind port (default: {PORT})")
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    print(f"Serving on http://{args.host}:{args.port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
