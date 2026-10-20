"""
Pipeline ETL completo da ANS.

Orquestra:
    1. Download (ZIPs + CADOP)
    2. Extração e transformação (gastos assistenciais)
    3. Carga no MySQL
    4. Registro de histórico

Uso:
    py -m etl.pipeline                # Processa 2024 (padrão)
    py -m etl.pipeline --ano 2023     # Processa ano específico
    py -m etl.pipeline --anos 2023,2024  # Processa múltiplos anos
"""

import argparse
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger
from sqlalchemy import create_engine, text

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.accounting_maps import DIMENSIONS, load_prefixes
from api.config import get_settings
from etl.download import ANSDownloader
from etl.extract import ANSExtractor
from etl.load import ANSLoader
from etl.validation import imprimir_relatorio, validar_ano


# ----------------------------------------------------------------------
# JOB MULTI-DIMENSÃO (Fase 5 / F2.4) — orquestra processar_contas por
# dimensão contábil e mescla tudo em um único DataFrame por operadora,
# pronto para o loader preservar as colunas entre dimensões (UPSERT).
# ----------------------------------------------------------------------
def extrair_dimensoes(ano: int, base_dir=None, extractor=None) -> dict:
    """
    Extrai todas as dimensões contábeis de um ano em uma passada cacheada.

    ``gastos`` usa ``processar_ano`` para manter as colunas trimestrais
    (gasto_1T..4T); as demais dimensões usam ``processar_contas``.

    Returns:
        {nome_da_dimensao: DataFrame(REG_ANS, RAZAO_SOCIAL, <colunas>)}
    """
    ex = extractor or ANSExtractor(base_dir=base_dir)
    results = {}
    for nome in DIMENSIONS:
        prefixes = dict(load_prefixes(nome))
        if nome == "financeira":
            # Contas internas para o fallback do resultado:
            # 3 = Receitas, 4 = Despesas, 61 = Impostos/participações.
            prefixes.update(
                {
                    "receita_total": "3",
                    "despesas_total": "4",
                    "impostos": "61",
                }
            )
        if nome == "gastos":
            df = ex.processar_ano(ano, quarterly_output=True)
        else:
            df = ex.processar_contas(ano, prefixos=prefixes, output_col=list(prefixes)[0])

        if nome == "financeira" and not df.empty:
            import pandas as pd

            apurado = df["lucro"] if "lucro" in df.columns else pd.Series(0.0, index=df.index)
            # 3 = Receitas, 4 = Despesas, 61 = Impostos e participações sobre
            # o lucro. A diferença é o RESULTADO DO EXERCÍCIO (a conta 69
            # "APURAÇÃO DO RESULTADO" vale exatamente isso quando publicada).
            derivado = (
                df.get("receita_total", 0.0)
                - df.get("despesas_total", 0.0)
                - df.get("impostos", 0.0)
            )
            # Regra uniforme para todas as operadoras: usa o derivado; só
            # recorre à apuração publicada quando o derivado não existe
            # (operadora sem 3/4/61 no período).
            df["lucro"] = derivado.where(derivado != 0, apurado)
            df = df.drop(
                columns=["receita_total", "despesas_total", "impostos"],
                errors="ignore",
            )

        results[nome] = df
        logger.info(f"🌳 [{ano}] dimensão '{nome}': {len(df)} operadoras")
    return results


