"""Every Ball Wins - FastAPI application entrypoint."""

from fastapi import FastAPI

from app import __version__
from app.models import HealthResponse
from app.routes import balls


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="Every Ball Wins",
        description="A FastAPI service where every ball wins a prize.",
        version=__version__,
    )

    app.include_router(balls.router, prefix="/api/v1")

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {"message": "Every Ball Wins!", "docs": "/docs"}

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
