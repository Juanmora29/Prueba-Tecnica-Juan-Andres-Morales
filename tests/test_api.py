from fastapi.testclient import TestClient

from backend.main import app


def test_health_returns_ok():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "chunks_count" in data


def test_ask_empty_question():
    with TestClient(app) as client:
        resp = client.post("/ask", json={"question": ""})
        assert resp.status_code == 400
        assert "vacía" in resp.json()["detail"]


def test_ask_missing_question():
    with TestClient(app) as client:
        resp = client.post("/ask", json={})
        assert resp.status_code == 422


def test_ask_returns_valid_response():
    with TestClient(app) as client:
        resp = client.post("/ask", json={"question": "Hola"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "sources" in data


def test_ingest_endpoint():
    with TestClient(app) as client:
        resp = client.post("/ingest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "chunks_indexed" in data
