-- Tabela de gastos assistenciais por operadora
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_periodo_registro (periodo, registro_ans),
    INDEX idx_periodo (periodo),
    INDEX idx_gasto_total (gasto_total DESC),
    INDEX idx_registro_ans (registro_ans)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Comentários
ALTER TABLE gastos_assistenciais COMMENT = 'Gastos assistenciais consolidados por operadora e período';