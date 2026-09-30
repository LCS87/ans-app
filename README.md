# ANS Intelligence

Aplicação full-stack de Business Intelligence para dados da Agência Nacional de Saúde Suplementar (ANS). Permite buscar operadoras de saúde, analisar gastos assistenciais e visualizar a concentração de mercado através de um dashboard interativo.

> **Status:**  Backend 100% funcional | 🟡 Frontend 80% funcional | 🔴 ETL em desenvolvimento

---

## 📸 Screenshots

![Dashboard Analytics](assets/pictures01.png)

![Busca de Operadoras](assets/pictures02.png)

![Busca de Operadoras](assets/pictures03.png)

![Busca de Operadoras](assets/pictures04.png)

![Busca de Operadoras](assets/pictures05.png)

---

## ✨ Funcionalidades

### 🔍 Busca de Operadoras
- Busca por registro ANS, CNPJ, razão social ou nome fantasia
- Normalização Unicode para buscas sem acento
- Paginação completa com metadata (page, limit, total, pages)
- Filtro por modalidade (Medicina de Grupo, Cooperativa, etc.)
- Exportação para CSV com encoding UTF-8 BOM
- Validação tolerante (registros inválidos são pulados silenciosamente)

### 📊 Ranking de Gastos
- Top 10 operadoras com maiores gastos assistenciais
- Barras de progresso relativas ao líder
- Valores formatados em R$ com separador de milhares
- *Dados atualmente em modo demonstração (ETL em desenvolvimento)*

### 📈 Dashboard Analytics
- Ranking de gastos anuais em R$ Bilhões (barras horizontais)
- Análise de concentração de mercado com linha de Pareto (80%)
- Evolução mensal das Top 3 operadoras em R$ Milhões
- Treemap de participação de mercado com paleta de cores consistente
- KPI cards: gastos totais, operadoras ativas, média e concentração Top 3
- Skeleton loaders para estados de carregamento

### 🎨 Interface
- Toggle Dark/Light com persistência via localStorage
- CSS Variables para temas consistentes
- Design responsivo (mobile-first)
- Animações suaves (fadeIn, hover effects)

### ⚙️ Administração
- Painel Admin com status do sistema em tempo real
- Execução manual de atualização via UI
- Monitoramento de uso de disco com breakdown por categoria
- Histórico de execuções com status e duração
- Health check detalhado (MySQL, Redis, uptime)

### 🔄 Pipeline ETL
- Limpeza automática de arquivos antigos (políticas de retenção)
- Notificações de falha via Discord webhook
- Scheduler mensal configurado (1º domingo, 03:00)
- Lock Redis para prevenir execução concorrente
- *Pipeline completo em desenvolvimento (download/extract/transform/load)*

### 📊 Observabilidade
- Prometheus + Grafana via Docker Compose
- Health checks endpoints
- Logs estruturados com rotação automática

---

## 🛠️ Tecnologias

### Backend

| Tecnologia | Versão | Uso |
|---|---|---|
| Python | 3.11+ | Linguagem principal |
| FastAPI | 0.100+ | Framework REST API |
| Pydantic | 2.x | Validação e serialização de dados |
| Pandas | 2.x | Processamento de dados CSV |
| PyMySQL | 1.1+ | Driver MySQL |
| Redis | 7 | Cache em memória |
| MySQL | 8.0 | Banco de dados relacional |
| APScheduler | 3.10+ | Agendamento de tarefas |

### Frontend

| Tecnologia | Versão | Uso |
|---|---|---|
| Vue.js | 3 | Framework reativo (Composition API) |
| Vite | 5+ | Build tool e dev server |
| Chart.js | 4 | Gráficos interativos |
| vue-chartjs | 5 | Wrapper Vue para Chart.js |

### ETL

| Tecnologia | Uso |
|---|---|
| BeautifulSoup4 | Web scraping do portal ANS |
| Tabula-py | Extração de tabelas de PDFs |
| Requests/httpx | Download de arquivos |
| Loguru | Logging estruturado |

### Infraestrutura

| Tecnologia | Uso |
|---|---|
| Docker Compose | Orquestração de containers |
| Uvicorn | ASGI server para FastAPI |
| Prometheus | Coleta de métricas |
| Grafana | Dashboards de monitoramento |

---

## 🚀 Quick Start

### Pré-requisitos

- Python 3.11+
- Node.js 18+
- Docker e Docker Compose
- PowerShell (Windows) ou Bash (Linux/Mac)

