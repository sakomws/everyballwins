"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage import repository


@pytest.fixture(autouse=True)
def clean_repository():
    """Reset the in-memory repository before each test."""
    repository.clear()
    yield
    repository.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())
