"""Serviço de busca de operadoras."""
from pathlib import Path
from typing import List, Optional
import unicodedata

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
        # Usar o caminho configurado
        self.csv_path = Path(settings.cadop_csv_path)
        self._items: List[dict] = []
        self._index: List[dict] = []
    
    def load(self) -> None:
        """Carrega dados do CSV e cria índice de busca."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV não encontrado: {self.csv_path}")
        
        try:
            # Detectar formato automaticamente
            # Tentar com ';' (formato novo) ou '\t' (formato antigo)
            df = None
            
            for sep in [';', '\t', ',']:
                try:
                    df_test = pd.read_csv(
                        self.csv_path,
                        sep=sep,
                        dtype=str,
                        encoding="utf-8",
                        on_bad_lines='skip',
                        nrows=5
                    )
                    # Se tiver mais de 2 colunas, é o separator correto
                    if len(df_test.columns) > 2:
                        df = pd.read_csv(
                            self.csv_path,
                            sep=sep,
                            dtype=str,
                            encoding="utf-8",
                            on_bad_lines='skip'
                        )
                        break
                except Exception:
                    continue
            
            if df is None:
                # Fallback: tentar latin1
                for sep in [';', '\t', ',']:
                    try:
                        df_test = pd.read_csv(
                            self.csv_path,
                            sep=sep,
                            dtype=str,
                            encoding="latin1",
                            on_bad_lines='skip',
                            nrows=5
                        )
                        if len(df_test.columns) > 2:
                            df = pd.read_csv(
                                self.csv_path,
                                sep=sep,
                                dtype=str,
                                encoding="latin1",
                                on_bad_lines='skip'
                            )
                            break
                    except Exception:
                        continue
            
            if df is None or len(df.columns) < 2:
                raise ValueError(f"Não foi possível ler o CSV com nenhum formato conhecido")
            
            # Normalizar colunas (uppercase)
            df.columns = [str(c).strip().upper() for c in df.columns]
            df = df.fillna("")
            
            items = []
            index = []
            
            # Mapeamento flexível de colunas
            def find_col(df, candidates):
                """Encontra coluna por possíveis nomes."""
                for cand in candidates:
                    for col in df.columns:
                        if cand.upper() in col.upper():
                            return col
                return None
            
            col_reg = find_col(df, ["REGISTRO", "REG_ANS"])
            col_cnpj = find_col(df, ["CNPJ"])
            col_razao = find_col(df, ["RAZAO", "RAZÃO SOCIAL"])
            col_fantasia = find_col(df, ["FANTASIA", "NOME FANTASIA"])
            col_modalidade = find_col(df, ["MODALIDADE"])
            col_uf = find_col(df, ["UF"])
            col_regiao = find_col(df, ["REGIAO_DE_COMERCIALIZACAO", "REGIAO"])

            if not col_reg or not col_razao:
                raise ValueError(
                    f"Colunas essenciais não encontradas. Disponível: {list(df.columns)}"
                )

            for _, row in df.iterrows():
                reg_ans = str(row.get(col_reg, "")).strip().replace('"', "")
                cnpj = str(row.get(col_cnpj, "")).strip() if col_cnpj else ""
                razao = str(row.get(col_razao, "")).strip().replace('"', "")
                fantasia = str(row.get(col_fantasia, "")).strip() if col_fantasia else ""
                modalidade = (
                    str(row.get(col_modalidade, "")).strip() if col_modalidade else ""
                )
                uf = str(row.get(col_uf, "")).strip().upper() if col_uf else ""
                regiao = str(row.get(col_regiao, "")).strip() if col_regiao else ""

                # Pular linhas sem registro
                if not reg_ans:
                    continue

                item_data = {
                    "registro_ans": reg_ans,
                    "cnpj": cnpj,
                    "razao_social": razao,
                    "nome_fantasia": fantasia or None,
                    "modalidade": modalidade or None,
                    "uf": uf or None,
                    "regiao_comercializacao": regiao or None,
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
        
        # Converte para Pydantic models COM TRATAMENTO DE ERRO
        results = []
        for hit in hits[:limit * 2]:
            try:
                # Limpa e valida campos antes de criar o model
                registro = str(hit.get("registro_ans", "")).strip()
                cnpj = ''.join(filter(str.isdigit, str(hit.get("cnpj", ""))))
                razao = str(hit.get("razao_social", "")).strip()
                
                # Normalizações defensivas
                registro = registro.zfill(6)[:6] if registro else "000000"
                cnpj = cnpj[:14].ljust(14, '0') if cnpj else "00000000000000"
                razao = razao if razao else "SEM RAZÃO SOCIAL"
                
                clean_hit = {
                    "registro_ans": registro,
                    "cnpj": cnpj,
                    "razao_social": razao,
                    "nome_fantasia": str(hit.get("nome_fantasia", "")).strip() or None,
                    "modalidade": str(hit.get("modalidade", "")).strip() or None,
                    "uf": str(hit.get("uf", "")).strip() or None,
                    "regiao_comercializacao": str(
                        hit.get("regiao_comercializacao", "")
                    ).strip()
                    or None,
                    "score": hit.get("score", 0),
                }
                results.append(OperadoraResponse(**clean_hit))

                if len(results) >= limit:
                    break
            except Exception as e:
                print(f"⚠ Registro inválido pulado: {hit.get('registro_ans', '?')} - {e}")
                continue

        return results

    def get_all(self) -> List[dict]:
        """Retorna todas as operadoras carregadas (metadata p/ filtros F3.4/F3.5)."""
        return list(self._items)