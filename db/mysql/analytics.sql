-- Top 10 operadoras por despesas no item solicitado.
-- Último trimestre (usando o maior (ano,trimestre) existente)

SELECT
  c.registro_ans,
  c.razao_social,
  SUM(d.vl_saldo_final) AS despesas
FROM demonstracoes_contabeis d
LEFT JOIN cadop_operadoras_ativas c
  ON c.registro_ans = d.reg_ans
WHERE UPPER(d.descricao_conta) = UPPER('EVENTOS/ SINISTROS CONHECIDOS OU AVISADOS DE ASSISTÊNCIA A SAÚDE MEDICO HOSPITALAR')
  AND (d.ano, d.trimestre) = (
    SELECT ano, trimestre
    FROM demonstracoes_contabeis
    ORDER BY ano DESC, trimestre DESC
    LIMIT 1
  )
GROUP BY c.registro_ans, c.razao_social
ORDER BY despesas DESC
LIMIT 10;

-- Último ano = 4 trimestres mais recentes
SELECT
  c.registro_ans,
  c.razao_social,
  SUM(d.vl_saldo_final) AS despesas
FROM demonstracoes_contabeis d
LEFT JOIN cadop_operadoras_ativas c
  ON c.registro_ans = d.reg_ans
WHERE UPPER(d.descricao_conta) = UPPER('EVENTOS/ SINISTROS CONHECIDOS OU AVISADOS DE ASSISTÊNCIA A SAÚDE MEDICO HOSPITALAR')
  AND CONCAT(d.ano, LPAD(d.trimestre, 2, '0')) IN (
    SELECT CONCAT(x.ano, LPAD(x.trimestre, 2, '0'))
    FROM (
      SELECT DISTINCT ano, trimestre
      FROM demonstracoes_contabeis
      ORDER BY ano DESC, trimestre DESC
      LIMIT 4
    ) x
  )
GROUP BY c.registro_ans, c.razao_social
ORDER BY despesas DESC
LIMIT 10;
