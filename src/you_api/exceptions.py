"""Exception hierarchy for the You.com API service."""

from __future__ import annotations


class YouAPIError(Exception):
    """Base error raised for You.com API failures.

    Attributes:
        message: Human readable error description.
        status_code: HTTP status code returned by the API, if any.
        body: Raw response body returned by the API, if any.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        body: object | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.status_code is not None:
            return f"[{self.status_code}] {self.message}"
        return self.message


class YouAuthenticationError(YouAPIError):
    """Raised when the API key is missing, invalid, or expired (HTTP 401)."""


class YouPermissionError(YouAPIError):
    """Raised when the API key lacks access to the endpoint (HTTP 403)."""


class YouNotFoundError(YouAPIError):
    """Raised when the requested resource does not exist (HTTP 404)."""


class YouRateLimitError(YouAPIError):
    """Raised when the request is rate limited (HTTP 429)."""


class YouServerError(YouAPIError):
    """Raised for server-side failures (HTTP 5xx)."""
