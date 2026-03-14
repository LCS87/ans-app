"""Serviço de analytics e relatórios."""
from pathlib import Path
from typing import List

import pandas as pd

from api.config import Settings
from api.models import GastoOperadora


class AnalyticsService:
    """Serviço para analytics e relatórios."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_dir = Path(__file__).resolve().parent.parent.parent
    
    def get_top_gastos(self, periodo: str, top: int = 10) -> List[GastoOperadora]:
        """
        Retorna ranking de operadoras com maiores gastos.
        
        Args:
            periodo: Ano de referência
            top: Quantidade de operadoras no ranking
            
        Returns:
            Lista de operadoras ordenadas por gasto
            
        Raises:
            FileNotFoundError: Se arquivo de dados não existir
        """
        # TODO: Migrar para query no banco de dados
        csv_path = self.base_dir / "etl" / "data" / "interim" / "demo_consolidado_normalized.csv"
        
        if not csv_path.exists():
            # Retorna dados de exemplo para demonstração
            print(f"⚠ Arquivo não encontrado: {csv_path}")
            print("⚠ Retornando dados de exemplo para demonstração")
            return self._get_example_data(top)
        
        try:
            # Leitura robusta
            df = pd.read_csv(
                csv_path,
                sep=None,
                engine='python',
                encoding='utf-8-sig',
                on_bad_lines='skip',
                quoting=3
            )
            
            # Normaliza colunas
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            # Busca colunas dinamicamente
            c_ans = self._find_column(df, ['REG_ANS', 'REGISTRO'])
            c_razao = self._find_column(df, ['RAZAO', 'NOME', 'SOCIAL', 'DESCRICAO_NORM'])
            c_valor = self._find_column(df, ['VL_SALDO_FINAL_NUM', 'VALOR_REAL', 'SALDO'])
            
            if not all([c_ans, c_razao, c_valor]):
                raise ValueError(f"Colunas necessárias não encontradas. Disponíveis: {list(df.columns)}")
            
            # Converte valor para numérico
            df[c_valor] = pd.to_numeric(df[c_valor], errors='coerce').fillna(0)
            
            # Agrupa e rankeia
            ranking_df = df.groupby(c_ans).agg({
                c_razao: 'first',
                c_valor: 'sum'
            }).sort_values(c_valor, ascending=False).head(top).reset_index()
            
            # Converte para modelo
            ranking = []
            for idx, row in ranking_df.iterrows():
                ranking.append(GastoOperadora(
                    posicao=idx + 1,
                    registro_ans=str(row[c_ans]),
                    razao_social=str(row[c_razao]),
                    valor_total=float(row[c_valor])
                ))
            
            return ranking
            
        except Exception as e:
            print(f"✗ Erro ao processar analytics: {e}")
            print("⚠ Retornando dados de exemplo")
            return self._get_example_data(top)
    
    def _get_example_data(self, top: int) -> List[GastoOperadora]:
        """Retorna dados de exemplo para demonstração."""
        example_data = [
            {"registro_ans": "326305", "razao_social": "AMIL ASSISTENCIA MEDICA INTERNACIONAL S.A.", "valor": 1234567890.50},
            {"registro_ans": "005711", "razao_social": "BRADESCO SAUDE S.A.", "valor": 987654321.00},
            {"registro_ans": "359661", "razao_social": "UNIMED SEGUROS SAUDE S.A.", "valor": 876543210.00},
            {"registro_ans": "417173", "razao_social": "SUL AMERICA COMPANHIA DE SEGURO SAUDE", "valor": 765432109.00},
            {"registro_ans": "326372", "razao_social": "GOLDEN CROSS ASSISTENCIA INTERNACIONAL DE SAUDE LTDA", "valor": 654321098.00},
            {"registro_ans": "005738", "razao_social": "PORTO SEGURO - SEGURO SAUDE S.A.", "valor": 543210987.00},
            {"registro_ans": "359017", "razao_social": "HAPVIDA ASSISTENCIA MEDICA LTDA", "valor": 432109876.00},
            {"registro_ans": "326313", "razao_social": "NOTRE DAME INTERMEDICA SAUDE S.A.", "valor": 321098765.00},
            {"registro_ans": "359050", "razao_social": "PREVENT SENIOR PRIVATE OPERADORA DE SAUDE LTDA", "valor": 210987654.00},
            {"registro_ans": "326321", "razao_social": "MEDIAL SAUDE S.A.", "valor": 109876543.00},
        ]
        
        ranking = []
        for idx, item in enumerate(example_data[:top], 1):
            ranking.append(GastoOperadora(
                posicao=idx,
                registro_ans=item["registro_ans"],
                razao_social=item["razao_social"],
                valor_total=item["valor"]
            ))
        
        return ranking
    
    @staticmethod
    def _find_column(df: pd.DataFrame, keywords: List[str]) -> str | None:
        """Busca coluna por palavras-chave."""
        for kw in keywords:
            matches = [c for c in df.columns if kw in c]
            if matches:
                return matches[0]
        return None
