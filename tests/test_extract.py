"""
Fase 1 / Tarefa 1.1 — Testes unitários do MÉTODO D (algoritmo central).

Cobrem a função pura ``ANSExtractor.metodo_d_total`` e o pipeline de
agregação ``processar_contas`` com dados sintéticos em diretório temporário,
sem depender dos ZIPs reais da ANS.
"""

import zipfile
from pathlib import Path

import pandas as pd
import pytest

from etl.extract import ANSExtractor


# ----------------------------------------------------------------------
# Núcleo puro: metodo_d_total
# ----------------------------------------------------------------------
class TestMetodoDCore:
    def test_somente_raiz_sem_filhas(self):
        # Raiz isolada: usa o próprio valor
        assert ANSExtractor.metodo_d_total({"41": 100.0}) == 100.0

    def test_folhas_cobrem_raiz_usa_folhas(self):
        # Folhas somam 100% da raiz → soma das folhas (sem dupla contagem)
        valores = {"41": 100.0, "411": 60.0, "412": 40.0}
        assert ANSExtractor.metodo_d_total(valores) == 100.0

    def test_folhas_parciais_usa_raiz(self):
        # Folhas cobrem apenas 50% (<90%) → método D usa a raiz
        valores = {"41": 100.0, "411": 50.0}
        assert ANSExtractor.metodo_d_total(valores) == 100.0

    def test_folhas_no_limiar_90_por_cento(self):
        # Cobertura exatamente 90% → usa folhas (>= 0.9 * raiz)
        valores = {"41": 100.0, "411": 90.0}
        assert ANSExtractor.metodo_d_total(valores) == 90.0

        # 89.9% → usa raiz
        valores = {"41": 100.0, "411": 89.9}
        assert ANSExtractor.metodo_d_total(valores) == 100.0

    def test_folhas_excedem_raiz_usa_folhas(self):
        # Raiz subdeclarada: folhas > raiz → soma das folhas
        valores = {"41": 100.0, "411": 80.0, "412": 60.0}
        assert ANSExtractor.metodo_d_total(valores) == pytest.approx(140.0)

    def test_multiplas_arvores_independentes(self):
        # Cada raiz é resolvida independentemente
        valores = {
            "41": 100.0,      # raiz com folhas completas → 100
            "411": 70.0,
            "412": 30.0,
            "31": 500.0,      # raiz sem folhas → 500
            "46": 200.0,      # raiz com folhas parciais → 200 (usa raiz)
            "461": 50.0,
        }
        assert ANSExtractor.metodo_d_total(valores) == 800.0

    def test_nao_dupla_contagem_aninhada(self):
        # Árvore profunda: 41 > 411 > 4111. Apenas a folha mais profunda conta.
        valores = {"41": 100.0, "411": 100.0, "4111": 100.0}
        # 41 não é raiz (4 está implícito? não: '4' não existe; raízes = ['41'])
        # folhas de 41: descendentes sem ancestral intermediário presente = 4111?
        # para c='411': ancestrais '4','41' → '41' presente → não é folha.
        # para c='4111': ancestrais '4','41','411' → presentes → não é folha.
        # Logo 41 não tem folhas → usa raiz 100.
        assert ANSExtractor.metodo_d_total(valores) == 100.0

    def test_valores_negativos_preservados(self):
        # Método D não descarta negativos (ex.: estornos)
        valores = {"41": 100.0, "411": 120.0, "412": -10.0}
        assert ANSExtractor.metodo_d_total(valores) == pytest.approx(110.0)

    def test_dicionario_vazio(self):
        assert ANSExtractor.metodo_d_total({}) == 0.0


# ----------------------------------------------------------------------
# Integração: processar_contas com ZIPs sintéticos
# ----------------------------------------------------------------------
CSV_COLS = ["REG_ANS", "CD_CONTA_CONTABIL", "DESCRICAO", "VL_SALDO_FINAL"]


def _make_zip(base_dir: Path, ano: int, trimestre: str, rows: list):
    """Cria raw/demonstracoes/<ano>/<trim>.zip com um CSV interno."""
    ano_dir = base_dir / "raw" / "demonstracoes" / str(ano)
    ano_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=CSV_COLS)
    csv_path = base_dir / f"_tmp_{trimestre}.csv"
    df.to_csv(csv_path, sep=";", index=False, encoding="utf-8")
    zip_path = ano_dir / f"{trimestre}.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(csv_path, arcname=f"{trimestre}.csv")
    csv_path.unlink()


