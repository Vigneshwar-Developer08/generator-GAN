"""Image generation and retrieval endpoints."""

import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from loguru import logger

from app.api.health import get_model_loader
from app.core.config import Settings, get_settings
from app.core.exceptions import ImageNotFoundError, RateLimitExceededError
from app.core.model_loader import ModelLoader
from app.core.rate_limiter import RateLimiter
from app.schemas.generate_request import GenerateRequest
from app.schemas.generate_response import GenerateResponse
from app.services.generator_service import GeneratorService

router = APIRouter(tags=["generation"])

# Bounds concurrent GPU/CPU-bound inference calls regardless of how many
# HTTP requests arrive simultaneously (protects memory + latency).
_generation_semaphore: asyncio.Semaphore | None = None
_rate_limiter: RateLimiter | None = None


def get_generation_semaphore(settings: Settings = Depends(get_settings)) -> asyncio.Semaphore:
    global _generation_semaphore
    if _generation_semaphore is None:
        _generation_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_GENERATIONS)
    return _generation_semaphore


def get_rate_limiter(settings: Settings = Depends(get_settings)) -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(max_requests=settings.RATE_LIMIT_PER_MINUTE, window_seconds=60)
    return _rate_limiter


def get_generator_service(
    settings: Settings = Depends(get_settings),
    loader: ModelLoader = Depends(get_model_loader),
) -> GeneratorService:
    return GeneratorService(model_loader=loader, settings=settings)


@router.post("/generate", response_model=GenerateResponse)
async def generate_image(
    request: Request,
    payload: GenerateRequest,
    service: GeneratorService = Depends(get_generator_service),
    semaphore: asyncio.Semaphore = Depends(get_generation_semaphore),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> GenerateResponse:
    client_key = request.client.host if request.client else "unknown"
    if not limiter.allow(client_key):
        logger.warning("Rate limit exceeded for client={}", client_key)
        raise RateLimitExceededError(
            "Too many generation requests. Please slow down and try again shortly."
        )

    async with semaphore:
        # torch inference is CPU/GPU-bound and synchronous; run it in a
        # worker thread so it never blocks the asyncio event loop.
        return await asyncio.to_thread(service.generate_image, payload.seed)


@router.get("/generated/{filename}")
async def get_generated_image(
    filename: str,
    service: GeneratorService = Depends(get_generator_service),
) -> FileResponse:
    file_path = service.resolve_image_path(filename)
    if not file_path.exists():
        raise ImageNotFoundError(f"Generated image '{filename}' does not exist.")
    return FileResponse(path=file_path, media_type="image/png", filename=filename)
