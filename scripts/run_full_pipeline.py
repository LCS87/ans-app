import os
import sys
from pathlib import Path

# Set name for final zip
os.environ.setdefault('ANS_TESTE_NOME', 'resultadofinal')

ROOT = Path(__file__).parent.parent
RAW_ANEXOS_DIR = ROOT / 'etl' / 'data' / 'raw'
PROCESSED_DIR = ROOT / 'etl' / 'data' / 'processed'


def run():
    print('=== Pipeline completo: download -> extração -> zip final ===')

    # 1) Download Anexos
    print('\n[1/4] Baixando Anexos (Anexo I e II)')
    try:
        from etl.scraping import download_anexos
        res = download_anexos.main()
        print('Download finalizado')
    except Exception as e:
        print('Falha no download dos anexos:', e)
        # continue - talvez já existam os PDFs

    # 2) Extrair Rol do Anexo I
    print('\n[2/4] Extraindo Rol de Procedimentos do Anexo I')
    try:
        from etl.transform import extract_rol_anexo_I
        extract_rol_anexo_I.main()
        print('Extração concluída')
    except Exception as e:
        print('Falha na extração:', e)
        sys.exit(1)

    # 3) Validar artefatos
    print('\n[3/4] Verificando artefatos gerados')
    interim_csv = ROOT / 'etl' / 'data' / 'interim' / 'rol_procedimentos_ans.csv'
    out_zip = ROOT / 'etl' / 'data' / 'processed' / f"Teste_{os.getenv('ANS_TESTE_NOME')}.zip"

    print('CSV interim existe?', interim_csv.exists())
    print('ZIP final existe?', out_zip.exists())

    # 4) Exibir local dos arquivos e fim
    print('\n[4/4] Fim. Artefatos:')
    if interim_csv.exists():
        print(' - CSV:', interim_csv)
    if out_zip.exists():
        print(' - ZIP:', out_zip)

    print('\nPipeline finalizado com sucesso (ou parcialmente, verifique mensagens acima).')


if __name__ == '__main__':
    run()
