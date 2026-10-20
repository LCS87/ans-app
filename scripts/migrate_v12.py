"""Migração do schema contábil v1.2 → v1.3 (mapeamento P1).

As colunas novas são adicionadas e as obsoletas (semântica contábil errada)
são removidas. A lista de colunas vem de ``etl.load.ANSLoader.EXTRA_COLUMNS``
para que script, loader e DDL nunca divirjam.

Uso:
    python scripts/migrate_v12.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text  # noqa: E402

from api.config import get_settings  # noqa: E402
from etl.load import ANSLoader  # noqa: E402


def migrate():
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    loader = ANSLoader()

    with engine.begin() as conn:
        res = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'gastos_assistenciais' AND table_schema = DATABASE()"
            )
        )
        existing = {r[0].lower() for r in res.fetchall()}

        for col_name, col_type in loader.EXTRA_COLUMNS.items():
            if col_name.lower() not in existing:
                print(f"Adding column {col_name}...")
                conn.execute(
                    text(f"ALTER TABLE gastos_assistenciais ADD COLUMN {col_name} {col_type}")
                )
            else:
                print(f"Column {col_name} already exists.")

        for col_name in sorted(loader.OBSOLETE_COLUMNS):
            if col_name.lower() in existing:
                print(f"Dropping obsolete column {col_name}...")
                conn.execute(text(f"ALTER TABLE gastos_assistenciais DROP COLUMN {col_name}"))

    print("Migration finished successfully!")


if __name__ == "__main__":
    migrate()
