"""CRUD endpoints for balls."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models import Ball, BallColor, BallCreate, BallUpdate
from app.storage import BallRepository, repository

router = APIRouter(prefix="/balls", tags=["balls"])


def get_repository() -> BallRepository:
    """Dependency providing the ball repository (overridable in tests)."""
    return repository


@router.get(
    "",
    response_model=list[Ball],
    summary="List balls",
)
def list_balls(
    color: BallColor | None = Query(default=None, description="Filter by color"),
    repo: BallRepository = Depends(get_repository),
) -> list[Ball]:
    """Return all balls, optionally filtered by color."""
    return repo.list(color=color.value if color else None)


@router.post(
    "",
    response_model=Ball,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ball",
)
def create_ball(
    payload: BallCreate,
    repo: BallRepository = Depends(get_repository),
) -> Ball:
    """Create a new ball. Every ball wins a prize!"""
    return repo.create(payload)


@router.get(
    "/{ball_id}",
    response_model=Ball,
    summary="Get a ball",
)
def get_ball(
    ball_id: int,
    repo: BallRepository = Depends(get_repository),
) -> Ball:
    """Return a single ball by id."""
    ball = repo.get(ball_id)
    if ball is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ball {ball_id} not found",
        )
    return ball


@router.patch(
    "/{ball_id}",
    response_model=Ball,
    summary="Update a ball",
)
def update_ball(
    ball_id: int,
    payload: BallUpdate,
    repo: BallRepository = Depends(get_repository),
) -> Ball:
    """Partially update a ball by id."""
    ball = repo.update(ball_id, payload)
    if ball is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ball {ball_id} not found",
        )
    return ball


@router.delete(
    "/{ball_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a ball",
)
def delete_ball(
    ball_id: int,
    repo: BallRepository = Depends(get_repository),
) -> None:
    """Delete a ball by id."""
    if not repo.delete(ball_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ball {ball_id} not found",
        )
