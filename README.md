# ANS Intelligence App 🚀

Aplicação Full-Stack para automação de processos da ANS (Agência Nacional de Saúde Suplementar). O projeto engloba desde o **Scraping** de dados públicos até a visualização em um **Dashboard de BI**.

## 🛠️ Tecnologias
- **Backend:** Python 3.11, FastAPI, Pandas.
- **Frontend:** Vue.js 3, Vite, Dashboard reativo.
- **ETL:** BeautifulSoup4 (Scraping), Tabula-py (Extração de tabelas em PDF).

## 📊 Desafios Superados
- **Parsing de Dados:** Tratamento de CSVs governamentais malformados e inconsistentes.
- **Analytics:** Processamento de desacumulado financeiro de balancetes trimestrais (> 3M de linhas).
- **Busca:** Algoritmo com normalização Unicode e sistema de pesos para busca de operadoras.

## 🚀 Execução
1. **Ambiente:** `pip install -r requirements.txt`
2. **Backend:** `python -m uvicorn api.main:app --reload`
3. **Frontend:** `cd frontend/vue-app && npm run dev`
