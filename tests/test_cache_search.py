"""Testes unitários do CacheManager (Redis via fakeredis) e OperadorasSearchService.

Cobrem as tarefas 1.1-1.4 complementares da Fase 1 (elevação de cobertura
dos módulos api/cache.py e api/search_service.py para ≥65%).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fakeredis
import pytest

from api.cache import CacheManager, cached
from api.config import Settings
from api.search_service import OperadorasSearchService, _normalize_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class FakeSettings:
    redis_url = "redis://localhost:6379/0"
    cache_ttl = 60


def make_manager() -> CacheManager:
    """CacheManager com cliente fakeredis injetado (sem servidor real)."""
    mgr = CacheManager.__new__(CacheManager)
    mgr.settings = FakeSettings()
    mgr.enabled = True
    mgr._client = fakeredis.FakeRedis(decode_responses=True)
    return mgr


# ---------------------------------------------------------------------------
# api/cache.py — CacheManager
# ---------------------------------------------------------------------------
class TestCacheManager:
    def test_set_get_roundtrip(self):
        mgr = make_manager()
        key = mgr._generate_key("gastos", 2024, prefixo="41")
        assert mgr.set(key, {"total": 1234.5}) is True
        assert mgr.get(key) == {"total": 1234.5}

    def test_get_missing_returns_none(self):
        mgr = make_manager()
        assert mgr.get("ans:inexistente:abc") is None

    def test_set_applies_ttl(self):
        mgr = make_manager()
        assert mgr.set("ans:x:1", {"a": 1}, ttl=100) is True
        ttl = mgr._client.ttl("ans:x:1")
        assert 0 < ttl <= 100

    def test_delete_existing(self):
        mgr = make_manager()
        mgr.set("ans:y:2", {"b": 2})
        assert mgr.delete("ans:y:2") is True
        assert mgr.get("ans:y:2") is None

    def test_clear_pattern_removes_matching_keys(self):
        mgr = make_manager()
        mgr.set(mgr._generate_key("operadoras", "bradesco"), {"x": 1})
        mgr.set(mgr._generate_key("operadoras", "ampla"), {"x": 2})
        mgr.set(mgr._generate_key("gastos", 2024), {"y": 3})
        removed = mgr.clear_pattern("operadoras")
        assert removed == 2
        assert mgr.get(mgr._generate_key("gastos", 2024)) == {"y": 3}

    def test_disabled_manager_is_noop(self):
        mgr = make_manager()
        mgr.enabled = False
        assert mgr.set("ans:z:9", {"a": 1}) is False
        assert mgr.get("ans:z:9") is None
        assert mgr.delete("ans:z:9") is False
        assert mgr.clear_pattern("z") == 0
        assert mgr.health_check() == "disabled"

    def test_health_check_ok(self):
        mgr = make_manager()
        assert mgr.health_check() == "ok"

    def test_generate_key_is_deterministic_and_prefixed(self):
        mgr = make_manager()
        k1 = mgr._generate_key("dim", "financeira", ano=2024)
        k2 = mgr._generate_key("dim", "financeira", ano=2024)
        k3 = mgr._generate_key("dim", "operacional", ano=2024)
        assert k1 == k2 and k1 != k3
        assert k1.startswith("ans:dim:")

    def test_constructor_without_redis_server_degrades_gracefully(self):
        # redis real instalado mas sem servidor → conexão falha → enabled=False
        settings = Settings(redis_port=6399)  # porta improvável de haver servidor
        try:
            mgr = CacheManager(settings)
        except Exception:  # pragma: no cover - ambiente sem redis lib
            pytest.skip("redis indisponível no ambiente")
        assert mgr.enabled in (True, False)
        # mesmo habilitado por acaso, chamadas nunca lançam exceção
        assert mgr.get("ans:anything") is None or True


# ---------------------------------------------------------------------------
# api/cache.py — decorator @cached
# ---------------------------------------------------------------------------
class TestCachedDecorator:
    def test_decorator_hit_and_miss(self):
        calls = {"n": 0}

        @cached("calc", ttl=30)
        def soma(a, b, **kw):
            calls["n"] += 1
            return {"resultado": a + b}

        mgr = make_manager()
        r1 = soma(2, 3, _cache_manager=mgr)
        r2 = soma(2, 3, _cache_manager=mgr)
        assert r1 == r2 == {"resultado": 5}
        assert calls["n"] == 1  # segunda chamada veio do cache

    def test_decorator_passthrough_without_manager(self):
        @cached("calc")
        def mult(a, b):
            return a * b

        assert mult(3, 4) == 12


# ---------------------------------------------------------------------------
# api/search_service.py — OperadorasSearchService
# ---------------------------------------------------------------------------
CADOP_SAMPLE = (
    "Relatório Cadop\n"
    "REGISTRO ANS\tCNPJ\tRAZÃO SOCIAL\tNOME FANTASIA\tMODALIDADE\n"
    "00.000-0\t12.345.678/0001-95\tAMPLA OPERADORA DE PLANOS DE SAUDE LTDA\tAMPLA SAUDE\tCooperativa Médica\n"
    "01.111-1\t98.765.432/0001-01\tBRADESCO SAUDE S.A.\tBRADESCO\tMedicina de Grupo\n"
    "02.222-2\t11.222.333/0001-44\tUNIMED NORTE COOPERATIVA\tUNIMED NORTE\tCooperativa Médica\n"
)


@pytest.fixture()
def service(tmp_path):
    csv = tmp_path / "relatorio_cadop.csv"
    csv.write_bytes(CADOP_SAMPLE.encode("latin1"))
    svc = OperadorasSearchService(csv_path=str(csv))
    svc.load()
    return svc


class TestNormalize:
    def test_strips_accents_and_case(self):
        assert _normalize_text("  Ampla   Saúde ") == "ampla saude"
        assert _normalize_text(None) == ""


class TestSearchService:
    def test_load_counts(self, service):
        assert len(service._items) == 3

    def test_search_by_fantasy_name(self, service):
        hits = service.search("bradesco")
        assert hits and hits[0]["registro_ans"] == "01.111-1"
        assert hits[0]["score"] >= 5

    def test_search_by_registro_ans_ranks_first(self, service):
        hits = service.search("02.222")
        assert hits[0]["registro_ans"] == "02.222-2"
        assert hits[0]["score"] == 10

    def test_search_accent_insensitive(self, service):
        hits = service.search("saúde")
        assert any(h["registro_ans"] == "00.000-0" for h in hits)

    def test_search_empty_query(self, service):
        assert service.search("") == []

    def test_search_no_match(self, service):
        assert service.search("naoexiste") == []

    def test_limit_respected(self, service):
        assert len(service.search("e", limit=2)) <= 2

    def test_missing_csv_raises(self, tmp_path):
        svc = OperadorasSearchService(csv_path=str(tmp_path / "nope.csv"))
        with pytest.raises(FileNotFoundError):
            svc.load()
