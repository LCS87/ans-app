CREATE TABLE IF NOT EXISTS cadop_operadoras_ativas (
  registro_ans        TEXT,
  cnpj                TEXT,
  razao_social        TEXT,
  nome_fantasia       TEXT,
  modalidade          TEXT,
  logradouro          TEXT,
  numero              TEXT,
  complemento         TEXT,
  bairro              TEXT,
  cidade              TEXT,
  uf                  TEXT,
  cep                 TEXT,
  ddd                 TEXT,
  telefone            TEXT,
  fax                 TEXT,
  email               TEXT,
  representante       TEXT,
  cargo_representante TEXT,
  data_registro_ans   TEXT
);

CREATE TABLE IF NOT EXISTS demonstracoes_contabeis (
  ano                 INTEGER NOT NULL,
  trimestre           INTEGER NOT NULL,
  reg_ans             TEXT,
  cd_conta_contabil   TEXT,
  descricao_conta     TEXT,
  vl_saldo_inicial    NUMERIC,
  vl_saldo_final      NUMERIC
);

CREATE INDEX IF NOT EXISTS idx_demonstracoes_periodo ON demonstracoes_contabeis (ano, trimestre);
CREATE INDEX IF NOT EXISTS idx_demonstracoes_reg_ans ON demonstracoes_contabeis (reg_ans);
