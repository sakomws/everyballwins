"""Unit tests for the You.com API HTTP service."""

from __future__ import annotations

import json
import unittest
from typing import Any
from unittest import mock

from you_api import YouAPIError, YouClient, YouRateLimitError
from you_api.service import YouAPIService


def make_service() -> tuple[YouAPIService, mock.MagicMock]:
    client = YouClient(api_key="test-key")
    client._transport = mock.MagicMock()  # ensure no real HTTP happens
    for method in ("search", "news", "content_snippets", "research", "run_agent"):
        setattr(client, method, mock.MagicMock(name=method))
    return YouAPIService(client), client  # type: ignore[return-value]


class ServiceGetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service, self.client = make_service()

    def test_health(self) -> None:
        status, payload = self.service.handle_get("/health", {})
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_search_requires_q(self) -> None:
        with self.assertRaises(ValueError):
            self.service.handle_get("/v1/search", {})

    def test_search_passes_options(self) -> None:
        self.client.search.return_value = {"results": []}
        status, payload = self.service.handle_get(
            "/v1/search",
            {
                "q": ["python"],
                "count": ["3"],
                "offset": ["6"],
                "country": ["US"],
                "include_domains": ["a.com,b.com"],
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"results": []})
        self.client.search.assert_called_once_with(
            "python",
            count=3,
            offset=6,
            country="US",
            include_domains=["a.com", "b.com"],
        )

    def test_search_rejects_non_integer_count(self) -> None:
        with self.assertRaises(ValueError):
            self.service.handle_get("/v1/search", {"q": ["x"], "count": ["abc"]})

    def test_news(self) -> None:
        self.client.news.return_value = {"news": []}
        status, payload = self.service.handle_get("/v1/news", {"q": ["ai"]})
        self.assertEqual(status, 200)
        self.client.news.assert_called_once_with("ai")

    def test_snippets(self) -> None:
        self.client.content_snippets.return_value = {"snippets": []}
        status, _ = self.service.handle_get(
            "/v1/snippets", {"urls": ["https://a.com, https://b.com"]}
        )
        self.assertEqual(status, 200)
        self.client.content_snippets.assert_called_once_with(
            ["https://a.com", "https://b.com"]
        )

    def test_unknown_route(self) -> None:
        status, payload = self.service.handle_get("/nope", {})
        self.assertEqual(status, 404)
        self.assertIn("error", payload)


class ServicePostTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service, self.client = make_service()

    def test_research_requires_question(self) -> None:
        status, payload = self.service.handle_post("/v1/research", {})
        self.assertEqual(status, 400)
        self.assertIn("question", payload["error"])

    def test_research(self) -> None:
        self.client.research.return_value = {"answer": "42"}
        status, payload = self.service.handle_post(
            "/v1/research",
            {"question": "meaning?", "model": "agent", "stream": True},
        )
        self.assertEqual(status, 200)
        self.client.research.assert_called_once_with(
            "meaning?", instructions=None, model="agent", stream=True
        )

    def test_agent_run_requires_fields(self) -> None:
        status, _ = self.service.handle_post("/v1/agents/runs", {})
        self.assertEqual(status, 400)
        status, _ = self.service.handle_post("/v1/agents/runs", {"agent": "a"})
        self.assertEqual(status, 400)

    def test_agent_run(self) -> None:
        self.client.run_agent.return_value = {"output": "ok"}
        status, _ = self.service.handle_post(
            "/v1/agents/runs", {"agent": "research", "input": {"query": "q"}}
        )
        self.assertEqual(status, 200)
        self.client.run_agent.assert_called_once_with(
            "research", input={"query": "q"}, stream=False
        )

    def test_non_object_body_rejected(self) -> None:
        status, payload = self.service.handle_post("/v1/research", ["nope"])
        self.assertEqual(status, 400)

    def test_unknown_route(self) -> None:
        status, _ = self.service.handle_post("/nope", {})
        self.assertEqual(status, 404)


class HandlerTests(unittest.TestCase):
    """Exercise the HTTP handler end-to-end over a real local socket."""

    def setUp(self) -> None:
        from http.server import ThreadingHTTPServer

        from you_api.service import make_handler

        self.service, self.client = make_service()
        handler = make_handler(self.service)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_address[1]

        import threading

        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, path: str, method: str = "GET", body: Any = None) -> tuple[int, Any]:
        import urllib.request

        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_health_over_http(self) -> None:
        status, payload = self.request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["service"], "you-api")

    def test_search_over_http(self) -> None:
        self.client.search.return_value = {"results": [{"url": "https://x.com"}]}
        status, payload = self.request("/v1/search?q=test&count=2")
        self.assertEqual(status, 200)
        self.assertEqual(payload["results"][0]["url"], "https://x.com")

    def test_missing_param_returns_400(self) -> None:
        status, payload = self.request("/v1/search")
        self.assertEqual(status, 400)
        self.assertIn("q", payload["error"])

    def test_research_over_http(self) -> None:
        self.client.research.return_value = {"answer": "42"}
        status, payload = self.request(
            "/v1/research", method="POST", body={"question": "meaning?"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["answer"], "42")

    def test_invalid_json_body_returns_400(self) -> None:
        import urllib.request

        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/research",
            data=b"{not json",
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 400)

    def test_upstream_error_maps_status(self) -> None:
        self.client.search.side_effect = YouRateLimitError(
            "too many", status_code=429
        )
        status, payload = self.request("/v1/search?q=x")
        self.assertEqual(status, 429)
        self.assertIn("too many", payload["error"])

    def test_unexpected_error_returns_500(self) -> None:
        self.client.search.side_effect = RuntimeError("boom")
        status, payload = self.request("/v1/search?q=x")
        self.assertEqual(status, 500)
        self.assertIn("boom", payload["error"])


if __name__ == "__main__":
    unittest.main()
