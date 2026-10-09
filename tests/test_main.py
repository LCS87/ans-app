"""Smoke test legado — usa TestClient real sobre create_app()."""

from fastapi.testclient import TestClient

from api.main import create_app


def test_health_check():
    app = create_app()
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] in ("ok", "degraded")
