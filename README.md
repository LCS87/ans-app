# ans-app

Esta aplicação automatiza o ciclo de vida de dados da ANS (Agência Nacional de Saúde Suplementar), processando desde o scraping de PDFs oficiais até a análise financeira de milhões de registros contábeis.

## Tecnologias Utilizadas

*   **Backend**: Python, FastAPI, Pandas, Uvicorn
*   **Frontend**: Vue.js, Vite, npm, Nginx
*   **Banco de Dados**: MySQL
*   **Containerização**: Docker, Docker Compose
*   **CI/CD**: GitHub Actions

## Estrutura do Projeto

```
ans-app/
├── api/                   # Backend da API FastAPI
├── etl/                   # Scripts de Extração, Transformação e Carga (ETL)
├── frontend/vue-app/      # Aplicação Frontend Vue.js
├── db/                    # Scripts SQL para configuração do banco de dados (MySQL, PostgreSQL)
├── docker/                # Configurações Docker (Dockerfile para backend e frontend, docker-compose.yml)
├── scripts/               # Scripts utilitários
├── tests/                 # Testes unitários e de integração
└── README.md              # Este arquivo
```

## Configuração e Execução

Você pode configurar e executar o projeto usando Docker Compose ou localmente.

### Opção 1: Usando Docker Compose (Recomendado)

#### Pré-requisitos

*   Docker Desktop (ou Docker Engine) instalado e em execução.

#### Passos

1.  **Navegue até o diretório `docker` do projeto:**
    ```bash
    cd E:\Projetos lv1\ans-app\docker\
    ```
2.  **Construa as imagens Docker e inicie os containers:**
    ```bash
    docker-compose up --build
    ```
    Este comando construirá as imagens para o backend (Python/FastAPI), frontend (Vue.js/Nginx) e iniciará um container MySQL.
    
    *   O backend estará disponível em: `http://localhost:8000`
    *   O frontend estará disponível em: `http://localhost:8080`
    *   O banco de dados MySQL estará acessível na porta `3307` do seu host.

3.  **Para derrubar os containers (quando terminar):**
    ```bash
    docker-compose down
    ```

### Opção 2: Execução Local

#### Pré-requisitos

*   Python 3.10+ e pip
*   Node.js (LTS recomendado) e npm
*   MySQL Server instalado e configurado (ou use o Docker para o DB e execute o backend/frontend localmente)

#### 2.1. Configuração e Execução do Backend (FastAPI)

1.  **Navegue até o diretório raiz do projeto:**
    ```bash
    cd E:\Projetos lv1\ans-app\
    ```
2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1   # No Windows PowerShell
    # source .venv/bin/activate      # No Linux/macOS
    ```
3.  **Instale as dependências do Python:**
    ```bash
    pip install -r api/requirements.txt
    ```
4.  **Certifique-se de que o banco de dados MySQL está em execução e acessível.**
    *   Se estiver usando o container MySQL do Docker, ele estará na porta `3307` (se configurado como acima).
    *   Você precisará garantir que suas variáveis de ambiente ou configuração da aplicação apontem para o banco de dados correto (e.g., ajuste `DATABASE_URL` se necessário).
5.  **Inicie o servidor FastAPI:**
    ```bash
    uvicorn api.main:app --host 0.0.0.0 --port 8000
    ```
    O backend estará disponível em: `http://localhost:8000`

#### 2.2. Configuração e Execução do Frontend (Vue.js)

1.  **Navegue até o diretório do frontend:**
    ```bash
    cd E:\Projetos lv1\ans-app\frontend\vue-app\
    ```
2.  **Instale as dependências do Node.js:**
    ```bash
    npm install
    ```
3.  **Inicie o servidor de desenvolvimento do Vue.js:**
    ```bash
    npm run dev
    ```
    O frontend estará disponível, por padrão, em: `http://localhost:5173` (ou outra porta indicada pelo Vite).

## Endpoints da API

A documentação interativa da API (Swagger UI) está disponível em:

*   `http://localhost:8000/docs`
*   `http://localhost:8000/redoc`

Os principais endpoints incluem:

*   `GET /health`: Verifica o status da API.
*   `GET /search?query={string}`: Realiza uma busca com base em uma query.
*   `GET /analytics/top-10`: Retorna os top 10 resultados de alguma análise.

## Contribuição

Sinta-se à vontade para contribuir! Por favor, siga as melhores práticas de codificação e envie Pull Requests.

## Licença

[MIT License](LICENSE) (ou a licença que o projeto utiliza)
