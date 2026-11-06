"""Minimal HTTP transport built on the standard library.

The transport is deliberately small so the service has no third-party
dependencies. Any object implementing the :class:`Transport` protocol can be
injected into the client (useful for testing or for plugging in ``requests``).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class HTTPResponse:
    """A normalised HTTP response."""

    status_code: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)

    def json(self) -> object:
        """Decode the body as JSON, or return an empty mapping if empty."""
        if not self.body:
            return {}
        return json.loads(self.body.decode("utf-8"))

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


@runtime_checkable
class Transport(Protocol):
    """Protocol implemented by HTTP transports."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, str] | None = None,
        json_body: object | None = None,
        timeout: float,
    ) -> HTTPResponse:
        ...


class UrllibTransport:
    """Default :class:`Transport` backed by :mod:`urllib`."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, str] | None = None,
        json_body: object | None = None,
        timeout: float,
    ) -> HTTPResponse:
        from urllib.parse import urlencode

        if params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(params)}"

        data: bytes | None = None
        request_headers = dict(headers)
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")

        req = urllib.request.Request(
            url, data=data, headers=request_headers, method=method.upper()
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return HTTPResponse(
                    status_code=resp.status,
                    body=resp.read(),
                    headers=dict(resp.headers.items()),
                )
        except urllib.error.HTTPError as exc:  # non-2xx responses
            return HTTPResponse(
                status_code=exc.code,
                body=exc.read() if exc.fp is not None else b"",
                headers=dict(exc.headers.items()) if exc.headers else {},
            )