@pytest.fixture()
def extractor(tmp_path):
    base = tmp_path / "data"
    (base / "processed").mkdir(parents=True)
    cadop_dir = base / "raw" / "operadoras_ativas"
    cadop_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "REGISTRO_ANS": ["111111", "222222"],
            "RAZAO_SOCIAL": ["OPERADORA ALPHA", "OPERADORA BETA"],
        }
    ).to_csv(cadop_dir / "relatorio_cadop.csv", sep=";", index=False)
    ex = ANSExtractor(base_dir=base)
    return ex


class TestProcessarContas:
    def test_prefixo_generico_receita(self, extractor):
        # F2.4: processar qualquer prefixo (aqui receita=31) com Método D
        rows_1t = [
            ("111111", "31", "RECEITA", "1000"),
            ("111111", "311", "REC OPER", "600"),
            ("111111", "312", "REC OUTRAS", "400"),
            ("222222", "31", "RECEITA", "500"),
        ]
        rows_2t = [
            ("111111", "31", "RECEITA", "1500"),  # acumulado cresce
            ("111111", "311", "REC OPER", "900"),
            ("111111", "312", "REC OUTRAS", "600"),
            ("222222", "31", "RECEITA", "700"),
        ]
        _make_zip(extractor.raw_dir.parent.parent, 2024, "1T2024", rows_1t)
        _make_zip(extractor.raw_dir.parent.parent, 2024, "2T2024", rows_2t)

        df = extractor.processar_contas(2024, prefixos={"receita": "31"})
        rec = df.set_index("REG_ANS")["receita"]
        # último valor não-zero por conta: 31=1500, 311=900, 312=600
        # folhas cobrem raiz → 1500 ; beta sem folhas → 700
        assert rec["111111"] == pytest.approx(1500.0)
        assert rec["222222"] == pytest.approx(700.0)
        assert set(df["RAZAO_SOCIAL"]) == {"OPERADORA ALPHA", "OPERADORA BETA"}

    def test_multiplos_prefixos_em_uma_passada(self, extractor):
        rows = [
            ("111111", "31", "RECEITA", "1000"),
            ("111111", "41", "SINISTROS", "400"),
            ("111111", "411", "EVENTOS", "300"),
            ("111111", "412", "OUTRAS", "100"),
        ]
        _make_zip(extractor.raw_dir.parent.parent, 2024, "1T2024", rows)
        df = extractor.processar_contas(
            2024, prefixos={"receita": "31", "sinistros": "41"}
        )
        assert df.loc[df.REG_ANS == "111111", "receita"].iloc[0] == 1000.0
        assert df.loc[df.REG_ANS == "111111", "sinistros"].iloc[0] == 400.0

    def test_quarterly_output(self, extractor):
        rows_1t = [("111111", "41", "SINISTROS", "300")]
        rows_2t = [
            ("111111", "41", "SINISTROS", "700"),
            ("222222", "41", "SINISTROS", "100"),
        ]
        _make_zip(extractor.raw_dir.parent.parent, 2024, "1T2024", rows_1t)
        _make_zip(extractor.raw_dir.parent.parent, 2024, "2T2024", rows_2t)
        df = extractor.processar_contas(
            2024,
            prefixos={"gasto_total": "41"},
            output_col="gasto_total",
            quarterly_output=True,
        )
        assert "gasto_total_1T2024" in df.columns
        r = df.set_index("REG_ANS")
        assert r.loc["111111", "gasto_total_1T2024"] == 300.0
        assert r.loc["111111", "gasto_total_2T2024"] == 700.0
        assert r.loc["222222", "gasto_total_1T2024"] == 0.0

    def test_processar_ano_retrocompativel(self, extractor):
        rows = [
            ("111111", "41", "SINISTROS", "1000"),
            ("111111", "411", "EVENTOS", "1000"),
        ]
        _make_zip(extractor.raw_dir.parent.parent, 2024, "1T2024", rows)
        df = extractor.processar_ano(2024, quarterly_output=False)
        assert {"REG_ANS", "RAZAO_SOCIAL", "gasto_total"} <= set(df.columns)
        assert df["gasto_total"].sum() == 1000.0

    def test_ano_sem_zips_levanta_erro(self, extractor):
        with pytest.raises(FileNotFoundError):
            extractor.processar_contas(2099, prefixos={"x": "31"})
