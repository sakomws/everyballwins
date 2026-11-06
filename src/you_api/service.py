"""HTTP service exposing the You.com API over simple REST endpoints.

Run it directly::

    YOU_API_KEY=... python -m you_api.service --port 8000

Endpoints:

* ``GET  /health``                  — liveness probe
* ``GET  /v1/search?q=...``         — web search
* ``GET  /v1/news?q=...``           — news search
* ``GET  /v1/snippets?urls=a,b``    — content snippets for URLs
* ``POST /v1/research``             — body: ``{"question": ...}``
* ``POST /v1/agents/runs``          — body: ``{"agent": ..., "input": ...}``
"""

from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from .client import YouClient
from .exceptions import YouAPIError, YouAuthenticationError


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class YouAPIService:
    """Small REST service that proxies calls to the You.com API."""

    def __init__(self, client: YouClient) -> None:
        self.client = client

    # -- routing ---------------------------------------------------------
    def handle_get(self, path: str, query: dict[str, list[str]]) -> tuple[int, Any]:
        if path == "/health":
            return HTTPStatus.OK, {"status": "ok", "service": "you-api"}
        if path == "/v1/search":
            q = self._required(query, "q")
            options = self._common_options(query)
            return HTTPStatus.OK, self.client.search(q, **options)
        if path == "/v1/news":
            q = self._required(query, "q")
            options = self._common_options(query)
            return HTTPStatus.OK, self.client.news(q, **options)
        if path == "/v1/snippets":
            raw = self._required(query, "urls")
            urls = [u.strip() for u in raw.split(",") if u.strip()]
            return HTTPStatus.OK, self.client.content_snippets(urls)
        return HTTPStatus.NOT_FOUND, {"error": f"unknown route: GET {path}"}

    def handle_post(self, path: str, body: Any) -> tuple[int, Any]:
        if not isinstance(body, dict):
            return HTTPStatus.BAD_REQUEST, {"error": "request body must be a JSON object"}
        if path == "/v1/research":
            question = body.get("question")
            if not question:
                return HTTPStatus.BAD_REQUEST, {"error": "'question' is required"}
            return HTTPStatus.OK, self.client.research(
                question,
                instructions=body.get("instructions"),
                model=body.get("model"),
                stream=bool(body.get("stream", False)),
            )
        if path == "/v1/agents/runs":
            agent = body.get("agent")
            if not agent:
                return HTTPStatus.BAD_REQUEST, {"error": "'agent' is required"}
            if "input" not in body:
                return HTTPStatus.BAD_REQUEST, {"error": "'input' is required"}
            return HTTPStatus.OK, self.client.run_agent(
                agent,
                input=body["input"],
                stream=bool(body.get("stream", False)),
            )
        return HTTPStatus.NOT_FOUND, {"error": f"unknown route: POST {path}"}

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _required(query: dict[str, list[str]], name: str) -> str:
        values = query.get(name)
        if not values or not values[0]:
            raise ValueError(f"missing required query parameter: '{name}'")
        return values[0]

    @staticmethod
    def _common_options(query: dict[str, list[str]]) -> dict[str, Any]:
        options: dict[str, Any] = {}
        for key in ("country", "language", "safesearch", "freshness", "livecrawl"):
            if query.get(key):
                options[key] = query[key][0]
        for key in ("count", "offset"):
            if query.get(key):
                try:
                    options[key] = int(query[key][0])
                except ValueError:
                    raise ValueError(f"query parameter '{key}' must be an integer")
        if query.get("include_domains"):
            options["include_domains"] = query["include_domains"][0].split(",")
        if query.get("exclude_domains"):
            options["exclude_domains"] = query["exclude_domains"][0].split(",")
        return options


def make_handler(service: YouAPIService) -> type[BaseHTTPRequestHandler]:
    """Build a ``BaseHTTPRequestHandler`` subclass bound to ``service``."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "YouAPIService/0.1.0"

        # -- plumbing ----------------------------------------------------
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            if os.environ.get("YOU_API_SERVICE_LOG"):
                super().log_message(format, *args)

        def _send_json(self, status: int, payload: Any) -> None:
            body = _json_bytes(payload)
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _error_status(self, exc: Exception) -> tuple[int, Any]:
            if isinstance(exc, YouAPIError):
                status = exc.status_code or 502
                # Never leak auth details upstream sent us.
                if isinstance(exc, YouAuthenticationError):
                    return 502, {"error": "upstream authentication failed"}
                return status, {"error": exc.message}
            return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)}

        # -- verbs ---------------------------------------------------------
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            try:
                status, payload = service.handle_get(parsed.path, query)
            except ValueError as exc:
                status, payload = HTTPStatus.BAD_REQUEST, {"error": str(exc)}
            except Exception as exc:  # noqa: BLE001
                status, payload = self._error_status(exc)
            self._send_json(status, payload)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            raw = self.rfile.read(length) if length > 0 else b""
            try:
                body: Any = json.loads(raw) if raw else {}
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON body"})
                return
            try:
                status, payload = service.handle_post(parsed.path, body)
            except ValueError as exc:
                status, payload = HTTPStatus.BAD_REQUEST, {"error": str(exc)}
            except Exception as exc:  # noqa: BLE001
                status, payload = self._error_status(exc)
            self._send_json(status, payload)

    return Handler


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="You.com API service")
    parser.add_argument("--host", default="127.0.0.1", help="bind host")
    parser.add_argument("--port", type=int, default=8000, help="bind port")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("YOU_API_BASE_URL", "https://api.you.com"),
        help="You.com API base URL",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="upstream timeout (s)")
    args = parser.parse_args(argv)

    client = YouClient(base_url=args.base_url, timeout=args.timeout)
    service = YouAPIService(client)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(service))
    print(f"you-api service listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
