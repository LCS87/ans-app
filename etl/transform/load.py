"""
Módulo de carga de dados no MySQL.

Lê o CSV consolidado de gastos assistenciais e carrega no banco de dados.

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

        df = pd.read_csv(csv_path, encoding='utf-8')
        logger.info(f"📊 CSV carregado: {len(df):,} linhas, {len(df.columns)} colunas")
        return df

    def normalizar_colunas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza colunas do DataFrame para o schema do MySQL."""
        df = df.copy()

        # Renomear colunas de gasto trimestral
        coluna_map = {}
        for col in df.columns:
            if col.startswith('gasto_') and col != 'gasto_total_2024':
                # gasto_1T2024 -> gasto_1T
                trimestre = col.replace('gasto_', '').replace('2024', '')
                coluna_map[col] = f'gasto_{trimestre}'
            elif col == 'gasto_total_2024':
                coluna_map[col] = 'gasto_total'
            elif col == 'REG_ANS':
                coluna_map[col] = 'registro_ans'
            elif col == 'RAZAO_SOCIAL':
                coluna_map[col] = 'razao_social'

        df = df.rename(columns=coluna_map)

        # Adicionar coluna de período
        df['periodo'] = '2024'

        # Selecionar e ordenar colunas
        colunas_esperadas = [
            'periodo', 'registro_ans', 'razao_social',
            'gasto_1T', 'gasto_2T', 'gasto_3T', 'gasto_4T', 'gasto_total'
        ]

        for col in colunas_esperadas:
            if col not in df.columns:
                logger.warning(f"⚠️  Coluna {col} não encontrada, adicionando com 0")
                df[col] = 0

        return df[colunas_esperadas]

    def carregar(self, df: pd.DataFrame, periodo: str, truncate: bool = True) -> int:
        """
        Carrega DataFrame no MySQL usando UPSERT.

        Args:
            df: DataFrame com os dados
            periodo: Período de referência (ex: "2024")
            truncate: Se True, remove dados do período antes de inserir

        Returns:
            Número de linhas inseridas/atualizadas
        """
        with self.engine.begin() as conn:
            # Truncar dados do período (se configurado)
            if truncate:
                logger.info(f"🗑️  Removendo dados antigos do período {periodo}...")
                conn.execute(
                    text("DELETE FROM gastos_assistenciais WHERE periodo = :periodo"),
                    {"periodo": periodo}
                )

            # Inserir em chunks pra evitar timeout
            chunk_size = 500
            total_inseridas = 0

            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i+chunk_size]

                # INSERT ... ON DUPLICATE KEY UPDATE
                for _, row in chunk.iterrows():
                    conn.execute(
                        text("""
                            INSERT INTO gastos_assistenciais 
                                (periodo, registro_ans, razao_social, 
                                 gasto_1T, gasto_2T, gasto_3T, gasto_4T, gasto_total)
                            VALUES 
                                (:periodo, :registro_ans, :razao_social,
                                 :gasto_1T, :gasto_2T, :gasto_3T, :gasto_4T, :gasto_total)
                            ON DUPLICATE KEY UPDATE
                                razao_social = VALUES(razao_social),
                                gasto_1T = VALUES(gasto_1T),
                                gasto_2T = VALUES(gasto_2T),
                                gasto_3T = VALUES(gasto_3T),
                                gasto_4T = VALUES(gasto_4T),
                                gasto_total = VALUES(gasto_total)
                        """),
                        dict(row)
                    )
                    total_inseridas += 1

                if (i // chunk_size) % 2 == 0:
                    logger.debug(f"📊 Inseridas {total_inseridas:,}/{len(df):,} linhas")

            logger.success(f"✅ {total_inseridas:,} linhas carregadas no MySQL")
            return total_inseridas

    def validar(self, periodo: str) -> dict:
        """Valida os dados carregados."""
        with self.engine.connect() as conn:
            # Contar registros
            result = conn.execute(
                text("SELECT COUNT(*) FROM gastos_assistenciais WHERE periodo = :periodo"),
                {"periodo": periodo}
            )
            total = result.scalar()

            # Somar gastos
            result = conn.execute(
                text("SELECT SUM(gasto_total) FROM gastos_assistenciais WHERE periodo = :periodo"),
                {"periodo": periodo}
            )
            soma = result.scalar() or 0

            # Top 5
            result = conn.execute(
                text("""
                    SELECT registro_ans, razao_social, gasto_total 
                    FROM gastos_assistenciais 
                    WHERE periodo = :periodo 
                    ORDER BY gasto_total DESC 
                    LIMIT 5
                """),
                {"periodo": periodo}
            )
            top5 = result.fetchall()

        return {
            "total_registros": total,
            "soma_gastos": float(soma),
            "top5": [dict(r._mapping) for r in top5]
        }


async def main():
    """Função principal."""
    logger.add(
        "etl_load.log",
        rotation="10 MB",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    )

    loader = ANSLoader()

    # Testar conexão
    if not loader.testar_conexao():
        logger.error("❌ Não foi possível conectar ao MySQL. Verifique se o container está rodando.")
        return

    # Ler CSV
    df = loader.ler_csv(2024)
    if df is None:
        return

    # Normalizar
    df_normalizado = loader.normalizar_colunas(df)
    logger.info(f"📋 Colunas finais: {list(df_normalizado.columns)}")

    # Carregar
    total = loader.carregar(df_normalizado, periodo="2024")

    # Validar
    logger.info("\n🔍 Validando dados no MySQL...")
    validacao = loader.validar("2024")

    print("\n" + "=" * 80)
    print("🎉 CARGA NO MYSQL CONCLUÍDA")
    print("=" * 80)
    print(f"📊 Registros na tabela: {validacao['total_registros']:,}")
    print(f"💰 Soma de gastos: R$ {validacao['soma_gastos']:,.2f}")
    print(f"\n🏆 TOP 5 NO BANCO:")
    for i, row in enumerate(validacao['top5'], 1):
        print(f"   {i}. {row['razao_social'][:50]:<50} | R$ {row['gasto_total']:>15,.2f}")
    print("=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())