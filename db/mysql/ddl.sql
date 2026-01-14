CREATE TABLE IF NOT EXISTS cadop_operadoras_ativas (
  registro_ans        VARCHAR(32),
  cnpj                VARCHAR(32),
  razao_social        VARCHAR(255),
  nome_fantasia       VARCHAR(255),
  modalidade          VARCHAR(128),
  logradouro          VARCHAR(255),
  numero              VARCHAR(64),
  complemento         VARCHAR(255),
  bairro              VARCHAR(255),
  cidade              VARCHAR(255),
  uf                  VARCHAR(8),
  cep                 VARCHAR(32),
  ddd                 VARCHAR(16),
  telefone            VARCHAR(64),
  fax                 VARCHAR(64),
  email               VARCHAR(255),
  representante       VARCHAR(255),
  cargo_representante VARCHAR(255),
  data_registro_ans   VARCHAR(32)
);

CREATE TABLE IF NOT EXISTS demonstracoes_contabeis (
  ano               INT NOT NULL,
  trimestre         INT NOT NULL,
  reg_ans           VARCHAR(32),
  cd_conta_contabil VARCHAR(64),
  descricao_conta   VARCHAR(512),
  vl_saldo_inicial  DECIMAL(18,2),
  vl_saldo_final    DECIMAL(18,2),
  INDEX idx_demonstracoes_periodo (ano, trimestre),
  INDEX idx_demonstracoes_reg_ans (reg_ans)
);
