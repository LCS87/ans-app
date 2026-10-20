"""
Fase 1 / Tarefa 1.4 — Testes do ETL com SQLite em memória (sem MySQL).

Cobre: normalização multi-dimensão, carga UPSERT-compatible e o job
orquestrador de dimensões (processar_contas por dimensão → load).
"""

import zipfile

import pandas as pd
import pytest
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
                "passivo_circulante": [50.0],
                "passivo_nao_circulante": [30.0],
            }
        )
        out = loader.normalizar_colunas(df, periodo="2024", dimensao="financeira")
        assert "receita" in out.columns and "passivo_nao_circulante" in out.columns
        # colunas ausentes são preenchidas com 0 (ex.: ativo_total não veio no
        # DataFrame; a financial exige as duas colunas de passivo)
        assert out["receita"].iloc[0] == 3000.0
        assert out["ativo_total"].iloc[0] == 0.0

    def test_coluna_ausente_vira_zero(self, sqlite_engine):
        loader = loader_for_test(sqlite_engine)
        df = pd.DataFrame({"REG_ANS": ["1"], "RAZAO_SOCIAL": ["X"]})
        out = loader.normalizar_colunas(df, periodo="2024", dimensao="gastos")
        assert (out["gasto_total"] == 0).all()

    def test_reg_ans_canonizado_no_load(self, sqlite_engine):
        loader = loader_for_test(sqlite_engine)
        df = pd.DataFrame(
            {
                "REG_ANS": ["5711"],
                "RAZAO_SOCIAL": ["BRADESCO"],
                "gasto_total": [100.0],
            }
        )
        out = loader.normalizar_colunas(df, periodo="2024", dimensao="gastos")
        assert out["registro_ans"].iloc[0] == "005711"

    def test_sem_reg_ans_levanta_erro(self, sqlite_engine):
        loader = loader_for_test(sqlite_engine)
        df = pd.DataFrame({"RAZAO_SOCIAL": ["SEM REGISTRO"]})
        with pytest.raises(ValueError, match="obrigatórias"):
            loader.normalizar_colunas(df, periodo="2024", dimensao="gastos")

    def test_normalizar_colunas_todas(self, sqlite_engine):
        loader = loader_for_test(sqlite_engine)
        df = pd.DataFrame(
            {
                "REG_ANS": ["111111"],
                "RAZAO_SOCIAL": ["ALPHA"],
                "gasto_total": [100.0],
                "receita": [300.0],
                "lucro": [20.0],
            }
        )
        out = loader.normalizar_colunas(df, periodo="2024", dimensao="todas")
        assert "receita" in out.columns
        assert out["receita"].iloc[0] == 300.0
        assert out["lucro"].iloc[0] == 20.0
        assert out["caixa"].iloc[0] == 0
        assert out["gasto_total"].iloc[0] == 100.0


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

    def test_carregar_normaliza_e_deduplica_ids(self, sqlite_engine):
        """5711 + 005711 no mesmo período devem virar uma única linha."""
        loader = loader_for_test(sqlite_engine)
        df = pd.DataFrame(
            {
                "periodo": ["2026", "2026"],
                "registro_ans": ["5711", "005711"],
                "razao_social": ["BRADESCO ANTIGO", "BRADESCO NOVO"],
                "gasto_1T": [10.0, 20.0],
                "gasto_2T": [10.0, 20.0],
                "gasto_3T": [10.0, 20.0],
                "gasto_4T": [10.0, 20.0],
                "gasto_total": [40.0, 80.0],
            }
        )

        n = loader.carregar(df, periodo="2026", truncate=True)

        assert n == 1
        with sqlite_engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT registro_ans, razao_social, gasto_total "
                    "FROM gastos_assistenciais WHERE periodo='2026'"
                )
            ).fetchone()
        assert row[0] == "005711"
        assert row[1] == "BRADESCO NOVO"
        assert float(row[2]) == 80.0

    def test_carregar_upsert_preserva_dimensao(self, seeded_db):
        """Carga só de gastos (truncate=False) não apaga receita/lucro."""
        loader = loader_for_test(seeded_db)
        df = pd.DataFrame(
            {
                "periodo": ["2024"],
                "registro_ans": ["111111"],
                "razao_social": ["ALPHA"],
                "gasto_1T": [10.0],
                "gasto_2T": [10.0],
                "gasto_3T": [10.0],
                "gasto_4T": [10.0],
                "gasto_total": [40.0],
            }
        )

        loader.carregar(df, periodo="2024", truncate=False)

        with seeded_db.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT gasto_total, receita FROM gastos_assistenciais "
                    "WHERE periodo='2024' AND registro_ans='111111'"
                )
            ).fetchone()
        assert float(row[0]) == 40.0
        assert float(row[1]) == 3000.0  # preservado do seed


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
            ("111111", "121", "CAIXA", "70"),
            ("111111", "1211", "C1", "70"),
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
        assert "gasto_1T2024" in results["gastos"].columns
        fin = results["financeira"]
        assert float(fin.loc[fin.REG_ANS == "111111", "receita"].iloc[0]) == 1000.0
        assert float(fin.loc[fin.REG_ANS == "111111", "caixa"].iloc[0]) == 70.0

    def test_mesclar_dimensoes_uma_linha_por_operadora(self):
        from etl.pipeline import mesclar_dimensoes

        gastos = pd.DataFrame(
            {
                "REG_ANS": ["111111"],
                "RAZAO_SOCIAL": ["ALPHA"],
                "gasto_total": [100.0],
                "gasto_1T2024": [100.0],
            }
        )
        financeira = pd.DataFrame(
            {
                "REG_ANS": ["111111", "222222"],
                "RAZAO_SOCIAL": ["ALPHA", "BETA"],
                "receita": [300.0, 500.0],
            }
        )

        out = mesclar_dimensoes({"gastos": gastos, "financeira": financeira})

        assert len(out) == 2
        assert "RAZAO_SOCIAL_x" not in out.columns
        assert "RAZAO_SOCIAL_y" not in out.columns
        beta = out.loc[out["REG_ANS"] == "222222"].iloc[0]
        assert beta["gasto_total"] == 0.0
        assert beta["receita"] == 500.0
        assert beta["RAZAO_SOCIAL"] == "BETA"


