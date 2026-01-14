import os
import re
from pathlib import Path
import pandas as pd
import tabula
import logging

# Configuração de Logs para acompanhar o progresso no terminal
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Importações internas
from etl.transform.map_abbreviations import extract_od_amb_legend, replace_od_amb_values
from etl.transform.to_csv_and_zip import save_csv, zip_file

# --- CONFIGURAÇÃO DE CAMINHOS ROBUSTA ---
# Baseado no seu 'dir', os PDFs estão em: E:\Projetos lv1\ans-app\data\raw
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2] # Sobe de 'transform' -> 'etl' -> 'ans-app'

RAW_DIR = PROJECT_ROOT / 'data' / 'raw'
INTERIM_DIR = PROJECT_ROOT / 'data' / 'interim'
PROCESSED_DIR = PROJECT_ROOT / 'data' / 'processed'

# Requisito 2.3: Nome do arquivo conforme o teste
_USER_NAME = os.getenv('ANS_TESTE_NOME', 'resultadofinal')
OUTPUT_ZIP = PROCESSED_DIR / f'Teste_{_USER_NAME}.zip'

def limpar_e_padronizar_colunas(df):
    """Padroniza nomes de colunas e remove ruídos."""
    df.columns = [str(c).strip().replace('\n', ' ') for c in df.columns]
    
    coluna_map = {
        r'c[oó]digo': 'codigo',
        r'descri[cç][aã]o|procedimento': 'procedimento',
        r'^od$': 'od',
        r'^amb$': 'amb'
    }
    
    for pattern, new_name in coluna_map.items():
        cols = [c for c in df.columns if re.search(pattern, c, re.IGNORECASE)]
        if cols:
            df = df.rename(columns={cols[0]: new_name})
    return df

def extrair_tabela_anexo_i(pdf_path):
    """Extração via Tabula isolando o processo Java para evitar erros de biblioteca."""
    logging.info(f"Lendo PDF oficial: {pdf_path.name}")
    
    try:
        legenda_map = extract_od_amb_legend(str(pdf_path))
    except:
        legenda_map = {"OD": "Odontológico", "AMB": "Ambulatorial"}

    dfs = []
    try:
        logging.info("Iniciando extração via Java isolado... Isso levará alguns minutos.")
        
        # O segredo aqui é não passar nenhum parâmetro que ative o JPype
        # O Tabula usará o comando 'java -jar' do sistema operacional
        tables = tabula.read_pdf(
            str(pdf_path), 
            pages='all', 
            multiple_tables=True, 
            encoding='latin-1', 
            lattice=True,
            silent=True
        )
        
        if not tables:
            logging.warning("Modo lattice não retornou dados. Tentando modo stream.")
            tables = tabula.read_pdf(str(pdf_path), pages='all', multiple_tables=True, stream=True)

        for i, table in enumerate(tables):
            if table.empty: continue
            df = table.dropna(how='all')
            df = limpar_e_padronizar_colunas(df)
            df = replace_od_amb_values(df, legenda_map)
            dfs.append(df)
            if i % 20 == 0: logging.info(f"Progresso: {i} tabelas estruturadas...")

    except Exception as e:
        logging.error(f"Erro técnico na extração: {e}")
        logging.info("DICA: Certifique-se de que o comando 'java -version' funciona no seu terminal.")
        return None

    if not dfs: return None
    return pd.concat(dfs, ignore_index=True).drop_duplicates().reset_index(drop=True)

def main():
    logging.info("=== Requisito 2: Transformação de Dados ===")
    
    # Garante que os diretórios existam
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Localização do arquivo (Lógica blindada contra o Anexo II)
    # Tenta primeiro o nome exato gerado pelo scraper corrigido
    anexo_i_file = RAW_DIR / "Anexo_I_Rol_Procedimentos.pdf"
    
    if not anexo_i_file.exists():
        logging.info("Arquivo padrão não encontrado, varrendo diretório...")
        pdf_files = list(RAW_DIR.glob('*.pdf'))
        anexo_i_file = None
        
        for f in pdf_files:
            name = f.name.lower()
            # Critérios: tem que ter 'anexo', pode ter 'i' ou '1', mas NÃO pode ter 'dut' ou 'ii'
            if 'anexo' in name and ('_i' in name or '1' in name or 'rol' in name):
                if 'dut' not in name and 'ii' not in name:
                    anexo_i_file = f
                    break
            
    if not anexo_i_file or not anexo_i_file.exists():
        logging.error(f"Arquivo Anexo I não encontrado em {RAW_DIR}")
        # Debug para você ver o que o script está enxergando
        if RAW_DIR.exists():
            logging.info(f"Conteúdo da pasta raw: {[f.name for f in RAW_DIR.glob('*')]}")
        return

    logging.info(f"Arquivo selecionado para extração: {anexo_i_file.name}")

    # 2. Execução da Extração
    df = extrair_tabela_anexo_i(anexo_i_file)
    
    if df is not None and not df.empty:
        # Requisito 2.2: Salvar em CSV estruturado
        csv_path = INTERIM_DIR / 'rol_procedimentos_ans.csv'
        save_csv(df, csv_path)
        
        # Requisito 2.3: Compactar em Teste_{nome}.zip
        # Certifique-se de que a variável OUTPUT_ZIP está definida no topo do seu arquivo
        zip_file(csv_path, OUTPUT_ZIP, arcname='rol_procedimentos_ans.csv')
        
        logging.info(f"Processo finalizado com sucesso!")
        logging.info(f"Arquivo gerado: {OUTPUT_ZIP.absolute()}")
        logging.info(f"Total de registros (linhas): {len(df)}")
    else:
        logging.error("A extração falhou ou retornou uma tabela vazia.")

if __name__ == "__main__":
    main()