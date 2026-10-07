"""
Fase 1 / Tarefa 1.3 — Testes da API REST (FastAPI + SQLite em memória).

Cobre os endpoints novos v1.2: /dimension/{dim}, /top-rankings, /quarterly,
/regional, /summary, /operadoras/{reg}/history, /export/pdf, /export/excel,
/upload-csv — além dos já existentes (/health, /analytics/gastos, /operadoras).
"""

import io


def loader_for_test(engine):
    """Fábrica de ANSLoader que usa o engine SQLite de teste (sem MySQL)."""

    def _factory():
        from etl.load import ANSLoader

        loader = ANSLoader.__new__(ANSLoader)
        loader.engine = engine
        return loader

    return _factory


class TestEndpointsLegados:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] in ("ok", "degraded")

    def test_analytics_gastos(self, client):
        r = client.get("/api/v1/analytics/gastos?periodo=2024&top=5")
        assert r.status_code == 200
        data = r.json()
        assert data["periodo"] == "2024"
        assert data["total_operadoras"] == 3
        assert data["total_geral"] == 10600.0
        assert data["ranking"][0]["razao_social"] == "OPERADORA GAMMA"

    def test_search_operadoras(self, client):
        r = client.get("/api/v1/operadoras?q=alpha&page=1&limit=10")
        assert r.status_code == 200
        assert "results" in r.json()


class TestDimension:
    def test_financeira_com_sinistralidade(self, client):
        r = client.get("/api/v1/dimension/financeira?periodo=2024&top=20")
        assert r.status_code == 200
        data = r.json()
        assert data["dimension"] == "financeira"
        first = data["ranking"][0]
        # sinistralidade = sinistros/receita
        assert first["agregados"]["sinistralidade"] > 0
        assert first["valores"]["receita"] >= first["valores"]["lucro"]

    def test_ordenacao_por_receita(self, client):
        r = client.get("/api/v1/dimension/financeira?periodo=2024")
        recs = [x["valores"]["receita"] for x in r.json()["ranking"]]
        assert recs == sorted(recs, reverse=True)

    def test_operacional_e_estrutura(self, client):
        for dim in ("operacional", "estrutura"):
            r = client.get(f"/api/v1/dimension/{dim}?periodo=2024")
            assert r.status_code == 200
            assert r.json()["dimension"] == dim

    def test_badge_outlier(self, client):
        # GAMMA é ~10x as demais → deve marcar outlier com top=3 (IQR)
        r = client.get("/api/v1/dimension/gastos?periodo=2024&top=3")
        rows = {x["registro_ans"]: x["outlier"] for x in r.json()["ranking"]}
        assert rows["333333"] is True

    def test_filtro_uf(self, client):
        r = client.get("/api/v1/dimension/gastos?periodo=2024&uf=RJ")
        data = r.json()
        assert data["total_operadoras"] == 1
        assert data["ranking"][0]["registro_ans"] == "222222"

    def test_filtro_modalidade(self, client):
        r = client.get(
            "/api/v1/dimension/gastos?periodo=2024&modalidade=Autogest%C3%A3o"
        )
        assert r.json()["total_operadoras"] == 1

    def test_dimensao_invalida_400(self, client):
        r = client.get("/api/v1/dimension/naexistente?periodo=2024")
        assert r.status_code == 400


class TestTopRankings:
    def test_cinco_rankings(self, client):
        r = client.get("/api/v1/top-rankings?periodo=2024&top=20")
        assert r.status_code == 200
        rk = r.json()["rankings"]
        assert set(rk) == {"receita", "sinistro", "patrimonio", "caixa", "lucro"}
        assert rk["receita"][0]["registro_ans"] == "333333"
        # lucro negativo (BETA=-50) não entra no ranking de lucro
        assert all(x["valor"] > 0 for x in rk["lucro"])


