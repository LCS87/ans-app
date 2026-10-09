"""
Verifica se 2026 está disponível e se passa no gate de qualidade.
Hoje é 07/10/2026 → esperamos 1T2026 e 2T2026 (talvez 3T2026).
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from etl.extract import ANSExtractor
from etl.validation import imprimir_relatorio, total_metodo_d, validar_ano

ANO, BASE = 2026, 2025
ext = ANSExtractor()

# 1) Tenta baixar 2026
try:
    from etl.download import download_demonstracoes

    download_demonstracoes(ANO)
except Exception as e:
    print(f"⚠️ Download automático indisponível: {e}")

zips = sorted((ext.raw_dir / str(ANO)).glob("*.zip"))
print(f"📦 ZIPs de {ANO}: {[z.name for z in zips]}")
if not zips:
    print("❌ Nenhum dado de 2026 disponível. Mantendo escopo 2024-2025.")
    sys.exit(0)


# 2) Monta df de 2026
def ler_ano(ano):
    dfs = []
    for f in ext.extract_zips(ano):
        d = ext._read_csv_demonstracao(f)
        d["TRIM"] = f.stem
        dfs.append(d)
    return pd.concat(dfs, ignore_index=True)


df26 = ler_ano(ANO)
df25 = ler_ano(BASE)

# 3) Total base (2025) para comparação
df25["CD_CONTA_CONTABIL"] = df25["CD_CONTA_CONTABIL"].fillna("").str.strip()
total_base = total_metodo_d(df25[df25["CD_CONTA_CONTABIL"].str.startswith("41")])

# 4) Gate de qualidade
veredito, checks = validar_ano(ANO, df26, total_base=total_base)
imprimir_relatorio(ANO, veredito, checks)

if veredito == "BLOQUEADO":
    print("🚫 2026 NÃO será importado (gate reprovou).")
else:
    print("✅ 2026 apto para importação. Rode o pipeline com ano=2026.")
