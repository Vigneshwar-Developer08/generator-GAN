"""
Centralized application configuration.

Loads settings from environment variables / .env file using
pydantic-settings, so the same codebase can run unchanged across
local, staging, and production environments (12-factor app style).
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing_extensions import Annotated

# Project root: backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Strongly typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App metadata ---
    APP_NAME: str = "Anime Generator API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = False

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- CORS ---
    # NoDecode: pydantic-settings would otherwise try to JSON-decode this
    # env var as a list *before* our validator runs. We accept a plain
    # comma-separated string (e.g. "https://a.com,https://b.com") instead.
    CORS_ORIGINS: Annotated[List[str], NoDecode] = ["*"]

    # --- Model ---
    MODEL_PATH: str = "models/generator_final.pth"
    LATENT_DIM: int = 100
    NGF: int = 64  # generator feature map depth
    NC: int = 3  # output channels (RGB)
    FORCE_CPU: bool = False  # override CUDA auto-detection for testing

    # --- Storage ---
    GENERATED_DIR: str = "app/generated"
    IMAGE_FORMAT: str = "PNG"

    # --- Rate limiting / concurrency ---
    MAX_CONCURRENT_GENERATIONS: int = 2
    RATE_LIMIT_PER_MINUTE: int = 20

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        """Allow CORS_ORIGINS to be provided as a comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def model_path_resolved(self) -> Path:
        return (BASE_DIR / self.MODEL_PATH).resolve()

    @property
    def generated_dir_resolved(self) -> Path:
        path = (BASE_DIR / self.GENERATED_DIR).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def log_dir_resolved(self) -> Path:
        path = (BASE_DIR / self.LOG_DIR).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings accessor.

    Using lru_cache means Settings() is constructed only once per
    process and can be safely injected via FastAPI's Depends().
    """
    return Settings()
