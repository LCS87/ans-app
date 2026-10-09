"""
Comparação 2024 × 2025 × 2026 (parcial) usando Método D.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from etl.extract import ANSExtractor

ext = ANSExtractor()

anos = [2024, 2025, 2026]
dfs = {}
for ano in anos:
    try:
        dfs[ano] = ext.processar_ano(ano)[["REG_ANS", "RAZAO_SOCIAL", "gasto_total"]].rename(
            columns={"gasto_total": f"g{ano}"}
        )
    except Exception as e:
        print(f"⚠️  Ano {ano} indisponível: {e}")

# Merge
m = dfs[2024]
for ano in anos[1:]:
    if ano in dfs:
        m = m.merge(dfs[ano][["REG_ANS", f"g{ano}"]], on="REG_ANS", how="outer")

m = m.fillna(0)

# Variações
if 2025 in dfs:
    m["d25-24"] = (m["g2025"] - m["g2024"]) / m["g2024"].replace(0, float("nan")) * 100
if 2026 in dfs:
    m["d26-25"] = (m["g2026"] - m["g2025"]) / m["g2025"].replace(0, float("nan")) * 100

# Top 20
top = m.sort_values("g2025", ascending=False).head(20)
print(
    f"\n{'REG':<8} {'OPERADORA':<35} {'2024':>10} {'2025':>10} {'2026*':>10} {'Δ25':>8} {'Δ26':>8}"
)
print("-" * 95)
for _, r in top.iterrows():
    nome = str(r.get("RAZAO_SOCIAL", ""))[:33]
    g24 = f"{r['g2024']/1e9:.2f}Bi"
    g25 = f"{r['g2025']/1e9:.2f}Bi"
    g26 = f"{r['g2026']/1e9:.2f}Bi" if "g2026" in r else "—"
    d25 = f"{r['d25-24']:.1f}%" if pd.notna(r.get("d25-24")) else "novo"
    d26 = f"{r['d26-25']:.1f}%" if pd.notna(r.get("d26-25")) else "—"
    print(f"{r['REG_ANS']:<8} {nome:<35} {g24:>10} {g25:>10} {g26:>10} {d25:>8} {d26:>8}")

print(f"\n* 2026 é parcial (apenas 1T + 2T disponíveis)")
print(f"\nTotais:")
print(f"  2024: R$ {m['g2024'].sum()/1e9:.1f} Bi")
print(f"  2025: R$ {m['g2025'].sum()/1e9:.1f} Bi")
if "g2026" in m:
    print(f"  2026 (parcial): R$ {m['g2026'].sum()/1e9:.1f} Bi")
