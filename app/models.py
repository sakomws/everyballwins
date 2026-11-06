"""Pydantic models for the Every Ball Wins API."""

from enum import Enum

from pydantic import BaseModel, Field


class BallColor(str, Enum):
    """Available ball colors."""

    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    GOLD = "gold"
    SILVER = "silver"


class BallBase(BaseModel):
    """Shared attributes of a ball."""

    name: str = Field(..., min_length=1, max_length=100, examples=["Lucky 7"])
    color: BallColor = Field(..., examples=[BallColor.GOLD])
    prize: str = Field(..., min_length=1, max_length=200, examples=["Jackpot"])


class BallCreate(BallBase):
    """Payload for creating a new ball."""


class BallUpdate(BaseModel):
    """Payload for partially updating a ball. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: BallColor | None = None
    prize: str | None = Field(default=None, min_length=1, max_length=200)


class Ball(BallBase):
    """A ball as stored and returned by the API."""

    id: int = Field(..., examples=[1])


class HealthResponse(BaseModel):
    """Response body for the health check endpoint."""

    status: str = Field(..., examples=["ok"])
    version: str = Field(..., examples=["0.1.0"])
