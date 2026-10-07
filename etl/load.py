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

    # Colunas novas do schema expandido v1.2 (F2.5) — adicionadas via migração
    # controlada ("ALTER TABLE ... ADD COLUMN IF NOT EXISTS" não existe no MySQL,
    # então checamos information_schema antes).
    EXTRA_COLUMNS = {
        # Financeira (F2.1)
        "receita": "DECIMAL(18,2) DEFAULT 0",
        "sinistros": "DECIMAL(18,2) DEFAULT 0",
        "lucro": "DECIMAL(18,2) DEFAULT 0",
        "patrimonio": "DECIMAL(18,2) DEFAULT 0",
        "caixa": "DECIMAL(18,2) DEFAULT 0",
        "obrigacoes_trabalhistas": "DECIMAL(18,2) DEFAULT 0",
        "fornecedores": "DECIMAL(18,2) DEFAULT 0",
        # Operacional (F2.2)
        "despesas_administrativas": "DECIMAL(18,2) DEFAULT 0",
        "pessoal": "DECIMAL(18,2) DEFAULT 0",
        "judiciais": "DECIMAL(18,2) DEFAULT 0",
        "provisoes": "DECIMAL(18,2) DEFAULT 0",
        "glosas": "DECIMAL(18,2) DEFAULT 0",
        # Estrutura (F2.3)
        "investimentos": "DECIMAL(18,2) DEFAULT 0",
        "imobilizado": "DECIMAL(18,2) DEFAULT 0",
        "intangivel": "DECIMAL(18,2) DEFAULT 0",
        "goodwill": "DECIMAL(18,2) DEFAULT 0",
        "it_softwares": "DECIMAL(18,2) DEFAULT 0",
    }

    def criar_tabela_se_nao_existe(self):
        """Cria tabela gastos_assistenciais se não existir (schema v1.2)."""
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
            receita DECIMAL(18,2) DEFAULT 0,
            sinistros DECIMAL(18,2) DEFAULT 0,
            lucro DECIMAL(18,2) DEFAULT 0,
            patrimonio DECIMAL(18,2) DEFAULT 0,
            caixa DECIMAL(18,2) DEFAULT 0,
            obrigacoes_trabalhistas DECIMAL(18,2) DEFAULT 0,
            fornecedores DECIMAL(18,2) DEFAULT 0,
            despesas_administrativas DECIMAL(18,2) DEFAULT 0,
            pessoal DECIMAL(18,2) DEFAULT 0,
            judiciais DECIMAL(18,2) DEFAULT 0,
            provisoes DECIMAL(18,2) DEFAULT 0,
            glosas DECIMAL(18,2) DEFAULT 0,
            investimentos DECIMAL(18,2) DEFAULT 0,
            imobilizado DECIMAL(18,2) DEFAULT 0,
            intangivel DECIMAL(18,2) DEFAULT 0,
            goodwill DECIMAL(18,2) DEFAULT 0,
            it_softwares DECIMAL(18,2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_periodo_registro (periodo, registro_ans),
            INDEX idx_periodo (periodo),
            INDEX idx_gasto_total (gasto_total DESC),
            INDEX idx_receita (receita DESC),
            INDEX idx_registro_ans (registro_ans)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        with self.engine.begin() as conn:
            conn.execute(text(ddl))
            self._migrar_colunas_extras(conn)
        logger.success("✅ Tabela gastos_assistenciais verificada/criada (v1.2)")

    def _migrar_colunas_extras(self, conn):
        """Migração controlada (F2.5): adiciona colunas v1.2 que faltarem."""
        existing = set()
        try:
            result = conn.execute(
                text(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME = 'gastos_assistenciais'"
                )
            )
            existing = {r[0] for r in result.fetchall()}
        except Exception as e:  # banco de teste pode não ter information_schema
            logger.warning(f"⚠️  Não foi possível ler information_schema: {e}")
            return

        for col, tipo in self.EXTRA_COLUMNS.items():
            if col not in existing:
                logger.info(f"🛠️  Migração: ALTER TABLE ADD COLUMN {col}")
                conn.execute(
                    text(f"ALTER TABLE gastos_assistenciais ADD COLUMN {col} {tipo}")
                )

    def normalizar_colunas(
        self, df: pd.DataFrame, periodo: str, dimensao: str = "gastos"
    ) -> pd.DataFrame:
        """Normaliza DataFrame para o schema MySQL da dimensão contábil (v1.2)."""
        df = df.copy()

        # Mapa {coluna_no_csv: coluna_no_banco} por dimensão
        from api.accounting_maps import DIMENSIONS

        dim = DIMENSIONS.get(dimensao, DIMENSIONS["gastos"])
        # nomes de colunas do banco são os mesmos do mapa (receita, lucro...)
        db_cols = set(dim["columns"].keys()) | {"registro_ans", "razao_social"}

        coluna_map = {}
        for col in df.columns:
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
            elif col == "REG_ANS":
                coluna_map[col] = "registro_ans"
            elif col == "RAZAO_SOCIAL":
                coluna_map[col] = "razao_social"
            elif col == "total":
                coluna_map[col] = "gasto_total"
            elif col.startswith("gasto_total_") and col[len("gasto_total_"):].isdigit():
                # variante com sufixo de ano (ex.: gasto_total_2024 → gasto_total)
                coluna_map[col] = "gasto_total"

        df = df.rename(columns=coluna_map)
        df["periodo"] = periodo

        if dimensao == "gastos" and "gasto_total" not in df.columns:
            # fallback: soma dos trimestres disponíveis
            tri_cols = [c for c in ("gasto_1T", "gasto_2T", "gasto_3T", "gasto_4T") if c in df.columns]
            if tri_cols:
                df["gasto_total"] = df[tri_cols].sum(axis=1)

        if dimensao == "gastos":
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
        else:
            colunas_esperadas = ["periodo", "registro_ans", "razao_social"] + sorted(
                db_cols - {"registro_ans", "razao_social"}
            )

        for col in colunas_esperadas:
            if col not in df.columns:
                logger.warning(f"⚠️  Coluna {col} não encontrada, adicionando com 0")
                df[col] = 0

        return df[colunas_esperadas]

    def carregar(self, df: pd.DataFrame, periodo: str, truncate: bool = True) -> int:
        """Carrega DataFrame no MySQL com UPSERT (preserva colunas de outras dimensões)."""
        with self.engine.begin() as conn:
            if truncate:
                logger.info(f"🗑️  Removendo dados antigos do período {periodo}...")
                conn.execute(
                    text("DELETE FROM gastos_assistenciais WHERE periodo = :periodo"),
                    {"periodo": periodo},
                )

            linhas = len(df)
            cols = list(df.columns)
            placeholders = ", ".join(f":{c}" for c in cols)
            is_mysql = self.engine.dialect.name == "mysql"
            if is_mysql:
                updates = ", ".join(f"{c} = VALUES({c})" for c in cols if c != "id")
                sql = (
                    f"INSERT INTO gastos_assistenciais ({', '.join(cols)}) "
                    f"VALUES ({placeholders}) "
                    f"ON DUPLICATE KEY UPDATE {updates}"
                )
            else:
                # SQLite/Postgres (testes em memória): UPSERT padrão SQL
                upd_cols = [c for c in cols if c not in ("periodo", "registro_ans")]
                updates = ", ".join(f"{c} = excluded.{c}" for c in upd_cols)
                sql = (
                    f"INSERT INTO gastos_assistenciais ({', '.join(cols)}) "
                    f"VALUES ({placeholders}) ON CONFLICT (periodo, registro_ans) "
                    f"DO UPDATE SET {updates}"
                )
            records = df.to_dict(orient="records")
            conn.execute(text(sql), records)

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
