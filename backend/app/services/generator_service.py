"""
Service layer: orchestrates latent-noise creation, model inference,
tensor->image conversion, and saving to disk.

Kept separate from the API layer (routes.py) so the same generation
logic could later be reused by a CLI script, a batch job, or a
websocket endpoint without duplicating code (separation of concerns).
"""

import time
from pathlib import Path
from typing import Optional

import torch
from loguru import logger

from app.core.config import Settings
from app.core.exceptions import ImageGenerationError
from app.core.model_loader import ModelLoader
from app.schemas.generate_response import GenerateResponse
from app.utils.image_utils import generate_filename, save_image, tensor_to_image


class GeneratorService:
    """Stateless-per-call wrapper around a loaded Generator model."""

    def __init__(self, model_loader: ModelLoader, settings: Settings) -> None:
        self._model_loader = model_loader
        self._settings = settings

    def generate_image(self, seed: Optional[int] = None) -> GenerateResponse:
        """
        Run one forward pass through the generator and persist the result.

        Thread safety: the model_loader's lock serializes access to the
        shared nn.Module + RNG state. PyTorch modules in eval() mode are
        safe to *read* concurrently, but sharing torch.manual_seed()
        across concurrent requests is not, so we serialize the whole
        generate+seed critical section rather than only the forward pass.
        """
        start = time.perf_counter()
        device = self._model_loader.get_device()
        model = self._model_loader.get_model()

        with self._model_loader.lock:
            try:
                if seed is not None:
                    torch.manual_seed(seed)

                noise = torch.randn(
                    1, self._settings.LATENT_DIM, 1, 1, device=device
                )

                with torch.inference_mode():  # stricter & faster than no_grad for pure inference
                    output = model(noise)

                image = tensor_to_image(output)
            except Exception as exc:  # noqa: BLE001
                logger.error("Image generation failed: {}", exc)
                raise ImageGenerationError(f"Failed to generate image: {exc}") from exc

        filename = generate_filename()
        try:
            save_image(image, filename, self._settings.generated_dir_resolved, self._settings.IMAGE_FORMAT)
        except OSError as exc:
            logger.error("Failed to save generated image '{}': {}", filename, exc)
            raise ImageGenerationError(f"Failed to save generated image: {exc}") from exc

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Generated image '{}' | seed={} | device={} | time={:.2f}ms",
            filename, seed, device, elapsed_ms,
        )

        return GenerateResponse(
            success=True,
            filename=filename,
            image_url=f"/generated/{filename}",
            generation_time_ms=round(elapsed_ms, 2),
            seed=seed,
        )

    def resolve_image_path(self, filename: str) -> Path:
        from app.utils.image_utils import resolve_safe_path

        return resolve_safe_path(filename, self._settings.generated_dir_resolved)
