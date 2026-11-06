"""In-memory storage for balls.

This module provides a simple thread-safe in-memory repository. It can be
swapped for a real database implementation later without touching the
route handlers.
"""

from threading import Lock

from app.models import Ball, BallCreate, BallUpdate


class BallRepository:
    """A simple in-memory repository for balls."""

    def __init__(self) -> None:
        self._balls: dict[int, Ball] = {}
        self._next_id: int = 1
        self._lock = Lock()

    def list(self, color: str | None = None) -> list[Ball]:
        """Return all balls, optionally filtered by color."""
        with self._lock:
            balls = list(self._balls.values())
        if color is not None:
            balls = [b for b in balls if b.color.value == color]
        return balls

    def get(self, ball_id: int) -> Ball | None:
        """Return a ball by id, or None if it does not exist."""
        with self._lock:
            return self._balls.get(ball_id)

    def create(self, payload: BallCreate) -> Ball:
        """Create and store a new ball."""
        with self._lock:
            ball = Ball(id=self._next_id, **payload.model_dump())
            self._balls[ball.id] = ball
            self._next_id += 1
            return ball

    def update(self, ball_id: int, payload: BallUpdate) -> Ball | None:
        """Apply a partial update to a ball. Returns None if not found."""
        with self._lock:
            ball = self._balls.get(ball_id)
            if ball is None:
                return None
            changes = payload.model_dump(exclude_unset=True)
            updated = ball.model_copy(update=changes)
            self._balls[ball_id] = updated
            return updated

    def delete(self, ball_id: int) -> bool:
        """Delete a ball by id. Returns True if it existed."""
        with self._lock:
            return self._balls.pop(ball_id, None) is not None

    def clear(self) -> None:
        """Remove all balls and reset the id counter (useful for tests)."""
        with self._lock:
            self._balls.clear()
            self._next_id = 1


# Module-level singleton used by the app.
repository = BallRepository()
