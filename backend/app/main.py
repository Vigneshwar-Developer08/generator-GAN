"""
Application entrypoint.

Run with:
    uvicorn app.main:app --reload

The Generator model is loaded exactly once here, in the lifespan
startup hook, and released on shutdown. All exception -> HTTP status
mapping is centralized below so route handlers can raise plain domain
exceptions (app.core.exceptions) without importing fastapi.responses.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api import health, routes
from app.core.config import get_settings
from app.core.exceptions import (
    AppException,
    ImageGenerationError,
    ImageNotFoundError,
    InvalidFilenameError,
    ModelFileNotFoundError,
    ModelLoadError,
    ModelNotReadyError,
    RateLimitExceededError,
)
from app.core.logging import configure_logging
from app.core.model_loader import model_loader

settings = get_settings()

# Maps each domain exception type to the HTTP status code it represents.
_EXCEPTION_STATUS_MAP: dict[type[AppException], int] = {
    ModelFileNotFoundError: status.HTTP_503_SERVICE_UNAVAILABLE,
    ModelLoadError: status.HTTP_503_SERVICE_UNAVAILABLE,
    ModelNotReadyError: status.HTTP_503_SERVICE_UNAVAILABLE,
    ImageGenerationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    InvalidFilenameError: status.HTTP_400_BAD_REQUEST,
    ImageNotFoundError: status.HTTP_404_NOT_FOUND,
    RateLimitExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("Starting {} v{} [{}]", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)

    try:
        model_loader.load(settings)
    except (ModelFileNotFoundError, ModelLoadError) as exc:
        # Fail loudly but do not crash the process: /health will report
        # model_loaded=false so orchestrators (k8s readiness probes, etc.)
        # can detect and act on the degraded state.
        logger.error("Model failed to load at startup: {}", exc.message)

    yield

    model_loader.unload()
    logger.info("Application shutdown complete.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="REST API serving a pre-trained DCGAN generator for anime face images.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials="*" not in settings.CORS_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(routes.router)

    for exc_type, http_status in _EXCEPTION_STATUS_MAP.items():
        app.add_exception_handler(exc_type, _make_handler(http_status))

    return app


def _make_handler(http_status: int):
    async def handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning("{} on {} -> {}: {}", exc.__class__.__name__, request.url.path, http_status, exc.message)
        return JSONResponse(
            status_code=http_status,
            content={
                "success": False,
                "error": exc.__class__.__name__,
                "detail": exc.message,
            },
        )

    return handler


app = create_app()
