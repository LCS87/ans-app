"""
Script de diagnóstico: identifica quais contas estão sendo capturadas
pelo filtro de "gastos assistenciais" para analisar se são reais.
"""

import sys
from pathlib import Path
from collections import Counter
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from etl.extract import ANSExtractor, KEYWORDS_ASSISTENCIAIS


def diagnosticar(ano: int = 2023, top_n: int = 50):
    """Lista as top N contas capturadas pelo filtro para análise."""
    extractor = ANSExtractor()

    print(f"\n{'='*80}")
    print(f"🔬 DIAGNÓSTICO DO FILTRO - ANO {ano}")
    print(f"{'='*80}")
    print(f"📋 Keywords atuais: {KEYWORDS_ASSISTENCIAIS}\n")

    # Extrair CSVs
    csv_files = extractor.extract_zips(ano)

    todas_contas = []

    for csv_path in csv_files:
        print(f"📊 Analisando {csv_path.stem}...")
        df = extractor._read_csv_demonstracao(csv_path)
        df.columns = [c.upper().strip() for c in df.columns]

        # Filtrar (mesmo filtro usado no ETL)
        df["VL_SALDO_FINAL"] = pd.to_numeric(
            df["VL_SALDO_FINAL"], errors="coerce"
        ).fillna(0)
        pattern = "|".join(KEYWORDS_ASSISTENCIAIS)
        mask = df["DESCRICAO"].str.lower().str.contains(pattern, na=False, regex=True)
        df_filtered = df[mask]
        df_filtered = df_filtered[df_filtered["VL_SALDO_FINAL"] > 0]

        todas_contas.append(df_filtered[["DESCRICAO", "VL_SALDO_FINAL"]])

    # Consolidar todas as descrições
    df_all = pd.concat(todas_contas, ignore_index=True)

    # Agrupar por descrição e somar valores
    agrupado = (
        df_all.groupby("DESCRICAO")["VL_SALDO_FINAL"]
        .agg(["sum", "count", "mean"])
        .sort_values("sum", ascending=False)
    )

    print(f"\n{'='*80}")
    print(f"📊 TOP {top_n} CONTAS CAPTURADAS PELO FILTRO")
    print(f"{'='*80}")
    print(f"{'Descrição':<80} {'Total (R$)':>20} {'Ocorr.':>8} {'Média':>15}")
    print(f"{'-'*80} {'-'*20} {'-'*8} {'-'*15}")

    total_geral = 0
    for desc, row in agrupado.head(top_n).iterrows():
        total = row["sum"]
        total_geral += total
        desc_curta = desc[:77] + "..." if len(desc) > 77 else desc
        print(
            f"{desc_curta:<80} {total:>20,.0f} {row['count']:>8,.0f} {row['mean']:>15,.0f}"
        )

    print(f"\n{'='*80}")
    print(f"💰 Total capturado: R$ {agrupado['sum'].sum():,.2f}")
    print(f"📊 Total de descrições únicas: {len(agrupado)}")
    print(f"{'='*80}")

    # Salvar em CSV para análise
    output_path = (
        Path(__file__).parent.parent
        / "data"
        / "processed"
        / f"diagnostico_filtro_{ano}.csv"
    )
    agrupado.to_csv(output_path)
    print(f"\n💾 Diagnóstico salvo em: {output_path}")

    # Análise de categorias suspeitas
    print(f"\n{'='*80}")
    print(f"⚠️  CATEGORIAS POTENCIALMENTE PROBLEMÁTICAS")
    print(f"{'='*80}")

    termos_suspeitos = [
        "PROVISÃO",
        "PROVISAO",
        "RESERVA",
        "ATIVO",
        "PASSIVO",
        "IMOBILIZADO",
        "INVESTIMENTO",
        "CAIXA",
        "DESPESA ADMIN",
        "RECEITA",
        "IMPOSTO",
        "TRIBUT",
        "DEPRECIAÇ",
    ]

    for termo in termos_suspeitos:
        mask_suspeito = agrupado.index.str.contains(termo, case=False, na=False)
        if mask_suspeito.any():
            total_suspeito = agrupado[mask_suspeito]["sum"].sum()
            count_suspeito = mask_suspeito.sum()
            print(f"  🔴 '{termo}': {count_suspeito} contas | R$ {total_suspeito:,.2f}")


if __name__ == "__main__":
    # Diagnosticar 2023 (o ano problemático) e 2024 (referência saudável)
    for ano in [2023, 2024]:
        try:
            diagnosticar(ano)
        except Exception as e:
            print(f"❌ Erro ao diagnosticar {ano}: {e}")
