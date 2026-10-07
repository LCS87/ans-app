"""
Rastreia ONDE estão os bilhões das grandes operadoras em cada ano,
SEM filtro, para revelar em quais códigos o valor vive.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from etl.extract import ANSExtractor

ALVOS = {
    "326305": "AMIL",
    "005711": "BRADESCO",
    "359017": "NOTRE DAME",
    "368253": "HAPVIDA",
}


def ler_ano(ano):
    extractor = ANSExtractor()
    dfs = []
    for csv_file in extractor.extract_zips(ano):
        df = pd.read_csv(
            csv_file, sep=";", encoding="utf-8", on_bad_lines="skip", dtype=str
        )
        df.columns = [c.upper().strip() for c in df.columns]
        df["TRIM"] = csv_file.stem
        df["VL_SALDO_FINAL"] = pd.to_numeric(
            df["VL_SALDO_FINAL"], errors="coerce"
        ).fillna(0)
        df["REG_NORM"] = df["REG_ANS"].str.strip().str.zfill(6)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


for ano in [2023, 2024, 2025]:
    df = ler_ano(ano)
    print(f"\n{'#'*90}")
    print(f"# ANO {ano}")
    print(f"{'#'*90}")

    # 1) Contas > R$ 100 Mi das operadoras-alvo (qualquer trimestre)
    sub = df[(df["REG_NORM"].isin(ALVOS)) & (df["VL_SALDO_FINAL"].abs() > 100_000_000)]
    print(f"\n📌 CONTAS > R$ 100 Mi DAS OPERADORAS-ALVO ({len(sub)} registros):")
    if len(sub) == 0:
        print(
            "   ⚠️  NENHUMA! Os bilhões não existem em nenhum código destas operadoras."
        )
    for _, r in sub.sort_values(
        ["REG_NORM", "TRIM", "VL_SALDO_FINAL"], ascending=[True, True, False]
    ).iterrows():
        print(
            f"   {ALVOS.get(r['REG_NORM'], r['REG_NORM']):>10} | {r['TRIM']} | "
            f"{r['CD_CONTA_CONTABIL']:>10} | R$ {r['VL_SALDO_FINAL']:>17,.0f} | "
            f"{str(r['DESCRICAO'])[:50]}"
        )

    # 2) Top 10 contas da AMIL no 4T, SEM threshold (para ver a magnitude real)
    amil_4t = df[(df["REG_NORM"] == "326305") & (df["TRIM"].str.contains("4T"))]
    amil_4t = amil_4t.nlargest(10, "VL_SALDO_FINAL")
    print(f"\n📌 AMIL (326305) — TOP 10 CONTAS NO 4T (sem filtro, sem threshold):")
    for _, r in amil_4t.iterrows():
        print(
            f"   {r['CD_CONTA_CONTABIL']:>10} | R$ {r['VL_SALDO_FINAL']:>17,.0f} | "
            f"{str(r['DESCRICAO'])[:60]}"
        )

    # 3) Total da AMIL no ano (todas as contas 4xx, sem filtro de código 411)
    amil_desp = df[
        (df["REG_NORM"] == "326305")
        & (df["CD_CONTA_CONTABIL"].str.match(r"^4"))
        & (df["TRIM"].str.contains("4T"))
    ]
    print(
        f"\n📌 AMIL — SOMA DE TODAS CONTAS 4xx NO 4T: R$ {amil_desp['VL_SALDO_FINAL'].sum():,.0f}"
    )
