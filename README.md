# 🏥 ANS Intelligence

Aplicação full-stack de **Business Intelligence** para os dados abertos da Agência Nacional de Saúde Suplementar (ANS). Permite buscar operadoras, analisar demonstrações contábeis em quatro dimensões (Gastos Assistenciais, Financeira, Operacional e Estrutura), comparar trimestres e sazonalidade, visualizar concentração regional (Heatmap das 27 UFs) e exportar relatórios consolidados em PDF e Excel.

> **Status:** 🟢 Full-Stack funcional | 🟢 4 dimensões contábeis com dados reais | 🟢 127 testes (74,8% de cobertura) | 🟢 Gate de qualidade com falha fechada | 🟢 CI/CD (GitHub Actions)

---

## 📚 Índice

| # | Seção | O que você encontra |
| :--: | :--- | :--- |
| 1 | [Sumário Executivo](#-sumário-executivo) | O que mudou desde a v1.2 e por quê |
| 2 | [Funcionalidades Principais](#-funcionalidades-principais) | Os 14 recursos do dashboard, um a um |
| 3 | [Metodologia Contábil](#-metodologia-contábil) | Do CSV bruto ao número na tela: parse, deduplicação, Método D, mapeamento, gate e reconciliação |
| 4 | [Limitações Conhecidas & Rigor Acadêmico](#-limitações-conhecidas--rigor-acadêmico) | O que este projeto **não** afirma |
| 5 | [Tecnologias Utilizadas](#-tecnologias-utilizadas) | Stack de backend, frontend e infraestrutura |
| 6 | [Como Executar Localmente](#-como-executar-localmente) | Setup ponta a ponta |
| 7 | [Referência da API](#-referência-da-api-v13) | Todos os endpoints |
| 8 | [Testes Automatizados](#-testes-automatizados--qualidade) | Suíte, cobertura e o que ela protege |
| 9 | [Estrutura do Repositório](#-estrutura-do-repositório) | Mapa das pastas |
| 10 | [Cronograma & Próximos Passos](#-cronograma--próximos-passos) | O que foi feito, o que falta e por quê |

---

## 📋 Sumário Executivo

| Métrica / Recurso | Antes (v1.2) | Atual |
| :--- | :--- | :--- |
| **Origem dos dados** | Mistura (sintético nas dimensões) | **100% dados reais da ANS** (CSV aberto) |
| **Total Gastos 2024** | R$ 19,57 Bi *(dado corrompido)* | **R$ 261,18 Bi** |
| **Total Gastos 2025** | R$ 44,48 Bi *(dado corrompido)* | **R$ 282,17 Bi** |
| **Cobertura da série** | 2024–2025 (2023 excluído) | **2023–2026** (2026 parcial, 2T) |
| **Mapeamento contábil** | Suposição (`25` = lucro, `12` = caixa) | **Plano DOC 275 conferido conta a conta** |
| **Dimensões contábeis** | 4 (2 delas sintéticas) | 4 (todas extraídas do bruto) |
| **Gate de qualidade** | Registrado no log, não executado | **Executa e bloqueia a carga** |
| **Suíte de testes** | 82 testes / 74% | **127 testes / 74,8%** |

### A correção que mudou a série inteira

Em **setembro–outubro de 2026** a auditoria do pipeline revelou que **os valores da ANS chegam em formato brasileiro** (`30.941.701.628,46`) e o ETL os lia com `pd.to_numeric(...)` **sem `decimal=","`**. Resultado: todo valor com centavos virava **zero**.

O efeito não era "2024 com lacuna da ANS": era **decimais perdidos**, ano a ano.

| Ano | Totais no app antes | Totais reais (bruto ANS) | Razão |
| :---: | ---: | ---: | ---: |
| 2023 | R$ 191,50 Bi *(excluído da série)* | **R$ 241,16 Bi** | valores com centavos → 0 |
| 2024 | R$ 19,57 Bi *(suposta "lacuna ANS")* | **R$ 261,18 Bi** | ~13× de diferença |
| 2025 | R$ 44,48 Bi | **R$ 282,17 Bi** | ~6× de diferença |
| 2026 | R$ 15,69 Bi *(2T)* | **R$ 145,80 Bi** *(2T)* | ~9× de diferença |

Com o parser corrigido, a série cresce de forma **suave e plausível** (+8,3% em 2024, +8,0% em 2025), como se espera do setor. A "lacuna da ANS em 2024" **não existe**: Bradesco, Amil e Hapvida estão no `4T2024.csv`, com o valor íntegro. O README anterior tratava uma hipótese não verificada como fato auditado — isso foi removido.

---

## ✨ Funcionalidades Principais

### 🔍 1. Busca e Detalhamento de Operadoras
- **Busca inteligente:** por registro ANS, CNPJ, razão social ou nome fantasia com normalização Unicode.
- **Base indexada:** **1.106 operadoras** ativas mapeadas em memória para resposta instantânea.
- **Chave canônica:** `REG_ANS` normalizado em 6 dígitos (`5711` ≡ `005711`) em ETL, banco e API.
- **Paginação completa:** metadados com `page`, `limit`, `total` e `pages`.
- **Filtro por modalidade** e exportação CSV com UTF-8 BOM.

### 🏥 2. Gastos Assistenciais (Foco no Sinistro)
- Top 10/20 operadoras com maiores gastos assistenciais (conta `41`).
- **Dropdown multi-ano** com badges de integridade (✅ Completo, ⚠️ Parcial).
- **Disclaimer acadêmico** contextual sobre ressalvas metodológicas da base.
- **Cache client-side por ano:** transições instantâneas entre períodos.
- **Visualizações:** ranking, Market Share (Top 5 vs Outros), evolução anual, comparação temporal e Curva de Pareto (80/20).

### 🏦 3. Análise Financeira 360° (F2.1)
Contas e métricas **todas extraídas do bruto**, com semântica conferida contra o plano de contas real (DOC 275):

| Métrica | Conta | 2023 | 2024 | 2025 |
| :--- | :--- | ---: | ---: | ---: |
| Receita c/ operações de planos | `31` | 286,35 Bi | 322,95 Bi | 355,40 Bi |
| Sinistros (eventos indenizáveis) | `41` | 241,16 Bi | 261,18 Bi | 282,17 Bi |
| **Resultado do exercício** | `3 - 4 - 61` | 2,93 Bi | 11,01 Bi | 24,43 Bi |
| Patrimônio líquido | `25` | 123,11 Bi | 135,70 Bi | 153,67 Bi |
| Caixa e investimentos | `121 + 122` | 94,31 Bi | 104,52 Bi | 119,41 Bi |
| Passivo circulante | `21` | 85,56 Bi | 97,56 Bi | 104,59 Bi |
| Passivo não circulante | `23` | 42,06 Bi | 48,89 Bi | 54,08 Bi |
| Ativo total | `1` | 249,46 Bi | 279,43 Bi | 307,58 Bi |
| **Sinistralidade** | `41 / 31` | 84,2% | 80,9% | 79,4% |

- **Sinistralidade (%)** = `41 / 31`.
- **Endividamento (%)** = `(21 + 23) / 1` (passivo total sobre ativo total — mesma dimensão, ambos estoques).
- **Margem de lucro (%)** = `(3 - 4 - 61) / 31`.
- Identidade contábil verificada no ETL: `1 = 21 + 23 + 25`.

### ⚙️ 4. Análise Operacional (F2.2)
- Despesas administrativas (`46`), pessoal próprio (`461`), serviços de terceiros (`462`), localização e funcionamento (`463`), publicidade (`464`), tributos (`465`), multas (`466`), despesas administrativas diversas (`468`) e outras despesas operacionais (`44`).
- **Provisões técnicas** (`211 + 231`): provisão de assistências a saúde no circulante e não circulante.

### 🏗️ 5. Estrutura & Ativos (F2.3)
- Investimentos (`132`), imobilizado (`133`), intangível (`134`).
- **Goodwill** (`132139013`) e **Sistemas de computação / TI** (`134129011`) — contas específicas que existem no layout real.

### 🏆 6. Rankings Top 20 Multi-Métrica (F3.1)
Cinco sub-rankings alternáveis: por **Receita**, **Sinistro**, **Patrimônio Líquido**, **Caixa e Investimentos** e **Lucro/Prejuízo**. Gráfico de barras acoplado à tabela com drill-down.

### 🔄 7. Análise Trimestral & Sazonalidade (F3.2)
Gráfico agrupado 1T × 2T × 3T × 4T do Top 5 e drill-down individual por operadora com pizza de sazonalidade.

### ⚠️ 8. Detecção Estatística de Outliers (F3.3)
Metodologia **IQR** (`Q3 + 1,5×IQR` / `Q1 - 1,5×IQR`) com guardrail de porte (mediana × 4) para amostras pequenas; badge `⚠️ Outlier` nas tabelas.

### 🗺️ 9. Distribuição Regional & Heatmap das 27 UFs (F3.5)
Agrupamento por Macrorregião, escala de calor em tons de azul e seletor de métrica (gastos, receita, caixa, PL, ativo total).

### 🔍 10. Filtros Avançados & Acessibilidade Visual (F3.4)
Recorte simultâneo por **Modalidade**, **UF** e **Região**, com contraste WCAG calibrado.

### 📥 11. Central de Exportação & Relatórios (F4.1 & F4.2)
- **PDF Institucional** (`/export/pdf`): ReportLab + Matplotlib, gráficos renderizados em memória.
- **Planilha Excel** (`/export/excel`): openpyxl com abas Resumo, Gastos, Financeiro, Operacional, Estrutura, Trimestral e Regional.

### 📤 12. Upload Manual de CSV & Histórico Individual (F4.3 & F4.4)
- `<UploadCsvModal>`: drag-and-drop de bases históricas para qualquer dimensão.
- `<OperadoraTimelineModal>`: trajetória plurianual de uma operadora (Gastos, Receita, Lucro, PL, Caixa).

### 🎭 13. Sistema de 4 Temas Institucionais
Claro (Azul), Escuro (Azul), Gold Institucional e Night Institucional, com persistência em `localStorage` e reatividade sem "efeitos fantasmas" no Chart.js.

### ⚙️ 14. Painel de Administração & Telemetria
- **Scheduler** (APScheduler) para o 1º domingo de cada mês às 03:00.
- **Disparo manual** do pipeline por ano (`/api/v1/admin/run-pipeline?ano={ano}`).
- **Histórico auditável** em `etl_executions` (status, duração, volumetria, veredito do gate).
- **Diagnóstico de recursos:** uso de disco por categoria e health check de MySQL/Redis.

---

## 🧮 Metodologia Contábil

### 0. Fluxo do dado (linhagem): do CSV bruto ao número na tela

```
dadosabertos.ans.gov.br
        │  4 ZIPs por ano (1T..4T) + relatorio_cadop.csv
        ▼
  etl/download.py ──── resiliente (httpx + tenacity), pula o que já existe
        ▼
  etl/extract.py  ──── 1) lê com decimal="," / thousands="."   (P0-1)
        │              2) canonicaliza REG_ANS (6 dígitos)     (P0-3)
        │              3) deduplica: último valor não-zero por conta
        │              4) aplica o Método D por ramo de conta (P0-4)
        ▼
  etl/pipeline.py ───  mescla as 4 dimensões em 1 linha por operadora
        │              roda o gate de qualidade (8 checks)      (P0-5)
        ▼
  etl/load.py     ───  UPSERT idempotente + cadastro de operadoras
        ▼
  MySQL (gastos_assistenciais)  ──►  api/services/analytics_service.py
                                              ▼
                                    FastAPI  ──►  Vue 3  (Chart.js)
```

Cada etapa é determinística: o mesmo conjunto de ZIPs produz exatamente a mesma linha na tabela.

### 1. Leitura do dado (P0-1): parse brasileiro

Os arquivos abertos da ANS gravam `VL_SALDO_FINAL` no formato brasileiro (`1.234.567,89`). O ETL agora lê com `decimal=","`, `thousands="."` e um parser próprio (`etl/normalization.py`) que também cobre negativos, parênteses, `R$`, valores vazios e separador ambíguo (`1.234` = milhar; `1234.56` = decimal).

| Entrada | Saída |
| :--- | ---: |
| `30.941.701.628,46` | `30941701628.46` |
| `1.234,56` | `1234.56` |
| `1,234.56` | `1234.56` |
| `1.234` *(milhar)* | `1234` |
| `1234.56` *(decimal)* | `1234.56` |
| `(1.234,56)` | `-1234.56` |
| `1.234,56-` | `-1234.56` |
| `R$ 1.234,56` | `1234.56` |
| *(vazio)* / `NaN` | `0.0` |

> Um único teste de regressão com a linha real `30.941.701.628,46 → 30941701628.46` teria evitado semanas de discussão sobre "lacuna da ANS" e "Método D".

### 2. Identidade da operadora (P0-3): `REG_ANS` canônico

`REG_ANS` chega com ou sem zeros à esquerda (`5711` × `005711`). Hoje **todas** as camadas usam a mesma chave de 6 dígitos: extração, CADOP, carga (UPSERT), serviços de analytics, busca e endpoints. O loader rejeita linhas sem registro válido em vez de criar a "operadora 000000".

Consequência prática: `GET /api/v1/operadoras/5711` e `GET /api/v1/operadoras/005711` retornam a **mesma** operadora, e o cruzamento entre o CADOP e as demonstrações não perde registros por diferença de formato.

### 3. Agregação (P0-4): Método D (híbrido) por ramo

O plano de contas da ANS é hierárquico (até 12 dígitos) e cada operadora publica em granularidade diferente. Para cada conta-ramo, o **Método D** evita dupla contagem pai/filho:

1. identifica as **raízes** (contas sem ancestral com valor);
2. se as **folhas** descendentes cobrem ≥ 90% da raiz (ou a superam), usa as folhas;
3. caso contrário, usa a **raiz** sintética.

Comparação entre as três estratégias (2025, mercado):

| Estratégia | Total | Diagnóstico |
| :--- | ---: | :--- |
| A — só folhas | R$ 282,17 Bi | ok, mas perde quem só publica a sintética |
| B — só raízes | R$ 282,17 Bi | ok, mas perde quem só publica as analíticas |
| **D — híbrido** | **R$ 282,17 Bi** | convergem; **C** (pai + filho) infla para R$ 1.975,50 Bi |

> **Por que a complexidade do D se justifica:** A, B e D convergem no total do mercado, mas **não por operadora**. Existem operadoras que publicam a conta sintética (`41`) e outras só as analíticas (`411xx`); a estratégia A zera as primeiras, a B zera as outras. O híbrido entrega o total **de cada** operadora.

**Regra de consolidação anual.** A ANS publica o **saldo de fechamento** de cada trimestre (e não o fluxo do trimestre). Para a série anual, o ETL usa o **último valor não-zero de cada conta**, priorizando o último trimestre publicado; quando a mesma conta aparece em duas publicações dentro do mesmo trimestre, vence a de **data mais recente**. É a regra que transforma um arquivo de saldos acumulados em um número anual comparável.

### 4. Mapeamento por dimensão (P1): o plano de contas real

Cada mapeamento foi conferido contra o **CSV bruto** e contra a identidade do balanço. `api/accounting_maps.py` documenta cada conta com o total de mercado em 2025.

| Dimensão | Coluna | Conta | Total 2025 |
| :--- | :--- | :--- | ---: |
| Financeira | `receita` | `31` | 355,71 Bi |
| Financeira | `sinistros` | `41` | 282,17 Bi |
| Financeira | `lucro` | `69` → derivado `3 - 4 - 61` | 24,43 Bi |
| Financeira | `patrimonio` | `25` | 148,52 Bi |
| Financeira | `caixa` | `121 + 122` | 119,27 Bi |
| Financeira | `passivo_circulante` | `21` | 104,30 Bi |
| Financeira | `passivo_nao_circulante` | `23` | 53,95 Bi |
| Financeira | `ativo_total` | `1` | 306,95 Bi |
| Operacional | `despesas_administrativas` | `46` | 32,32 Bi |
| Operacional | `pessoal` | `461` | 14,06 Bi |
| Operacional | `servicos_terceiros` | `462` | 7,57 Bi |
| Operacional | `localizacao_funcionamento` | `463` | 5,09 Bi |
| Operacional | `publicidade` | `464` | 1,40 Bi |
| Operacional | `tributos_operacionais` | `465` | 0,67 Bi |
| Operacional | `multas` | `466` | 0,72 Bi |
| Operacional | `adm_diversas` | `468` | 2,80 Bi |
| Operacional | `outras_despesas_operacionais` | `44` | 31,76 Bi |
| Operacional | `provisoes_tecnicas` | `211 + 231` | 82,50 Bi |
| Estrutura | `investimentos` | `132` | 38,57 Bi |
| Estrutura | `imobilizado` | `133` | 31,68 Bi |
| Estrutura | `intangivel` | `134` | 19,97 Bi |
| Estrutura | `goodwill` | `132139013` | 3,58 Bi (9 ops) |
| Estrutura | `it_softwares` | `134129011` | 6,01 Bi |

**Leituras que evitam erro de interpretação:**

- `25` é o **Patrimônio Líquido** (não lucro líquido). O lucro acumulado é `256` (R$ 1,30 Bi em 2025).
- `12` é o **Ativo Circulante** (R$ 160,37 Bi), **não** caixa. Liquidez imediata = `121` (Disponível) + `122` (Aplicações Financeiras).
- `21` é o **Passivo Circulante** e `23` o **Passivo Não Circulante** (não "obrigações trabalhistas"/"fornecedores").
- `6` é o **pai** de `61` (impostos) e `69` (apuração do resultado): usar `6` como despesa contaria o resultado duas vezes.
- `468` são despesas administrativas diversas (não judiciais) e `463` é localização e funcionamento (não glosas).
- A identidade do balanço é `1 = 21 + 23 + 25`.

### 5. Gate de qualidade (fail-closed)

`etl/validation.py` roda **8 checagens** sobre o frame bruto **antes** da carga e **bloqueia** o ano se qualquer uma falhar:

1. colunas obrigatórias · 2. `REG_ANS` válido · 3. valores numéricos · 4. ramo `411` presente · 5. estrutura de códigos · 6. volume plausível · 7. sem duplicidades · 8. comparação com o ano-base (razão entre 0,1× e 10×).

O check 8 é o que teria barrado a série corrompida: 2024/2023 = 0,10 → bloqueio.

### 6. Reconciliação com o bruto

`python scripts/auditar_serie.py` recalcula os agregados a partir dos CSV e compara com o banco. Resultado da última execução (2023–2026):

| Conta | 2023 | 2024 | 2025 | 2026 |
| :--- | ---: | ---: | ---: | ---: |
| Receita (`31`) | 0,056% | 0,005% | 0,085% | 0,000% |
| Sinistros (`41`) | 0,000% | 0,000% | 0,001% | 0,000% |
| Ativo (`1`) | 0,203% | 0,203% | 0,205% | 0,215% |
| Passivo circulante (`21`) | ~0,2% | ~0,2% | 0,272% | ~0,2% |
| Resultado (`3 - 4 - 61`) | 0,243% | 0,027% | 0,008% | 0,001% |
| Patrimônio (`25`) | 0,991% | 2,233% | 3,472% | 0,345% |

A diferença no patrimônio é o próprio Método D: para operadoras que não publicam a conta sintética `25`, o híbrido soma as folhas analíticas — resultado **mais próximo** do balanço real do que a raiz isolada.

### 7. Reprodutibilidade e determinismo

| Garantia | Como é garantida |
| :--- | :--- |
| Mesmos ZIPs ⇒ mesma tabela | Nenhuma etapa usa `random`, `now()` ou relógio na transformação; o `etl_executions` grava o histórico sem influenciar o dado |
| Carga idempotente | `UPSERT` por `(periodo, registro_ans)` + remoção apenas das operadoras ausentes do novo conjunto |
| Nenhuma "operadora 000000" | `REG_ANS` vazio ou inválido **rejeita** a carga (antes criava uma linha fantasma) |
| Nenhuma dupla contagem | Deduplicação por conta/trimestre + Método D (folhas **ou** raiz, nunca as duas) |
| Número publicável auditado | `scripts/auditar_serie.py` reconcilia banco × bruto a qualquer momento |

---

## ⚠️ Limitações Conhecidas & Rigor Acadêmico

### Delimitação temporal
A série cobre **2023, 2024 e 2025** completos e **2026 parcial** (1T + 2T — a ANS ainda não publicou 3T/4T de 2026). O badge `⚠️ Parcial` aparece no seletor de período. **Comparações ano a ano entre 2026 e os demais não são válidas**: 2026 é um exercício incompleto.

### Natureza do dado
- A base é a **demonstração contábil quarterly publicada pela ANS**, com o valor de fechamento de cada trimestre (saldos acumulados, **não** fluxo trimestral).
- Nem toda operadora publica todas as contas: quando uma conta falta, a métrica correspondente é **zero**, não "desconhecida". Rankings por métrica específica consideram apenas quem tem valor.
- O **Método D** é uma regra de consolidação sobre a árvore de contas da ANS, **não** um procedimento oficial da ANS. A reconciliação com o bruto (item 6) é a evidência de que a distorção é pequena (< 0,3% nas contas agregadas).
- A identidade contábil `1 = 21 + 23 + 25` fecha exatamente para a maioria das operadoras; resíduo nas demais reflete assimetria de publicação (patrimônio de um trimestre, resultado de outro).

### Limitações do resultado do exercício
- O `lucro` é o resultado **anual** (`3 - 4 - 61`), não um fluxo trimestral. A ANS publica o fechamento acumulado de cada trimestre; para obter o resultado de um trimestre isolado seria necessário usar as demonstrações **parciais** (1T, 2T, 3T), que a ANS só disponibiliza para o exercício corrente.
- A série de resultado reflete o momento do setor (2023: R$ 2,93 Bi; 2024: R$ 11,01 Bi; 2025: R$ 24,43 Bi). A variação entre anos é **real no dado**, mas exige cautela ao comparar exercícios com regras de provisionamento (provisões técnicas) muito distintas.

### Limitações operacionais
- O cadastro vem do **CADOP da ANS** (1.106 operadoras ativas no momento da carga). Operadoras que saíram do cadastro antes do período analisado não aparecem, mesmo que tenham publicado demonstrações.
- A ANS **republica** demonstrações corrigidas. O ETL fica com o **último** valor publicado por conta; não há histórico de versões nem trilha de auditoria das republicações.
- O pipeline processa ~3 milhões de linhas por ano; a memória é o limite real de execução (o ETL reduz cada trimestre a uma linha por conta antes de concatenar).
- O `git` do repositório foi **reescrito** para remover artefatos pesados do histórico (`.venv`, dados brutos da ANS, logs): os commits antigos têm hashes diferentes dos publicados anteriormente.

### Ausência de "lacuna ANS 2024"
Não há evidência de lacuna de publicação em 2024: os totais de 2024 refletem a série completa do `4T2024.csv`. A alegação anterior foi removida do código, do README e da interface.

### O que este projeto **não** é
- **Não é** uma projeção, previsão ou cenário de resultado.
- **Não é** uma classificação de risco, solvência ou rating de operadora.
- **Não substitui** a leitura das demonstrações pela ANS nem a análise de um contador.
- **Não** afirma que os totais aqui reproduzem qualquer número oficial da ANS: a ANS publica por operadora e por conta, não por ramos agregados — o Método D é uma consolidação própria, reconciliada com o bruto e documentada.

---

## 🛠️ Tecnologias Utilizadas

### Backend
- **Python 3.11+**, **FastAPI**, **Pydantic 2.x** / `pydantic-settings`
- **SQLAlchemy 2.x** + **PyMySQL**, **Pandas 2.x** / **NumPy**
- **ReportLab** + **Matplotlib** (PDF), **openpyxl** (Excel)
- **APScheduler**, **httpx** + **tenacity**, **Loguru**

### Frontend
- **Vue.js 3** (Composition API), **Vite 5+**, **Chart.js 4**
- **Vanilla CSS** com design system próprio (4 temas institucionais, contraste WCAG)

### Infraestrutura & DevOps
- **Docker & Docker Compose**: MySQL 8.0 (porta 3307) e Redis 7
- **Dockerfile multi-stage** (builder / produção / teste) em Python 3.12-slim
- **GitHub Actions**: lint (`black`, `isort`, `flake8`), testes com gate de cobertura ≥ 60%, integração com MySQL/Redis ao vivo e build da imagem

---

## 🚀 Como Executar Localmente

### Pré-requisitos
Python 3.11+, Node.js 18+, Docker e Docker Compose.

### 1. Configurar o ambiente

```bash
git clone https://github.com/LCS87/ans-app.git
cd ans-app
cp .env.example .env          # Windows: Copy-Item .env.example .env

py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Subir MySQL e Redis

```bash
cd docker
docker-compose up -d db redis
cd ..
```

### 3. (Opcional) Dados sintéticos para desenvolvimento rápido

```bash
python scripts/seed_ci.py     # 60 operadoras sintéticas, período 2023-2025
```

> O seed **recusa gravar sobre dados reais** (a menos que `ANS_SEED_FORCE=1`). Para o dashboard com dados da ANS, use o pipeline (passo 5).

### 4. Backend

```bash
py -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Swagger em `http://localhost:8000/api/v1/docs`.

### 5. Frontend

```bash
cd frontend/vue-app
npm install
npm run dev
```

Dashboard em **`http://localhost:5173/`**.

### 6. Carregar os dados reais da ANS

```bash
py -m etl.pipeline --ano 2023
py -m etl.pipeline --ano 2024
py -m etl.pipeline --ano 2025
py -m etl.pipeline --ano 2026
```

Cada execução: download (pula o que já existe) → extração multi-dimensão → **gate de qualidade** → carga idempotente no MySQL. Alternativa: `POST /api/v1/admin/run-pipeline?ano={ano}`.

---

## 📡 Referência da API (v1.3)

### Dimensões Contábeis & Analytics
| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `GET` | `/api/v1/dimension/{dim}` | Ranking da dimensão (`gastos`, `financeira`, `operacional`, `estrutura`) com filtros (`periodo`, `top`, `modalidade`, `uf`, `regiao`) e badges de outlier |
| `GET` | `/api/v1/top-rankings` | 5 sub-rankings Top 20 (receita, sinistro, PL, caixa, lucro) |
| `GET` | `/api/v1/quarterly` | Análise 1T×2T×3T×4T do Top 5 ou drill-down por operadora |
| `GET` | `/api/v1/regional` | Agregado por UF e Região (Heatmap) com seletor de métrica |
| `GET` | `/api/v1/summary` | Resumo consolidado do período |
| `GET` | `/api/v1/operadoras/{registro_ans}/history` | Timeline plurianual da operadora |
| `GET` | `/api/v1/analytics/gastos` | Ranking clássico de gastos assistenciais |
| `GET` | `/api/v1/analytics/year-metadata` | Metadados dos anos (trimestres, totais, badges) |

### Exportação & Relatórios
| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `GET` | `/api/v1/export/pdf?periodo={ano}` | Relatório institucional em PDF |
| `GET` | `/api/v1/export/excel?periodo={ano}` | Planilha `.xlsx` multi-abas |
| `POST` | `/api/v1/upload-csv` | Upload manual de CSV com validação e normalização |

### Operadoras
| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `GET` | `/api/v1/operadoras?q={termo}&page={p}&limit={n}` | Busca paginada com normalização Unicode |
| `GET` | `/api/v1/operadoras/{registro_ans}` | Detalhes cadastrais (aceita `5711` ou `005711`) |

### Administração & Saúde
| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `GET` | `/health` | Liveness/readiness (status, banco, uptime) |
| `GET` | `/api/v1/admin/status` | Status do scheduler e dos componentes |
| `GET` | `/api/v1/admin/disk-usage` | Uso de disco por categoria |
| `GET` | `/api/v1/admin/pipeline-history` | Histórico do ETL com veredito do gate |
| `POST` | `/api/v1/admin/run-pipeline?ano={ano}` | Disparo manual do pipeline |

---

## 🧪 Testes Automatizados & Qualidade

```bash
pytest tests/ -q --ignore=tests/test_endpoints.py --ignore=tests/test_pipeline.py
```

- **127 testes passando** · **74,8% de cobertura** (gate do CI: ≥ 60%).
- Cobrem: normalização (`etl/normalization.py`), Método D, mapeamento P1 (multi-prefixo, identidade de balanço, lucro derivado), carga/upsert, gate de qualidade, contrato dos endpoints REST e normalização de `REG_ANS`.
- `scripts/auditar_serie.py` reconcilia o banco com o CSV bruto (fora da suíte, por depender dos arquivos da ANS).

---

## 📁 Estrutura do Repositório

```text
ans-app/
├── .github/workflows/ci.yml      # Lint, testes + gate de cobertura, integração, Docker
├── api/                          # Backend FastAPI
│   ├── main.py                   # Rotas, lifespan, CORS, year-metadata
│   ├── accounting_maps.py        # Plano de contas ANS (DOC 275) por dimensão
│   ├── console.py                # Console UTF-8 (Windows cp1252)
│   ├── models.py / config.py / cache.py / scheduler.py / search_service.py
│   └── services/
│       ├── analytics_service.py  # Rankings, trimestral, regional, outliers
│       ├── operadoras_service.py # Cadastro CADOP e busca
│       └── export/               # pdf_export.py, excel_export.py
├── frontend/vue-app/src/         # Vue 3 + Vite (App.vue, 8 abas, modais)
├── etl/                          # Pipeline de dados
│   ├── pipeline.py               # Orquestrador (extrair → mesclar → gate → carga)
│   ├── download.py               # Download resiliente (httpx + tenacity)
│   ├── extract.py                # Leitura, normalização e Método D
│   ├── load.py                   # UPSERT idempotente + migração de schema
│   ├── normalization.py          # REG_ANS canônico, parser BRL, deduplicação
│   ├── validation.py             # Gate de qualidade (8 checks, fail-closed)
│   └── scripts/                  # Diagnósticos e comparativos A/B/C/D
├── scripts/
│   ├── seed_ci.py                # Seed sintético (somente CI/testes)
│   ├── auditar_serie.py          # Reconciliação banco × CSV bruto
│   ├── migrate_v12.py            # Migração de schema
│   └── run_full_pipeline.py      # Execução ponta a ponta
├── db/mysql/01_ddl.sql           # Schema (inclui FK para `operadoras`)
├── docker/                       # Compose (MySQL, Redis, backend, frontend)
├── tests/                        # 127 testes (pytest)
├── requirements.txt              # Ambiente completo (dev + runtime)
├── requirements.prod.txt         # Runtime enxuto (Docker)
├── pyproject.toml                # black/isort (linha 100) e config do pytest
├── .flake8 / pytest.ini
├── cronograma.md                 # Roadmap detalhado (F1–F5 + Fase 0)
└── README.md
```

> **Artefatos fora do Git** (`.gitignore`): ambiente virtual, dados brutos e processados da ANS (~1 GB), dumps de banco em `backups/`, logs, `.env` e cobertura. O histórico do repositório também foi reescrito (`git filter-repo`) para retirar esses artefatos dos commits antigos — **os hashes antigos não existem mais no GitHub**.

---

## 🗺️ Cronograma & Próximos Passos

### Fase 0 — Correção da série e do mapeamento contábil ✅ (Out/2026)

Antes de qualquer funcionalidade nova, a auditoria do dado bruto mostrou que a série inteira estava corrompida. Esta fase está **concluída**.

| ID | Correção | Entrega | Estado |
| :--- | :--- | :--- | :--- |
| P0-1 | Parse brasileiro (`decimal=","`) + parser próprio | 2024: R$ 19,57 Bi → **R$ 261,18 Bi** | ✅ |
| P0-3 | `REG_ANS` canônico (6 dígitos) em todas as camadas | 0 duplicatas; `5711` ≡ `005711` | ✅ |
| P0-4 | Carga multi-dimensão + UPSERT sem DELETE cego + sync do cadastro | 4 dimensões com **dados reais** | ✅ |
| P0-5 | Gate de qualidade com falha fechada | A série corrompida seria barrada pelo check 8 | ✅ |
| P1 | Mapeamento conferido contra o DOC 275 | `25` = PL, `12` ≠ caixa, `21/23` = passivo, `69` = apuração | ✅ |
| P1.1 | Reconciliação banco × bruto | `scripts/auditar_serie.py` (< 0,3% nas contas agregadas) | ✅ |
| P1.2 | 2023 reintegrado; "lacuna 2024" removida | Série contínua 2023–2026 | ✅ |
| P1.3 | Higiene do repositório | `.git` de 458 MB → **55 MB** (histórico reescrito) | ✅ |

### Roadmap original (F1–F5)

| Fase | Escopo | Itens | Estado |
| :--- | :--- | :--- | :--- |
| **F1** | Qualidade & testes | Método D coberto, gate de qualidade, contrato REST, integração SQLite | ✅ Concluída (127 testes, 74,8%) |
| **F2** | Novas abas contábeis | Financeira, Operacional, Estrutura; multi-prefixo; schema expandido | ✅ Concluída (com dados reais) |
| **F3** | Análises avançadas | Top 20 multi-métrica, trimestral 1T–4T, outliers IQR, filtros cruzados, heatmap 27 UFs | ✅ Concluída |
| **F4** | Exportação & relatórios | PDF institucional, Excel multi-abas, upload CSV, timeline por operadora | ✅ Concluída |
| **F5** | CI/CD & deploy | GitHub Actions (lint + gate + integração + Docker), Dockerfile multi-stage | 🟡 Parcial — falta o deploy público |

### Backlog priorizado

1. **🚀 Deploy em nuvem (Render/Railway)** — `render.yaml` servindo o backend FastAPI + o `dist/` do frontend, com o MySQL gerenciado. *Alta prioridade: é o que falta para o link público no currículo.*
2. **📊 Observabilidade (Prometheus + Grafana)** — endpoint `/metrics` com `prometheus-fastapi-instrumentator` e 4 dashboards (RPS/latência, taxa de erros, status do ETL, cache). O esqueleto de containers já existe em `docker-compose.monitoring.yml`.
3. **🔌 WebSocket de progresso do ETL** — `/ws/etl-progress` para feedback visual durante o download e a carga.
4. **🧪 Smoke-test E2E no navegador** — percorrer as 8 abas e validar os downloads de PDF/Excel.
5. **📐 Resultado trimestral** — o `lucro` é anual; o fluxo 1T–4T exige as demonstrações parciais (1T/2T/3T), que a ANS só disponibiliza para o exercício corrente.
6. **🧾 Trilha de republicações** — guardar o histórico de versões publicadas pela ANS por conta, para auditar correções retroativas.

---

## 👤 Autor

**Leo** — Desenvolvedor Full-Stack & Engenheiro/Analista de Dados
- **GitHub:** [@LCS87](https://github.com/LCS87) · **Projeto:** [ANS Intelligence](https://github.com/LCS87/ans-app)

---

## 🙏 Agradecimentos

**ANS (Agência Nacional de Saúde Suplementar)** pela disponibilização dos Dados Abertos e das demonstrações contábeis, e as comunidades open-source de FastAPI, Vue.js, Chart.js e ReportLab.

---

*Última atualização: Outubro/2026 · Versão: **1.3.0** (mapeamento contábil P1 + dados reais)*
