"""Testes do pipeline ETL — exige rede/ANS, marcado como integration."""

import pytest


@pytest.mark.integration
def test_full_pipeline_creates_zip():
    pytest.skip("Requer download real da ANS + tabula; executado apenas em CI com network")
