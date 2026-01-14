import os
import requests
import zipfile
from pathlib import Path

# Configurações de Caminhos
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOWNLOAD_DIR = PROJECT_ROOT / 'data' / 'raw'
OUTPUT_ZIP = PROJECT_ROOT / 'data' / 'processed' / 'anexos_ans.zip'

# Links Oficiais (Fallback Direto)
LINKS_ANEXOS = [
    {
        'url': 'https://www.ans.gov.br/images/stories/Legislacao/rn/Anexo_I_Rol_2021RN_465.2021_RN654.2025L.pdf',
        'nome': 'Anexo_I_Rol_Procedimentos.pdf'
    },
    {
        'url': 'https://www.ans.gov.br/images/stories/Legislacao/rn/Anexo_II_DUT_2021_RN_465.2021_RN660.2025.pdf',
        'nome': 'Anexo_II_DUT.pdf'
    }
]

def ensure_dirs():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ZIP.parent.mkdir(parents=True, exist_ok=True)

def download_file(url, dest_path):
    print(f"Baixando: {url}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    try:
        # Timeout longo e desabilita verificação SSL para evitar travamentos de rede local
        with requests.get(url, stream=True, timeout=120, verify=False, headers=headers) as r:
            r.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Sucesso: {dest_path.name}")
        return True
    except Exception as e:
        print(f"Erro ao baixar {url}: {e}")
        return False

def create_zip(files):
    print(f"Criando ZIP em: {OUTPUT_ZIP}")
    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f in files:
            zipf.write(f, arcname=f.name)

def main():
    print("=== Requisito 1: Web Scraping ANS (Modo de Resiliência Total) ===\n")
    ensure_dirs()
    
    downloaded = []
    for item in LINKS_ANEXOS:
        dest = DOWNLOAD_DIR / item['nome']
        if download_file(item['url'], dest):
            downloaded.append(dest)
    
    if downloaded:
        create_zip(downloaded)
        print("\nPipeline de Scraping concluído com sucesso!")
    else:
        print("\nFalha crítica: Não foi possível obter os arquivos da ANS.")

if __name__ == "__main__":
    # Suprime avisos de SSL não verificado (comum em redes Windows)
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()