"""
Tests for POST /generate and GET /generated/{filename}.

A lightweight fake Generator (random weights, same architecture) is
injected via the model_loader singleton so these tests never depend
on a real trained checkpoint being present on disk.
"""

import shutil
from pathlib import Path

import pytest
import torch
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.generator_arch import Generator
from app.core.model_loader import model_loader
from app.main import app


@pytest.fixture(autouse=True)
def _inject_fake_model() -> None:
    """Bypass real checkpoint loading with a randomly-initialized model."""
    settings = get_settings()
    fake_generator = Generator(latent_dim=settings.LATENT_DIM, ngf=settings.NGF, nc=settings.NC)
    fake_generator.eval()
    model_loader._model = fake_generator  # noqa: SLF001 - test-only white-box injection
    model_loader._device = torch.device("cpu")  # noqa: SLF001

    yield

    model_loader._model = None  # noqa: SLF001
    model_loader._device = None  # noqa: SLF001
    generated_dir: Path = settings.generated_dir_resolved
    for f in generated_dir.glob("*.png"):
        f.unlink(missing_ok=True)


def test_generate_without_seed_returns_image() -> None:
    with TestClient(app) as client:
        response = client.post("/generate", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["filename"].endswith(".png")
    assert body["image_url"] == f"/generated/{body['filename']}"
    assert body["generation_time_ms"] > 0


def test_generate_with_seed_is_deterministic() -> None:
    with TestClient(app) as client:
        first = client.post("/generate", json={"seed": 42}).json()
        second = client.post("/generate", json={"seed": 42}).json()

    settings = get_settings()
    first_bytes = (settings.generated_dir_resolved / first["filename"]).read_bytes()
    second_bytes = (settings.generated_dir_resolved / second["filename"]).read_bytes()
    assert first_bytes == second_bytes


def test_get_generated_image_success() -> None:
    with TestClient(app) as client:
        gen = client.post("/generate", json={}).json()
        response = client.get(f"/generated/{gen['filename']}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_get_generated_image_rejects_path_traversal() -> None:
    with TestClient(app) as client:
        response = client.get("/generated/..%2f..%2fetc%2fpasswd")
    assert response.status_code in (400, 404)


def test_get_generated_image_not_found() -> None:
    with TestClient(app) as client:
        response = client.get("/generated/deadbeef.png")
    assert response.status_code == 404
