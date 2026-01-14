# Scripts de automação

Este diretório contém utilitários para executar o pipeline completo de download e extração dos Anexos ANS e gerar o ZIP final `Teste_resultadofinal.zip`.

Pré-requisitos do sistema
- Python 3.x (venv recomendado)
- Ghostscript (necessário para o Camelot)
- Java (necessário para Tabula fallback)

Como executar
1. Ative a venv do projeto:
   - Powershell: `py -m venv .venv; .\.venv\Scripts\Activate.ps1`
2. Instale dependências (no root do projeto):
   - `pip install -r requirements.txt`
3. Execute o pipeline completo:
   - `python scripts/run_full_pipeline.py`

O script faz:
- Baixa os PDFs (Anexo I/II) se ainda não existirem
- Extrai a tabela "Rol de Procedimentos" do Anexo I (camelot, com Tabula fallback)
- Substitui abreviações `OD`/`AMB` pela legenda encontrada no PDF
- Salva `rol_procedimentos_ans.csv` em `etl/data/interim`
- Cria `Teste_resultadofinal.zip` em `etl/data/processed`
Testes
- Há um teste de integração `tests/test_pipeline.py` que executa o pipeline e valida se o ZIP final foi criado. Execute `pytest -k integration` para rodá-lo.
Observações
- Se já houver os PDFs em `etl/data/raw`, o passo de download será ignorado.
- Verifique se `Ghostscript` e `Java` estão instalados caso a extração falhe com Camelot.
- **Modo alternativo sem Ghostscript:** você pode forçar o uso do Tabula (requer Java) definindo a variável de ambiente `ANS_PREFER_TABULA=1` antes de executar a extração. Exemplo (PowerShell): `setx ANS_PREFER_TABULA 1 -m` e então reabra o terminal.
