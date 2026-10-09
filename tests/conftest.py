"""Fixtures compartilhadas da suíte de testes (Fase 1).

Estratégia:
- Banco em memória SQLite com a tabela ``gastos_assistenciais`` (schema v1.2),
  criado via SQLAlchemy Core — sem dependência de MySQL local.
- App FastAPI com ``dependency override`` implícito: trocamos o engine dos
  serviços pelo engine de teste antes de cada request.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Evita tocar no agendador/APScheduler durante os testes
os.environ.setdefault("ETL_SCHEDULER_DISABLED", "1")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


@pytest.fixture()
def sqlite_engine():
    """Banco em memória compartilhado entre conexões.

    ``StaticPool`` garante que todas as ``engine.connect()`` reutilizem a
    MESMA conexão SQLite — com o pool default, cada conexão nova abre um
    banco :memory: vazio (schema e dados 'desapareciam' entre requests).
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(text("""
                CREATE TABLE gastos_assistenciais (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    periodo TEXT NOT NULL,
                    registro_ans TEXT NOT NULL,
                    razao_social TEXT NOT NULL,
                    gasto_1T REAL DEFAULT 0,
                    gasto_2T REAL DEFAULT 0,
                    gasto_3T REAL DEFAULT 0,
                    gasto_4T REAL DEFAULT 0,
                    gasto_total REAL NOT NULL,
                    receita REAL DEFAULT 0,
                    sinistros REAL DEFAULT 0,
                    lucro REAL DEFAULT 0,
                    patrimonio REAL DEFAULT 0,
                    caixa REAL DEFAULT 0,
                    obrigacoes_trabalhistas REAL DEFAULT 0,
                    fornecedores REAL DEFAULT 0,
                    despesas_administrativas REAL DEFAULT 0,
                    pessoal REAL DEFAULT 0,
                    judiciais REAL DEFAULT 0,
                    provisoes REAL DEFAULT 0,
                    glosas REAL DEFAULT 0,
                    investimentos REAL DEFAULT 0,
                    imobilizado REAL DEFAULT 0,
                    intangivel REAL DEFAULT 0,
                    goodwill REAL DEFAULT 0,
                    it_softwares REAL DEFAULT 0,
                    UNIQUE (periodo, registro_ans)
                )
                """))
    yield engine
    engine.dispose()


@pytest.fixture()
def seeded_db(sqlite_engine):
    """Banco de teste com dados sintéticos determinísticos (2 períodos)."""
    # Cada linha é um dicionário chave→coluna — imune a desalinhamento de
    # posição (bug anterior: 24 valores × 25 chaves via zip).
    rows = [
        dict(
            p="2024",
            r="111111",
            n="OPERADORA ALPHA",
            gt=900.0,
            q1=200,
            q2=250,
            q3=200,
            q4=250,
            rec=3000.0,
            sin=900.0,
            luc=100.0,
            pat=5000.0,
            cx=400.0,
            ot=50.0,
            forn=30.0,
            dadm=600.0,
            pes=200.0,
            jud=100.0,
            prov=10.0,
            glos=800.0,
            inv=500.0,
            imob=300.0,
            intang=50.0,
            gw=20.0,
            itsoft=20.0,
        ),
        dict(
            p="2024",
            r="222222",
            n="OPERADORA BETA",
            gt=700.0,
            q1=150,
            q2=150,
            q3=200,
            q4=200,
            rec=2000.0,
            sin=700.0,
            luc=-50.0,
            pat=3000.0,
            cx=200.0,
            ot=40.0,
            forn=20.0,
            dadm=400.0,
            pes=150.0,
            jud=60.0,
            prov=5.0,
            glos=600.0,
            inv=400.0,
            imob=200.0,
            intang=30.0,
            gw=10.0,
            itsoft=10.0,
        ),
        dict(
            p="2024",
            r="333333",
            n="OPERADORA GAMMA",
            gt=9000.0,
            q1=2000,
            q2=2200,
            q3=2300,
            q4=2500,
            rec=20000.0,
            sin=9000.0,
            luc=800.0,
            pat=15000.0,
            cx=1200.0,
            ot=300.0,
            forn=120.0,
            dadm=2500.0,
            pes=900.0,
            jud=400.0,
            prov=50.0,
            glos=5000.0,
            inv=3000.0,
            imob=1500.0,
            intang=400.0,
            gw=150.0,
            itsoft=150.0,
        ),
        dict(
            p="2023",
            r="111111",
            n="OPERADORA ALPHA",
            gt=800.0,
            q1=200,
            q2=200,
            q3=200,
            q4=200,
            rec=2800.0,
            sin=800.0,
            luc=90.0,
            pat=4500.0,
            cx=350.0,
            ot=45.0,
            forn=25.0,
            dadm=550.0,
            pes=180.0,
            jud=90.0,
            prov=9.0,
            glos=700.0,
            inv=450.0,
            imob=250.0,
            intang=40.0,
            gw=15.0,
            itsoft=15.0,
        ),
    ]
    sql = """
        INSERT INTO gastos_assistenciais (
            periodo, registro_ans, razao_social, gasto_total,
            gasto_1T, gasto_2T, gasto_3T, gasto_4T,
            receita, sinistros, lucro, patrimonio, caixa,
            obrigacoes_trabalhistas, fornecedores,
            despesas_administrativas, pessoal, judiciais, provisoes, glosas,
            investimentos, imobilizado, intangivel, goodwill, it_softwares
        ) VALUES (:p, :r, :n, :gt, :q1, :q2, :q3, :q4,
                  :rec, :sin, :luc, :pat, :cx,
                  :ot, :forn, :dadm, :pes, :jud, :prov, :glos,
                  :inv, :imob, :intang, :gw, :itsoft)
    """
    with sqlite_engine.begin() as conn:
        for row in rows:
            conn.execute(text(sql), row)
    return sqlite_engine


