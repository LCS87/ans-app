import os
import re
import urllib3
import requests
from datetime import date
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Configuração de Logs Simples
def log(msg):
    print(f"[*] {msg}")

# --- CONFIGURAÇÃO DE DIRETÓRIOS ---
# Define a raiz baseada na localização deste script (sobe 2 níveis)
# Estrutura esperada: raiz/etl/scraping/script.py -> RAW_DIR: raiz/data/raw
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

DEMONSTRACOES_BASE_URL = "https://dadosabertos.ans.gov.br/FTP/PDA/demonstracoes_contabeis/"
CADOP_URL = "https://www.gov.br/ans/pt-br/arquivos/acesso-a-informacao/perfil-do-setor/dados-e-indicadores-do-setor/operadoras-de-planos-privados-de-saude/relatorio_cadop.csv"

# Suprime avisos de conexões HTTPS não seguras (comum em servidores governamentais)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def _safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def _download(url: str, dest: Path, timeout: int = 180) -> Path:
    """Realiza o download de arquivos grandes em chunks."""
    _safe_mkdir(dest.parent)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # verify=False é necessário para o servidor PDA da ANS devido a certificados instáveis
    with requests.get(url, stream=True, timeout=timeout, verify=False, headers=headers) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            # Download em blocos de 1MB para eficiência
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return dest

def download_demonstracoes_contabeis_last_2_years() -> list[Path]:
    """Baixa os ZIPs trimestrais de 2023 e 2024 (dados estáveis no servidor)."""
    
    # Definimos anos fixos pois o servidor da ANS demora a subir o ano corrente
    years = [2023, 2024]
    downloaded: list[Path] = []
    
    session = requests.Session()
    session.verify = False 
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
    })

    for y in years:
        year_url = f"{DEMONSTRACOES_BASE_URL}{y}/"
        log(f"Listando arquivos em: {year_url}")

        try:
            resp = session.get(year_url, timeout=45)
            if resp.status_code != 200:
                log(f"Aviso: Ano {y} não disponível no servidor (Status {resp.status_code})")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            zips = []
            
            # Busca todos os links que terminam em .zip
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.lower().endswith(".zip"):
                    zips.append(urljoin(year_url, href))

            if not zips:
                log(f"Nenhum arquivo ZIP encontrado para o ano {y}")
                continue

            for zip_url in zips:
                name = zip_url.split("/")[-1]
                out = RAW_DIR / "demonstracoes_contabeis" / str(y) / name
                
                if out.exists():
                    log(f"Arquivo ignorado (já existe): {name}")
                    downloaded.append(out)
                    continue

                log(f"Baixando demonstração: {name}...")
                downloaded.append(_download(zip_url, out))
                
        except Exception as e:
            log(f"Erro ao processar ano {y}: {e}")

    return downloaded

def download_operadoras_ativas_cadop() -> Path | None:
    """Baixa o CSV de operadoras ativas (Relatório CADOP)."""
    out = RAW_DIR / "operadoras_ativas" / "relatorio_cadop.csv"
    log(f"Iniciando download do CADOP: {CADOP_URL}")

    try:
        if out.exists():
            log("Arquivo CADOP já existe localmente.")
            return out
        return _download(CADOP_URL, out)
    except Exception as e:
        log(f"Falha no download do CADOP: {e}")
        return None

def main():
    log("=== Início do Requisito 3: Coleta de Dados Abertos ===\n")
    
    # Garante que a pasta raw exista antes de tudo
    _safe_mkdir(RAW_DIR)

    # 1. Download das Demonstrações Contábeis
    downloaded_zips = download_demonstracoes_contabeis_last_2_years()
    
    # 2. Download do Cadastro de Operadoras (CADOP)
    cadop = download_operadoras_ativas_cadop()

    print("\n" + "="*50)
    print("RESUMO DA OPERAÇÃO:")
    print(f"-> Total de ZIPs processados: {len(downloaded_zips)}")
    print(f"-> Local do CADOP: {cadop if cadop else 'FALHA'}")
    print("="*50)

if __name__ == "__main__":
    main()