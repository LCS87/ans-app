import os
from pathlib import Path
import pytest

from scripts import run_full_pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ZIP = PROJECT_ROOT / 'etl' / 'data' / 'processed' / f"Teste_{os.getenv('ANS_TESTE_NOME','resultadofinal')}.zip"

@pytest.mark.integration
def test_full_pipeline_creates_zip(tmp_path):
    # Run pipeline (may download files if not present)
    run_full_pipeline.run()

    assert EXPECTED_ZIP.exists(), f'ZIP final não encontrado em {EXPECTED_ZIP}'
