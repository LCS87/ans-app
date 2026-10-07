"""
Validação CORRETA: as contas 411 FOLHA são acumuladas ou movimento trimestral?
"""

import sys
from pathlib import Path
import pandas as pd

# Ajustar path para encontrar os módulos do projeto
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from etl.extract import ANSExtractor

ext = ANSExtractor()

print("=" * 80)
print("VALIDAÇÃO: CONTAS 411 FOLHA - ACUMULADAS OU TRIMESTRAIS?")
print("=" * 80)

# Ler todos os trimestres de 2025
ano = 2025
csv_files = ext.extract_zips(ano)

dfs = []
for f in csv_files:
    df = pd.read_csv(f, sep=";", encoding="utf-8", on_bad_lines="skip", dtype=str)
    df.columns = [c.upper().strip() for c in df.columns]
    df["VL_SALDO_FINAL"] = pd.to_numeric(df["VL_SALDO_FINAL"], errors="coerce").fillna(
        0
    )
    df["TRIM"] = f.stem
    dfs.append(df)

df_all = pd.concat(dfs, ignore_index=True)

# Aplicar is_leaf
df_all = ext.marcar_folhas(df_all)

# Filtrar APENAS folhas 411 com valor > 0
df_folhas = df_all[
    (df_all["is_leaf"] == True)
    & (df_all["CD_CONTA_CONTABIL"].str.startswith("411"))
    & (df_all["VL_SALDO_FINAL"] > 0)
].copy()

print(f"\n📊 Total de folhas 411 com valor > 0: {len(df_folhas):,}")

# Testar com Top 5 operadoras por soma total
print("\n" + "=" * 80)
print("TOP 5 OPERADORAS - ANÁLISE TRIMESTRAL")
print("=" * 80)

top_ops = (
    df_folhas.groupby("REG_ANS")["VL_SALDO_FINAL"]
    .sum()
    .sort_values(ascending=False)
    .head(5)
    .index.tolist()
)

for reg in top_ops:
    print(f"\n{'─'*80}")
    print(f"🏥 Operadora: {reg}")

    df_op = df_folhas[df_folhas["REG_ANS"].astype(str) == reg].copy()

    # Pegar a conta 411 folha com MAIOR valor total
    conta_maior = (
        df_op.groupby("CD_CONTA_CONTABIL")["VL_SALDO_FINAL"]
        .sum()
        .sort_values(ascending=False)
        .index[0]
    )

    df_conta = df_op[df_op["CD_CONTA_CONTABIL"] == conta_maior].copy()

    print(f"📊 Conta: {conta_maior} (maior valor)")
    print(f"   Descrição: {df_conta['DESCRICAO'].iloc[0][:60]}")

    vals = {}
    for trim in ["1T2025", "2T2025", "3T2025", "4T2025"]:
        df_trim = df_conta[df_conta["TRIM"] == trim]
        if not df_trim.empty:
            vals[trim] = df_trim["VL_SALDO_FINAL"].sum()
            print(f"   {trim}: R$ {vals[trim]:>15,.2f}")
        else:
            print(f"   {trim}: (sem dados)")

    # Análise
    if len(vals) >= 2:
        v_list = list(vals.values())
        diffs = [v_list[i + 1] - v_list[i] for i in range(len(v_list) - 1)]

        # Se valores crescem monotonicamente → ACUMULADO
        if all(d > 0 for d in diffs):
            print(f"   ✅ ACUMULADO (valores crescem)")
            print(f"   → CORRETO: usar ÚLTIMO trimestre = R$ {v_list[-1]:,.2f}")
        # Se valores estáveis (variação < 30%) → TRIMESTRAL
        elif all(abs(d) < v_list[0] * 0.3 for d in diffs) and all(
            v > 0 for v in v_list
        ):
            print(f"   ✅ TRIMESTRAL (valores estáveis)")
            print(f"   → CORRETO: SOMAR todos = R$ {sum(v_list):,.2f}")
        else:
            print(f"   ⚠️  IRREGULAR → usar último trim disponível")

print("\n" + "=" * 80)
print("CONCLUSÃO E RECOMENDAÇÃO")
print("=" * 80)
print(
    """
Se as contas 411 FOLHA forem:

1. ACUMULADAS (100 → 200 → 300 → 400)
   → Usar valor do 4T como anual
   → Nosso método "último trim por conta" está CORRETO

2. TRIMESTRAIS (100 → 100 → 100 → 100)
   → Somar 1T + 2T + 3T + 4T
   → Nosso método está ERRADO (subestima por ~4x)

3. IRREGULARES
   → Usar último trimestre disponível (conservador)
"""
)
