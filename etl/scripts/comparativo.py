"""
Comparativo direto: FOLHAS vs RAIZ REPORTADA vs TUDO (com dupla contagem)
por operadora.

Objetivo: mostrar onde cada método funciona ou falha.

Método A: folhas (is_leaf) - último trim não-zero
Método B: raiz reportada - último trim não-zero, sem ancestral com valor
Método C: tudo (com dupla contagem) - último trim não-zero

Uso:
    py etl/scripts/comparativo.py
"""

import sys
from pathlib import Path

import pandas as pd

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from etl.extract import ANSExtractor

BRANCH = "41"  # EVENTOS INDENIZÁVEIS / SINISTROS


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


def compute_methods(df):
    """Calcula os 3 métodos por operadora."""

    # Método A: folhas (is_leaf) - último trim não-zero
    ext = ANSExtractor()
    df_leaf = ext.marcar_folhas(df)
    df_leaf_nz = df_leaf[(df_leaf["is_lea"]) & (df_leaf["VL_SALDO_FINAL"] != 0)]
    last_leaf = (
        df_leaf_nz.sort_values("TRIM")
        .groupby(["REG_ANS", "CD_CONTA_CONTABIL"], as_index=False)
        .tail(1)
    )
    A = last_leaf.groupby("REG_ANS")["VL_SALDO_FINAL"].sum()

    # Método B: raiz reportada - último trim não-zero, sem ancestral com valor
    nz = df[df["VL_SALDO_FINAL"] != 0]
    last_all = (
        nz.sort_values("TRIM").groupby(["REG_ANS", "CD_CONTA_CONTABIL"], as_index=False).tail(1)
    )
    B_dict = {}
    for reg, grp in last_all.groupby("REG_ANS"):
        contas = set(grp["CD_CONTA_CONTABIL"])
        total = 0.0
        for c, v in zip(grp["CD_CONTA_CONTABIL"], grp["VL_SALDO_FINAL"]):
            if not any(c[:L] in contas for L in range(1, len(c))):
                total += v
        B_dict[reg] = total
    B = pd.Series(B_dict)

    # Método C: tudo (com dupla contagem) - último trim não-zero
    C = last_all.groupby("REG_ANS")["VL_SALDO_FINAL"].sum()

    return A, B, C


