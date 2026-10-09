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
    receita DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 31 - Receita c/ planos de saúde',
    sinistros DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 41 - Eventos/sinistros',
    lucro DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 25 - Lucro líquido do exercício',
    patrimonio DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 256 - Resultado acumulado (proxy PL)',
    caixa DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 12 - Caixa e equivalentes',
    obrigacoes_trabalhistas DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 21',
    fornecedores DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 23',
    despesas_administrativas DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 46',
    pessoal DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 461 - Despesas com pessoal',
    judiciais DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 468 - Despesas judiciais',
    provisoes DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 44 - Provisões técnicas',
    glosas DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 463 - Glosas/ressarcimentos',
    investimentos DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 132 - Investimentos',
    imobilizado DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 133 - Imobilizado',
    intangivel DECIMAL(18,2) DEFAULT 0 COMMENT 'Conta 134 - Intangível',
    goodwill DECIMAL(18,2) DEFAULT 0 COMMENT 'Goodwill (132139013)',
    it_softwares DECIMAL(18,2) DEFAULT 0 COMMENT 'Softwares/IT (134129011)',
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