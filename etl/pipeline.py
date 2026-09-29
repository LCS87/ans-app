#!/usr/bin/env python3
"""Pipeline ETL completo para ANS Intelligence."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.cleanup import cleanup_old_files

from etl.scraping.download_dados_abertos_ans import download_dados_abertos_ans

def run_pipeline():
    print("🚀 Iniciando pipeline ETL...")
    # 1. Download
    download_dados_abertos_ans()
    # 2. Limpeza
    cleanup_old_files()
    # 3. Transform (placeholder para extração real)
    print("✅ Pipeline concluído.")
    return {"status": "ok", "steps": ["download", "cleanup", "transform"]}

if __name__ == "__main__":
    result = run_pipeline()
    print(result)
