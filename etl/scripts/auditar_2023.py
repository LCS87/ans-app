"""
Auditoria profunda de 2023 para explicar o salto de R$ 152 Bi.
Compara 2023 vs 2024 vs 2025 em 5 dimensões.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from etl.extract import ANSExtractor, CODIGOS_DESPESAS_ASSISTENCIAIS, CODIGOS_EXCLUIR


def ler_csvs_com_filtro(ano: int):
    """Lê CSVs aplicando o filtro atual por código contábil."""
    extractor = ANSExtractor()
    csv_files = extractor.extract_zips(ano)
    
    dfs = []
    for csv_file in csv_files:
        trimestre = csv_file.stem  # ex: '1T2024'
        df = pd.read_csv(csv_file, sep=';', encoding='utf-8', 
                         on_bad_lines='skip', dtype=str)
        df.columns = [c.upper().strip() for c in df.columns]
        df['TRIMESTRE'] = trimestre
        df['VL_SALDO_FINAL'] = pd.to_numeric(
            df['VL_SALDO_FINAL'], errors='coerce'
        ).fillna(0)
        dfs.append(df)
    
    df_all = pd.concat(dfs, ignore_index=True)
    
    # Aplicar o MESMO filtro do ETL
    mask_analitica = df_all['CD_CONTA_CONTABIL'].str.len() == 9
    mask_eventos = df_all['CD_CONTA_CONTABIL'].str.match(r'^411')
    mask_sem_provisao = ~df_all['CD_CONTA_CONTABIL'].str.match(r'^414')
    mask_sem_admin = ~df_all['CD_CONTA_CONTABIL'].str.match(r'^46')
    mask_positivo = df_all['VL_SALDO_FINAL'] > 0
    
    return df_all[mask_analitica & mask_eventos & mask_sem_provisao & 
                  mask_sem_admin & mask_positivo].copy()


def auditar_ano(df: pd.DataFrame, ano: int):
    """Auditoria completa de um ano."""
    print(f"\n{'='*80}")
    print(f"🔍 AUDITORIA {ano}")
    print(f"{'='*80}")
    
    # 1. Estatísticas gerais
    print(f"\n📊 ESTATÍSTICAS DO VALOR (VL_SALDO_FINAL):")
    desc = df['VL_SALDO_FINAL'].describe()
    for stat, val in desc.items():
        print(f"  {stat:>10}: R$ {val:>20,.2f}")
    
    total = df['VL_SALDO_FINAL'].sum()
    print(f"\n  💰 SOMA TOTAL: R$ {total:,.2f}")
    print(f"  📦 Registros: {len(df):,}")
    print(f"  🏢 Operadoras únicas: {df['REG_ANS'].nunique()}")
    
    # 2. Top 30 registros individuais (linha a linha)
    print(f"\n🔥 TOP 30 REGISTROS INDIVIDUAIS:")
    print(f"{'REG_ANS':>10} | {'CD_CONTA':>10} | {'VALOR':>20} | {'DESCRICAO':<40}")
    print("-" * 90)
    top_reg = df.nlargest(30, 'VL_SALDO_FINAL')
    for _, row in top_reg.iterrows():
        desc_curta = str(row['DESCRICAO'])[:40]
        print(f"{row['REG_ANS']:>10} | {row['CD_CONTA_CONTABIL']:>10} | "
              f"R$ {row['VL_SALDO_FINAL']:>18,.2f} | {desc_curta}")
    
    # 3. Top 30 operadoras (agrupado)
    print(f"\n🏆 TOP 30 OPERADORAS (soma por REG_ANS):")
    por_op = (df.groupby('REG_ANS')['VL_SALDO_FINAL']
              .agg(['sum', 'count', 'mean', 'max'])
              .sort_values('sum', ascending=False))
    
    print(f"{'REG_ANS':>10} | {'SOMA':>18} | {'COUNT':>6} | {'MÉDIA':>15} | {'MAX':>15}")
    print("-" * 75)
    for reg, row in por_op.head(30).iterrows():
        print(f"{reg:>10} | R$ {row['sum']:>15,.2f} | {row['count']:>6.0f} | "
              f"R$ {row['mean']:>12,.2f} | R$ {row['max']:>12,.2f}")
    
    # 4. Detecção de outliers (IQR)
    Q1 = df['VL_SALDO_FINAL'].quantile(0.25)
    Q3 = df['VL_SALDO_FINAL'].quantile(0.75)
    IQR = Q3 - Q1
    limite = Q3 + 1.5 * IQR
    outliers = df[df['VL_SALDO_FINAL'] > limite]
    
    print(f"\n🚨 DETECÇÃO DE OUTLIERS (IQR 1.5x):")
    print(f"  Q1:           R$ {Q1:,.2f}")
    print(f"  Q3:           R$ {Q3:,.2f}")
    print(f"  IQR:          R$ {IQR:,.2f}")
    print(f"  Limite:       R$ {limite:,.2f}")
    print(f"  Outliers:     {len(outliers):,} registros ({len(outliers)/len(df)*100:.1f}%)")
    print(f"  Soma outliers: R$ {outliers['VL_SALDO_FINAL'].sum():,.2f} "
          f"({outliers['VL_SALDO_FINAL'].sum()/total*100:.1f}% do total)")
    
    # 5. Por trimestre
    print(f"\n📅 POR TRIMESTRE:")
    por_trim = (df.groupby('TRIMESTRE')['VL_SALDO_FINAL']
                .agg(['count', 'sum', 'mean', 'max']))
    print(f"{'TRIM':>5} | {'COUNT':>7} | {'SOMA':>20} | {'MÉDIA':>15} | {'MAX':>15}")
    print("-" * 75)
    for trim, row in por_trim.iterrows():
        print(f"{trim:>5} | {row['count']:>7.0f} | R$ {row['sum']:>17,.2f} | "
              f"R$ {row['mean']:>12,.2f} | R$ {row['max']:>12,.2f}")
    
    # 6. Por código contábil (top 10)
    print(f"\n🔢 TOP 10 CÓDIGOS CONTÁBEIS:")
    por_cd = (df.groupby('CD_CONTA_CONTABIL')['VL_SALDO_FINAL']
              .agg(['count', 'sum'])
              .sort_values('sum', ascending=False))
    print(f"{'CÓDIGO':>12} | {'COUNT':>7} | {'SOMA':>20}")
    print("-" * 50)
    for cd, row in por_cd.head(10).iterrows():
        print(f"{cd:>12} | {row['count']:>7.0f} | R$ {row['sum']:>17,.2f}")
    
    return {
        'ano': ano,
        'total': total,
        'registros': len(df),
        'operadoras': df['REG_ANS'].nunique(),
        'media': desc['mean'],
        'mediana': desc['50%'],
        'maximo': desc['max'],
        'outliers_pct': len(outliers)/len(df)*100,
        'outliers_soma_pct': outliers['VL_SALDO_FINAL'].sum()/total*100,
    }


def main():
    print("="*80)
    print("🔬 AUDITORIA COMPARATIVA 2023 vs 2024 vs 2025")
    print("="*80)
    
    resultados = []
    for ano in [2023, 2024, 2025]:
        try:
            df = ler_csvs_com_filtro(ano)
            stats = auditar_ano(df, ano)
            resultados.append(stats)
        except Exception as e:
            print(f"❌ Erro ao auditar {ano}: {e}")
    
    # Tabela comparativa
    print(f"\n\n{'='*80}")
    print(f"📊 TABELA COMPARATIVA")
    print(f"{'='*80}")
    df_comp = pd.DataFrame(resultados).set_index('ano')
    print(df_comp.to_string(float_format=lambda x: f"R$ {x:,.2f}"))
    
    # Análise de proporção
    print(f"\n🔍 ANÁLISE DE PROPORÇÃO:")
    if len(resultados) >= 2:
        r23 = next((r for r in resultados if r['ano'] == 2023), None)
        r24 = next((r for r in resultados if r['ano'] == 2024), None)
        r25 = next((r for r in resultados if r['ano'] == 2025), None)
        
        if r23 and r24:
            print(f"  2023/2024 (total):    {r23['total']/r24['total']:.2f}x")
            print(f"  2023/2024 (média):    {r23['media']/r24['media']:.2f}x")
            print(f"  2023/2024 (mediana):  {r23['mediana']/r24['mediana']:.2f}x")
            print(f"  2023/2024 (max):      {r23['maximo']/r24['maximo']:.2f}x")
            print(f"  2023/2024 (registros): {r23['registros']/r24['registros']:.2f}x")
        
        if r23 and r25:
            print(f"  2023/2025 (total):    {r23['total']/r25['total']:.2f}x")


if __name__ == "__main__":
    main()