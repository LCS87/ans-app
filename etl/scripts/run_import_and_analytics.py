import re
import os
from pathlib import Path
import pandas as pd
import logging
from etl.transform.prepare_demonstracoes_contabeis import extract_all_zips, consolidate_demonstracoes, INTERIM_DIR

# Configuração de Log para monitorar o processamento
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

CATEGORY = 'EVENTOS/ SINISTROS CONHECIDOS OU AVISADOS DE ASSISTÊNCIA A SAÚDE MEDICO HOSPITALAR'

def clean_numeric(s):
    """Converte padrão monetário brasileiro (milhar com ponto, decimal com vírgula)."""
    if pd.isna(s) or str(s).strip().lower() in ['nan', 'none', '']:
        return 0.0
    s = str(s).strip()
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        return float(re.sub(r'[^\d.-]', '', s))
    except:
        return 0.0

def get_desacumulado(df_subset):
    """Subtrai o trimestre anterior do atual para obter o gasto real do período."""
    df = df_subset.copy()
    df = df.sort_values(['reg_ans', 'ano', 'trimestre'])
    
    df['valor_real'] = df['vl_saldo_final_num']
    # Apenas subtrai se for a mesma operadora, mesmo ano e trimestre > 1
    mask_subtrair = (df['trimestre'] > 1)
    df.loc[mask_subtrair, 'valor_real'] = df['vl_saldo_final_num'] - df.groupby(['reg_ans', 'ano'])['vl_saldo_final_num'].shift(1)
    
    df['valor_real'] = df['valor_real'].fillna(df['vl_saldo_final_num'])
    return df

def main():
    logging.info('=== Requisito 3.5: Processamento Analítico ===')
    
    # 1. Extração e Consolidação
    extracted = extract_all_zips()
    if not extracted:
        logging.error('Nenhum ZIP extraído.')
        return
        
    df, _ = consolidate_demonstracoes(extracted)
    if df.empty:
        logging.error('DataFrame consolidado está vazio.')
        return

    # 2. Limpeza de Dados
    df['vl_saldo_final_num'] = df['vl_saldo_final'].map(clean_numeric)
    
    # Normaliza reg_ans para 6 dígitos (essencial para o Merge)
    df['reg_ans'] = df['reg_ans'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.zfill(6)

    # 3. Filtragem de Categoria Assistencial
    df['descricao_norm'] = df['descricao_conta'].astype(str).str.strip().str.upper()
    mask = df['descricao_norm'].str.contains('SINISTROS CONHECIDOS') & df['descricao_norm'].str.contains('HOSPITALAR')
    subset = df[mask].copy()

    if subset.empty:
        logging.error('Categoria de despesas não encontrada nos dados.')
        return

    # 4. Ajuste de Datas (Evita nanT/nan)
    subset['ano'] = pd.to_numeric(subset['ano'], errors='coerce')
    subset['trimestre'] = pd.to_numeric(subset['trimestre'], errors='coerce')
    
    # Se ainda houver NaNs, tentamos preencher com 2024 (ano base do download)
    subset['ano'] = subset['ano'].fillna(2024).astype(int)
    subset['trimestre'] = subset['trimestre'].fillna(4).astype(int)

    # 5. Cálculo de Gasto Real
    subset = get_desacumulado(subset)

    # 6. Rankings
    periods = subset[['ano','trimestre']].drop_duplicates().sort_values(['ano','trimestre'], ascending=False)
    last_ano, last_tri = periods.iloc[0]['ano'], periods.iloc[0]['trimestre']
    logging.info(f'Processando período: {last_tri}T/{last_ano}')

    # Top 10 Trimestre
    last_q = subset[(subset['ano'] == last_ano) & (subset['trimestre'] == last_tri)]
    res_q = last_q.groupby('reg_ans')['valor_real'].sum().reset_index()
    res_q = res_q.sort_values('valor_real', ascending=False).head(10)

    # Top 10 Ano (Últimos 4 trimestres)
    last_year_df = subset.merge(periods.head(4), on=['ano', 'trimestre'])
    res_y = last_year_df.groupby('reg_ans')['valor_real'].sum().reset_index()
    res_y = res_y.sort_values('valor_real', ascending=False).head(10)


        # 7. Merge Inteligente com CADOP (Versão Blindada contra Aspas)
    cadop_path = Path(__file__).parent.parent / 'data' / 'raw' / 'operadoras_ativas' / 'relatorio_cadop.csv'
    
    if cadop_path.exists():
        logging.info("Carregando CADOP (Modo de compatibilidade para arquivos malformados)...")
        
        try:
            # quoting=3 (csv.QUOTE_NONE) ignora as aspas que estão quebrando seu arquivo
            cadop = pd.read_csv(
                cadop_path, 
                skiprows=1, 
                sep=None, 
                engine='python', 
                encoding='latin1', 
                dtype=str,
                quoting=3 
            )
        except Exception as e:
            logging.error(f"Falha na leitura bruta: {e}")
            return

        # Limpeza agressiva: remove caracteres estranhos das colunas
        cadop.columns = [str(c).replace('"', '').strip().upper() for c in cadop.columns]
        
        # Identificação de colunas (ANS e Razão Social)
        col_ans = [c for c in cadop.columns if 'REGISTRO' in c and 'ANS' in c]
        col_razao = [c for c in cadop.columns if 'RAZ' in c and 'SOCIAL' in c]

        if col_ans and col_razao:
            # Selecionamos e limpamos os dados
            cadop_clean = pd.DataFrame({
                'registro_ans_key': cadop[col_ans[0]].str.replace('"', '').str.strip().str.zfill(6),
                'Razao Social': cadop[col_razao[0]].str.replace('"', '').str.strip()
            })
            
            # Merge com os rankings calculados
            res_q = res_q.merge(cadop_clean, left_on='reg_ans', right_on='registro_ans_key', how='left')
            res_y = res_y.merge(cadop_clean, left_on='reg_ans', right_on='registro_ans_key', how='left')
        else:
            logging.warning(f"Cabeçalhos identificados: {list(cadop.columns)}")

    # 8. Exibição de Resultados
    print('\n' + '='*70)
    print(f'TOP 10 OPERADORAS - GASTO REAL NO {last_tri}T/{last_ano}')
    print('='*70)
    print(res_q[['reg_ans', 'Razao Social', 'valor_real']].to_string(index=False))

    print('\n' + '='*70)
    print(f'TOP 10 OPERADORAS - GASTO ACUMULADO (ÚLTIMOS 4 TRI)')
    print('='*70)
    print(res_y[['reg_ans', 'Razao Social', 'valor_real']].to_string(index=False))

    # 9. Salva Consolidado
    out_path = Path(INTERIM_DIR) / 'demo_consolidado_normalized.csv'
    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    logging.info(f'CSV final normalizado salvo em: {out_path}')

if __name__ == '__main__':
    main()