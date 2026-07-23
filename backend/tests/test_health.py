"""
Tests for GET / and GET /health.

Note: these use FastAPI's TestClient which triggers the real lifespan
(so it will attempt to load models/generator_final.pth). If no model
file is present, /health should still respond with model_loaded=false
rather than crashing the app (graceful-degradation behavior in
app.main.lifespan).
"""

from fastapi.testclient import TestClient

from app.main import app


def test_root_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "Anime Generator API"
    assert body["status"] == "running"


def test_health_endpoint_shape() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"status", "model_loaded", "device"}
    assert isinstance(body["model_loaded"], bool)
