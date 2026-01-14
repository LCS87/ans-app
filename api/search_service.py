import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

DEFAULT_CADOP_CSV_PATH = (
    Path(__file__).resolve().parent.parent
    / "etl" / "data" / "raw" / "operadoras_ativas" / "relatorio_cadop.csv"
)

def _normalize_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    s = str(value).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = " ".join(s.split())
    return s

@dataclass
class SearchHit:
    score: int
    item: Dict[str, Any]

class OperadorasSearchService:
    def __init__(self, csv_path: Optional[str] = None):
        self.csv_path = Path(csv_path) if csv_path else DEFAULT_CADOP_CSV_PATH
        self._items: List[Dict[str, Any]] = []
        self._index: List[Dict[str, str]] = []

    def load(self) -> None:
        """Carrega e limpa o CSV tratando o título e o separador TAB."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV do CADOP não encontrado: {self.csv_path}")

        try:
            # Pula o título e tenta ler como TAB (conforme sua amostra)
            df = pd.read_csv(
                self.csv_path, 
                skiprows=1, 
                sep='\t', 
                dtype=str, 
                encoding="latin1",
                quoting=3 
            )
            
            # Fallback se o TAB não separar as colunas
            if len(df.columns) < 2:
                df = pd.read_csv(self.csv_path, skiprows=1, sep=None, engine='python', encoding="latin1", quoting=3)

            # Limpeza de cabeçalhos
            df.columns = [str(c).strip().upper() for c in df.columns]
            df = df.fillna("")

            items = []
            index = []

            for _, row in df.iterrows():
                # Mapeamento robusto: busca a coluna mesmo com nomes ligeiramente diferentes
                reg_ans = str(row.get("REGISTRO ANS", "")).strip().replace('"', '')
                cnpj = str(row.get("CNPJ", "")).strip()
                razao = str(row.get("RAZÃO SOCIAL", row.get("RAZAO SOCIAL", ""))).strip().replace('"', '')
                fantasia = row.get("NOME FANTASIA", "").strip()
                modalidade = row.get("MODALIDADE", "").strip()

                item_data = {
                    "registro_ans": reg_ans,
                    "cnpj": cnpj,
                    "razao_social": razao,
                    "nome_fantasia": fantasia,
                    "modalidade": modalidade
                }

                items.append(item_data)
                index.append({
                    "registro_ans": _normalize_text(reg_ans),
                    "cnpj": _normalize_text(cnpj),
                    "razao_social": _normalize_text(razao),
                    "nome_fantasia": _normalize_text(fantasia),
                })

            self._items = items
            self._index = index
            print(f"Sucesso: {len(self._items)} operadoras carregadas.")

        except Exception as e:
            print(f"Erro ao carregar busca: {e}")

    def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        q = _normalize_text(query)
        if not q:
            return []

        hits: List[SearchHit] = []
        for item, idx in zip(self._items, self._index):
            score = 0
            if q in idx.get("registro_ans", ""): score += 10
            if q in idx.get("cnpj", ""): score += 9
            if q in idx.get("nome_fantasia", ""): score += 5
            if q in idx.get("razao_social", ""): score += 4

            if score > 0:
                hits.append(SearchHit(score=score, item=item))

        hits.sort(key=lambda h: h.score, reverse=True)
        return [{"score": h.score, **h.item} for h in hits[:limit]]

def build_service_from_env() -> OperadorasSearchService:
    csv_path = os.getenv("CADOP_CSV_PATH")
    service = OperadorasSearchService(csv_path=csv_path)
    service.load()
    return service