### 1. Clonar e configurar ambiente

```bash
# Clonar repositório
git clone <repo-url>
cd ans-app

# Copiar variáveis de ambiente
cp .env.example .env

# Criar ambiente virtual Python
py -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux/Mac
source .venv/bin/activate

# Instalar dependências
py -m pip install -r requirements.txt

2. Subir infraestrutura (MySQL + Redis)

cd docker
docker-compose up -d db redis

# Verificar se subiu
docker-compose ps

Esperado:

NAME        STATUS         PORTS
ans-mysql   Up (healthy)   0.0.0.0:3307->3306/tcp
ans-redis   Up             0.0.0.0:6379->6379/tcp

3. Iniciar backend

# Voltar pra raiz do projeto
cd ..

# Ativar venv (se não estiver ativo)
.\.venv\Scripts\Activate.ps1

# Subir FastAPI
py -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

Esperado:

INFO:     Uvicorn running on http://127.0.0.1:8000
✓ 1180 operadoras carregadas
INFO:     Application startup complete.

4. Iniciar frontend
Abre um novo terminal:

cd frontend/vue-app
npm install
npm run dev

Esperado:

VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/

5. Acessar aplicação

Serviço
URL
Status
Frontend
http://localhost:5173                     ✅
Backend
http://localhost:8000                     ✅
Swagger UI
http://localhost:8000/api/v1/doc          ✅
ReDoc
http://localhost:8000/api/v1/redoc        ✅
Prometheus
http://localhost:9090                     🟡 Opcional
Grafana
http://localhost:3000                     🟡 Opcional

API Reference
Busca de Operadoras

GET /api/v1/operadoras?q={query}&page={page}&limit={limit}

Parâmetros:

q (obrigatório): Termo de busca (mínimo 1 caractere)
page (opcional): Número da página (padrão: 1)
limit (opcional): Itens por página (padrão: 50, máximo: 200)

Exemplo:

curl "http://localhost:8000/api/v1/operadoras?q=unimed&page=1&limit=5"

Resposta:

{
  "query": "unimed",
  "results": [
    {
      "registro_ans": "339679",
      "cnpj": "28124680001060",
      "razao_social": "CENTRAL NACIONAL UNIMED - COOPERATIVA CENTRAL",
      "nome_fantasia": "CENTRAL NACIONAL UNIMED",
      "modalidade": "Cooperativa Médica",
      "score": 9
    }
  ],
  "metadata": {
    "page": 1,
    "limit": 5,
    "total": 277,
    "pages": 56
  }
}

Ranking de Gastos

GET /api/v1/analytics/gastos?periodo={ano}&top={quantidade}

Exemplo:

curl "http://localhost:8000/api/v1/analytics/gastos?periodo=2024&top=10"

Resposta:

{
  "periodo": "2024",
  "top": 10,
  "total_geral": 6135802453.5,
  "ranking": [
    {
      "posicao": 1,
      "registro_ans": "326305",
      "razao_social": "AMIL ASSISTENCIA MEDICA INTERNACIONAL S.A.",
      "valor_total": 1234567890.5
    }
  ]
}

⚠️ Nota: Dados atualmente em modo demonstração. Pipeline ETL completo em desenvolvimento.

Endpoints Admin

GET  /api/v1/admin/status          # Status do sistema
GET  /api/v1/admin/disk-usage      # Uso de disco
GET  /api/v1/admin/history         # Histórico de atualizações
POST /api/v1/admin/run-update      # Disparar atualização manual
GET  /api/v1/admin/health-detail   # Health check detalhado

Exemplo - Disk Usage:

curl http://localhost:8000/api/v1/admin/disk-usage

{
  "total_gb": 930.54,
  "used_gb": 793.04,
  "free_gb": 137.5,
  "used_percent": 85.22,
  "breakdown": {
    "backups": 0,
    "raw_data": 0.28,
    "logs": 0
  }
}

Health Check

GET /health

{
  "status": "ok",
  "version": "1.0.0",
  "database": "ok",
  "cache": "not_configured",
  "uptime_seconds": 70.64
}

 Estrutura do Projeto

 ans-app/
├── api/                        # Backend FastAPI
│   ├── main.py                 # Rotas, lifespan, exception handlers
│   ├── admin.py                # Endpoints de administração
│   ├── models.py               # Pydantic DTOs com validação tolerante
│   ├── config.py               # Settings com pydantic-settings
│   ├── cache.py                # CacheManager com Redis
│   └── services/
│       ├── operadoras_service.py   # Busca com score de relevância
│       └── analytics_service.py    # Ranking de gastos
│
├── frontend/vue-app/           # Frontend Vue 3
│   └── src/
│       ├── App.vue             # Componente principal (4 abas)
│       ├── style.css           # CSS com variáveis de tema
│       ├── main.js             # Entry point
│       └── components/
│           ├── AdminPanel.vue      # Painel de administração
│           ├── BarChart.vue        # Gráfico de barras
│           ├── LineChart.vue       # Gráfico de linha
│           ├── TreemapChart.vue    # Treemap
│           ├── SkeletonChart.vue   # Loading skeleton
│           ├── ThemeToggle.vue     # Toggle dark/light
│           └── ExportButton.vue    # Exportar CSV
│
├── etl/                        # Pipeline de dados
│   ├── pipeline.py             # Orquestrador (em desenvolvimento)
│   ├── cleanup.py              # Limpeza de arquivos antigos
│   ├── notifications.py        # Webhook Discord
│   ├── scraping/               # Web scraping ANS
│   ├── transform/              # Transformação de dados
│   └── data/                   # Dados brutos e processados
│       ├── raw/                # CSVs originais
│       └── interim/            # Dados processados
│
├── docker/
│   ├── docker-compose.yml          # MySQL + Redis + Backend + Frontend
│   └── docker-compose.monitoring.yml  # Prometheus + Grafana
│
├── tests/                      # Testes automatizados
│   ├── test_main.py
│   └── test_analytics.py
│
├── assets/                     # Screenshots
├── .env                        # Variáveis de ambiente (não commitar)
├── .env.example                # Template de variáveis
├── requirements.txt            # Dependências Python
├── pytest.ini                  # Configuração de testes
└── README.md                   # Este arquivo


Docker

Containers Principais

cd docker

# Subir MySQL e Redis
docker-compose up -d db redis

# Subir todos os serviços
docker-compose up -d

# Ver status
docker-compose ps

# Ver logs
docker-compose logs -f backend

Containers de Monitoring (Opcional)

# Subir Prometheus + Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# Acessar
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)


Tabela de Containers     

Nome                  Serviço                 Porta        Status
ans-mysql             MySQL 8.0               3307      ✅ Obrigatório
ans-redis             Redis 7                 6379      ✅ Obrigatório
ans-backend           FastAPI + Uvicorn       8000      🟡 Opcional (pode rodar local)
ans-frontend          Nginx                   8080      🟡 Opcional (pode rodar local)
ans-app-prometheus-1  Prometheus              9090      🟢 Opcional
ans-app-grafana-1     Grafana                 3000      🟢 Opcion


Testes

# Ativar ambiente virtual
.\.venv\Scripts\Activate.ps1

# Rodar todos os testes
py -m pytest

# Com cobertura
py -m pytest --cov=api --cov=etl --cov-report=term-missing

# Testes específicos
py -m pytest tests/test_analytics.py -v

Cobertura atual: ~13% (meta: 80%)

Roadmap

✅ Concluído (v1.0)
Backend FastAPI com rotas REST
Busca de operadoras com paginação
Validação tolerante (Pydantic)
Frontend Vue 3 com 4 abas
Toggle Dark/Light funcional
Exportação CSV
Painel Admin com disk usage real
Docker Compose (MySQL + Redis)
Health checks


🚧 Em Desenvolvimento (v1.1)
Pipeline ETL completo (download → extract → transform → load)
Dados reais de demonstrações contábeis da ANS
Scheduler mensal funcionando end-to-end
Testes automatizados (meta: 80% cobertura)
Discord webhook configurado
Monitoring stack com métricas reais


📋 Futuro (v2.0)
WebSocket para progresso em tempo real
Upload manual de CSVs
Comparação entre períodos (diff)
Exportação de relatórios PDF
CI/CD com GitHub Actions
Deploy em cloud (AWS/GCP/Render)



👤 Autor
Leo - Desenvolvedor Python/Java & Analista de Dados

GitHub: @LCS87
Projeto: ANS Intelligence


Agradecimentos
ANS - Agência Nacional de Saúde Suplementar pelos dados abertos
Comunidade FastAPI, Vue.js e Chart.js


Última atualização: 2026-09-30
Versão: 1.0.0-beta
Status: 🟢 Backend funcional | 🟡 Frontend 80% | 🔴 ETL em desenvolvimento

