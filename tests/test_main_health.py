def test_main_health():
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
