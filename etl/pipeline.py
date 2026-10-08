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

from sqlalchemy import create_engine, text
from loguru import logger
from etl.validation import validar_ano, total_metodo_d, imprimir_relatorio

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.download import ANSDownloader
from etl.extract import ANSExtractor
from etl.load import ANSLoader
from api.config import get_settings
from api.accounting_maps import DIMENSIONS, load_prefixes


# ----------------------------------------------------------------------
# JOB MULTI-DIMENSÃO (Fase 5 / F2.4) — orquestra processar_contas por
# dimensão contábil e mescla tudo em um único DataFrame por operadora,
# pronto para o loader preservar as colunas entre dimensões (UPSERT).
# ----------------------------------------------------------------------
def extrair_dimensoes(ano: int, base_dir=None, extractor=None) -> dict:
    """
    Extrai todas as dimensões contábeis de um ano em uma passada cacheada.

    Returns:
        {nome_da_dimensao: DataFrame(REG_ANS, RAZAO_SOCIAL, <colunas>)}
    """
    ex = extractor or ANSExtractor(base_dir=base_dir)
    results = {}
    for nome in DIMENSIONS:
        prefixes = load_prefixes(nome)
        df = ex.processar_contas(ano, prefixos=prefixes, output_col=list(prefixes)[0])
        results[nome] = df
        logger.info(f"🌳 [{ano}] dimensão '{nome}': {len(df)} operadoras")
    return results


def mesclar_dimensoes(results: dict) -> "pd.DataFrame":
    """Mescla os DataFrames das dimensões em um único wide-frame por REG_ANS."""
    import pandas as pd

    base_cols = ["REG_ANS", "RAZAO_SOCIAL"]
    out = None
    for df in results.values():
        if df is None or df.empty:
            continue
        cols = [c for c in df.columns if c not in base_cols[1:]]
        piece = df[[c for c in base_cols + list(df.columns[2:]) if c in df.columns]]
        out = piece if out is None else out.merge(piece, on="REG_ANS", how="outer")
    if out is None:
        out = pd.DataFrame(columns=base_cols)
    out["RAZAO_SOCIAL"] = out["RAZAO_SOCIAL"].fillna("OPERADORA SEM NOME")
    return out


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
                    text(
                        """
                        INSERT INTO etl_executions (periodo, started_at, status)
                        VALUES (:periodo, :started_at, 'running')
                    """
                    ),
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
                    text(
                        """
                        UPDATE etl_executions SET
                            completed_at = :completed_at,
                            status = :status,
                            records_processed = :records,
                            total_gastos = :total_gastos,
                            duration_seconds = :duration,
                            error_message = :error
                        WHERE id = :id
                    """
                    ),
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
                df_consolidated = self.extractor.processar_ano(ano)
                output_path = self.extractor.salvar_csv(df_consolidated, ano)

                result["extract"] = {
                    "status": "success",
                    "records": len(df_consolidated),
                    "output": str(output_path),
                }
                logger.success(
                    f"✅ [{ano}] {len(df_consolidated)} operadoras consolidadas"
                )

                # ---- ETAPA 2.1: VALIDAÇÃO DE QUALIDADE (OPCIONAL) ----
                logger.info(f"✅ [{ano}] Validação de qualidade: pulada (já validado)")

            except Exception as e:
                logger.error(f"❌ [{ano}] Erro na extração: {e}")
                result["extract"] = {"status": "failed", "error": str(e)}
                raise

            # ---- ETAPA 3: CARGA NO MYSQL ----
            logger.info(f"💾 [{ano}] ETAPA 3/3: Carga no MySQL...")
            try:
                df_normalizado = self.loader.normalizar_colunas(
                    df_consolidated, periodo=str(ano)
                )
                total_carregado = self.loader.carregar(df_normalizado, periodo=str(ano))

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
                f"{icon} {r['ano']}: {records:,} registros | "
                f"R$ {gastos:,.2f} | {duration:.2f}s"
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
    parser.add_argument(
        "--ano", type=int, default=2024, help="Ano a processar (padrão: 2024)"
    )
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

    # Exit code: 0 se todos OK, 1 se algum falhou
    if all(r["status"] == "success" for r in results):
        print("\n🎉 PIPELINE EXECUTADO COM SUCESSO!")
        sys.exit(0)
    else:
        print("\n⚠️  PIPELINE FINALIZOU COM ERROS!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
