import pytest
import requests

BACKEND = "http://127.0.0.1:8002"
VITE = "http://localhost:5173"


def _is_up(url: str) -> bool:
    try:
        requests.get(url, timeout=1)
        return True
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.skipif(not _is_up(BACKEND), reason="Backend não está rodando na porta 8002")
def test_backend_health():
    r = requests.get(f"{BACKEND}/health", timeout=5)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


@pytest.mark.integration
@pytest.mark.skipif(not _is_up(BACKEND), reason="Backend não está rodando na porta 8002")
def test_backend_search():
    r = requests.get(f"{BACKEND}/search", params={"query": "amil"}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("results"), list)


@pytest.mark.skipif(not _is_up(VITE), reason="Vite não está rodando na porta 5173")
def test_proxy_search():
    r = requests.get(f"{VITE}/search", params={"query": "amil"}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("results"), list)
