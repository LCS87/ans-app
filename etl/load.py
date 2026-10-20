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
from loguru import logger
from sqlalchemy import create_engine, text

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))
from api.config import get_settings
from etl.normalization import normalizar_serie_registro_ans


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
    #
    # P1: nomes e semânticas conferidos contra o plano de contas real da ANS
    # (DOC 275). Ver api/accounting_maps.py para o detalhamento das contas.
    EXTRA_COLUMNS = {
        # Financeira (F2.1)
        "receita": "DECIMAL(18,2) DEFAULT 0",  # 31
        "sinistros": "DECIMAL(18,2) DEFAULT 0",  # 41
        "lucro": "DECIMAL(18,2) DEFAULT 0",  # 69 ou 3-4-61
        "patrimonio": "DECIMAL(18,2) DEFAULT 0",  # 25
        "caixa": "DECIMAL(18,2) DEFAULT 0",  # 121 + 122
        "passivo_circulante": "DECIMAL(18,2) DEFAULT 0",  # 21
        "passivo_nao_circulante": "DECIMAL(18,2) DEFAULT 0",  # 23
        "ativo_total": "DECIMAL(18,2) DEFAULT 0",  # 1
        # Operacional (F2.2)
        "despesas_administrativas": "DECIMAL(18,2) DEFAULT 0",  # 46
        "pessoal": "DECIMAL(18,2) DEFAULT 0",  # 461
        "servicos_terceiros": "DECIMAL(18,2) DEFAULT 0",  # 462
        "localizacao_funcionamento": "DECIMAL(18,2) DEFAULT 0",  # 463
        "publicidade": "DECIMAL(18,2) DEFAULT 0",  # 464
        "tributos_operacionais": "DECIMAL(18,2) DEFAULT 0",  # 465
        "multas": "DECIMAL(18,2) DEFAULT 0",  # 466
        "adm_diversas": "DECIMAL(18,2) DEFAULT 0",  # 468
        "outras_despesas_operacionais": "DECIMAL(18,2) DEFAULT 0",  # 44
        "provisoes_tecnicas": "DECIMAL(18,2) DEFAULT 0",  # 211 + 231
        # Estrutura (F2.3)
        "investimentos": "DECIMAL(18,2) DEFAULT 0",  # 132
        "imobilizado": "DECIMAL(18,2) DEFAULT 0",  # 133
        "intangivel": "DECIMAL(18,2) DEFAULT 0",  # 134
        "goodwill": "DECIMAL(18,2) DEFAULT 0",  # 132139013
        "it_softwares": "DECIMAL(18,2) DEFAULT 0",  # 134129011
    }

    # Colunas do schema anterior (v1.2 inicial) com semântica errada: os nomes
    # sugeriam contas que não existem no layout ANS (obrigações trabalhistas,
    # fornecedores, glosas) e os valores vinham das contas erradas. São
    # removidas na migração para não sobrar métrica sem fundamentação.
    OBSOLETE_COLUMNS = {
        "obrigacoes_trabalhistas",
        "fornecedores",
        "judiciais",
        "provisoes",
        "glosas",
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
            passivo_circulante DECIMAL(18,2) DEFAULT 0,
            passivo_nao_circulante DECIMAL(18,2) DEFAULT 0,
            ativo_total DECIMAL(18,2) DEFAULT 0,
            despesas_administrativas DECIMAL(18,2) DEFAULT 0,
            pessoal DECIMAL(18,2) DEFAULT 0,
            servicos_terceiros DECIMAL(18,2) DEFAULT 0,
            localizacao_funcionamento DECIMAL(18,2) DEFAULT 0,
            publicidade DECIMAL(18,2) DEFAULT 0,
            tributos_operacionais DECIMAL(18,2) DEFAULT 0,
            multas DECIMAL(18,2) DEFAULT 0,
            adm_diversas DECIMAL(18,2) DEFAULT 0,
            outras_despesas_operacionais DECIMAL(18,2) DEFAULT 0,
            provisoes_tecnicas DECIMAL(18,2) DEFAULT 0,
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
        """Migração controlada (F2.5): sincroniza o schema com o mapa P1.

        * adiciona as colunas novas que faltarem;
        * remove as colunas obsoletas (semântica contábil errada).
        """
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
                conn.execute(text(f"ALTER TABLE gastos_assistenciais ADD COLUMN {col} {tipo}"))

        for col in sorted(self.OBSOLETE_COLUMNS & existing):
            logger.info(f"🗑️  Migração: ALTER TABLE DROP COLUMN {col} (semântica inválida)")
            conn.execute(text(f"ALTER TABLE gastos_assistenciais DROP COLUMN {col}"))

    # ------------------------------------------------------------------
    # CADASTRO DE OPERADORAS (tabela referenciada pela FK do DDL)
    # ------------------------------------------------------------------
    OPERADORAS_COLUMNS = {
        "cnpj": "VARCHAR(14) NOT NULL DEFAULT ''",
        "razao_social": "VARCHAR(255) NOT NULL DEFAULT ''",
        "nome_fantasia": "VARCHAR(255) DEFAULT NULL",
        "modalidade": "VARCHAR(100) DEFAULT NULL",
        "logradouro": "VARCHAR(255) DEFAULT NULL",
        "numero": "VARCHAR(20) DEFAULT NULL",
        "complemento": "VARCHAR(100) DEFAULT NULL",
        "bairro": "VARCHAR(100) DEFAULT NULL",
        "cidade": "VARCHAR(100) DEFAULT NULL",
        "uf": "CHAR(2) DEFAULT NULL",
        "cep": "VARCHAR(8) DEFAULT NULL",
        "ddd": "VARCHAR(2) DEFAULT NULL",
        "telefone": "VARCHAR(20) DEFAULT NULL",
        "fax": "VARCHAR(20) DEFAULT NULL",
        "endereco_eletronico": "VARCHAR(255) DEFAULT NULL",
        "representante": "VARCHAR(255) DEFAULT NULL",
        "cargo_representante": "VARCHAR(100) DEFAULT NULL",
        "regiao_comercializacao": "INT DEFAULT NULL",
        "data_registro_ans": "DATE DEFAULT NULL",
    }

    def sincronizar_operadoras(self, cadop: pd.DataFrame) -> int:
        """Sincroniza o cadastro CADOP na tabela ``operadoras``.

        A tabela ``gastos_assistenciais`` referencia ``operadoras`` por
        chave estrangeira (ver db/mysql/01_ddl.sql): sem esta sincronização,
        qualquer carga em um banco recem-criado é rejeitada pela FK.
        """
        if cadop is None or cadop.empty:
            logger.warning("⚠️  CADOP vazio: cadastro de operadoras não sincronizado")
            return 0

        df = cadop.copy()
        df["registro_ans"] = normalizar_serie_registro_ans(df["REG_ANS"])
        df = df[df["registro_ans"] != ""]
        df["razao_social"] = (
            df.get("RAZAO_SOCIAL", pd.Series("", index=df.index))
            .fillna("")
            .astype(str)
            .str.strip()
            .replace("", "SEM RAZAO SOCIAL")
        )
        df["cnpj"] = (
            df.get("cnpj", pd.Series("", index=df.index))
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
            .str.zfill(14)
            .str[:14]
        )
        df = df.drop_duplicates(subset=["registro_ans"], keep="first")

        ddl = """
        CREATE TABLE IF NOT EXISTS operadoras (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            registro_ans VARCHAR(10) NOT NULL UNIQUE,
            cnpj VARCHAR(14) NOT NULL DEFAULT '',
            razao_social VARCHAR(255) NOT NULL DEFAULT '',
            nome_fantasia VARCHAR(255) DEFAULT NULL,
            modalidade VARCHAR(100) DEFAULT NULL,
            logradouro VARCHAR(255) DEFAULT NULL,
            numero VARCHAR(20) DEFAULT NULL,
            complemento VARCHAR(100) DEFAULT NULL,
            bairro VARCHAR(100) DEFAULT NULL,
            cidade VARCHAR(100) DEFAULT NULL,
            uf CHAR(2) DEFAULT NULL,
            cep VARCHAR(8) DEFAULT NULL,
            ddd VARCHAR(2) DEFAULT NULL,
            telefone VARCHAR(20) DEFAULT NULL,
            fax VARCHAR(20) DEFAULT NULL,
            endereco_eletronico VARCHAR(255) DEFAULT NULL,
            representante VARCHAR(255) DEFAULT NULL,
            cargo_representante VARCHAR(100) DEFAULT NULL,
            regiao_comercializacao INT DEFAULT NULL,
            data_registro_ans DATE DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """

        with self.engine.begin() as conn:
            conn.execute(text(ddl))
            existing = set()
            try:
                result = conn.execute(
                    text(
                        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() "
                        "AND TABLE_NAME = 'operadoras'"
                    )
                )
                existing = {r[0] for r in result.fetchall()}
            except Exception as e:
                logger.warning(f"⚠️  Não foi possível ler information_schema: {e}")

            for col, tipo in self.OPERADORAS_COLUMNS.items():
                if col not in existing:
                    logger.info(f"🛠️  Migração: ALTER TABLE-operadoras ADD COLUMN {col}")
                    conn.execute(text(f"ALTER TABLE operadoras ADD COLUMN {col} {tipo}"))

            cols = [c for c in df.columns if c in existing or c == "registro_ans"]
            payload = df[cols].copy()
            payload = payload.replace({None: None, "": None, "nan": None})

            placeholders = ", ".join(f":{c}" for c in cols)
            if self.engine.dialect.name == "mysql":
                updates = ", ".join(f"{c} = VALUES({c})" for c in cols if c != "registro_ans")
                sql = (
                    f"INSERT INTO operadoras ({', '.join(cols)}) VALUES ({placeholders}) "
                    f"ON DUPLICATE KEY UPDATE {updates}"
                )
            else:
                updates = ", ".join(f"{c} = excluded.{c}" for c in cols if c != "registro_ans")
                sql = (
                    f"INSERT INTO operadoras ({', '.join(cols)}) VALUES ({placeholders}) "
                    f"ON CONFLICT (registro_ans) DO UPDATE SET {updates}"
                )
            conn.execute(text(sql), payload.to_dict(orient="records"))

        logger.success(f"✅ Cadastro sincronizado: {len(payload):,} operadoras")
        return len(payload)

    def normalizar_colunas(
        self, df: pd.DataFrame, periodo: str, dimensao: str = "gastos"
    ) -> pd.DataFrame:
        """Normaliza DataFrame para o schema MySQL da dimensão contábil (v1.2)."""
        df = df.copy()

        # Mapa {coluna_no_csv: coluna_no_banco} por dimensão
        from api.accounting_maps import DIMENSIONS

        if dimensao == "todas":
            db_cols = set(self.EXTRA_COLUMNS) | {"registro_ans", "razao_social"}
        else:
            dim = DIMENSIONS.get(dimensao, DIMENSIONS["gastos"])
            # nomes de colunas do banco são os mesmos do mapa (receita, lucro...)
            db_cols = set(dim["columns"].keys()) | {"registro_ans", "razao_social"}

        import re

        coluna_map = {}
        for col in df.columns:
            m = re.search(r"([1-4]T)", col, re.IGNORECASE)
            if m:
                coluna_map[col] = f"gasto_{m.group(1).upper()}"
            elif col == "REG_ANS":
                coluna_map[col] = "registro_ans"
            elif col == "RAZAO_SOCIAL":
                coluna_map[col] = "razao_social"
            elif col in ("total", "gasto_total") or (
                col.startswith("gasto_total_") and col[len("gasto_total_") :].isdigit()
            ):
                coluna_map[col] = "gasto_total"

        df = df.rename(columns=coluna_map)
        df["periodo"] = periodo

        # P0-3: não silenciar ausência de REG_ANS com 0 (isso criava uma
        # "operadora 000000" e podia sobrescrever linhas umas das outras).
        faltando = {"registro_ans", "razao_social"} - set(df.columns)
        if faltando:
            raise ValueError(
                f"Colunas obrigatórias ausentes no CSV: {sorted(faltando)}. "
                "Esperado REG_ANS e RAZAO_SOCIAL."
            )

        df["registro_ans"] = normalizar_serie_registro_ans(df["registro_ans"])
        sem_registro = int((df["registro_ans"] == "").sum())
        if sem_registro:
            raise ValueError(
                f"{sem_registro} linha(s) sem REG_ANS válido. " "Corrija o CSV antes de importar."
            )

        df["razao_social"] = (
            df["razao_social"].fillna("").astype(str).str.strip().replace("", "SEM RAZAO SOCIAL")
        )

        if dimensao in ("gastos", "todas") and "gasto_total" not in df.columns:
            # fallback: soma dos trimestres disponíveis
            tri_cols = [
                c for c in ("gasto_1T", "gasto_2T", "gasto_3T", "gasto_4T") if c in df.columns
            ]
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
        elif dimensao == "todas":
            # Carga completa: gastos + todas as dimensões v1.2.
            colunas_esperadas = [
                "periodo",
                "registro_ans",
                "razao_social",
                "gasto_1T",
                "gasto_2T",
                "gasto_3T",
                "gasto_4T",
                "gasto_total",
            ] + sorted(self.EXTRA_COLUMNS)
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
        """Carrega DataFrame no MySQL via UPSERT.

        ``truncate=True`` remove, **depois do UPSERT**, as operadoras do
        período que não vieram no DataFrame. Diferente do DELETE anterior,
        isso preserva as colunas de dimensão de quem continua no período e
        evita apagar a tabela antes de saber se a carga vai funcionar.
        """
        df = df.copy()

        if df.empty:
            raise ValueError("DataFrame vazio: nada para carregar")
        if "registro_ans" not in df.columns:
            raise ValueError("Coluna obrigatória 'registro_ans' ausente")

        # P0-3: garante a mesma chave canônica usada pelo ETL e pela API.
        df["periodo"] = str(periodo)
        df["registro_ans"] = normalizar_serie_registro_ans(df["registro_ans"])

        invalidos = int((df["registro_ans"] == "").sum())
        if invalidos:
            raise ValueError(f"{invalidos} linha(s) sem REG_ANS válido")

        antes = len(df)
        df = df.drop_duplicates(subset=["periodo", "registro_ans"], keep="last")
        if len(df) != antes:
            logger.warning(
                f"🧹 {antes - len(df):,} linha(s) duplicada(s) por "
                f"(periodo, registro_ans) removida(s) antes do UPSERT"
            )

        with self.engine.begin() as conn:
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

            if truncate:
                # Remove somente quem não está no novo conjunto. O UPSERT já
                # atualizou as colunas das operadoras que continuam.
                ids = df["registro_ans"].drop_duplicates().tolist()
                id_params = {f"id{i}": valor for i, valor in enumerate(ids)}
                id_placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
                resultado = conn.execute(
                    text(
                        "DELETE FROM gastos_assistenciais "
                        "WHERE periodo = :periodo "
                        f"AND registro_ans NOT IN ({id_placeholders})"
                    ),
                    {"periodo": periodo, **id_params},
                )
                removidas = resultado.rowcount or 0
                if removidas:
                    logger.info(
                        f"🧹 {removidas:,} operadora(s) ausente(s) do novo "
                        f"conjunto removida(s) do período {periodo}"
                    )

            logger.success(f"✅ {linhas:,} linhas do período {periodo} carregadas")
            return linhas

    def validar(self, periodo: str) -> dict:
        """Valida os dados carregados."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM gastos_assistenciais WHERE periodo = :periodo"),
                {"periodo": periodo},
            )
            total = result.scalar()

            result = conn.execute(
                text("SELECT SUM(gasto_total) FROM gastos_assistenciais WHERE periodo = :periodo"),
                {"periodo": periodo},
            )
            soma = result.scalar() or 0

            result = conn.execute(
                text("""
                    SELECT registro_ans, razao_social, gasto_total
                    FROM gastos_assistenciais
                    WHERE periodo = :periodo
                    ORDER BY gasto_total DESC
                    LIMIT 5
                """),
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
    # Carga manual do CSV de gastos: não remover operadoras ausentes, para
    # não apagar linhas que só existem em outras dimensões.
    loader.carregar(df_normalizado, periodo=periodo_alvo, truncate=False)

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
        print(f"   {i}. {row['razao_social'][:50]:<50} | R$ {row['gasto_total']:>15,.2f}")
    print("=" * 80)


if __name__ == "__main__":
    main()