def mesclar_dimensoes(results: dict) -> "pd.DataFrame":  # noqa: F821
    """Mescla as dimensões em um wide-frame único por REG_ANS.

    A primeira dimensão define a base (idealmente ``gastos``, que já traz
    ``gasto_total`` e as colunas trimestrais). As seguintes entram apenas
    com ``REG_ANS`` + suas métricas, evitando ``RAZAO_SOCIAL_x/_y`` e
    colunas duplicadas. Operadoras que só existem em outra dimensão ficam
    com ``gasto_total = 0``.
    """
    import pandas as pd

    base = None
    for df in results.values():
        if df is None or df.empty:
            continue
        if base is None:
            base = df.copy()
            continue

        piece = df.drop(columns=["RAZAO_SOCIAL"], errors="ignore")
        duplicadas = [c for c in piece.columns if c in base.columns and c != "REG_ANS"]
        if duplicadas:
            piece = piece.drop(columns=duplicadas)
        base = base.merge(piece, on="REG_ANS", how="outer")

    if base is None:
        return pd.DataFrame(columns=["REG_ANS", "RAZAO_SOCIAL"])

    # Nome mais completo disponível em qualquer dimensão.
    nomes = {}
    for df in results.values():
        if df is None or df.empty:
            continue
        if {"REG_ANS", "RAZAO_SOCIAL"} <= set(df.columns):
            nomes.update(dict(zip(df["REG_ANS"], df["RAZAO_SOCIAL"])))

    base["RAZAO_SOCIAL"] = base["REG_ANS"].map(nomes).fillna("OPERADORA SEM NOME")
    for col in base.columns:
        if col not in ("REG_ANS", "RAZAO_SOCIAL"):
            base[col] = pd.to_numeric(base[col], errors="coerce").fillna(0.0)

    return base.reset_index(drop=True)