@pytest.fixture()
def client(seeded_db):
    """TestClient com os serviços apontando para o SQLite de teste.

    O app é criado do zero (create_app) a cada teste para evitar estado
    global compartilhado entre suítes.
    """
    from fastapi.testclient import TestClient

    from api.main import create_app
    from api.services.analytics_service import AnalyticsService
    from api.services.operadoras_service import OperadorasService

    class _FakeOperadoras(OperadorasService):
        def __init__(self):  # não toca disco/MySQL
            self._owns_load = False

        def load(self):
            self._data = []

        def search(self, query, limit=50):
            return []

        def get_all(self):
            return [
                {
                    "registro_ans": "111111",
                    "u": "SP",
                    "regiao_comercializacao": "Sudeste",
                    "modalidade": "Cooperativa Médica",
                },
                {
                    "registro_ans": "222222",
                    "u": "RJ",
                    "regiao_comercializacao": "Sudeste",
                    "modalidade": "Autogestão",
                },
                {
                    "registro_ans": "333333",
                    "u": "SP",
                    "regiao_comercializacao": "Sudeste",
                    "modalidade": "Cooperativa Médica",
                },
            ]

    test_app = create_app()

    analytics = AnalyticsService.__new__(AnalyticsService)
    analytics.engine = seeded_db
    analytics.cadop_meta = {}
    analytics.settings = None

    fake = _FakeOperadoras()
    analytics.configure_cadop(fake)

    # Factory por nome: o handler resolve via dependency ``_resolve`` na
    # primeira request (o state do TestClient é recriado pelo lifespan,
    # então atributos setados aqui podem ser sobrescritos — a factory não).
    services = {"analytics_service": analytics, "operadoras_service": fake}
    test_app.state._service_factory = lambda name: services.get(name)

    with TestClient(test_app) as c:
        yield c


@pytest.fixture()
def seeded_analytics(seeded_db):
    """Instância isolada do AnalyticsService sobre o SQLite de teste."""
    from api.services.analytics_service import AnalyticsService

    svc = AnalyticsService.__new__(AnalyticsService)
    svc.engine = seeded_db
    svc.settings = None
    svc.cadop_meta = {
        "111111": {"uf": "SP", "regiao": "SUDESTE", "modalidade": "Cooperativa Médica"},
        "222222": {"uf": "RJ", "regiao": "SUDESTE", "modalidade": "Autogestão"},
        "333333": {"uf": "SP", "regiao": "SUDESTE", "modalidade": "Cooperativa Médica"},
    }
    return svc
