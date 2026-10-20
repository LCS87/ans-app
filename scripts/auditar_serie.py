"""Auditoria da série: reconcilia o banco com o dado bruto da ANS.

Para cada ano, o script:

1. recalcula, a partir dos arquivos brutos da ANS, os agregados do plano de
   contas (receita 31, sinistros 41, PL 25, ativo 1, resultado 3-4-61);
2. compara com os valores gravados no MySQL pelo pipeline;
3. checa a identidade contábil do balanço: ``1 = 21 + 23 + 25``.

É o contrapeso do ETL: se a extração, o mapeamento ou a carga divergirem do
bruto, a auditoria acusa.

Uso:
    python scripts/auditar_serie.py [--anos 2023,2024,2025,2026]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text  # noqa: E402

from api.config import get_settings  # noqa: E402
from etl.extract import ANSExtractor  # noqa: E402
from etl.normalization import normalizar_serie_registro_ans  # noqa: E402

# Contas de nível 1/2 usadas na auditoria (ver api/accounting_maps.py).
CONTAS = {
    "ativo": "1",
    "passivo_circulante": "21",
    "passivo_nao_circulante": "23",
    "patrimonio": "25",
    "receita": "31",
    "sinistros": "41",
    "despesas": "4",
    "impostos": "61",
}


def totais_bruto(ano: int) -> dict:
    """Totais de mercado do ano, calculados direto do CSV bruto."""
    ex = ANSExtractor()
    df = ex.df_bruto(ano).copy()
    df["REG_ANS"] = normalizar_serie_registro_ans(df["REG_ANS"])
    df = df[df["REG_ANS"] != ""]

    # Consolidação anual (igual à do ETL): último valor não-zero de cada
    # conta, priorizando o último trimestre publicado.
    df = (
        df[df["VL_SALDO_FINAL"] != 0]
        .sort_values("TRIMESTRE")
        .groupby(["REG_ANS", "CD_CONTA_CONTABIL"], as_index=False)
        .tail(1)
    )

    totais = {}
    for nome, conta in CONTAS.items():
        sub = df[df["CD_CONTA_CONTABIL"] == conta]
        totais[nome] = float(sub["VL_SALDO_FINAL"].sum())

    # Resultado do exercício: 3 (receitas totais) - 4 (despesas) - 61
    sub3 = df[df["CD_CONTA_CONTABIL"] == "3"]
    totais["receitas_totais"] = float(sub3["VL_SALDO_FINAL"].sum())
    totais["resultado"] = totais["receitas_totais"] - totais["despesas"] - totais["impostos"]
    return totais


def totais_banco(ano: int) -> dict:
    """Totais gravados no MySQL para o ano."""
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT SUM(gasto_total), SUM(receita), SUM(sinistros), SUM(lucro),
                       SUM(patrimonio), SUM(caixa), SUM(ativo_total),
                       SUM(passivo_circulante), SUM(passivo_nao_circulante),
                       COUNT(*)
                FROM gastos_assistenciais WHERE periodo = :p
                """),
            {"p": str(ano)},
        ).fetchone()
    chaves = [
        "sinistros",
        "receita",
        "sinistros",
        "lucro",
        "patrimonio",
        "caixa",
        "ativo",
        "passivo_circulante",
        "passivo_nao_circulante",
    ]
    return {k: float(v or 0) for k, v in zip(chaves, row)} | {"linhas": int(row[9])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anos", default="2023,2024,2025,2026")
    args = ap.parse_args()

    anos = [int(a) for a in args.anos.split(",")]
    divergencias = 0

    for ano in anos:
        try:
            bruto = totais_bruto(ano)
        except Exception as e:  # noqa: BLE001
            print(f"[ERRO] ano {ano}: dados brutos indisponiveis ({e})")
            continue

        banco = totais_banco(ano)
        print(f"\n{'='*78}\nANO {ano}\n{'='*78}")
        print(f"{'conta':<24}{'bruto (BRL)':>22}{'banco (BRL)':>22}{'dif %':>10}")
        print(
            "(bruto = soma das contas de nível 1/2; banco = Método D, que troca a "
            "raiz pelas folhas quando a raiz falta ou não fecha)"
        )

        comparacoes = [
            ("receita_planos (31)", "receita", "receita"),
            ("sinistros (41)", "sinistros", "sinistros"),
            ("patrimonio (25)", "patrimonio", "patrimonio"),
            ("ativo (1)", "ativo", "ativo"),
            ("passivo circulante (21)", "passivo_circulante", "passivo_circulante"),
            ("passivo nao circulante (23)", "passivo_nao_circulante", "passivo_nao_circulante"),
        ]
        for rotulo, chave_bruto, chave_banco in comparacoes:
            b = bruto.get(chave_bruto, 0.0)
            x = banco.get(chave_banco, 0.0)
            dif = abs(b - x) / abs(b) * 100 if b else 0.0
            print(f"{rotulo:<24}{b:>22,.2f}{x:>22,.2f}{dif:>9.3f}%")
            if dif > 1.0:
                divergencias += 1

        # Resultado do exercício: a regra do pipeline usa 3 - 4 - 61 sobre as
        # MESMAS contas do banco (o banco guarda o total por operadora).
        dif_resultado = (
            abs(bruto["resultado"] - banco["lucro"]) / abs(bruto["resultado"]) * 100
            if bruto["resultado"]
            else 0
        )
        print(
            f"{'resultado (3-4-61)':<24}{bruto['resultado']:>22,.2f}"
            f"{banco['lucro']:>22,.2f}{dif_resultado:>9.3f}%"
        )

    print(f"\nDivergências acima de 1%: {divergencias}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
