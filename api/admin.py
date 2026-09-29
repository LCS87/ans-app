"""Endpoints de administração do sistema."""
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
import redis

from api.config import get_settings

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])
settings = get_settings()

# Estado em memória
_update_running = False
_update_history = []
START_TIME = time.time()


class DiskUsageResponse(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    used_percent: float
    breakdown: dict


class UpdateStatusResponse(BaseModel):
    is_running: bool
    last_run: Optional[dict] = None
    next_run: Optional[str] = None
    uptime_seconds: float


class RunUpdateResponse(BaseModel):
    message: str
    started_at: str


def _get_real_disk_usage() -> dict:
    """Calcula uso real de disco."""
    project_root = Path(__file__).parent.parent
    
    def dir_size(path: Path) -> float:
        if not path.exists():
            return 0
        return sum(f.stat().st_size for f in path.rglob('*') if f.is_file()) / (1024**3)
    
    total, used, free = shutil.disk_usage(project_root)
    
    return {
        "total_gb": round(total / (1024**3), 2),
        "used_gb": round(used / (1024**3), 2),
        "free_gb": round(free / (1024**3), 2),
        "used_percent": round((used / total) * 100, 2),
        "breakdown": {
            "backups": round(dir_size(project_root / "backups"), 2),
            "raw_data": round(dir_size(project_root / "etl" / "data" / "raw"), 2),
            "logs": round(dir_size(project_root / "logs"), 2),
        }
    }


def _check_redis() -> str:
    """Verifica status do Redis."""
    try:
        r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        return "ok"
    except Exception:
        return "error"


@router.get("/disk-usage", response_model=DiskUsageResponse)
async def get_disk_usage():
    """Retorna uso real de disco."""
    data = _get_real_disk_usage()
    return DiskUsageResponse(**data)


@router.get("/status", response_model=UpdateStatusResponse)
async def get_status():
    """Retorna status do sistema."""
    last_run = _update_history[-1] if _update_history else None
    
    return UpdateStatusResponse(
        is_running=_update_running,
        last_run=last_run,
        next_run="1º domingo do mês às 03:00" if settings.scheduler_enabled else None,
        uptime_seconds=round(time.time() - START_TIME, 2)
    )


async def _run_pipeline_background():
    """Executa pipeline em background."""
    global _update_running
    _update_running = True
    
    started_at = datetime.now()
    try:
        # Simulação temporária (substituir por pipeline real depois)
        import asyncio
        await asyncio.sleep(2)
        
        _update_history.append({
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "status": "success",
            "records_processed": 0,
            "duration_seconds": 2.0
        })
    except Exception as e:
        _update_history.append({
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "status": "failed",
            "error": str(e)
        })
    finally:
        _update_running = False


@router.post("/run-update", response_model=RunUpdateResponse)
async def trigger_update(background_tasks: BackgroundTasks):
    """Dispara atualização manual."""
    global _update_running
    
    if _update_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Atualização já em execução"
        )
    
    background_tasks.add_task(_run_pipeline_background)
    
    return RunUpdateResponse(
        message="Atualização iniciada",
        started_at=datetime.now().isoformat()
    )


@router.get("/history")
async def get_history(limit: int = 10):
    """Retorna histórico de atualizações."""
    return {"history": list(reversed(_update_history[-limit:]))}


@router.get("/health-detail")
async def health_detail():
    """Health check detalhado."""
    return {
        "redis": _check_redis(),
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "scheduler_enabled": settings.scheduler_enabled
    }