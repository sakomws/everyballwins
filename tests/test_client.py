"""Unit tests for the You.com API client using a stub transport."""

from __future__ import annotations

import json
import os
import unittest
from typing import Any, Mapping, Optional

from you_api import (
    YouAPIError,
    YouAuthenticationError,
    YouClient,
    YouNotFoundError,
    YouPermissionError,
    YouRateLimitError,
    YouServerError,
)
from you_api.http import HTTPResponse


class StubTransport:
    """Records requests and returns canned responses."""

    def __init__(self, responses: list[HTTPResponse]) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Optional[Mapping[str, str]] = None,
        json_body: Any = None,
        timeout: float,
    ) -> HTTPResponse:
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "params": dict(params or {}),
                "json_body": json_body,
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise AssertionError("StubTransport received more requests than expected")
        return self.responses.pop(0)


def json_response(status: int, payload: Any) -> HTTPResponse:
    return HTTPResponse(
        status_code=status,
        body=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


class ClientRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop("YOU_API_KEY", None)

    def make_client(self, *responses: HTTPResponse) -> tuple[YouClient, StubTransport]:
        transport = StubTransport(list(responses))
        client = YouClient(api_key="test-key", transport=transport, timeout=5.0)
        return client, transport

    def test_search_sends_expected_request(self) -> None:
        client, transport = self.make_client(json_response(200, {"results": []}))
        result = client.search(
            "python news",
            count=5,
            offset=10,
            country="US",
            language="en",
            safesearch="moderate",
            freshness="day",
            include_domains=["example.com", "docs.python.org"],
            exclude_domains=["spam.example"],
            livecrawl="web",
        )
        self.assertEqual(result, {"results": []})

        (req,) = transport.requests
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"], "https://api.you.com/v1/search")
        self.assertEqual(req["headers"]["X-API-Key"], "test-key")
        self.assertEqual(req["headers"]["Accept"], "application/json")
        self.assertEqual(req["timeout"], 5.0)
        self.assertEqual(
            req["params"],
            {
                "query": "python news",
                "count": "5",
                "offset": "10",
                "country": "US",
                "language": "en",
                "safesearch": "moderate",
                "freshness": "day",
                "include_domains": "example.com,docs.python.org",
                "exclude_domains": "spam.example",
                "livecrawl": "web",
            },
        )

    def test_search_omits_none_params(self) -> None:
        client, transport = self.make_client(json_response(200, {}))
        client.search("hello")
        (req,) = transport.requests
        self.assertEqual(req["params"], {"query": "hello"})

    def test_news_uses_v1_news(self) -> None:
        client, transport = self.make_client(json_response(200, {"news": []}))
        result = client.news("ai", spellcheck=True)
        self.assertEqual(result, {"news": []})
        (req,) = transport.requests
        self.assertEqual(req["url"], "https://api.you.com/v1/news")
        self.assertEqual(req["params"]["spellcheck"], "true")

    def test_news_falls_back_to_legacy_route_on_404(self) -> None:
        client, transport = self.make_client(
            json_response(404, {"message": "not found"}),
            json_response(200, {"news": [{"title": "x"}]}),
        )
        result = client.news("ai")
        self.assertEqual(result["news"], [{"title": "x"}])
        self.assertEqual(len(transport.requests), 2)
        self.assertEqual(transport.requests[0]["url"], "https://api.you.com/v1/news")
        self.assertEqual(
            transport.requests[1]["url"], "https://api.you.com/v1/news-search"
        )

    def test_content_snippets(self) -> None:
        client, transport = self.make_client(json_response(200, {"snippets": []}))
        client.content_snippets(["https://a.example", "https://b.example"])
        (req,) = transport.requests
        self.assertEqual(req["url"], "https://api.you.com/v1/content-snippets")
        self.assertEqual(req["params"]["urls"], "https://a.example,https://b.example")

    def test_content_snippets_validates_urls(self) -> None:
        client, _ = self.make_client()
        with self.assertRaises(ValueError):
            client.content_snippets([])
        with self.assertRaises(ValueError):
            client.content_snippets([f"https://{i}.example" for i in range(11)])

    def test_research_posts_payload(self) -> None:
        client, transport = self.make_client(json_response(200, {"answer": "42"}))
        result = client.research("meaning of life", model="agent")
        self.assertEqual(result, {"answer": "42"})
        (req,) = transport.requests
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["url"], "https://api.you.com/v1/research")
        self.assertEqual(
            req["json_body"],
            {"question": "meaning of life", "stream": False, "model": "agent"},
        )

    def test_run_agent_posts_payload(self) -> None:
        client, transport = self.make_client(json_response(200, {"output": "done"}))
        result = client.run_agent(
            "research", input={"query": "q"}, stream=True, extra={"mode": "fast"}
        )
        self.assertEqual(result, {"output": "done"})
        (req,) = transport.requests
        self.assertEqual(req["url"], "https://api.you.com/v1/agents/runs")
        self.assertEqual(
            req["json_body"],
            {
                "agent": "research",
                "input": {"query": "q"},
                "stream": True,
                "mode": "fast",
            },
        )

    def test_base_url_trailing_slash_is_trimmed(self) -> None:
        transport = StubTransport([json_response(200, {})])
        client = YouClient(
            api_key="k", base_url="https://proxy.example/", transport=transport
        )
        client.search("x")
        self.assertEqual(
            transport.requests[0]["url"], "https://proxy.example/v1/search"
        )

    def test_api_key_from_environment(self) -> None:
        os.environ["YOU_API_KEY"] = "env-key"
        try:
            transport = StubTransport([json_response(200, {})])
            client = YouClient(transport=transport)
            client.search("x")
            self.assertEqual(
                transport.requests[0]["headers"]["X-API-Key"], "env-key"
            )
        finally:
            os.environ.pop("YOU_API_KEY", None)

    def test_missing_api_key_raises(self) -> None:
        client = YouClient(api_key=None, transport=StubTransport([]))
        with self.assertRaises(YouAuthenticationError):
            client.search("x")


