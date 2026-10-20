"""Testes de regressão para P0-1 (valores BRL) e P0-3 (REG_ANS).

Estes são os casos que o dataset real da ANS usa e que a suíte anterior
não cobria: valores com vírgula decimal e o mesmo registro com/sem zeros
à esquerda.
"""

import math

import pandas as pd
import pytest

from etl.normalization import (
    deduplicar_contas,
    normalizar_registro_ans,
    normalizar_serie_registro_ans,
    parse_serie_valor_brl,
    parse_valor_brl,
)


class TestRegistroAns:
    @pytest.mark.parametrize(
        "entrada, esperado",
        [
            ("5711", "005711"),
            ("005711", "005711"),
            (" 005711 ", "005711"),
            ('"5711"', "005711"),
            ("5711.0", "005711"),
            ("000582", "000582"),
            ("582", "000582"),
            ("", ""),
            (None, ""),
            ("abc", ""),
        ],
    )
    def test_normaliza_para_seis_digitos(self, entrada, esperado):
        assert normalizar_registro_ans(entrada) == esperado

    def test_serie_vetorizada(self):
        serie = pd.Series(["5711", "005711", None, " 582 ", "abc"])
        out = normalizar_serie_registro_ans(serie)
        assert out.tolist() == ["005711", "005711", "", "000582", ""]


class TestValorBrl:
    @pytest.mark.parametrize(
        "entrada, esperado",
        [
            ("30.941.701.628,46", 30941701628.46),
            ("30941701628,46", 30941701628.46),
            ("29251162680", 29251162680.0),
            ("1.234,56", 1234.56),
            ("1,234.56", 1234.56),
            ("1.234", 1234.0),
            ("1234.56", 1234.56),
            ("-7.500,00", -7500.0),
            ("(1.234,56)", -1234.56),
            ("R$ 1.234,56", 1234.56),
            ("", 0.0),
            ("abc", 0.0),
            (None, 0.0),
            (1234.56, 1234.56),
        ],
    )
    def test_parse_escalar(self, entrada, esperado):
        assert parse_valor_brl(entrada) == pytest.approx(esperado)

    def test_invalido_pode_ser_nan_para_o_gate(self):
        assert math.isnan(parse_valor_brl("abc", preencher_zero=False))
        assert math.isnan(parse_valor_brl("", preencher_zero=False))

    def test_serie_vetorizada(self):
        serie = pd.Series(
            [
                "30.941.701.628,46",
                "29251162680",
                "1.234,56",
                "1,234.56",
                "-7.500,00",
                "",
                "abc",
                None,
            ]
        )
        out = parse_serie_valor_brl(serie)
        assert out.tolist() == pytest.approx(
            [30941701628.46, 29251162680.0, 1234.56, 1234.56, -7500.0, 0.0, 0.0, 0.0]
        )

    def test_serie_vetorizada_preserva_nan(self):
        out = parse_serie_valor_brl(pd.Series(["abc", "1.234,56"]), preencher_zero=False)
        assert math.isnan(out.iloc[0])
        assert out.iloc[1] == pytest.approx(1234.56)


class TestDeduplicacao:
    def test_mantem_linha_com_data_mais_recente(self):
        df = pd.DataFrame(
            [
                ("111111", "411", "SINISTROS", 1000.0, "1T", "2024-10-01"),
                ("111111", "411", "SINISTROS", 2000.0, "1T", "2024-12-31"),
                ("111111", "412", "OUTRAS", 500.0, "1T", "2024-12-31"),
            ],
            columns=["REG_ANS", "CD_CONTA_CONTABIL", "DESCRICAO", "VL_SALDO_FINAL", "TRIM", "DATA"],
        )
        out, removidas = deduplicar_contas(df, chaves=("REG_ANS", "CD_CONTA_CONTABIL", "TRIM"))
        assert removidas == 1
        assert len(out) == 2
        valor = out.loc[out["CD_CONTA_CONTABIL"] == "411", "VL_SALDO_FINAL"].iloc[0]
        assert valor == 2000.0
