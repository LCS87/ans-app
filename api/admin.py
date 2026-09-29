from fastapi import APIRouter
from apscheduler.schedulers.asyncio import AsyncIOScheduler

router = APIRouter(prefix="/admin")
scheduler = AsyncIOScheduler()

@router.get("/disk-usage")
async def disk_usage():
    return {"total_space_gb": 50, "used_gb": 28.5, "free_gb": 21.5}
