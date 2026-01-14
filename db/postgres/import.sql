-- Ajuste os caminhos conforme seu ambiente.
-- Dica: se o arquivo vier em ISO-8859-1, use ENCODING 'LATIN1'.

-- CADOP (operadoras ativas)
-- Exemplo de caminho (Windows): E:\\Wind\\ans-app\\etl\\data\\raw\\operadoras_ativas\\relatorio_cadop.csv
-- CSV separado por ';' e com aspas duplas.

TRUNCATE cadop_operadoras_ativas;

COPY cadop_operadoras_ativas (
  registro_ans,
  cnpj,
  razao_social,
  nome_fantasia,
  modalidade,
  logradouro,
  numero,
  complemento,
  bairro,
  cidade,
  uf,
  cep,
  ddd,
  telefone,
  fax,
  email,
  representante,
  cargo_representante,
  data_registro_ans
)
FROM :cadop_csv_path
WITH (FORMAT csv, HEADER true, DELIMITER ';', QUOTE '"', ENCODING 'LATIN1');

-- Demonstrações contábeis
-- O ETL etl/transform/prepare_demonstracoes_contabeis.py gera um CSV consolidado em UTF-8:
-- etl/data/interim/demonstracoes_contabeis_consolidado.csv

TRUNCATE demonstracoes_contabeis;

-- Importa para staging textual, depois converte números de forma segura.
CREATE TEMP TABLE IF NOT EXISTS stg_demonstracoes_contabeis (
  ano               TEXT,
  trimestre         TEXT,
  reg_ans           TEXT,
  cd_conta_contabil TEXT,
  descricao_conta   TEXT,
  vl_saldo_inicial  TEXT,
  vl_saldo_final    TEXT
);

TRUNCATE stg_demonstracoes_contabeis;

COPY stg_demonstracoes_contabeis (
  ano,
  trimestre,
  reg_ans,
  cd_conta_contabil,
  descricao_conta,
  vl_saldo_inicial,
  vl_saldo_final
)
FROM :demonstracoes_consolidado_csv_path
WITH (FORMAT csv, HEADER true, DELIMITER ',', QUOTE '"', ENCODING 'UTF8');

INSERT INTO demonstracoes_contabeis (
  ano,
  trimestre,
  reg_ans,
  cd_conta_contabil,
  descricao_conta,
  vl_saldo_inicial,
  vl_saldo_final
)
SELECT
  NULLIF(ano, '')::INTEGER,
  NULLIF(trimestre, '')::INTEGER,
  NULLIF(reg_ans, ''),
  NULLIF(cd_conta_contabil, ''),
  NULLIF(descricao_conta, ''),
  CASE
    WHEN vl_saldo_inicial IS NULL OR btrim(vl_saldo_inicial) = '' THEN NULL
    ELSE REPLACE(REPLACE(vl_saldo_inicial, '.', ''), ',', '.')::NUMERIC
  END,
  CASE
    WHEN vl_saldo_final IS NULL OR btrim(vl_saldo_final) = '' THEN NULL
    ELSE REPLACE(REPLACE(vl_saldo_final, '.', ''), ',', '.')::NUMERIC
  END
FROM stg_demonstracoes_contabeis;
