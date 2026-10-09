"""
Validação da regra da RAIZ DE VALOR REPORTADO (ramo 41).
Compara totais anuais sem dupla contagem e sem perder sintéticas.
"""

import sys
from pathlib import Path

import pandas as pd

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from etl.extract import ANSExtractor

BRANCH = "41"  # EVENTOS INDENIZÁVEIS / SINISTROS (inclui 411)


def load_year(ano):
    ext = ANSExtractor()
    dfs = []
    for f in ext.extract_zips(ano):
        df = pd.read_csv(f, sep=";", encoding="utf-8", on_bad_lines="skip", dtype=str)
        df.columns = [c.upper().strip() for c in df.columns]
        df["VL_SALDO_FINAL"] = pd.to_numeric(df["VL_SALDO_FINAL"], errors="coerce").fillna(0)
        df["TRIM"] = f.stem
        df["CD_CONTA_CONTABIL"] = df["CD_CONTA_CONTABIL"].fillna("").str.strip()
        dfs.append(df)
    df = pd.concat(dfs, ignore_index=True)
    return df[df["CD_CONTA_CONTABIL"].str.startswith(BRANCH)]


def root_totals(df):
    """Último valor não-zero por conta; soma só raízes de valor."""
    nz = df[df["VL_SALDO_FINAL"] != 0]
    last = nz.sort_values("TRIM").groupby(["REG_ANS", "CD_CONTA_CONTABIL"], as_index=False).tail(1)
    out = {}
    for reg, grp in last.groupby("REG_ANS"):
        contas = set(grp["CD_CONTA_CONTABIL"])
        total = 0.0
        for c, v in zip(grp["CD_CONTA_CONTABIL"], grp["VL_SALDO_FINAL"]):
            # raiz = nenhum prefixo próprio tem valor reportado
            if not any(c[:L] in contas for L in range(1, len(c))):
                total += v
        out[reg] = total
    return out


for ano in [2023, 2024, 2025]:
    df = load_year(ano)
    tot = pd.Series(root_totals(df)).sort_values(ascending=False)
    print(f"\n{'='*70}")
    print(f"=== {ano} ===  (regra da raiz, ramo {BRANCH})")
    print(f"💰 Total anual: R$ {tot.sum():>20,.0f}")
    print(f"🏢 Operadoras com valor: {len(tot)}")
    print("🏆 Top 10:")
    for reg, v in tot.head(10).items():
        print(f"   {reg}: R$ {v:,.0f}")
