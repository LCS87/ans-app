"""Serviço de analytics e relatórios - Versão com MySQL."""

from typing import List

from sqlalchemy import create_engine, text

from api.config import Settings


class AnalyticsService:
    """Serviço para analytics e relatórios usando MySQL."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
        )

    def get_top_gastos(self, periodo: str, top: int = 10) -> dict:
        """
        Retorna ranking de operadoras com maiores gastos.

        Agora também retorna total_operadoras do período.
        """
        try:
            with self.engine.connect() as conn:
                # Buscar ranking
                result = conn.execute(
                    text(
                        """
                        SELECT registro_ans, razao_social, gasto_total
                        FROM gastos_assistenciais
                        WHERE periodo = :periodo
                        ORDER BY gasto_total DESC
                        LIMIT :limit
                    """
                    ),
                    {"periodo": periodo, "limit": top},
                )
                rows = result.fetchall()

                # Contar total de operadoras no período
                result_count = conn.execute(
                    text(
                        """
                        SELECT COUNT(*) as total, SUM(gasto_total) as soma
                        FROM gastos_assistenciais
                        WHERE periodo = :periodo
                    """
                    ),
                    {"periodo": periodo},
                )
                stats = result_count.fetchone()
                total_operadoras = stats[0] if stats else 0
                total_geral = float(stats[1]) if stats and stats[1] else 0

                if not rows:
                    print(f"⚠ Nenhum dado para período {periodo}, usando exemplo")
                    return self._get_example_data(top, periodo)

                ranking = []
                for idx, row in enumerate(rows, 1):
                    ranking.append(
                        {
                            "posicao": idx,
                            "registro_ans": str(row[0]),
                            "razao_social": str(row[1]),
                            "valor_total": float(row[2]),
                        }
                    )

                return {
                    "periodo": periodo,
                    "top": top,
                    "total_geral": total_geral,
                    "total_operadoras": total_operadoras,
                    "ranking": ranking,
                }

        except Exception as e:
            print(f"✗ Erro ao consultar MySQL: {e}")
            return self._get_example_data(top, periodo)

    def _get_example_data(self, top: int, periodo: str) -> dict:
        """Fallback: dados de exemplo."""
        example_data = [
            {
                "registro_ans": "326305",
                "razao_social": "AMIL ASSISTENCIA MEDICA INTERNACIONAL S.A.",
                "valor": 18693588016.00,
            },
            {
                "registro_ans": "359017",
                "razao_social": "NOTRE DAME INTERMÉDICA SAÚDE S.A.",
                "valor": 7847703848.00,
            },
            {
                "registro_ans": "304701",
                "razao_social": "UNIMED CURITIBA",
                "valor": 7019162293.00,
            },
            {
                "registro_ans": "339679",
                "razao_social": "UNIMED CNU",
                "valor": 4665399310.00,
            },
            {
                "registro_ans": "335614",
                "razao_social": "SAMEDIL",
                "valor": 4184185257.00,
            },
        ]

        ranking = []
        for idx, item in enumerate(example_data[:top], 1):
            ranking.append(
                {
                    "posicao": idx,
                    "registro_ans": item["registro_ans"],
                    "razao_social": item["razao_social"],
                    "valor_total": item["valor"],
                }
            )

        return {
            "periodo": periodo,
            "top": top,
            "total_geral": sum(i["valor"] for i in example_data[:top]),
            "total_operadoras": len(example_data[:top]),
            "ranking": ranking,
        }
