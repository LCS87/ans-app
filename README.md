# ANS Intelligence App 🚀

Aplicação Full-Stack para automação de processos da ANS (Agência Nacional de Saúde Suplementar). O projeto engloba desde o **Scraping** de dados públicos até a visualização em um **Dashboard de BI**.

## 🛠️ Tecnologias
- **Backend:** Desenvolvido em Python 3.11, utilizando:
    - **FastAPI:** Um framework web moderno e rápido para construção de APIs, focado em alta performance e fácil codificação.
    - **Pandas:** Biblioteca robusta para manipulação e análise de dados, essencial para o tratamento dos balancetes e informações da ANS.
- **Frontend:** Construído com:
    - **Vue.js 3:** Um framework progressivo para a construção de interfaces de usuário reativas e componentizadas.
    - **Vite:** Uma ferramenta de build rápida que melhora a experiência de desenvolvimento do frontend.
    - **Dashboard interativo:** Oferece visualizações dinâmicas e personalizáveis dos dados.
- **ETL (Extract, Transform, Load):** Utiliza ferramentas específicas para cada etapa:
    - **BeautifulSoup4:** Biblioteca Python para web scraping, usada para coletar dados públicos da ANS.
    - **Tabula-py:** Ferramenta para extração de tabelas de arquivos PDF, crucial para processar documentos não-estruturados da ANS.

## 📊 Desafios Superados
- **Parsing de Dados:** Enfrentamos o desafio de lidar com a variabilidade e inconsistências em CSVs governamentais, que frequentemente apresentavam formatação incorreta e dados ausentes. Isso foi superado com rotinas robustas de limpeza e padronização de dados.
- **Analytics:** Desenvolvemos um pipeline para processar e desacumular dados financeiros de balancetes trimestrais, que somavam mais de 3 milhões de linhas. Isso exigiu otimização de performance e algoritmos eficientes para garantir a precisão dos cálculos.
- **Busca:** Implementamos um algoritmo de busca avançado com normalização Unicode e um sistema de pesos para rankear resultados, garantindo buscas eficientes e precisas por operadoras de planos de saúde, mesmo com variações na entrada do usuário.

## 🚀 Execução
Para colocar a aplicação em funcionamento, siga os passos abaixo:
1. **Ambiente:** Certifique-se de ter o Python 3.11 instalado. Em seguida, instale as dependências do projeto Python:
   `pip install -r requirements.txt`
2. **Backend:** Inicie o servidor FastAPI. O parâmetro `--reload` permite que o servidor reinicie automaticamente a cada alteração no código:
   `python -m uvicorn api.main:app --reload`
3. **Frontend:** Navegue até o diretório do frontend e inicie a aplicação Vue.js. O comando `npm run dev` irá compilar e servir o frontend, geralmente acessível em `http://localhost:5173`:
   `cd frontend/vue-app && npm run dev`