def compare(ano):
    print(f"\n{'='*100}")
    print(f"COMPARATIVO: FOLHAS vs RAIZ vs TUDO — ANO {ano}")
    print(f"{'='*100}")

    df = load_year(ano)
    A, B, C = compute_methods(df)

    # Unir os 3 métodos
    comp = pd.DataFrame({"A_folhas": A, "B_raiz": B, "C_tudo": C}).fillna(0)

    # Calcular diferenças
    comp["B-A"] = comp["B_raiz"] - comp["A_folhas"]
    comp["C-B"] = comp["C_tudo"] - comp["B_raiz"]
    comp["B/A"] = (comp["B_raiz"] / comp["A_folhas"]).replace([float("in")], float("nan"))
    comp["C/B"] = (comp["C_tudo"] / comp["B_raiz"]).replace([float("in")], float("nan"))

    # Ordenar por B (raiz) decrescente
    comp = comp.sort_values("B_raiz", ascending=False)

    # Totais
    print(f"\n📊 TOTAIS:")
    print(f"   A (folhas):  R$ {comp['A_folhas'].sum():>18,.0f}")
    print(f"   B (raiz):    R$ {comp['B_raiz'].sum():>18,.0f}")
    print(f"   C (tudo):    R$ {comp['C_tudo'].sum():>18,.0f}")
    print(
        f"\n   B-A (ganho da raiz): R$ {comp['B-A'].sum():>18,.0f} ({(comp['B-A'].sum()/comp['A_folhas'].sum()*100):+.1f}%)"
    )
    print(
        f"   C-B (dupla contagem): R$ {comp['C-B'].sum():>18,.0f} ({(comp['C-B'].sum()/comp['B_raiz'].sum()*100):+.1f}%)"
    )

    # Top 20 operadoras
    print(f"\n{'─'*100}")
    print(
        f"{'REG_ANS':<10} {'A (folhas)':>15} {'B (raiz)':>15} {'C (tudo)':>15} {'B-A':>12} {'B/A':>8} {'C/B':>8}"
    )
    print(f"{'─'*100}")

    for reg, row in comp.head(20).iterrows():
        A_val = (
            f"R$ {row['A_folhas']/1e9:.2f}Bi"
            if row["A_folhas"] >= 1e9
            else f"R$ {row['A_folhas']/1e6:.1f}Mi"
        )
        B_val = (
            f"R$ {row['B_raiz']/1e9:.2f}Bi"
            if row["B_raiz"] >= 1e9
            else f"R$ {row['B_raiz']/1e6:.1f}Mi"
        )
        C_val = (
            f"R$ {row['C_tudo']/1e9:.2f}Bi"
            if row["C_tudo"] >= 1e9
            else f"R$ {row['C_tudo']/1e6:.1f}Mi"
        )
        BA_val = f"+R$ {row['B-A']/1e6:.1f}Mi" if row["B-A"] > 0 else f"R$ {row['B-A']/1e6:.1f}Mi"
        BA_ratio = (
            f"{row['B/A']:.2f}x"
            if not pd.isna(row["B/A"]) and row["B/A"] < 100
            else "∞" if pd.isna(row["B/A"]) else f"{row['B/A']:.0f}x"
        )
        CB_ratio = f"{row['C/B']:.2f}x" if not pd.isna(row["C/B"]) else "∞"

        print(
            f"{reg:<10} {A_val:>15} {B_val:>15} {C_val:>15} {BA_val:>12} {BA_ratio:>8} {CB_ratio:>8}"
        )

    print(f"{'─'*100}")

    # Casos interessantes
    print(f"\n🔬 CASOS INTERESSANTES:")

    # Onde raiz recupera muito (B >> A)
    big_gain = comp[comp["B-A"] > 100_000_000].head(5)
    if len(big_gain) > 0:
        print(f"\n   📈 Raiz recupera > R$ 100 Mi vs folhas (B >> A):")
        for reg, row in big_gain.iterrows():
            print(
                f"      {reg}: A={row['A_folhas']/1e6:.1f}Mi → B={row['B_raiz']/1e6:.1f}Mi (+{row['B-A']/1e6:.1f}Mi)"
            )

    # Onde há dupla contagem massiva (C >> B)
    big_dup = comp[comp["C-B"] > 500_000_000].head(5)
    if len(big_dup) > 0:
        print(f"\n   ⚠️  Dupla contagem > R$ 500 Mi (C >> B):")
        for reg, row in big_dup.iterrows():
            print(
                f"      {reg}: B={row['B_raiz']/1e6:.1f}Mi → C={row['C_tudo']/1e6:.1f}Mi (+{row['C-B']/1e6:.1f}Mi)"
            )

    # Onde folhas e raiz são iguais (B ≈ A)
    equal = comp[(comp["B-A"].abs() < 10_000_000) & (comp["A_folhas"] > 100_000_000)].head(5)
    if len(equal) > 0:
        print(f"\n   ✅ Folhas e raiz são iguais (B ≈ A, > R$ 100 Mi):")
        for reg, row in equal.iterrows():
            print(f"      {reg}: A={row['A_folhas']/1e6:.1f}Mi, B={row['B_raiz']/1e6:.1f}Mi")

    # Onde folhas é zero mas raiz tem valor
    leaf_zero = comp[(comp["A_folhas"] == 0) & (comp["B_raiz"] > 100_000_000)].head(5)
    if len(leaf_zero) > 0:
        print(f"\n   🚨 Folhas = 0, mas raiz tem > R$ 100 Mi (perda total):")
        for reg, row in leaf_zero.iterrows():
            print(f"      {reg}: A=0 → B={row['B_raiz']/1e6:.1f}Mi (recuperado pela raiz)")


if __name__ == "__main__":
    compare(2025)
    compare(2024)
    compare(2023)
