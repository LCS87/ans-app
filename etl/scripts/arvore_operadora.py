"""
Reconstrói a árvore contábil completa 411 de uma operadora nos 4 trimestres.

Objetivo: revelar se a ANS está:
  - mudando o código da conta entre trimestres
  - mudando a granularidade (pai vs folha)
  - acumulando valores
  - simplesmente não reportando aquela conta

Saída: tabela com código | descrição | 1T | 2T | 3T | 4T | is_leaf
"""

import sys
from pathlib import Path

import pandas as pd

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from etl.extract import ANSExtractor


def reconstruir_arvore(ano: int, reg_ans: str):
    ext = ANSExtractor()
    csv_files = ext.extract_zips(ano)

    dfs = []
    for f in csv_files:
        df = pd.read_csv(f, sep=";", encoding="utf-8", on_bad_lines="skip", dtype=str)
        df.columns = [c.upper().strip() for c in df.columns]
        df["VL_SALDO_FINAL"] = pd.to_numeric(df["VL_SALDO_FINAL"], errors="coerce").fillna(0)
        df["TRIM"] = f.stem  # 1T2025, 2T2025...
        dfs.append(df)

    df_all = pd.concat(dfs, ignore_index=True)
    df_all["CD_CONTA_CONTABIL"] = df_all["CD_CONTA_CONTABIL"].fillna("").str.strip()

    # Filtrar operadora + ramo 411 (inteiro, incluindo sintéticas)
    mask = (df_all["REG_ANS"].astype(str).str.strip() == str(reg_ans)) & (
        df_all["CD_CONTA_CONTABIL"].str.startswith("411")
    )
    df_op = df_all[mask].copy()

    print(f"\n🏥 Operadora: {reg_ans}  |  📅 Ano: {ano}")
    print(f"📊 Total de registros no ramo 411: {len(df_op):,}")

    # Pivot: (REG_ANS, CD_CONTA_CONTABIL, DESCRICAO) × TRIM
    pivot = df_op.pivot_table(
        index=["CD_CONTA_CONTABIL", "DESCRICAO"],
        columns="TRIM",
        values="VL_SALDO_FINAL",
        aggfunc="sum",
    ).reset_index()

    # Garantir os 4 trimestres
    trims = [f"{i}T{ano}" for i in range(1, 5)]
    for t in trims:
        if t not in pivot.columns:
            pivot[t] = None
    pivot = pivot[["CD_CONTA_CONTABIL", "DESCRICAO"] + trims]

    # Ordenar por código (ordem hierárquica natural)
    pivot = pivot.sort_values("CD_CONTA_CONTABIL").reset_index(drop=True)

    # Detectar folha: não existe outro código no mesmo DataFrame
    # que comece com ele e seja mais longo
    cods = set(pivot["CD_CONTA_CONTABIL"].tolist())

    def eh_folha(c):
        for outro in cods:
            if outro != c and outro.startswith(c) and len(outro) > len(c):
                return False
        return True

    pivot["is_lea"] = pivot["CD_CONTA_CONTABIL"].apply(eh_folha)

    # ====================================================================
    # Impressão tabular
    # ====================================================================
    def fmt(v):
        if v is None or pd.isna(v) or v == 0:
            return "—"
        if v >= 1_000_000_000:
            return f"{v/1e9:>10.2f}Bi"
        if v >= 1_000_000:
            return f"{v/1e6:>10.2f}Mi"
        if v >= 1_000:
            return f"{v/1e3:>10.2f}k"
        return f"{v:>13,.0f}"

    sep = "─"
    print(f"\n{sep*110}")
    print(f"{'CÓDIGO':<12} {'DESCRIÇÃO':<55} " f"{'1T':>11} {'2T':>11} {'3T':>11} {'4T':>11} leaf")
    print(sep * 110)

    for _, row in pivot.iterrows():
        cod = row["CD_CONTA_CONTABIL"]
        desc = str(row["DESCRICAO"])[:55]
        marker = "🍃" if row["is_lea"] else "  "
        v1 = fmt(row.get(f"1T{ano}"))
        v2 = fmt(row.get(f"2T{ano}"))
        v3 = fmt(row.get(f"3T{ano}"))
        v4 = fmt(row.get(f"4T{ano}"))
        print(f"{cod:<12} {desc:<55} {v1:>11} {v2:>11} {v3:>11} {v4:>11} {marker}")

    print(sep * 110)

    # Totais
    print("\n📊 TOTAIS POR TRIMESTRE (soma de TODOS os registros 411, incl. sintéticas):")
    for t in trims:
        total = pivot[t].sum()
        print(f"   {t}: R$ {total:>18,.0f}")

    print("\n📊 TOTAIS POR TRIMESTRE (somente folhas 411):")
    folhas = pivot[pivot["is_leaf"] == True]
    for t in trims:
        total = folhas[t].sum()
        print(f"   {t}: R$ {total:>18,.0f}")

    # Diagnóstico de padrão
    print("\n🔬 DIAGNÓSTICO DE PADRÃO (folhas 411):")
    vals = [folhas[t].sum() for t in trims]
    presentes = [(t, v) for t, v in zip(trims, vals) if v > 0]

    if len(presentes) == 0:
        print("   ⚠️  Nenhum valor em nenhum trimestre")
    elif len(presentes) == 1:
        print(
            f"   ⚠️  Valor em apenas 1 trimestre ({presentes[0][0]}): " f"R$ {presentes[0][1]:,.0f}"
        )
        print("   → lacuna nos outros trimestres ou reporte único")
    else:
        vs = [v for _, v in presentes]
        diffs = [vs[i + 1] - vs[i] for i in range(len(vs) - 1)]
        if all(d > 0 for d in diffs):
            print("   ✅ ACUMULADO (crescimento monotônico)")
            print(f"   → anual correto = último valor disponível = R$ {vs[-1]:,.0f}")
        elif all(abs(d) < max(vs) * 0.3 for d in diffs):
            print("   ✅ TRIMESTRAL (valores estáveis)")
            print(f"   → anual correto = soma = R$ {sum(vs):,.0f}")
        else:
            print("   ⚠️  MISTO/IRREGULAR")
            print(f"   → diffs: {[f'R$ {d:,.0f}' for d in diffs]}")
            print("   → precisa análise manual da conta específica")


if __name__ == "__main__":
    # Hapvida — a operadora mais interessante para diagnóstico
    print("=" * 80)
    print("🔬 RECONSTRUÇÃO DE ÁRVORE 411 — HAPVIDA (359017) EM 2025")
    print("=" * 80)
    reconstruir_arvore(2025, "359017")

    print("\n\n" + "=" * 80)
    print("🔬 RECONSTRUÇÃO DE ÁRVORE 411 — 303623 EM 2025 (caso acumulado)")
    print("=" * 80)
    reconstruir_arvore(2025, "303623")
