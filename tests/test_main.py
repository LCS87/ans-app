import pytest
from api.main import create_app

@pytest.fixture
def client():
    app = create_app()
    return app

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
