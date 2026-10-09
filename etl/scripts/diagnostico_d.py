"""
Diagnóstico dos casos onde D diverge drasticamente de A e B.
Investiga 421715 e 416428 em 2023.
"""

import sys
from pathlib import Path

import pandas as pd

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from etl.extract import ANSExtractor


def analisar_operadora(ano, reg_ans):
    """Analisa a árvore contábil completa de uma operadora."""
    ext = ANSExtractor()
    csv_files = ext.extract_zips(ano)

    dfs = []
    for f in csv_files:
        df = pd.read_csv(f, sep=";", encoding="utf-8", on_bad_lines="skip", dtype=str)
        df.columns = [c.upper().strip() for c in df.columns]
        df["VL_SALDO_FINAL"] = pd.to_numeric(df["VL_SALDO_FINAL"], errors="coerce").fillna(0)
        df["TRIM"] = f.stem
        df["CD_CONTA_CONTABIL"] = df["CD_CONTA_CONTABIL"].fillna("").str.strip()
        dfs.append(df)

    df = pd.concat(dfs, ignore_index=True)
    df = df[df["CD_CONTA_CONTABIL"].str.startswith("41")]
    df = df[df["REG_ANS"] == reg_ans]

    print(f"\n{'='*100}")
    print(f"OPERADORA {reg_ans} — ANO {ano}")
    print(f"{'='*100}")

    # Último valor por conta
    nz = df[df["VL_SALDO_FINAL"] != 0]
    last = nz.sort_values("TRIM").groupby(["REG_ANS", "CD_CONTA_CONTABIL"], as_index=False).tail(1)

    # Identificar folhas
    df_leaf = ext.marcar_folhas(last)
    folhas = df_leaf[df_leaf["is_lea"]]["CD_CONTA_CONTABIL"].tolist()

    print(f"\n📊 TODAS AS CONTAS (último trim não-zero):")
    print(f"{'CD_CONTA':<12} {'VALOR':>15} {'FOLHA':>8} {'DESCRICAO':<60}")
    print(f"{'-'*100}")

    for _, row in last.sort_values("CD_CONTA_CONTABIL").iterrows():
        cd = row["CD_CONTA_CONTABIL"]
        val = row["VL_SALDO_FINAL"]
        folha = "🍃" if cd in folhas else "  "
        desc = str(row["DESCRICAO"])[:60]
        print(f"{cd:<12} R$ {val:>13,.0f} {folha:>8} {desc:<60}")

    # Análise por raiz
    contas_set = set(last["CD_CONTA_CONTABIL"])
    raizes = [c for c in contas_set if not any(c[:L] in contas_set for L in range(1, len(c)))]

    print(f"\n🌱 RAÍzes DE VALOR (sem ancestral com valor):")
    print(f"{'RAIZ':<12} {'VALOR':>15} {'FOLHAS DESC':>20} {'SOMA FOLHAS':>15}")
    print(f"{'-'*70}")

    total_A = 0.0  # folhas
    total_B = 0.0  # raízes
    total_D = 0.0  # híbrido

    for raiz in sorted(raizes):
        # Folhas descendentes
        folhas_desc = [c for c in folhas if c.startswith(raiz) and c != raiz]

        valor_raiz = last[last["CD_CONTA_CONTABIL"] == raiz]["VL_SALDO_FINAL"].sum()
        soma_folhas = last[last["CD_CONTA_CONTABIL"].isin(folhas_desc)]["VL_SALDO_FINAL"].sum()

        # Método A (folhas)
        total_A += soma_folhas

        # Método B (raízes)
        total_B += valor_raiz

        # Método D (híbrido)
        if len(folhas_desc) == 0:
            # Caso 1: só raiz
            valor_d = valor_raiz
        elif soma_folhas >= 0.9 * valor_raiz:
            # Caso 2: folhas cobrem bem
            valor_d = soma_folhas
        elif soma_folhas > valor_raiz:
            # Caso 4: folhas > raiz (raiz subdeclarada)
            valor_d = soma_folhas
        else:
            # Caso 3: folhas incompletas
            valor_d = valor_raiz

        total_D += valor_d

        print(f"{raiz:<12} R$ {valor_raiz:>13,.0f} {len(folhas_desc):>20} R$ {soma_folhas:>13,.0f}")
        if folhas_desc:
            for f in sorted(folhas_desc):
                val_f = last[last["CD_CONTA_CONTABIL"] == f]["VL_SALDO_FINAL"].sum()
                print(f"  └─ {f:<10} R$ {val_f:>13,.0f}")

    print(f"\n{'='*100}")
    print("📊 TOTAIS:")
    print(f"   A (folhas):  R$ {total_A:>13,.0f}")
    print(f"   B (raízes):  R$ {total_B:>13,.0f}")
    print(f"   D (híbrido): R$ {total_D:>13,.0f}")
    print(f"{'='*100}")


if __name__ == "__main__":
    analisar_operadora(2023, "421715")
    analisar_operadora(2023, "416428")
