Cronograma de Implementação — ANS Intelligence v1.2
🎯 Visão Geral
Dividi as 15 tarefas do roadmap em 5 fases com duração estimada de 12 a 16 semanas (considerando dedicação parcial, ~15-20h/semana).

Fase 1 ━━┫ Qualidade & Testes (crítico)
Fase 2 ━━┫ Novas Abas Contábeis (Financeira / Operacional / Estrutura)
Fase 3 ━━┫ Análises Avançadas (trimestral / outliers / Top 20)
Fase 4 ━━┫ Exportação & Relatórios
Fase 5 ━━┫ CI/CD & Deploy (contínuo)

Cronograma Detalhado

🏁 FASE 1 — Qualidade & Testes (Semanas 1-3)

Objetivo: Garantir que a Metodologia D e os endpoints críticos estejam protegidos por testes antes de adicionar mais funcionalidades.

Tarefa
Est.
Prioridade
Entrega
1.1 
tests/test_extract.py — testes unitários do Método D
12h
🔴 Crítico
Cobertura do algoritmo central
1.2
tests/test_validation.py — gate de qualidade
6h
🔴 Crítico
8 checks testados
1.3
tests/test_api.py — contrato dos endpoints REST
10h
🔴 Alto
/operadoras, /gastos, /year-metadata
1.4
tests/test_etl.py — integração com banco em memória (SQLite)
14h
🟡 Médio
Pipeline E2E mockado
1.5
Investigação profunda da Lacuna ANS 2024 (script de auditoria)
8h
🟡 Médio
Relatório quantitativo

📌 Milestone F1: Cobertura ≥ 65%, CI verde, relatório da lacuna 2024 documentado

🏦 FASE 2 — Novas Abas Contábeis (Semanas 4-7)

Objetivo: Expandir o dashboard das 3 dimensões atuais (Gastos Assistenciais) para uma análise 360° das operadoras.
#
Tarefa
Est.
Prioridade
Entrega
2.1
Aba Financeira — Receita (31), Sinistralidade (41/31), Lucro (256), PL (25), Endividamento (21+23), Caixa (12)
20h
🟡 Alto
Nova tab no dashboard
2.2
Aba Operacional — Despesas adm (46), Pessoal (461), Judiciais (468), Glosas, Provisões (44)
16h
🟡 Alto
Nova tab + 4 gráficos
2.3
Aba Estrutura — Imobilizado (133), Goodwill (132139013), Intangível (134), IT (134129011), Investimentos (132)
14h
🟡 Médio
Nova tab + 3 gráficos
2.4
Refatorar extract.py para suportar múltiplos prefixos
8h
🔴 Crítico
processar_ano(prefixo="31") genérico
2.5
Schema MySQL expandido (receita, lucro, pl, etc.)
6h
🟡 Alto
Migração controlada

📌 Milestone F2: 4 abas funcionais (Gastos + Financeira + Operacional + Estrutura)

📈 FASE 3 — Análises Avançadas (Semanas 8-10)

Objetivo: Elevar a profundidade analítica do sistema com ferramentas estatísticas e drill-down.

Tarefa
Est.
Prioridade
Entrega
3.1
Ranking Top 20 — por receita, sinistro, patrimônio, caixa, lucro
10h
🟡 Alto
5 sub-rankings
3.2
Análise Trimestral — gráficos 1T × 2T × 3T × 4T por operadora
12h
🟡 Médio
Drill-down temporal
3.3
Detecção de Outliers (IQR) — por porte de operadora
8h
🟢 Baixo
Badge "⚠️ Outlier"
3.4
Filtros Avançados — recorte por modalidade, região, porte
10h
🟡 Médio
Sidebar de filtros
3.5
Comparação Regional — heat map por UF (se CADOP permitir)
8h
🟢 Baixo
Mapa do Brasil

📌 Milestone F3: 8+ visualizações analíticas, drill-down funcional

📤 FASE 4 — Exportação & Relatórios (Semanas 11-12)

Objetivo: Permitir que o usuário leve os insights para fora da aplicação (essencial para trabalho acadêmico).
#
Tarefa
Est.
Prioridade
Entrega
4.1
Exportação PDF — relatório com gráficos renderizados (WeasyPrint / ReportLab)
16h
🟡 Alto
PDF institucional
4.2
Exportação Excel — múltiplas abas consolidadas (openpyxl)
8h
🟡 Alto
.xlsx completo
4.3
Upload Manual de CSV — interface para bases históricas custom
10h
🟢 Baixo
Modal de upload
4.4
Histórico por Operadora — timeline de 3 anos individual
6h
🟡 Médio
Modal detalhado

📌 Milestone F4: Botões "📥 PDF" e "📥 Excel" em todas as abas

🚀 FASE 5 — CI/CD & Deploy (Semanas 13-16, contínua)

Objetivo: Profissionalizar o projeto para portfólio/produção.

Tarefa
Est.
Prioridade
Entrega
5.1
GitHub Actions — lint (black, isort, flake8) + testes automáticos
8h
🟡 Alto
Pipeline CI verde
5.2
Docker multi-stage — otimizar imagem de produção
6h
🟢 Baixo
Imagem < 500MB
5.3
Deploy em nuvem — Render/Railway (free tier)
10h
🟢 Baixo
URL pública
5.4
Observabilidade — dashboards Grafana + métricas Prometheus
12h
🟢 Baixo
4 dashboards
5.5
WebSocket — progresso ETL em tempo real
8h
🟢 Muito baixo
Nice-to-have

📌 Milestone F5: Deploy público + badge de CI no README
📋 Resumo Consolidado

Fase
Semanas
Horas
Entregas-Chave

F1 — Testes
1-3
~50h
Cobertura 65%, CI verde
F2 — Abas
4-7
~64h
4 abas contábeis
F3 — Análises
8-10
~48h
8+ visualizações
F4 — Export
11-12
~40h
PDF + Excel
F5 — Deploy
13-16
~44h
URL pública
TOTAL
~16 sem
~246h
Versão 2.0 completa

🎯 Minha Recomendação de Ordem de Execução
Para um projeto acadêmico, eu sugeriria priorizar valor visual + entregáveis tangíveis:

🥇 Trilha Recomendada (para defesa em ~10 semanas):

Sem 1-2  →  F1.1 + F1.2 (testes do Método D + validation)
Sem 3-4  →  F2.1 (Aba Financeira — maior impacto visual)
Sem 5-6  →  F2.2 + F2.3 (Operacional + Estrutura)
Sem 7-8  →  F3.1 + F3.2 (Top 20 + Trimestral)
Sem 9    →  F4.1 + F4.2 (PDF + Excel — "wow factor" para banca)
Sem 10   →  F5.1 + F5.3 (CI + Deploy público para link no currículo)

🥈 Trilha Acelerada (5 semanas, MVP acadêmico):

Sem 1    →  F1.1 (só testes do Método D)
Sem 2-3  →  F2.1 (Aba Financeira)
Sem 4    →  F3.1 (Top 20)
Sem 5    →  F4.1 (PDF) + F5.3 (deploy)

