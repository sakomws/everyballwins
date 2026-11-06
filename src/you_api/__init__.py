"""you-api: a small API service and client for the You.com platform APIs."""

from .client import DEFAULT_BASE_URL, YouClient
from .exceptions import (
    YouAPIError,
    YouAuthenticationError,
    YouNotFoundError,
    YouPermissionError,
    YouRateLimitError,
    YouServerError,
)
from .http import HTTPResponse, Transport, UrllibTransport
from .service import YouAPIService, make_handler, main

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_BASE_URL",
    "HTTPResponse",
    "Transport",
    "UrllibTransport",
    "YouAPIError",
    "YouAPIService",
    "YouAuthenticationError",
    "YouClient",
    "YouNotFoundError",
    "YouPermissionError",
    "YouRateLimitError",
    "YouServerError",
    "__version__",
    "main",
    "make_handler",
]
