"""
Diagnóstico estrutural dos dados da ANS.
Objetivo: entender hierarquia de contas, saldos, e acumulação trimestral.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from etl.extract import ANSExtractor


def diagnosticar_estrutura(ano: int = 2024):
    """Analisa estrutura dos dados da ANS."""
    extractor = ANSExtractor()

    print("=" * 80)
    print(f"🔬 DIAGNÓSTICO ESTRUTURAL - ANO {ano}")
    print("=" * 80)

    # Extrair apenas o primeiro trimestre
    csv_files = extractor.extract_zips(ano)
    csv_1t = [f for f in csv_files if "1T" in f.stem][0]

    print(f"\n📄 Analisando: {csv_1t.name}")

    # Ler CSV completo (sem filtro)
    df = pd.read_csv(csv_1t, sep=";", encoding="utf-8", on_bad_lines="skip", dtype=str)
    df.columns = [c.upper().strip() for c in df.columns]

    # 1. Listar TODAS as colunas disponíveis
    print("\n" + "=" * 80)
    print("📋 COLUNAS DISPONÍVEIS")
    print("=" * 80)
    for col in df.columns:
        print(f"  • {col}")

    # 2. Verificar se existe CD_CONTA_CONTABIL
    col_conta = None
    for col in df.columns:
        if "CD_CONTA" in col or "CODIGO" in col or "CONTA_CONTABIL" in col:
            col_conta = col
            break

    if col_conta:
        print(f"\n✅ Coluna de código contábil encontrada: {col_conta}")
    else:
        print(f"\n❌ NÃO há coluna de código contábil!")
        print("   Contas disponíveis:", [c for c in df.columns if "CONT" in c.upper()])

    # 3. Verificar se existe VL_SALDO_INICIAL e VL_SALDO_FINAL
    col_inicial = None
    col_final = None
    for col in df.columns:
        if "INICIAL" in col:
            col_inicial = col
        if "FINAL" in col:
            col_final = col

    print(f"\n📊 Colunas de saldo:")
    print(f"   • Saldo Inicial: {col_inicial or 'NÃO ENCONTRADO'}")
    print(f"   • Saldo Final: {col_final or 'NÃO ENCONTRADO'}")

    # 4. Filtrar por uma operadora específica (maior gasto)
    print("\n" + "=" * 80)
    print("🏥 ANÁLISE DE UMA OPERADORA ESPECÍFICA")
    print("=" * 80)

    # Pegar operadora com mais registros
    reg_counts = df["REG_ANS"].value_counts()
    operadora_exemplo = reg_counts.index[0]
    print(
        f"Operadora com mais registros: {operadora_exemplo} ({reg_counts.iloc[0]} registros)"
    )

    df_op = df[df["REG_ANS"] == operadora_exemplo].copy()

    # Converter valores
    if col_final:
        df_op[col_final] = pd.to_numeric(df_op[col_final], errors="coerce").fillna(0)
    if col_inicial:
        df_op[col_inicial] = pd.to_numeric(df_op[col_inicial], errors="coerce").fillna(
            0
        )

    # Mostrar colunas relevantes
    cols_mostrar = ["DESCRICAO"]
    if col_conta:
        cols_mostrar.insert(0, col_conta)
    if col_inicial:
        cols_mostrar.append(col_inicial)
    if col_final:
        cols_mostrar.append(col_final)

    print(f"\n📊 Top 50 contas da operadora {operadora_exemplo}:")
    print("=" * 80)

    df_sorted = df_op.sort_values(
        col_final if col_final else "DESCRICAO", ascending=False
    )
    for idx, row in df_sorted.head(50).iterrows():
        desc = row["DESCRICAO"][:60]
        valor_final = row.get(col_final, 0) if col_final else 0
        valor_inicial = row.get(col_inicial, 0) if col_inicial else 0
        codigo = row.get(col_conta, "N/A") if col_conta else "N/A"

        print(
            f"{codigo:<10} | {desc:<60} | Inicial: {valor_inicial:>15,.0f} | Final: {valor_final:>15,.0f}"
        )

    # 5. Verificar acumulação trimestral (comparar 1T vs 2T)
    print("\n" + "=" * 80)
    print("📅 VERIFICAÇÃO DE ACUMULAÇÃO TRIMESTRAL")
    print("=" * 80)

    csv_2t = [f for f in csv_files if "2T" in f.stem][0]
    df_2t = pd.read_csv(
        csv_2t, sep=";", encoding="utf-8", on_bad_lines="skip", dtype=str
    )
    df_2t.columns = [c.upper().strip() for c in df_2t.columns]

    # Filtrar mesma operadora no 2T
    df_op_2t = df_2t[df_2t["REG_ANS"] == operadora_exemplo].copy()
    if col_final:
        df_op_2t[col_final] = pd.to_numeric(
            df_op_2t[col_final], errors="coerce"
        ).fillna(0)

    # Comparar uma conta específica que existe em ambos
    conta_exemplo = df_op["DESCRICAO"].iloc[0] if len(df_op) > 0 else None

    if conta_exemplo:
        valor_1t = (
            df_op[df_op["DESCRICAO"] == conta_exemplo][col_final].sum()
            if col_final
            else 0
        )
        valor_2t = (
            df_op_2t[df_op_2t["DESCRICAO"] == conta_exemplo][col_final].sum()
            if col_final
            else 0
        )

        print(f"\nConta exemplo: {conta_exemplo[:70]}")
        print(f"  • Valor no 1T: R$ {valor_1t:,.0f}")
        print(f"  • Valor no 2T: R$ {valor_2t:,.0f}")

        if valor_2t > valor_1t:
            print(f"  ⚠️  2T > 1T → Possível ACUMULAÇÃO (não trimestral)")
        else:
            print(f"  ✅ 2T ≤ 1T → Trimestral independente")

    # 6. Contar contas sintéticas vs analíticas
    print("\n" + "=" * 80)
    print("🌳 HIERARQUIA DE CONTAS")
    print("=" * 80)

    if col_conta:
        # Verificar níveis hierárquicos pelo código
        df_op["NIVEL"] = df_op[col_conta].str.len()
        niveis = df_op["NIVEL"].value_counts().sort_index()
        print(f"\nNíveis hierárquicos detectados:")
        for nivel, count in niveis.items():
            print(f"  • Nível {nivel}: {count} contas")

        # Contas com menor nível (sintéticas) vs maior nível (analíticas)
        nivel_min = niveis.index.min()
        nivel_max = niveis.index.max()

        contas_sinteticas = df_op[df_op["NIVEL"] == nivel_min]
        contas_analiticas = df_op[df_op["NIVEL"] == nivel_max]

        print(f"\n📊 Contas sintéticas (nível {nivel_min}): {len(contas_sinteticas)}")
        print(f"📊 Contas analíticas (nível {nivel_max}): {len(contas_analiticas)}")
    else:
        print("❌ Não é possível determinar hierarquia sem código contábil")


if __name__ == "__main__":
    diagnosticar_estrutura(2024)
