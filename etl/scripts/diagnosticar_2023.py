"""
Diagnóstico específico de 2023 para identificar contas anômalas.
"""

import sys
from pathlib import Path
from collections import Counter
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from etl.extract import ANSExtractor, PATTERNS_GASTOS_ASSISTENCIAIS, PATTERNS_EXCLUSAO


def diagnosticar_2023():
    """Identifica contas problemáticas em 2023."""
    extractor = ANSExtractor()

    print("=" * 80)
    print("🔬 DIAGNÓSTICO ESPECÍFICO DE 2023")
    print("=" * 80)

    csv_files = extractor.extract_zips(2023)

    todas_contas = []
    for csv_path in csv_files:
        df = extractor._read_csv_demonstracao(csv_path)
        df.columns = [c.upper().strip() for c in df.columns]
        df["VL_SALDO_FINAL"] = pd.to_numeric(
            df["VL_SALDO_FINAL"], errors="coerce"
        ).fillna(0)

        descricao = df["DESCRICAO"].fillna("")

        # Aplicar filtros atuais
        mask_inclusao = pd.Series([False] * len(df), index=df.index)
        for pattern in PATTERNS_GASTOS_ASSISTENCIAIS:
            mask_inclusao |= descricao.str.contains(
                pattern, case=False, na=False, regex=True
            )

        mask_exclusao = pd.Series([False] * len(df), index=df.index)
        for pattern in PATTERNS_EXCLUSAO:
            mask_exclusao |= descricao.str.contains(
                pattern, case=False, na=False, regex=True
            )

        mask_final = mask_inclusao & (~mask_exclusao) & (df["VL_SALDO_FINAL"] > 0)
        df_filtered = df[mask_final].copy()

        todas_contas.append(df_filtered[["DESCRICAO", "VL_SALDO_FINAL"]])

    df_all = pd.concat(todas_contas, ignore_index=True)

    # Agrupar por descrição
    agrupado = (
        df_all.groupby("DESCRICAO")["VL_SALDO_FINAL"]
        .agg(["sum", "count"])
        .sort_values("sum", ascending=False)
    )

    print(f"\n📊 TOTAL CAPTURADO EM 2023: R$ {agrupado['sum'].sum():,.2f}\n")

    # TOP 30 contas problemáticas
    print("=" * 80)
    print("🔥 TOP 30 CONTAS EM 2023")
    print("=" * 80)
    for i, (desc, row) in enumerate(agrupado.head(30).iterrows(), 1):
        print(f"{i:2}. {desc[:80]:<80} | R$ {row['sum']:>20,.0f} | {row['count']:>4}x")

    # Comparar com 2024
    print("\n" + "=" * 80)
    print("🔍 COMPARAÇÃO: 2023 vs 2024")
    print("=" * 80)

    csv_files_2024 = extractor.extract_zips(2024)
    todas_2024 = []
    for csv_path in csv_files_2024:
        df = extractor._read_csv_demonstracao(csv_path)
        df.columns = [c.upper().strip() for c in df.columns]
        df["VL_SALDO_FINAL"] = pd.to_numeric(
            df["VL_SALDO_FINAL"], errors="coerce"
        ).fillna(0)
        descricao = df["DESCRICAO"].fillna("")

        mask_inclusao = pd.Series([False] * len(df), index=df.index)
        for pattern in PATTERNS_GASTOS_ASSISTENCIAIS:
            mask_inclusao |= descricao.str.contains(
                pattern, case=False, na=False, regex=True
            )

        mask_exclusao = pd.Series([False] * len(df), index=df.index)
        for pattern in PATTERNS_EXCLUSAO:
            mask_exclusao |= descricao.str.contains(
                pattern, case=False, na=False, regex=True
            )

        mask_final = mask_inclusao & (~mask_exclusao) & (df["VL_SALDO_FINAL"] > 0)
        df_filtered = df[mask_final].copy()
        todas_2024.append(df_filtered[["DESCRICAO", "VL_SALDO_FINAL"]])

    df_2024 = pd.concat(todas_2024, ignore_index=True)
    agrupado_2024 = df_2024.groupby("DESCRICAO")["VL_SALDO_FINAL"].sum()

    # Contas que existem em 2023 mas não em 2024 (ou valores muito diferentes)
    contas_2023 = set(agrupado.index)
    contas_2024 = set(agrupado_2024.index)

    contas_somente_2023 = contas_2023 - contas_2024

    print(f"\n📋 Contas capturadas em 2023: {len(contas_2023)}")
    print(f"📋 Contas capturadas em 2024: {len(contas_2024)}")
    print(f"⚠️  Contas SÓ em 2023: {len(contas_somente_2023)}")

    if contas_somente_2023:
        print("\n🔥 CONTAS EXCLUSIVAS DE 2023 (possível fonte da anomalia):")
        for conta in sorted(contas_somente_2023):
            valor = agrupado.loc[conta, "sum"] if conta in agrupado.index else 0
            print(f"  • {conta[:100]} → R$ {valor:,.0f}")

    # Salvar relatório
    output_path = (
        Path(__file__).parent.parent / "data" / "processed" / "diagnostico_2023.csv"
    )
    agrupado.to_csv(output_path)
    print(f"\n💾 Relatório salvo: {output_path}")


if __name__ == "__main__":
    diagnosticar_2023()
