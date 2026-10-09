"""Migration script to ensure all v1.2 accounting columns exist in MySQL."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from api.config import get_settings

COLS = [
    ("receita", "DECIMAL(18,2) DEFAULT 0"),
    ("sinistros", "DECIMAL(18,2) DEFAULT 0"),
    ("lucro", "DECIMAL(18,2) DEFAULT 0"),
    ("patrimonio", "DECIMAL(18,2) DEFAULT 0"),
    ("caixa", "DECIMAL(18,2) DEFAULT 0"),
    ("obrigacoes_trabalhistas", "DECIMAL(18,2) DEFAULT 0"),
    ("fornecedores", "DECIMAL(18,2) DEFAULT 0"),
    ("despesas_administrativas", "DECIMAL(18,2) DEFAULT 0"),
    ("pessoal", "DECIMAL(18,2) DEFAULT 0"),
    ("judiciais", "DECIMAL(18,2) DEFAULT 0"),
    ("provisoes", "DECIMAL(18,2) DEFAULT 0"),
    ("glosas", "DECIMAL(18,2) DEFAULT 0"),
    ("investimentos", "DECIMAL(18,2) DEFAULT 0"),
    ("imobilizado", "DECIMAL(18,2) DEFAULT 0"),
    ("intangivel", "DECIMAL(18,2) DEFAULT 0"),
    ("goodwill", "DECIMAL(18,2) DEFAULT 0"),
    ("it_softwares", "DECIMAL(18,2) DEFAULT 0"),
]

def migrate():
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.begin() as conn:
        res = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'gastos_assistenciais' AND table_schema = DATABASE()"
            )
        )
        existing = {r[0].lower() for r in res.fetchall()}
        for col_name, col_type in COLS:
            if col_name.lower() not in existing:
                print(f"Adding column {col_name}...")
                conn.execute(text(f"ALTER TABLE gastos_assistenciais ADD COLUMN {col_name} {col_type}"))
            else:
                print(f"Column {col_name} already exists.")
    print("Migration finished successfully!")

if __name__ == "__main__":
    migrate()
