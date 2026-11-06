"""A simple REST API service built with FastAPI.

Provides a small in-memory item store with CRUD endpoints plus
root and health-check routes.

Run with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from itertools import count
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="everyballwins API",
    description="A simple API service with an in-memory item store.",
    version="1.0.0",
)


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
class Item(BaseModel):
    """An item stored in the service."""

    id: int
    name: str
    description: Optional[str] = None
    price: float = Field(ge=0)
    tags: list[str] = []


class ItemCreate(BaseModel):
    """Payload for creating an item."""

    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    price: float = Field(ge=0)
    tags: list[str] = []


class ItemUpdate(BaseModel):
    """Payload for partially updating an item (all fields optional)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    price: Optional[float] = Field(default=None, ge=0)
    tags: Optional[list[str]] = None


# --------------------------------------------------------------------------
# In-memory storage
# --------------------------------------------------------------------------
_items: dict[int, Item] = {}
_id_counter = count(1)


def reset_store() -> None:
    """Clear all items and reset the id counter (useful for tests)."""
    global _id_counter
    _items.clear()
    _id_counter = count(1)


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.get("/")
def read_root() -> dict[str, str]:
    """Service info."""
    return {"service": "everyballwins API", "version": app.version, "docs": "/docs"}


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/items", response_model=list[Item])
def list_items(
    q: Optional[str] = Query(default=None, description="Filter by name substring"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[Item]:
    """List all items, optionally filtered by a name substring."""
    items = sorted(_items.values(), key=lambda item: item.id)
    if q is not None:
        items = [item for item in items if q.lower() in item.name.lower()]
    return items[offset : offset + limit]


@app.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate) -> Item:
    """Create a new item."""
    item = Item(id=next(_id_counter), **payload.model_dump())
    _items[item.id] = item
    return item


@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int) -> Item:
    """Get a single item by id."""
    item = _items.get(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found",
        )
    return item


@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, payload: ItemUpdate) -> Item:
    """Partially update an existing item."""
    item = _items.get(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found",
        )
    changes: dict[str, Any] = payload.model_dump(exclude_unset=True)
    updated = item.model_copy(update=changes)
    _items[item_id] = updated
    return updated


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int) -> None:
    """Delete an item by id."""
    if item_id not in _items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found",
        )
    del _items[item_id]
