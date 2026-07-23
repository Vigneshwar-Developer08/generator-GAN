"""Response schemas for /generate, /health, and / endpoints."""

from typing import Optional

from pydantic import BaseModel, Field


class GenerateResponse(BaseModel):
    success: bool
    filename: str
    image_url: str
    generation_time_ms: float = Field(description="Wall-clock inference + save time in milliseconds.")
    seed: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str


class RootResponse(BaseModel):
    service: str
    status: str


class ErrorResponse(BaseModel):
    """Consistent error envelope returned by all exception handlers."""

    success: bool = False
    error: str
    detail: str
