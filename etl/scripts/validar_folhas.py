"""Prova que is_leaf elimina dupla contagem e compara com o filtro antigo."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from etl.extract import ANSExtractor

ext = ANSExtractor()

for ano in [2023, 2024, 2025]:
    dfs = []
    for f in ext.extract_zips(ano):
        df = pd.read_csv(f, sep=";", encoding="utf-8", on_bad_lines="skip", dtype=str)
        df.columns = [c.upper().strip() for c in df.columns]
        df["VL_SALDO_FINAL"] = pd.to_numeric(df["VL_SALDO_FINAL"], errors="coerce").fillna(0)
        df["TRIM"] = f.stem
        dfs.append(df)
    df = pd.concat(dfs, ignore_index=True)
    df = ext.marcar_folhas(df)

    print(f"\n{'='*70}\n=== {ano} ===")
    dist = df["CD_CONTA_CONTABIL"].str.len().value_counts().sort_index()
    print(f"Comprimentos de código: {dist.to_dict()}")
    print(
        f"Contas: {len(df):,} | folhas: {df['is_leaf'].sum():,} | pais: {(~df['is_leaf']).sum():,}"
    )

    m411 = df["CD_CONTA_CONTABIL"].str.startswith("411") & (df["VL_SALDO_FINAL"] > 0)
    soma_len9 = df[m411 & (df["CD_CONTA_CONTABIL"].str.len() == 9)]["VL_SALDO_FINAL"].sum()
    soma_folha = df[m411 & df["is_lea"]]["VL_SALDO_FINAL"].sum()
    soma_tudo = df[m411]["VL_SALDO_FINAL"].sum()

    print(f"Soma 411 (len==9, filtro antigo)      : R$ {soma_len9:>20,.0f}")
    print(f"Soma 411 (is_leaf, filtro novo)       : R$ {soma_folha:>20,.0f}")
    print(f"Soma 411 (tudo, c/ pais+filhos)       : R$ {soma_tudo:>20,.0f}  ← dupla contagem")

    # ================================================================
    # EIXO TEMPORAL: DRE é acumulada no ano
    # O valor anual correto = último trimestre reportado de cada conta
    # ================================================================
    folhas411 = df[
        df["is_lea"] & df["CD_CONTA_CONTABIL"].str.startswith("411") & (df["VL_SALDO_FINAL"] > 0)
    ].copy()

    ultimo_trim = (
        folhas411.sort_values("TRIM")
        .groupby(["REG_ANS", "CD_CONTA_CONTABIL"], as_index=False)
        .tail(1)
    )
    so_4t = folhas411[folhas411["TRIM"].str.contains("4T", na=False)]

    print(
        f"Soma 411 folhas (últ. trim. por conta): R$ {ultimo_trim['VL_SALDO_FINAL'].sum():>20,.0f}  ← CORRETO (anual)"
    )
    print(f"Soma 411 folhas (somente 4T)          : R$ {so_4t['VL_SALDO_FINAL'].sum():>20,.0f}")
