"""
Scheduler mensal do pipeline ETL.

Dispara automaticamente no 1º domingo de cada mês às 03:00 (America/Sao_Paulo).
Usa lock Redis para evitar execuções concorrentes.
"""

import os
from datetime import datetime

from loguru import logger

try:  # dependências opcionais em ambientes de teste/CI minimalistas
    import redis
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    _APS_AVAILABLE = True
except ImportError:  # pragma: no cover
    redis = None
    AsyncIOScheduler = None
    CronTrigger = None
    _APS_AVAILABLE = False

from api.config import get_settings

# Configurações fixas do scheduler
SCHEDULER_TIMEZONE = "America/Sao_Paulo"
SCHEDULER_HOUR = 3  # 03:00
SCHEDULER_MINUTE = 0
# Desativação via env (testes/CI): ETL_SCHEDULER_DISABLED=1
SCHEDULER_ENABLED = _APS_AVAILABLE and os.getenv("ETL_SCHEDULER_DISABLED") != "1"

if _APS_AVAILABLE:
    scheduler = AsyncIOScheduler(timezone=SCHEDULER_TIMEZONE)
else:  # pragma: no cover
    scheduler = None

LOCK_KEY = "etl_pipeline_lock"
LOCK_TTL = 7200  # 2 horas


def _get_redis():
    """Retorna cliente Redis."""
    settings = get_settings()
    return redis.from_url(settings.redis_url, socket_connect_timeout=2)


def is_pipeline_running() -> bool:
    """Verifica se há pipeline em execução (lock Redis)."""
    try:
        return _get_redis().exists(LOCK_KEY) == 1
    except Exception:
        return False


async def scheduled_pipeline():
    """Job mensal: executa o pipeline completo."""
    ano_atual = datetime.now().year
    logger.info(f"⏰ Job mensal disparado para o ano {ano_atual}")

    r = None
    try:
        r = _get_redis()
        if not r.set(LOCK_KEY, "1", nx=True, ex=LOCK_TTL):
            logger.warning("⚠️ Pipeline já em execução, pulando job agendado")
            return
    except Exception as e:
        logger.warning(f"⚠️ Redis indisponível, rodando sem lock: {e}")
        r = None

    try:
        from etl.pipeline import PipelineOrchestrator

        orchestrator = PipelineOrchestrator()
        results = await orchestrator.run([ano_atual])

        if all(r_["status"] == "success" for r_ in results):
            logger.success(f"✅ Job mensal concluído com sucesso ({ano_atual})")
        else:
            logger.error(f"❌ Job mensal finalizou com erros ({ano_atual})")

    except Exception as e:
        logger.error(f"❌ Erro no job mensal: {e}")

    finally:
        if r is not None:
            try:
                r.delete(LOCK_KEY)
            except Exception:
                pass


async def run_pipeline_manual(ano: int = None):
    """Executa o pipeline manualmente (via endpoint admin)."""
    ano = ano or datetime.now().year

    r = None
    try:
        r = _get_redis()
        if not r.set(LOCK_KEY, "1", nx=True, ex=LOCK_TTL):
            raise RuntimeError("Pipeline já em execução")
    except RuntimeError:
        raise
    except Exception as e:
        logger.warning(f"⚠️ Redis indisponível, rodando sem lock: {e}")
        r = None

    try:
        from etl.pipeline import PipelineOrchestrator

        orchestrator = PipelineOrchestrator()
        results = await orchestrator.run([ano])
        return results
    finally:
        if r is not None:
            try:
                r.delete(LOCK_KEY)
            except Exception:
                pass


def start_scheduler():
    """Inicia o scheduler com o job mensal."""
    if not SCHEDULER_ENABLED:
        logger.info("⏸️ Scheduler desabilitado via config")
        return

    # 1º domingo = dias 1-7 que caem em domingo
    scheduler.add_job(
        scheduled_pipeline,
        trigger=CronTrigger(
            day="1-7",
            day_of_week="sun",
            hour=SCHEDULER_HOUR,
            minute=SCHEDULER_MINUTE,
            timezone=SCHEDULER_TIMEZONE,
        ),
        id="monthly_etl_pipeline",
        name="Pipeline ETL Mensal ANS",
        replace_existing=True,
    )

    scheduler.start()

    job = scheduler.get_job("monthly_etl_pipeline")
    if job:
        logger.success(f"✅ Scheduler iniciado. Próxima execução: {job.next_run_time}")


def stop_scheduler():
    """Para o scheduler no shutdown."""
    if scheduler is not None and scheduler.running:
        scheduler.shutdown()
        logger.info("⏹️ Scheduler parado")


def get_scheduler_status() -> dict:
    """Retorna status do scheduler para o endpoint admin."""
    job = scheduler.get_job("monthly_etl_pipeline")

    return {
        "enabled": SCHEDULER_ENABLED,
        "running": scheduler.running,
        "next_run": job.next_run_time.isoformat() if job else None,
        "pipeline_running": is_pipeline_running(),
        "timezone": SCHEDULER_TIMEZONE,
        "cron": f"1º domingo às {SCHEDULER_HOUR:02d}:{SCHEDULER_MINUTE:02d}",
    }
