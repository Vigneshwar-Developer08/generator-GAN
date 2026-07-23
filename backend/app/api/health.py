"""GET / and GET /health endpoints."""

from fastapi import APIRouter, Depends

from app.core.model_loader import ModelLoader, model_loader
from app.schemas.generate_response import HealthResponse, RootResponse

router = APIRouter(tags=["health"])


def get_model_loader() -> ModelLoader:
    """Dependency accessor for the process-wide model loader singleton."""
    return model_loader


@router.get("/", response_model=RootResponse)
def root() -> RootResponse:
    return RootResponse(service="Anime Generator API", status="running")


@router.get("/health", response_model=HealthResponse)
def health(loader: ModelLoader = Depends(get_model_loader)) -> HealthResponse:
    device = str(loader.get_device()) if loader.is_loaded else "unavailable"
    return HealthResponse(
        status="healthy" if loader.is_loaded else "degraded",
        model_loaded=loader.is_loaded,
        device=device,
    )
