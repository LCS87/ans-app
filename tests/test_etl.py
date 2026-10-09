"""
Fase 1 / Tarefa 1.4 — Testes do ETL com SQLite em memória (sem MySQL).

Cobre: normalização multi-dimensão, carga UPSERT-compatible e o job
orquestrador de dimensões (processar_contas por dimensão → load).
"""

import zipfile

import pandas as pd
from sqlalchemy import text



def loader_for_test(engine):
    from etl.load import ANSLoader as _L

    loader = _L.__new__(_L)
    loader.engine = engine
    return loader


class TestNormalizacao:
    def test_gastos_quarters(self, sqlite_engine):
        loader = loader_for_test(sqlite_engine)
        df = pd.DataFrame(
            {
                "REG_ANS": ["111111"],
                "RAZAO_SOCIAL": ["ALPHA"],
                "gasto_total_2024": [900.0],
                "gasto_1T2024": [200.0],
                "gasto_2T2024": [250.0],
                "gasto_3T2024": [200.0],
                "gasto_4T2024": [250.0],
            }
        )
        out = loader.normalizar_colunas(df, periodo="2024", dimensao="gastos")
        assert list(out.columns) == [
            "periodo",
            "registro_ans",
            "razao_social",
            "gasto_1T",
            "gasto_2T",
            "gasto_3T",
            "gasto_4T",
            "gasto_total",
        ]
        assert out["gasto_total"].iloc[0] == 900.0

    def test_dimensao_financeira_cols_banco(self, sqlite_engine):
        loader = loader_for_test(sqlite_engine)
        df = pd.DataFrame(
            {
                "REG_ANS": ["111111"],
                "RAZAO_SOCIAL": ["ALPHA"],
                "receita": [3000.0],
                "sinistros": [900.0],
                "lucro": [100.0],
                "patrimonio": [5000.0],
                "caixa": [400.0],
                "obrigacoes_trabalhistas": [50.0],
                "fornecedores": [30.0],
            }
        )
        out = loader.normalizar_colunas(df, periodo="2024", dimensao="financeira")
        assert "receita" in out.columns and "fornecedores" in out.columns
        # colunas ausentes são preenchidas com 0 (ex.: glosas não pertence a
        # financeira mas pode faltar; aqui checamos apenas as da dimensão)
        assert out["receita"].iloc[0] == 3000.0

    def test_coluna_ausente_vira_zero(self, sqlite_engine):
        loader = loader_for_test(sqlite_engine)
        df = pd.DataFrame({"REG_ANS": ["1"], "RAZAO_SOCIAL": ["X"]})
        out = loader.normalizar_colunas(df, periodo="2024", dimensao="gastos")
        assert (out["gasto_total"] == 0).all()


class TestCarga:
    def test_carregar_e_validar(self, sqlite_engine):
        loader = loader_for_test(sqlite_engine)
        df = pd.DataFrame(
            {
                "periodo": ["2026", "2026"],
                "registro_ans": ["111111", "222222"],
                "razao_social": ["ALPHA", "BETA"],
                "gasto_1T": [10.0, 20.0],
                "gasto_2T": [10.0, 20.0],
                "gasto_3T": [10.0, 20.0],
                "gasto_4T": [10.0, 20.0],
                "gasto_total": [40.0, 80.0],
            }
        )
        n = loader.carregar(df, periodo="2026", truncate=True)
        assert n == 2
        with sqlite_engine.connect() as conn:
            total = conn.execute(
                text("SELECT SUM(gasto_total) FROM gastos_assistenciais WHERE periodo='2026'")
            ).fetchone()[0]
        assert total == 120.0

    def test_truncate_apenas_periodo_alvo(self, seeded_db):
        loader = loader_for_test(seeded_db)
        df = pd.DataFrame(
            {
                "periodo": ["2024"],
                "registro_ans": ["999999"],
                "razao_social": ["NOVA"],
                "gasto_1T": [1.0],
                "gasto_2T": [1.0],
                "gasto_3T": [1.0],
                "gasto_4T": [1.0],
                "gasto_total": [4.0],
            }
        )
        loader.carregar(df, periodo="2024", truncate=True)
        with seeded_db.connect() as conn:
            regs = {
                r[0]
                for r in conn.execute(
                    text("SELECT registro_ans FROM gastos_assistenciais WHERE periodo='2024'")
                )
            }
            rest = conn.execute(
                text("SELECT COUNT(*) FROM gastos_assistenciais WHERE periodo='2023'")
            ).fetchone()[0]
        assert regs == {"999999"}  # 2024 substituído
        assert rest == 1  # 2023 intacto


class TestJobMultiDimensao:
    """Fase 5: orquestração processar_contas por dimensão no pipeline."""

    def test_extrair_dimensoes_pipeline(self, tmp_path):
        from etl.pipeline import extrair_dimensoes

        base = tmp_path / "data"
        (base / "processed").mkdir(parents=True)
        cadop = base / "raw" / "operadoras_ativas"
        cadop.mkdir(parents=True)
        pd.DataFrame({"REGISTRO_ANS": ["111111"], "RAZAO_SOCIAL": ["ALPHA"]}).to_csv(
            cadop / "relatorio_cadop.csv", sep=";", index=False
        )

        rows = [
            ("111111", "31", "RECEITA", "1000"),
            ("111111", "311", "R1", "600"),
            ("111111", "312", "R2", "400"),
            ("111111", "41", "SINISTROS", "300"),
            ("111111", "411", "S1", "300"),
            ("111111", "11", "CAIXA", "70"),
            ("111111", "111", "C1", "70"),
        ]
        ano_dir = base / "raw" / "demonstracoes" / "2024"
        ano_dir.mkdir(parents=True)
        csvp = tmp_path / "in.csv"
        pd.DataFrame(
            rows, columns=["REG_ANS", "CD_CONTA_CONTABIL", "DESCRICAO", "VL_SALDO_FINAL"]
        ).to_csv(csvp, sep=";", index=False)
        with zipfile.ZipFile(ano_dir / "1T2024.zip", "w") as zf:
            zf.write(csvp, arcname="1T2024.csv")

        results = extrair_dimensoes(2024, base_dir=base)
        assert set(results) >= {"gastos", "financeira", "operacional", "estrutura"}
        fin = results["financeira"]
        assert float(fin.loc[fin.REG_ANS == "111111", "receita"].iloc[0]) == 1000.0
        assert float(fin.loc[fin.REG_ANS == "111111", "caixa"].iloc[0]) == 70.0
