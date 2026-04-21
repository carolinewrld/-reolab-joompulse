from __future__ import annotations

from fastapi.testclient import TestClient

from joompulse.api.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "version" in body
