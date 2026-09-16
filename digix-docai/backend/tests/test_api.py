from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_rejects_unsupported_type():
    r = client.post("/api/v1/documents/analyze",
                    files={"file": ("test.txt", b"hello", "text/plain")})
    assert r.status_code == 415
