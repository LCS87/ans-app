"""
Fase 1 / Tarefa 1.2 — Testes do Data Quality Gate (etl/validation.py).

Cobre: colunas obrigatórias, REG_ANS válido, valores numéricos, ramo 411,
estrutura de códigos, volume, duplicidades e comparação com ano base.
"""

import numpy as np
import pandas as pd
import pytest

from etl.validation import _ultimo_valor, total_metodo_d, validar_ano


def _df_base(n_ops=350, trim=("1T", "2T")):
    """DataFrame sintético no layout ANS (DOC 275): contas de até 9 dígitos.

    Hierarquia por operadora:
      41              (raiz, 2d)          = 1000
      411             (sub-ramo, 3d)      = 700
      411010000       (folha 9d)          = 300
      411020000       (folha 9d)          = 400
    n_ops >= 350 satisfaz o threshold PASS do check `ramo_411_presente` (>=300).
    """
    rows = []
    for t in trim:
        for i in range(n_ops):
            reg = f"{100000 + i}"
            rows.append((reg, "41", "EVENTOS/SINISTROS", 1000.0, t))
            rows.append((reg, "411", "EVENTOS CONHECIDOS", 700.0, t))
            rows.append((reg, "411010000", "INTERNADOS", 300.0, t))
            rows.append((reg, "411020000", "AMBULATORIAIS", 400.0, t))
    df = pd.DataFrame(
        rows, columns=["REG_ANS", "CD_CONTA_CONTABIL", "DESCRICAO", "VL_SALDO_FINAL", "TRIM"]
    )
    return df


class TestValidarAno:
    def test_ano_saudavel_aprovado(self):
        veredito, checks = validar_ano(2025, _df_base())
        statuses = {c["check"]: c["status"] for c in checks}
        assert "FAIL" not in statuses.values()
        assert veredito in ("APROVADO", "APROVADO_COM_RESSALVAS")
        assert statuses["colunas_obrigatorias"] == "PASS"
        assert statuses["ramo_411_presente"] == "PASS"

    def test_colunas_faltando_bloqueia(self):
        df = _df_base().drop(columns=["DESCRICAO"])
        veredito, checks = validar_ano(2025, df)
        assert veredito == "BLOQUEADO"
        by_name = {c["check"]: c for c in checks}
        assert by_name["colunas_obrigatorias"]["status"] == "FAIL"

    def test_reg_ans_invalido_bloqueia(self):
        df = _df_base()
        # >10% dos registros não numéricos → FAIL
        mask = np.random.RandomState(0).random(len(df)) < 0.5
        df.loc[mask, "REG_ANS"] = "XX-INVALIDO"
        veredito, checks = validar_ano(2025, df)
        assert veredito == "BLOQUEADO"

    def test_valores_nao_numericos_bloqueia(self):
        df = _df_base()
        df["VL_SALDO_FINAL"] = "abc"  # 100% não numérico
        veredito, checks = validar_ano(2025, df)
        assert veredito == "BLOQUEADO"
        by_name = {c["check"]: c for c in checks}
        assert by_name["valores_numericos"]["status"] == "FAIL"

    def test_ramo_411_ausente_bloqueia(self):
        df = _df_base()
        df["CD_CONTA_CONTABIL"] = df["CD_CONTA_CONTABIL"].str.replace("41", "31", regex=False)
        veredito, checks = validar_ano(2025, df)
        assert veredito == "BLOQUEADO"

    def test_duplicidades_geram_warn(self):
        df = pd.concat([_df_base(), _df_base()], ignore_index=True)
        veredito, checks = validar_ano(2025, df)
        by_name = {c["check"]: c for c in checks}
        assert by_name["sem_duplicidades"]["status"] == "WARN"
        assert veredito == "APROVADO_COM_RESSALVAS"

    def test_comparacao_ano_base_explosao_bloqueia(self):
        df = _df_base()
        # total_method_d ≈ 150 × 1400; base muito menor → ratio > 10 → FAIL
        veredito, checks = validar_ano(2025, df, total_base=100.0)
        assert veredito == "BLOQUEADO"
        by_name = {c["check"]: c for c in checks}
        assert by_name["comparacao_ano_base"]["status"] == "FAIL"

    def test_comparacao_ano_base_plausivel_passa(self):
        df = _df_base()
        t = total_metodo_d(df[df["CD_CONTA_CONTABIL"].str.startswith("41")])
        veredito, checks = validar_ano(2025, df, total_base=t * 1.05)
        by_name = {c["check"]: c for c in checks}
        assert by_name["comparacao_ano_base"]["status"] == "PASS"


class TestTotalMetodoD:
    def test_ultimo_valor_por_conta(self):
        df = pd.DataFrame(
            [
                ("111111", "41", "X", 100.0, "1T"),
                ("111111", "41", "X", 250.0, "2T"),
                ("111111", "41", "X", 0.0, "3T"),  # zero é ignorado
            ],
            columns=["REG_ANS", "CD_CONTA_CONTABIL", "DESCRICAO", "VL_SALDO_FINAL", "TRIM"],
        )
        last = _ultimo_valor(df)
        assert float(last["VL_SALDO_FINAL"].iloc[0]) == 250.0

    def test_total_sem_dupla_contagem(self):
        df = pd.DataFrame(
            [
                ("111111", "41", "RAIZ", 1000.0, "4T"),
                ("111111", "411", "F1", 600.0, "4T"),
                ("111111", "412", "F2", 400.0, "4T"),
            ],
            columns=["REG_ANS", "CD_CONTA_CONTABIL", "DESCRICAO", "VL_SALDO_FINAL", "TRIM"],
        )
        # folhas cobrem a raiz → soma das folhas = 1000 (não 2000)
        assert total_metodo_d(df) == pytest.approx(1000.0)

    def test_duas_operadoras(self):
        df = pd.DataFrame(
            [
                ("111111", "41", "RAIZ", 1000.0, "4T"),
                ("222222", "41", "RAIZ", 500.0, "4T"),
            ],
            columns=["REG_ANS", "CD_CONTA_CONTABIL", "DESCRICAO", "VL_SALDO_FINAL", "TRIM"],
        )
        assert total_metodo_d(df) == pytest.approx(1500.0)