class PipelineOrchestrator:
    """Orquestrador do pipeline ETL completo."""

    def __init__(self):
        self.settings = get_settings()
        self.downloader = ANSDownloader()
        self.extractor = ANSExtractor()
        self.loader = ANSLoader()

        # Engine para gravar histórico
        self.engine = create_engine(
            self.settings.database_url,
            pool_pre_ping=True,
        )

        # Garantir tabela de histórico
        self._criar_tabela_historico()

    def _criar_tabela_historico(self):
        """Cria tabela de histórico de execuções se não existir."""
        ddl = """
        CREATE TABLE IF NOT EXISTS etl_executions (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            periodo VARCHAR(10) NOT NULL,
            started_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP NULL,
            status ENUM('running', 'success', 'failed') NOT NULL,
            records_processed INT DEFAULT 0,
            total_gastos DECIMAL(20,2) DEFAULT 0,
            error_message TEXT NULL,
            duration_seconds DECIMAL(10,2) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_periodo (periodo),
            INDEX idx_status (status),
            INDEX idx_started (started_at DESC)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        try:
            with self.engine.begin() as conn:
                conn.execute(text(ddl))
        except Exception as e:
            logger.warning(f"⚠️  Não foi possível criar tabela de histórico: {e}")

    def _registrar_inicio(self, periodo: str) -> Optional[int]:
        """Registra início de execução no histórico."""
        try:
            with self.engine.begin() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO etl_executions (periodo, started_at, status)
                        VALUES (:periodo, :started_at, 'running')
                    """),
                    {"periodo": periodo, "started_at": datetime.now()},
                )
                return result.lastrowid
        except Exception as e:
            logger.warning(f"⚠️  Não foi possível registrar início: {e}")
            return None

    def _registrar_fim(
        self,
        execution_id: Optional[int],
        status: str,
        records: int = 0,
        total_gastos: float = 0,
        duration: float = 0,
        error: Optional[str] = None,
    ):
        """Registra fim de execução no histórico."""
        if execution_id is None:
            return
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE etl_executions SET
                            completed_at = :completed_at,
                            status = :status,
                            records_processed = :records,
                            total_gastos = :total_gastos,
                            duration_seconds = :duration,
                            error_message = :error
                        WHERE id = :id
                    """),
                    {
                        "id": execution_id,
                        "completed_at": datetime.now(),
                        "status": status,
                        "records": records,
                        "total_gastos": total_gastos,
                        "duration": duration,
                        "error": error,
                    },
                )
        except Exception as e:
            logger.warning(f"⚠️  Não foi possível registrar fim: {e}")

    async def run_for_year(self, ano: int) -> dict:
        """
        Executa pipeline completo para um ano específico.

        Returns:
            Dict com status e métricas da execução.
        """
        started = time.time()
        execution_id = self._registrar_inicio(str(ano))

        result = {
            "ano": ano,
            "status": "running",
            "download": {"status": "pending"},
            "extract": {"status": "pending"},
            "load": {"status": "pending"},
        }

        try:
            # ---- ETAPA 1: DOWNLOAD ----
            logger.info(f"📥 [{ano}] ETAPA 1/3: Download de dados...")
            try:
                download_result = await self.downloader.download_all(ano)
                result["download"] = {
                    "status": "success",
                    "files": len(download_result["demonstracoes"]),
                    "cadop": download_result["cadop"] is not None,
                }
                logger.success(f"✅ [{ano}] Download completo")
            except Exception as e:
                logger.error(f"❌ [{ano}] Erro no download: {e}")
                result["download"] = {"status": "failed", "error": str(e)}
                raise
            # ---- ETAPA 2: EXTRAÇÃO E TRANSFORMAÇÃO ----
            logger.info(f"🔄 [{ano}] ETAPA 2/3: Extração e transformação...")
            try:
                # P0-4: uma única passada extrai gastos + financeira +
                # operacional + estrutura e mescla por REG_ANS.
                resultados = extrair_dimensoes(ano, extractor=self.extractor)
                df_gastos = resultados.get("gastos")
                if df_gastos is None or df_gastos.empty:
                    raise ValueError("Nenhuma operadora com gastos assistenciais")
                df_consolidado = mesclar_dimensoes(resultados)
                output_path = self.extractor.salvar_csv(df_gastos, ano)

                # Cadastro de operadoras (referenciado pela FK do DDL).
                self.loader.sincronizar_operadoras(self.extractor.carregar_cadop())

                result["extract"] = {
                    "status": "success",
                    "records": len(df_gastos),
                    "dimensions": {nome: len(df) for nome, df in resultados.items()},
                    "output": str(output_path),
                }
                logger.success(
                    f"✅ [{ano}] {len(df_gastos)} operadoras de gastos | "
                    f"{len(df_consolidado)} operadoras no consolidado multi-dimensão"
                )

                # ---- ETAPA 2.1: GATE DE QUALIDADE (BLOQUEIA A CARGA) ----
                bruto = self.extractor.df_bruto(ano).rename(columns={"TRIMESTRE": "TRIM"})
                veredito, checks = validar_ano(
                    ano,
                    bruto,
                    total_base=self.loader.obter_total(str(ano - 1)),
                )
                imprimir_relatorio(ano, veredito, checks)
                result["quality_gate"] = {"veredito": veredito, "checks": checks}
                if veredito == "BLOQUEADO":
                    raise ValueError(
                        f"Gate de qualidade bloqueou o ano {ano}: "
                        + "; ".join(
                            f"{c['check']}={c['detalhe']}" for c in checks if c["status"] == "FAIL"
                        )
                    )

            except Exception as e:
                logger.error(f"❌ [{ano}] Erro na extração: {e}")
                result["extract"] = {"status": "failed", "error": str(e)}
                raise

            # ---- ETAPA 3: CARGA NO MYSQL ----
            logger.info(f"💾 [{ano}] ETAPA 3/3: Carga no MySQL...")
            try:
                df_normalizado = self.loader.normalizar_colunas(
                    df_consolidado, periodo=str(ano), dimensao="todas"
                )
                total_carregado = self.loader.carregar(
                    df_normalizado, periodo=str(ano), truncate=True
                )

                validacao = self.loader.validar(str(ano))

                result["load"] = {
                    "status": "success",
                    "records_loaded": total_carregado,
                    "total_gastos": validacao["soma_gastos"],
                }
                logger.success(f"✅ [{ano}] {total_carregado} registros no MySQL")
                logger.success(f"💰 [{ano}] Total: R$ {validacao['soma_gastos']:,.2f}")

            except Exception as e:
                logger.error(f"❌ [{ano}] Erro na carga: {e}")
                result["load"] = {"status": "failed", "error": str(e)[:1000]}
                raise

            # ---- SUCESSO ----
            duration = time.time() - started
            result["status"] = "success"
            result["duration_seconds"] = round(duration, 2)
            result["records_processed"] = result["extract"]["records"]
            result["total_gastos"] = result["load"]["total_gastos"]

            self._registrar_fim(
                execution_id,
                status="success",
                records=result["records_processed"],
                total_gastos=result["total_gastos"],
                duration=duration,
            )

            return result

        except Exception as e:
            duration = time.time() - started
            result["status"] = "failed"
            result["error"] = str(e)
            result["duration_seconds"] = round(duration, 2)

            self._registrar_fim(
                execution_id,
                status="failed",
                duration=duration,
                error=str(e),
            )

            return result

    async def run(self, anos: List[int]) -> List[dict]:
        """Executa pipeline para múltiplos anos em sequência."""
        logger.info("=" * 70)
        logger.info(f"🚀 PIPELINE ETL INICIADO - Anos: {anos}")
        logger.info("=" * 70)

        started_total = time.time()
        results = []

        for ano in anos:
            logger.info(f"\n{'='*70}")
            logger.info(f"📅 Processando ano {ano}")
            logger.info(f"{'='*70}")

            result = await self.run_for_year(ano)
            results.append(result)

        duration_total = time.time() - started_total

        # Resumo final
        logger.info("\n" + "=" * 70)
        logger.info("📊 RESUMO FINAL DO PIPELINE")
        logger.info("=" * 70)

        success_count = sum(1 for r in results if r["status"] == "success")
        total_records = sum(r.get("records_processed", 0) for r in results)
        total_gastos = sum(r.get("total_gastos", 0) for r in results)

        for r in results:
            icon = "✅" if r["status"] == "success" else "❌"
            records = r.get("records_processed", 0)
            gastos = r.get("total_gastos", 0)
            duration = r.get("duration_seconds", 0)
            logger.info(
                f"{icon} {r['ano']}: {records:,} registros | " f"R$ {gastos:,.2f} | {duration:.2f}s"
            )

        logger.info(f"\n⏱️  Tempo total: {duration_total:.2f}s")
        logger.info(f"✅ Sucessos: {success_count}/{len(anos)}")
        logger.info(f"📊 Total registros: {total_records:,}")
        logger.info(f"💰 Total gastos: R$ {total_gastos:,.2f}")
        logger.info("=" * 70)

        return results


async def main():
    """Entry point para execução via CLI."""
    parser = argparse.ArgumentParser(description="Pipeline ETL ANS Intelligence")
    parser.add_argument("--ano", type=int, default=2024, help="Ano a processar (padrão: 2024)")
    parser.add_argument(
        "--anos",
        type=str,
        default=None,
        help="Lista de anos separados por vírgula (ex: 2023,2024)",
    )
    args = parser.parse_args()

    # Determinar lista de anos
    if args.anos:
        anos = [int(a.strip()) for a in args.anos.split(",")]
    else:
        anos = [args.ano]

    # Configurar logging em arquivo
    logger.add(
        "etl_pipeline.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    )

    orchestrator = PipelineOrchestrator()
    results = await orchestrator.run(anos)

    # Exit code: 0 se todos OK, 1 se algum falhou.
    # Usa logger (e não print) porque o console do Windows (cp1252) não
    # consegue codificar os emojis e derrubava o processo no final.
    if all(r["status"] == "success" for r in results):
        logger.success("PIPELINE EXECUTADO COM SUCESSO!")
        sys.exit(0)
    else:
        logger.error("PIPELINE FINALIZOU COM ERROS!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
