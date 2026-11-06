"""Typed client for the You.com platform APIs.

The client covers the public You.com API surface available at
``https://api.you.com``:

* **Search**           — ``GET /v1/search``
* **News search**      — ``GET /v1/news`` (fallback: ``GET /v1/news-search``)
* **Content snippets** — ``GET /v1/content-snippets``
* **Research agent**   — ``POST /v1/research``
* **Agents**           — ``POST /v1/agents/runs``
"""

from __future__ import annotations

import os
from typing import Any, Iterable, Mapping, Optional, Sequence

from .exceptions import (
    YouAPIError,
    YouAuthenticationError,
    YouNotFoundError,
    YouPermissionError,
    YouRateLimitError,
    YouServerError,
)
from .http import HTTPResponse, Transport, UrllibTransport

DEFAULT_BASE_URL = "https://api.you.com"
API_KEY_ENV_VAR = "YOU_API_KEY"
USER_AGENT = "you-api-python/0.1.0"


def _normalise_domains(domains: Optional[Iterable[str]]) -> Optional[str]:
    if domains is None:
        return None
    return ",".join(d.strip() for d in domains if d and d.strip())


class YouClient:
    """Synchronous client for the You.com API.

    Args:
        api_key: You.com API key. Falls back to the ``YOU_API_KEY``
            environment variable when omitted.
        base_url: API base URL (override for testing/proxies).
        timeout: Request timeout in seconds.
        transport: Custom :class:`~you_api.http.Transport` implementation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        transport: Optional[Transport] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get(API_KEY_ENV_VAR)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport: Transport = transport if transport is not None else UrllibTransport()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        *,
        count: Optional[int] = None,
        offset: Optional[int] = None,
        country: Optional[str] = None,
        language: Optional[str] = None,
        safesearch: Optional[str] = None,
        freshness: Optional[str] = None,
        include_domains: Optional[Iterable[str]] = None,
        exclude_domains: Optional[Iterable[str]] = None,
        livecrawl: Optional[str] = None,
    ) -> dict[str, Any]:
        """Run a web search via ``GET /v1/search``."""
        params = self._clean_params(
            {
                "query": query,
                "count": count,
                "offset": offset,
                "country": country,
                "language": language,
                "safesearch": safesearch,
                "freshness": freshness,
                "include_domains": _normalise_domains(include_domains),
                "exclude_domains": _normalise_domains(exclude_domains),
                "livecrawl": livecrawl,
            }
        )
        return self._request_json("GET", "/v1/search", params=params)

    def news(
        self,
        query: str,
        *,
        count: Optional[int] = None,
        offset: Optional[int] = None,
        country: Optional[str] = None,
        language: Optional[str] = None,
        safesearch: Optional[str] = None,
        spellcheck: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Search news articles.

        Uses ``GET /v1/news`` and falls back to the legacy
        ``GET /v1/news-search`` route when the former returns 404.
        """
        params = self._clean_params(
            {
                "query": query,
                "count": count,
                "offset": offset,
                "country": country,
                "language": language,
                "safesearch": safesearch,
                "spellcheck": spellcheck,
            }
        )
        try:
            return self._request_json("GET", "/v1/news", params=params)
        except YouNotFoundError:
            return self._request_json("GET", "/v1/news-search", params=params)

    def content_snippets(self, urls: Sequence[str]) -> dict[str, Any]:
        """Fetch extracted snippets for up to ten URLs."""
        if not urls:
            raise ValueError("urls must contain at least one URL")
        if len(urls) > 10:
            raise ValueError("content_snippets accepts at most 10 URLs")
        return self._request_json(
            "GET", "/v1/content-snippets", params={"urls": ",".join(urls)}
        )

    def research(
        self,
        question: str,
        *,
        instructions: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Submit a research job via ``POST /v1/research``."""
        payload: dict[str, Any] = {"question": question, "stream": stream}
        if instructions:
            payload["instructions"] = instructions
        if model:
            payload["model"] = model
        return self._request_json("POST", "/v1/research", json_body=payload)

    def run_agent(
        self,
        agent: str,
        *,
        input: Any,
        stream: bool = False,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        """Run a You.com agent via ``POST /v1/agents/runs``."""
        payload: dict[str, Any] = {"agent": agent, "input": input, "stream": stream}
        if extra:
            payload.update(extra)
        return self._request_json("POST", "/v1/agents/runs", json_body=payload)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _clean_params(params: Mapping[str, Any]) -> dict[str, str]:
        cleaned: dict[str, str] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, bool):
                cleaned[key] = "true" if value else "false"
            else:
                cleaned[key] = str(value)
        return cleaned

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, str]] = None,
        json_body: Any = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise YouAuthenticationError(
                "A You.com API key is required. Pass `api_key` to YouClient or "
                f"set the {API_KEY_ENV_VAR} environment variable."
            )

        url = f"{self.base_url}{path}"
        response = self._transport.request(
            method,
            url,
            headers=self._headers(),
            params=params,
            json_body=json_body,
            timeout=self.timeout,
        )
        return self._handle_response(response)

    @staticmethod
    def _handle_response(response: HTTPResponse) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise YouAPIError(
                "Failed to decode JSON response from You.com",
                status_code=response.status_code,
                body=response.body[:500],
            ) from exc

        if response.ok:
            if isinstance(data, dict):
                return data
            return {"data": data}

        message = YouClient._extract_error_message(data)
        status = response.status_code
        if status == 401:
            raise YouAuthenticationError(message, status_code=status, body=data)
        if status == 403:
            raise YouPermissionError(message, status_code=status, body=data)
        if status == 404:
            raise YouNotFoundError(message, status_code=status, body=data)
        if status == 429:
            raise YouRateLimitError(message, status_code=status, body=data)
        if 500 <= status < 600:
            raise YouServerError(message, status_code=status, body=data)
        raise YouAPIError(message, status_code=status, body=data)

    @staticmethod
    def _extract_error_message(data: object) -> str:
        if isinstance(data, dict):
            for key in ("message", "error", "detail"):
                value = data.get(key)
                if isinstance(value, str) and value:
                    return value
            error = data.get("error")
            if isinstance(error, dict):
                value = error.get("message")
                if isinstance(value, str) and value:
                    return value
        return "You.com API request failed"
