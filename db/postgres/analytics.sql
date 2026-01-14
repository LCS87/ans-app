-- Top 10 operadoras por despesas no item:
-- "EVENTOS/ SINISTROS CONHECIDOS OU AVISADOS DE ASSISTÊNCIA A SAÚDE MEDICO HOSPITALAR"
-- Último trimestre e último ano (4 trimestres mais recentes)

-- Último trimestre disponível
WITH ultimo_periodo AS (
  SELECT ano, trimestre
  FROM demonstracoes_contabeis
  ORDER BY ano DESC, trimestre DESC
  LIMIT 1
), filtrado AS (
  SELECT d.*
  FROM demonstracoes_contabeis d
  JOIN ultimo_periodo u
    ON d.ano = u.ano AND d.trimestre = u.trimestre
  WHERE UPPER(d.descricao_conta) = UPPER('EVENTOS/ SINISTROS CONHECIDOS OU AVISADOS DE ASSISTÊNCIA A SAÚDE MEDICO HOSPITALAR')
)
SELECT
  c.registro_ans,
  c.razao_social,
  SUM(f.vl_saldo_final) AS despesas
FROM filtrado f
LEFT JOIN cadop_operadoras_ativas c
  ON c.registro_ans = f.reg_ans
GROUP BY c.registro_ans, c.razao_social
ORDER BY despesas DESC
LIMIT 10;

-- Último ano (4 trimestres mais recentes)
WITH periodos AS (
  SELECT DISTINCT ano, trimestre
  FROM demonstracoes_contabeis
  ORDER BY ano DESC, trimestre DESC
  LIMIT 4
), filtrado AS (
  SELECT d.*
  FROM demonstracoes_contabeis d
  JOIN periodos p
    ON d.ano = p.ano AND d.trimestre = p.trimestre
  WHERE UPPER(d.descricao_conta) = UPPER('EVENTOS/ SINISTROS CONHECIDOS OU AVISADOS DE ASSISTÊNCIA A SAÚDE MEDICO HOSPITALAR')
)
SELECT
  c.registro_ans,
  c.razao_social,
  SUM(f.vl_saldo_final) AS despesas
FROM filtrado f
LEFT JOIN cadop_operadoras_ativas c
  ON c.registro_ans = f.reg_ans
GROUP BY c.registro_ans, c.razao_social
ORDER BY despesas DESC
LIMIT 10;
