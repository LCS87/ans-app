import os
import pandas as pd
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from api.search_service import build_service_from_env

app = FastAPI(title="ANS Search API", version="0.1.0")

# CORS configurado para o frontend Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("CORS_ALLOW_ORIGIN", "http://localhost:5173"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_service = None

@app.on_event("startup")
def _startup() -> None:
    global _service
    _service = build_service_from_env()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/search")
def search(
    query: str = Query(min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    results = _service.search(query=query, limit=limit)
    return {"query": query, "count": len(results), "results": results}

@app.get("/analytics/top-10")
def get_top_10():
    # Define o caminho de forma robusta
    base_dir = Path(__file__).resolve().parent.parent
    path = base_dir / "etl" / "data" / "interim" / "demo_consolidado_normalized.csv"
    
    if not path.exists():
        print(f"Arquivo não encontrado: {path}")
        return []

    try:
        # Leitura blindada
        df = pd.read_csv(path, sep=None, engine='python', encoding='utf-8-sig', on_bad_lines='skip', quoting=3)
        
        # Normalização das colunas
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Busca segura de colunas para evitar "index out of range"
        def find_col(keywords):
            for kw in keywords:
                match = [c for c in df.columns if kw in c]
                if match: return match[0]
            return None

        # Atualize estas linhas dentro de get_top_10:
        c_ans = find_col(['REG_ANS', 'REGISTRO'])
        c_razao = find_col(['RAZAO', 'NOME', 'SOCIAL', 'DESCRICAO_NORM']) 
        c_valor = find_col(['VL_SALDO_FINAL_NUM', 'VALOR_REAL', 'SALDO'])

        if not all([c_ans, c_razao, c_valor]):
            print(f"Colunas ausentes no CSV. Encontradas: {list(df.columns)}")
            return []

        # Garante que o valor é numérico
        df[c_valor] = pd.to_numeric(df[c_valor], errors='coerce').fillna(0)

        # Agrupamento e Ranking
        top_10 = df.groupby(c_ans).agg({
            c_razao: 'first',
            c_valor: 'sum'
        }).sort_values(c_valor, ascending=False).head(10).reset_index()
        
        # Padronização para o Frontend Vue
        top_10.columns = ['reg_ans', 'Razao Social', 'valor_real']
        return top_10.to_dict(orient="records")

    except Exception as e:
        print(f"Erro no processamento do Ranking: {e}")
        return []