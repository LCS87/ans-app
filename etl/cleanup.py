from datetime import datetime, timedelta
from pathlib import Path


def cleanup_old_files():
    policies = {
        "/backups/mysql": timedelta(days=180),
        "/data/raw/csv": timedelta(days=60),
        "/logs": timedelta(days=90),
    }
    for path, retention in policies.items():
        cutoff = datetime.now() - retention
        for file in Path(path).glob("*"):
            if file.stat().st_mtime < cutoff.timestamp():
                file.unlink()
