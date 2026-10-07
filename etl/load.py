"""
Módulo de carga de dados no MySQL.

Lê o CSV consolidado de gastos assistenciais e carrega no banco.

Uso:
    py -m etl.load
"""

import sys
from pathlib import Path
from typing import Optional
import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.config import get_settings


class ANSLoader:
    """Loader de dados para MySQL."""

    def __init__(self):
        self.settings = get_settings()
        self.processed_dir = Path(__file__).parent / "data" / "processed"
        self.engine = create_engine(
            self.settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )

    def testar_conexao(self) -> bool:
        """Testa conexão com MySQL."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            logger.success("✅ Conexão MySQL OK")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao conectar no MySQL: {e}")
            return False

    def ler_csv(self, ano: int) -> Optional[pd.DataFrame]:
        """Lê CSV consolidado de gastos."""
        csv_path = self.processed_dir / f"gastos_assistenciais_{ano}.csv"

        if not csv_path.exists():
            logger.error(f"❌ CSV não encontrado: {csv_path}")
            return None

        df = pd.read_csv(csv_path, encoding="utf-8")
        logger.info(f"📊 CSV carregado: {len(df):,} linhas, {len(df.columns)} colunas")
        return df

    def criar_tabela_se_nao_existe(self):
        """Cria tabela gastos_assistenciais se não existir."""
        ddl = """
        CREATE TABLE IF NOT EXISTS gastos_assistenciais (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            periodo VARCHAR(4) NOT NULL,
            registro_ans VARCHAR(10) NOT NULL,
            razao_social VARCHAR(255) NOT NULL,
            gasto_1T DECIMAL(18,2) DEFAULT 0,
            gasto_2T DECIMAL(18,2) DEFAULT 0,
            gasto_3T DECIMAL(18,2) DEFAULT 0,
            gasto_4T DECIMAL(18,2) DEFAULT 0,
            gasto_total DECIMAL(18,2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_periodo_registro (periodo, registro_ans),
            INDEX idx_periodo (periodo),
            INDEX idx_gasto_total (gasto_total DESC),
            INDEX idx_registro_ans (registro_ans)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        with self.engine.begin() as conn:
            conn.execute(text(ddl))
        logger.success("✅ Tabela gastos_assistenciais verificada/criada")

    def normalizar_colunas(self, df: pd.DataFrame, periodo: str) -> pd.DataFrame:
        """Normaliza colunas do DataFrame para o schema do MySQL."""
        df = df.copy()

        coluna_map = {}
        for col in df.columns:
            # Colunas de gasto trimestral (ex: gasto_1T2024, gasto_1T2023)
            if col.startswith("gasto_") and col not in (
                "gasto_total",
                "gasto_total_2024",
                "gasto_total_2023",
            ):
                trimestre = (
                    col.replace("gasto_", "")
                    .replace(periodo, "")
                    .replace("2024", "")
                    .replace("2023", "")
                    .replace("2025", "")
                    .replace("2026", "")
                )
                coluna_map[col] = f"gasto_{trimestre}"
            elif "total" in col.lower():
                coluna_map[col] = "gasto_total"
            elif col == "REG_ANS":
                coluna_map[col] = "registro_ans"
            elif col == "RAZAO_SOCIAL":
                coluna_map[col] = "razao_social"

        df = df.rename(columns=coluna_map)
        df["periodo"] = periodo

        colunas_esperadas = [
            "periodo",
            "registro_ans",
            "razao_social",
            "gasto_1T",
            "gasto_2T",
            "gasto_3T",
            "gasto_4T",
            "gasto_total",
        ]

        for col in colunas_esperadas:
            if col not in df.columns:
                logger.warning(f"⚠️  Coluna {col} não encontrada, adicionando com 0")
                df[col] = 0

        return df[colunas_esperadas]

    def carregar(self, df: pd.DataFrame, periodo: str, truncate: bool = True) -> int:
        """Carrega DataFrame no MySQL."""
        with self.engine.begin() as conn:
            if truncate:
                logger.info(f"🗑️  Removendo dados antigos do período {periodo}...")
                conn.execute(
                    text("DELETE FROM gastos_assistenciais WHERE periodo = :periodo"),
                    {"periodo": periodo},
                )

            linhas = len(df)
            df.to_sql(
                "gastos_assistenciais",
                conn,
                if_exists="append",
                index=False,
                chunksize=500,
                method="multi",
            )

            logger.success(f"✅ {linhas:,} linhas do período {periodo} carregadas")
            return linhas

    def validar(self, periodo: str) -> dict:
        """Valida os dados carregados."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM gastos_assistenciais WHERE periodo = :periodo"
                ),
                {"periodo": periodo},
            )
            total = result.scalar()

            result = conn.execute(
                text(
                    "SELECT SUM(gasto_total) FROM gastos_assistenciais WHERE periodo = :periodo"
                ),
                {"periodo": periodo},
            )
            soma = result.scalar() or 0

            result = conn.execute(
                text(
                    """
                    SELECT registro_ans, razao_social, gasto_total
                    FROM gastos_assistenciais
                    WHERE periodo = :periodo
                    ORDER BY gasto_total DESC
                    LIMIT 5
                """
                ),
                {"periodo": periodo},
            )
            top5 = result.fetchall()

        return {
            "total_registros": total,
            "soma_gastos": float(soma),
            "top5": [dict(r._mapping) for r in top5],
        }

    def obter_total(self, periodo: str) -> float:
        """
        Retorna o total de gastos assistenciais de um período.
        Usado pelo pipeline para calcular a base de validação do próximo ano.
        """
        try:
            sql = """
                SELECT COALESCE(SUM(gasto_total), 0)
                FROM gastos_assistenciais
                WHERE periodo = :periodo
            """
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), {"periodo": str(periodo)})
                total = result.scalar()
                return float(total) if total else 0.0
        except Exception as e:
            logger.warning(f"⚠️  Não foi possível obter total de {periodo}: {e}")
            return 0.0


def main():
    """Função principal."""
    periodo_alvo = "2024"
    loader = ANSLoader()

    # Testar conexão
    if not loader.testar_conexao():
        logger.error("❌ Não foi possível conectar ao MySQL.")
        return

    # Criar tabela
    loader.criar_tabela_se_nao_existe()

    # Ler CSV
    df = loader.ler_csv(int(periodo_alvo))
    if df is None:
        return

    # Normalizar
    df_normalizado = loader.normalizar_colunas(df, periodo=periodo_alvo)
    logger.info(f"📋 Colunas finais: {list(df_normalizado.columns)}")

    # Carregar
    loader.carregar(df_normalizado, periodo=periodo_alvo)

    # Validar
    logger.info("\n🔍 Validando dados no MySQL...")
    validacao = loader.validar(periodo_alvo)

    print("\n" + "=" * 80)
    print("🎉 CARGA NO MYSQL CONCLUÍDA")
    print("=" * 80)
    print(f"📊 Registros na tabela: {validacao['total_registros']:,}")
    print(f"💰 Soma de gastos: R$ {validacao['soma_gastos']:,.2f}")
    print("\n🏆 TOP 5 NO BANCO:")
    for i, row in enumerate(validacao["top5"], 1):
        print(
            f"   {i}. {row['razao_social'][:50]:<50} | R$ {row['gasto_total']:>15,.2f}"
        )
    print("=" * 80)


if __name__ == "__main__":
    main()