class ClientErrorTests(unittest.TestCase):
    def make_client(self, status: int, payload: Any) -> YouClient:
        transport = StubTransport([json_response(status, payload)])
        return YouClient(api_key="k", transport=transport)

    def test_401_raises_authentication_error(self) -> None:
        client = self.make_client(401, {"message": "bad key"})
        with self.assertRaises(YouAuthenticationError) as ctx:
            client.search("x")
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("bad key", str(ctx.exception))

    def test_403_raises_permission_error(self) -> None:
        client = self.make_client(403, {"message": "forbidden"})
        with self.assertRaises(YouPermissionError):
            client.search("x")

    def test_404_raises_not_found(self) -> None:
        client = self.make_client(404, {"message": "missing"})
        with self.assertRaises(YouNotFoundError):
            client.search("x")

    def test_429_raises_rate_limit(self) -> None:
        client = self.make_client(429, {"error": {"message": "slow down"}})
        with self.assertRaises(YouRateLimitError) as ctx:
            client.search("x")
        self.assertIn("slow down", str(ctx.exception))

    def test_500_raises_server_error(self) -> None:
        client = self.make_client(500, {"message": "boom"})
        with self.assertRaises(YouServerError):
            client.search("x")

    def test_other_error_raises_generic(self) -> None:
        client = self.make_client(400, {"message": "bad request"})
        with self.assertRaises(YouAPIError):
            client.search("x")

    def test_invalid_json_raises(self) -> None:
        transport = StubTransport([HTTPResponse(status_code=200, body=b"not-json")])
        client = YouClient(api_key="k", transport=transport)
        with self.assertRaises(YouAPIError):
            client.search("x")

    def test_non_dict_success_is_wrapped(self) -> None:
        client = self.make_client(200, ["a", "b"])
        result = client.search("x")
        self.assertEqual(result, {"data": ["a", "b"]})


if __name__ == "__main__":
    unittest.main()
