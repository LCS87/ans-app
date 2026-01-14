-- Ajuste caminhos e permissões do MySQL.
-- Para LOAD DATA LOCAL INFILE funcionar, pode ser necessário habilitar:
-- SET GLOBAL local_infile = 1;

TRUNCATE TABLE cadop_operadoras_ativas;

LOAD DATA LOCAL INFILE '{CADOP_CSV_PATH}'
INTO TABLE cadop_operadoras_ativas
CHARACTER SET latin1
FIELDS TERMINATED BY ';'
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(
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
);

-- Demonstrações contábeis:
-- O ETL etl/transform/prepare_demonstracoes_contabeis.py gera um CSV consolidado em UTF-8:
-- etl/data/interim/demonstracoes_contabeis_consolidado.csv
--
-- Observação sobre decimais:
-- se os valores vierem no formato pt-BR (ex.: 1.234,56), a carga direta em DECIMAL pode falhar.
-- Uma estratégia simples é carregar em staging VARCHAR e converter com REPLACE.

TRUNCATE TABLE demonstracoes_contabeis;

CREATE TEMPORARY TABLE stg_demonstracoes_contabeis (
  ano               VARCHAR(16),
  trimestre         VARCHAR(16),
  reg_ans           VARCHAR(64),
  cd_conta_contabil VARCHAR(128),
  descricao_conta   VARCHAR(1024),
  vl_saldo_inicial  VARCHAR(64),
  vl_saldo_final    VARCHAR(64)
);

TRUNCATE TABLE stg_demonstracoes_contabeis;

LOAD DATA LOCAL INFILE '{DEMONSTRACOES_CONSOLIDADO_CSV_PATH}'
INTO TABLE stg_demonstracoes_contabeis
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;

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
  NULLIF(ano, '') + 0,
  NULLIF(trimestre, '') + 0,
  NULLIF(reg_ans, ''),
  NULLIF(cd_conta_contabil, ''),
  NULLIF(descricao_conta, ''),
  CASE
    WHEN vl_saldo_inicial IS NULL OR TRIM(vl_saldo_inicial) = '' THEN NULL
    ELSE REPLACE(REPLACE(vl_saldo_inicial, '.', ''), ',', '.') + 0
  END,
  CASE
    WHEN vl_saldo_final IS NULL OR TRIM(vl_saldo_final) = '' THEN NULL
    ELSE REPLACE(REPLACE(vl_saldo_final, '.', ''), ',', '.') + 0
  END
FROM stg_demonstracoes_contabeis;
