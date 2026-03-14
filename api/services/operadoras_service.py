"""Serviço de busca de operadoras."""
import unicodedata
from pathlib import Path
from typing import List

import pandas as pd

from api.config import Settings
from api.models import OperadoraResponse


def _normalize_text(value: str | None) -> str:
    """Normaliza texto para busca (remove acentos, lowercase)."""
    if value is None:
        return ""
    s = str(value).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = " ".join(s.split())
    return s


class OperadorasService:
    """Serviço para busca de operadoras."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.csv_path = Path(settings.cadop_csv_path)
        self._items: List[dict] = []
        self._index: List[dict] = []
    
    def load(self) -> None:
        """Carrega dados do CSV e cria índice de busca."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV não encontrado: {self.csv_path}")
        
        try:
            # Tenta ler com TAB separator
            df = pd.read_csv(
                self.csv_path,
                skiprows=1,
                sep='\t',
                dtype=str,
                encoding="latin1",
                quoting=3
            )
            
            # Fallback para auto-detect
            if len(df.columns) < 2:
                df = pd.read_csv(
                    self.csv_path,
                    skiprows=1,
                    sep=None,
                    engine='python',
                    encoding="latin1",
                    quoting=3
                )
            
            # Normaliza colunas
            df.columns = [str(c).strip().upper() for c in df.columns]
            df = df.fillna("")
            
            items = []
            index = []
            
            for _, row in df.iterrows():
                reg_ans = str(row.get("REGISTRO ANS", "")).strip().replace('"', '')
                cnpj = str(row.get("CNPJ", "")).strip()
                razao = str(row.get("RAZÃO SOCIAL", row.get("RAZAO SOCIAL", ""))).strip().replace('"', '')
                fantasia = str(row.get("NOME FANTASIA", "")).strip()
                modalidade = str(row.get("MODALIDADE", "")).strip()
                
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
            
            print(f"✓ {len(self._items)} operadoras carregadas")
            
        except Exception as e:
            print(f"✗ Erro ao carregar operadoras: {e}")
            raise
    
    def search(self, query: str, limit: int = 50) -> List[OperadoraResponse]:
        """
        Busca operadoras por termo.
        
        Args:
            query: Termo de busca
            limit: Limite de resultados
            
        Returns:
            Lista de operadoras ordenadas por relevância
        """
        q = _normalize_text(query)
        if not q:
            return []
        
        hits = []
        
        for item, idx in zip(self._items, self._index):
            score = 0
            
            # Pesos por campo
            if q in idx.get("registro_ans", ""):
                score += 10
            if q in idx.get("cnpj", ""):
                score += 9
            if q in idx.get("nome_fantasia", ""):
                score += 5
            if q in idx.get("razao_social", ""):
                score += 4
            
            if score > 0:
                hits.append({
                    "score": score,
                    **item
                })
        
        # Ordena por score decrescente
        hits.sort(key=lambda h: h["score"], reverse=True)
        
        # Converte para Pydantic models
        return [OperadoraResponse(**hit) for hit in hits[:limit]]
