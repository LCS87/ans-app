"""
Mapeamento de códigos contábeis para despesas assistenciais.
Usa CD_CONTA_CONTABIL em vez de regex em DESCRICAO.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from etl.extract import ANSExtractor


def mapear_contas_assistenciais(ano: int = 2024):
    """Identifica códigos contábeis de despesas assistenciais."""
    extractor = ANSExtractor()

    print("=" * 80)
    print(f"🗺️  MAPEAMENTO DE CONTAS ASSISTENCIAIS - ANO {ano}")
    print("=" * 80)

    # Extrair todos os trimestres
    csv_files = extractor.extract_zips(ano)

    # Consolidar todos os trimestres
    dfs = []
    for csv_file in csv_files:
        df = pd.read_csv(
            csv_file, sep=";", encoding="utf-8", on_bad_lines="skip", dtype=str
        )
        df.columns = [c.upper().strip() for c in df.columns]
        dfs.append(df)

    df_all = pd.concat(dfs, ignore_index=True)

    # Converter valores
    df_all["VL_SALDO_FINAL"] = pd.to_numeric(
        df_all["VL_SALDO_FINAL"], errors="coerce"
    ).fillna(0)

    # 1. Filtrar apenas contas analíticas (9 dígitos)
    df_analiticas = df_all[df_all["CD_CONTA_CONTABIL"].str.len() == 9].copy()
    print(f"\n📊 Total de contas analíticas: {len(df_analiticas):,}")

    # 2. Filtrar apenas contas de resultado (3xx, 4xx)
    df_resultado = df_analiticas[
        df_analiticas["CD_CONTA_CONTABIL"].str.match(r"^[34]")
    ].copy()
    print(f"📊 Contas de resultado (3xx, 4xx): {len(df_resultado):,}")

    # 3. Agrupar por código + descrição
    contas_agrupadas = (
        df_resultado.groupby(["CD_CONTA_CONTABIL", "DESCRICAO"])["VL_SALDO_FINAL"]
        .agg(["sum", "count"])
        .sort_values("sum", ascending=False)
        .reset_index()
    )

    # 4. Mostrar TOP 100 contas de despesas
    print("\n" + "=" * 80)
    print("🔥 TOP 100 CONTAS DE DESPESAS (por valor total)")
    print("=" * 80)

    # Filtrar apenas despesas (não receitas)
    # Tipicamente: 4xxx são despesas, 3xxx são receitas
    despesas = contas_agrupadas[
        contas_agrupadas["CD_CONTA_CONTABIL"].str.startswith("4")
    ]

    print(f"\nTotal de contas de despesas (4xxx): {len(despesas):,}")
    print(f"Soma total: R$ {despesas['sum'].sum():,.2f}\n")

    for idx, row in despesas.head(100).iterrows():
        codigo = row["CD_CONTA_CONTABIL"]
        desc = row["DESCRICAO"][:70]
        total = row["sum"]
        count = row["count"]

        # Marcar contas relevantes
        marcador = ""
        desc_lower = row["DESCRICAO"].lower()

        if "evento" in desc_lower or "sinistro" in desc_lower:
            marcador = "⭐ EVENTO/SINISTRO"
        elif "assist" in desc_lower:
            marcador = "🏥 ASSISTENCIAL"
        elif "provis" in desc_lower or "peona" in desc_lower:
            marcador = "⚠️  PROVISÃO"
        elif "variação" in desc_lower or "variacao" in desc_lower:
            marcador = "📊 VARIAÇÃO"

        print(f"{codigo} | {desc:<70} | R$ {total:>15,.0f} | {count:>5}x | {marcador}")

    # 5. Identificar contas de eventos/sinistros especificamente
    print("\n" + "=" * 80)
    print("🎯 CONTAS DE EVENTOS/SINISTROS (códigos específicos)")
    print("=" * 80)

    eventos_sinistros = despesas[
        despesas["DESCRICAO"].str.contains("EVENTO|SINISTRO", case=False, na=False)
    ]

    print(f"\nTotal de contas de eventos/sinistros: {len(eventos_sinistros):,}")
    print(f"Soma total: R$ {eventos_sinistros['sum'].sum():,.2f}\n")

    for idx, row in eventos_sinistros.head(50).iterrows():
        codigo = row["CD_CONTA_CONTABIL"]
        desc = row["DESCRICAO"][:80]
        total = row["sum"]
        print(f"{codigo} | {desc:<80} | R$ {total:>15,.0f}")

    # 6. Salvar mapeamento completo
    output_path = (
        Path(__file__).parent.parent / "data" / "processed" / "mapeamento_contas.csv"
    )
    despesas.to_csv(output_path, index=False)
    print(f"\n💾 Mapeamento salvo: {output_path}")

    # 7. Resumo final
    print("\n" + "=" * 80)
    print("📋 RESUMO DO MAPEAMENTO")
    print("=" * 80)

    print(
        f"""
✅ Estratégia correta identificada:

1. Filtrar APENAS contas analíticas (CD_CONTA_CONTABIL com 9 dígitos)
2. Filtrar APENAS contas de despesas (códigos 4xxx)
3. Identificar códigos específicos de:
   - Eventos/sinistros conhecidos (41xx, 42xx?)
   - Despesas com eventos (43xx?)
   - Provisões (44xx?)
   - Variações de provisão (45xx?)

⚠️  Próximos passos:
   - Mapear códigos exatos de cada categoria
   - Excluir provisões e variações (não são despesas realizadas)
   - Usar apenas eventos/sinistros conhecidos (despesas reais)
"""
    )


if __name__ == "__main__":
    mapear_contas_assistenciais(2024)