class TestQuarterly:
    def test_consolidado(self, client):
        r = client.get("/api/v1/quarterly?periodo=2024")
        assert r.status_code == 200
        s = r.json()["series"][0]
        assert s["trimestres"]["1T"] == 2350.0
        assert s["trimestres"]["4T"] == 2950.0

    def test_drilldown_operadora(self, client):
        r = client.get("/api/v1/quarterly?periodo=2024&registro_ans=111111")
        s = r.json()["series"]
        assert len(s) == 1
        assert s[0]["trimestres"]["2T"] == 250.0
        assert s[0]["total"] == 900.0


class TestRegional:
    def test_heat_map_por_uf(self, client):
        r = client.get("/api/v1/regional?periodo=2024")
        data = r.json()
        ufs = {u["uf"]: u for u in data["ufs"]}
        assert ufs["SP"]["operadoras"] == 2
        assert ufs["SP"]["valor"] == 9900.0
        assert ufs["RJ"]["valor"] == 700.0
        # ordenado decrescente
        vals = [u["valor"] for u in data["ufs"]]
        assert vals == sorted(vals, reverse=True)

    def test_metric_alternativa(self, client):
        r = client.get("/api/v1/regional?periodo=2024&metric=receita")
        assert r.json()["metric"] == "receita"

    def test_metric_inexistente_fallback(self, client):
        r = client.get("/api/v1/regional?periodo=2024&metric=drop_table")
        assert r.json()["metric"] == "gasto_total"


class TestSummaryHistory:
    def test_summary(self, client):
        r = client.get("/api/v1/summary?periodo=2024")
        assert r.status_code == 200
        data = r.json()
        assert set(data) == {"periodo", "gastos", "financeiro", "trimestral"}

    def test_history_multiplo_periodos(self, client):
        r = client.get("/api/v1/operadoras/111111/history")
        data = r.json()
        periods = [h["periodo"] for h in data["history"]]
        assert periods == ["2023", "2024"]
        assert data["uf"] == "SP"

    def test_history_desconhecido_404(self, client):
        r = client.get("/api/v1/operadoras/999999/history")
        assert r.status_code == 404


class TestExport:
    def test_pdf(self, client):
        r = client.get("/api/v1/export/pdf?periodo=2024")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 1000

    def test_excel(self, client):
        r = client.get("/api/v1/export/excel?periodo=2024")
        assert r.status_code == 200
        # assinatura ZIP do .xlsx
        assert r.content[:2] == b"PK"
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        assert "Gastos" in wb.sheetnames

    def test_upload_csv_ok(self, client, seeded_db, monkeypatch):
        csv = (
            "REG_ANS;RAZAO_SOCIAL;gasto_total;gasto_1T;gasto_2T;gasto_3T;gasto_4T\n"
            "444444;OPERADORA DELTA;123.45;30;30;30;33.45\n"
        ).encode("utf-8")

        # ANSLoader real aponta para MySQL; no teste trocamos o engine pelo
        # SQLite compartilhado da fixture (mesma tabela/colunas).
        import etl.load as load_mod

        monkeypatch.setattr(load_mod, "ANSLoader", loader_for_test(seeded_db))

        r = client.post(
            "/api/v1/upload-csv?periodo=2025&dimensao=gastos",
            files={"file": ("delta.csv", io.BytesIO(csv), "text/csv")},
        )
        assert r.status_code == 200, r.text
        assert r.json()["linhas"] == 1
        with seeded_db.connect() as conn:
            from sqlalchemy import text

            n = conn.execute(
                text("SELECT COUNT(*) FROM gastos_assistenciais WHERE periodo='2025'")
            ).fetchone()[0]
        assert n == 1

    def test_upload_csv_extensao_invalida(self, client):
        r = client.post(
            "/api/v1/upload-csv?periodo=2025",
            files={"file": ("nota.txt", io.BytesIO(b"x"), "text/plain")},
        )
        assert r.status_code == 400

    def test_upload_csv_dimensao_invalida(self, client):
        r = client.post(
            "/api/v1/upload-csv?periodo=2025&dimensao=xyz",
            files={"file": ("a.csv", io.BytesIO(b"x"), "text/csv")},
        )
        assert r.status_code == 400
