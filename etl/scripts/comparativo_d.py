"""
Comparativo A vs B vs C vs D por operadora.

A = folhas (is_leaf), último trim não-zero
B = raiz reportada (sem ancestral com valor)
C = tudo (com dupla contagem)
D = folha com fallback: raiz usa folhas se elas cobrem >=90% do valor da raiz
"""

import sys
from pathlib import Path

import pandas as pd

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from etl.extract import ANSExtractor

BRANCH = "41"


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


def last_values(df):
    """Último valor não-zero por (operadora, conta)."""
    nz = df[df["VL_SALDO_FINAL"] != 0]
    return nz.sort_values("TRIM").groupby(["REG_ANS", "CD_CONTA_CONTABIL"], as_index=False).tail(1)


def compute_all(df):
    ext = ANSExtractor()
    last = last_values(df)  # último valor não-zero por conta

    # ---- A: folhas sobre o CONSOLIDADO (não o df completo) ----
    df_leaf = ext.marcar_folhas(last)
    A = df_leaf[df_leaf["is_lea"]].groupby("REG_ANS")["VL_SALDO_FINAL"].sum()

    result_B, result_C, result_D = {}, {}, {}

    for reg, grp in last.groupby("REG_ANS"):
        contas = grp["CD_CONTA_CONTABIL"].tolist()
        valores = dict(zip(contas, grp["VL_SALDO_FINAL"]))
        contas_set = set(contas)

        result_C[reg] = sum(valores.values())

        raizes = [c for c in contas if not any(c[:L] in contas_set for L in range(1, len(c)))]
        result_B[reg] = sum(valores[r] for r in raizes)

        # ---- D corrigido ----
        total_d = 0.0
        for r in raizes:
            folhas_desc = [
                c
                for c in contas
                if c != r
                and c.startswith(r)
                and not any(c[:L] in contas_set for L in range(len(r) + 1, len(c)))
            ]
            if not folhas_desc:
                # Raiz sem folhas: usa o PRÓPRIO valor (±)
                total_d += valores[r]
            else:
                soma_folhas = sum(valores[f] for f in folhas_desc)
                if soma_folhas >= 0.9 * valores[r] or soma_folhas > valores[r]:
                    total_d += soma_folhas
                else:
                    total_d += valores[r]
        result_D[reg] = total_d

    return A, pd.Series(result_B), pd.Series(result_C), pd.Series(result_D)


def fmt(v):
    if abs(v) >= 1e9:
        return f"R$ {v/1e9:>7.2f}Bi"
    return f"R$ {v/1e6:>7.1f}Mi"


def compare(ano):
    print(f"\n{'='*110}")
    print(f"COMPARATIVO A vs B vs C vs D — {ano}")
    print(f"{'='*110}")

    df = load_year(ano)
    A, B, C, D = compute_all(df)

    comp = pd.DataFrame({"A_folhas": A, "B_raiz": B, "C_tudo": C, "D_hibrido": D}).fillna(0)
    comp = comp.sort_values("D_hibrido", ascending=False)

    print(f"\n📊 TOTAIS:")
    print(f"   A (folhas):  {fmt(comp['A_folhas'].sum())}")
    print(f"   B (raiz):    {fmt(comp['B_raiz'].sum())}")
    print(f"   C (tudo):    {fmt(comp['C_tudo'].sum())}  ❌ dupla contagem")
    print(f"   D (híbrido): {fmt(comp['D_hibrido'].sum())}  ← CANDIDATO")

    print(f"\n{'─'*110}")
    print(
        f"{'REG':<8} {'A folhas':>13} {'B raiz':>13} {'C tudo':>13} "
        f"{'D hibrido':>13} {'D-A':>11} {'D-B':>11}"
    )
    print(f"{'─'*110}")
    for reg, row in comp.head(20).iterrows():
        da = row["D_hibrido"] - row["A_folhas"]
        db = row["D_hibrido"] - row["B_raiz"]
        print(
            f"{reg:<8} {fmt(row['A_folhas']):>13} {fmt(row['B_raiz']):>13} "
            f"{fmt(row['C_tudo']):>13} {fmt(row['D_hibrido']):>13} "
            f"{fmt(da):>11} {fmt(db):>11}"
        )
    print(f"{'─'*110}")

    # Onde D difere de A e B
    print(f"\n🔬 ONDE D DIVERGE:")
    diff = comp[
        ((comp["D_hibrido"] - comp["A_folhas"]).abs() > 1e8)
        | ((comp["D_hibrido"] - comp["B_raiz"]).abs() > 1e8)
    ].head(8)
    for reg, row in diff.iterrows():
        print(
            f"   {reg}: A={fmt(row['A_folhas'])} B={fmt(row['B_raiz'])} "
            f"→ D={fmt(row['D_hibrido'])}"
        )


if __name__ == "__main__":
    compare(2025)
    compare(2024)
    compare(2023)