class TestMapeamentoContabilP1:
    """P1 — mapeamento das contas conferido contra o plano ANS (DOC 275)."""

    def _ambiente(self, tmp_path, rows):
        """Monta um ano fictício (1T) com as contas informadas."""
        base = tmp_path / "data"
        (base / "processed").mkdir(parents=True, exist_ok=True)
        cadop = base / "raw" / "operadoras_ativas"
        cadop.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"REGISTRO_ANS": ["111111"], "RAZAO_SOCIAL": ["ALPHA"]}).to_csv(
            cadop / "relatorio_cadop.csv", sep=";", index=False
        )

        ano_dir = base / "raw" / "demonstracoes" / "2024"
        ano_dir.mkdir(parents=True, exist_ok=True)
        csvp = tmp_path / "in.csv"
        pd.DataFrame(
            rows, columns=["REG_ANS", "CD_CONTA_CONTABIL", "DESCRICAO", "VL_SALDO_FINAL"]
        ).to_csv(csvp, sep=";", index=False)
        with zipfile.ZipFile(ano_dir / "1T2024.zip", "w") as zf:
            zf.write(csvp, arcname="1T2024.csv")
        return base

    def test_mapa_financeiro_usa_contas_corretas(self):
        from api.accounting_maps import DIMENSIONS

        cols = DIMENSIONS["financeira"]["columns"]
        # 25 é Patrimônio Líquido; 69 é Apuração do Resultado; 12 é Ativo
        # Circulante (NÃO é caixa) — a liquidez é 121 + 122.
        assert cols["patrimonio"] == "25"
        assert cols["lucro"] == "69"
        assert cols["caixa"] == ("121", "122")
        assert cols["passivo_circulante"] == "21"
        assert cols["passivo_nao_circulante"] == "23"
        assert cols["ativo_total"] == "1"

    def test_caixa_soma_disponivel_e_aplicacoes(self, tmp_path):
        from etl.extract import ANSExtractor

        base = self._ambiente(
            tmp_path,
            [
                ("111111", "121", "DISPONIVEL", "100"),
                ("111111", "122", "APLICACOES", "900"),
            ],
        )
        ex = ANSExtractor(base_dir=base)
        df = ex.processar_contas(2024, prefixos={"caixa": ("121", "122")}, output_col="caixa")
        assert float(df.loc[df.REG_ANS == "111111", "caixa"].iloc[0]) == 1000.0

    def test_lucro_derivado_quando_nao_ha_apuracao(self, tmp_path):
        """Sem a conta 69, o lucro vem de 3 - 4 - 61 (regra do pipeline)."""
        from etl.pipeline import extrair_dimensoes

        base = self._ambiente(
            tmp_path,
            [
                ("111111", "3", "RECEITAS", "1000"),
                ("111111", "31", "RECEITA PLANOS", "1000"),
                ("111111", "4", "DESPESAS", "300"),
                ("111111", "41", "SINISTROS", "300"),
            ],
        )
        results = extrair_dimensoes(2024, base_dir=base)
        fin = results["financeira"]
        linha = fin[fin.REG_ANS == "111111"].iloc[0]
        assert float(linha["lucro"]) == 700.0

    def test_identidade_do_balanco_ativo_igual_passivo_mais_pl(self, tmp_path):
        """1 = 21 + 23 + 25 para cada operadora."""
        from etl.extract import ANSExtractor

        base = self._ambiente(
            tmp_path,
            [
                ("111111", "1", "ATIVO", "1000"),
                ("111111", "21", "PASSIVO CIRCULANTE", "400"),
                ("111111", "23", "PASSIVO NAO CIRCULANTE", "300"),
                ("111111", "25", "PATRIMONIO LIQUIDO", "300"),
            ],
        )
        ex = ANSExtractor(base_dir=base)
        df = ex.processar_contas(
            2024,
            prefixos={
                "ativo_total": "1",
                "passivo_circulante": "21",
                "passivo_nao_circulante": "23",
                "patrimonio": "25",
            },
            output_col="ativo_total",
        )
        linha = df[df.REG_ANS == "111111"].iloc[0]
        assert float(linha["ativo_total"]) == 1000.0
        assert float(linha["passivo_circulante"]) + float(linha["passivo_nao_circulante"]) + float(
            linha["patrimonio"]
        ) == float(linha["ativo_total"])
