-- ANS Intelligence - DDL Inicial
-- Este arquivo é executado automaticamente na primeira inicialização do MySQL

-- Garantir charset UTF-8
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- Tabela de operadoras (CADOP)
CREATE TABLE IF NOT EXISTS operadoras (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    registro_ans VARCHAR(10) NOT NULL UNIQUE,
    cnpj VARCHAR(14) NOT NULL,
    razao_social VARCHAR(255) NOT NULL,
    nome_fantasia VARCHAR(255),
    modalidade VARCHAR(100),
    logradouro VARCHAR(255),
    numero VARCHAR(20),
    complemento VARCHAR(100),
    bairro VARCHAR(100),
    cidade VARCHAR(100),
    uf CHAR(2),
    cep VARCHAR(8),
    ddd VARCHAR(2),
    telefone VARCHAR(20),
    fax VARCHAR(20),
    endereco_eletronico VARCHAR(255),
    representante VARCHAR(255),
    cargo_representante VARCHAR(100),
    regiao_comercializacao INT,
    data_registro_ans DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_registro_ans (registro_ans),
    INDEX idx_cnpj (cnpj),
    INDEX idx_razao_social (razao_social)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de gastos assistenciais (ETL)
CREATE TABLE IF NOT EXISTS gastos_assistenciais (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    periodo VARCHAR(4) NOT NULL COMMENT 'Ano de referência (ex: 2024)',
    registro_ans VARCHAR(10) NOT NULL COMMENT 'Registro ANS da operadora',
    razao_social VARCHAR(255) NOT NULL COMMENT 'Razão social da operadora',
    gasto_1T DECIMAL(18,2) DEFAULT 0 COMMENT 'Gasto no 1º trimestre',
    gasto_2T DECIMAL(18,2) DEFAULT 0 COMMENT 'Gasto no 2º trimestre',
    gasto_3T DECIMAL(18,2) DEFAULT 0 COMMENT 'Gasto no 3º trimestre',
    gasto_4T DECIMAL(18,2) DEFAULT 0 COMMENT 'Gasto no 4º trimestre',
    gasto_total DECIMAL(18,2) NOT NULL COMMENT 'Gasto total do período',
    -- Schema expandido v1.2 (F2.5): dimensões Financeira / Operacional / Estrutura
    -- Contas conferidas contra o plano real da ANS (DOC 275) — ver api/accounting_maps.py
    receita DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 31 - Receita c/ operações de assistência à saúde',
    sinistros DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 41 - Eventos indenizáveis líquidos',
    lucro DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 69 (apuração do resultado) ou 3-4-61',
    patrimonio DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 25 - Patrimônio líquido',
    caixa DECIMAL(18,2) DEFAULT 0 COMMENT 'Contas 121 (disponível) + 122 (aplicações financeiras)',
    passivo_circulante DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 21 - Passivo circulante',
    passivo_nao_circulante DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 23 - Passivo não circulante',
    ativo_total DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 1 - Ativo total',
    despesas_administrativas DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 46 - Despesas administrativas',
    pessoal DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 461 - Despesas com pessoal próprio',
    servicos_terceiros DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 462 - Despesas com serviços de terceiros',
    localizacao_funcionamento DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 463 - Localização e funcionamento',
    publicidade DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 464 - Publicidade e propaganda',
    tributos_operacionais DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 465 - Despesas com tributos',
    multas DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 466 - Multas administrativas',
    adm_diversas DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 468 - Despesas administrativas diversas',
    outras_despesas_operacionais DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 44 - Outras despesas operacionais',
    provisoes_tecnicas DECIMAL(18,2) DEFAULT 0 COMMENT 'Contas 211 + 231 - Provisões técnicas',
    investimentos DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 132 - Investimentos',
    imobilizado DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 133 - Imobilizado',
    intangivel DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 134 - Intangível',
    goodwill DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 132139013 - Goodwill',
    it_softwares DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 134129011 - Sistemas de computação',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_periodo_registro (periodo, registro_ans),
    INDEX idx_periodo (periodo),
    INDEX idx_receita (receita DESC),
    INDEX idx_gasto_total (gasto_total DESC),
    INDEX idx_registro_ans (registro_ans),
    FOREIGN KEY (registro_ans) REFERENCES operadoras(registro_ans) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Comentários
ALTER TABLE operadoras COMMENT = 'Cadastro de operadoras de planos de saúde (CADOP)';
ALTER TABLE gastos_assistenciais COMMENT = 'Gastos assistenciais consolidados por operadora e período';