#!/usr/bin/env python3
"""
Seed de dados sintéticos v1.2 para o job de integração do CI (F5.1).

Popula `operadoras` (CADOP) e `gastos_assistenciais` (todas as dimensões
contábeis: gastos, financeira, operacional, estrutura) com dados determinísticos
para que os testes de integração contra MySQL real tenham conteúdo consistente.

Uso (CI):
    MYSQL_HOST=127.0.0.1 MYSQL_PORT=3307 ... python scripts/seed_ci.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from api.config import get_settings  # noqa: E402

PERIODOS = ["2022", "2023", "2024"]
N_OPS = 60
SEED = 42

MODALIDADES = [
    "Cooperativa Médica",
    "Medicina de Grupo",
    "Odontologia de Grupo",
    "Autogestão",
    "Filantropia",
    "Seguradora Especializada",
]
UFS = ["SP", "RJ", "MG", "RS", "PR", "SC", "BA", "PE", "CE", "DF"]
REGIOES = {
    "SP": "Sudeste",
    "RJ": "Sudeste",
    "MG": "Sudeste",
    "DF": "Centro-Oeste",
    "RS": "Sul",
    "PR": "Sul",
    "SC": "Sul",
    "BA": "Nordeste",
    "PE": "Nordeste",
    "CE": "Nordeste",
}


def build_operadoras(rng: np.random.Generator) -> pd.DataFrame:
    regs = [str(1 << 9 + i) and f"{30000 + i:05d}" for i in range(N_OPS)]
    return pd.DataFrame(
        {
            "registro_ans": regs,
            "cnpj": [f"{rng.integers(10**13, 10**14 - 1)}" for _ in range(N_OPS)],
            "razao_social": [f"OPERADORA TESTE {r} S/A" for r in regs],
            "nome_fantasia": [f"OpTeste {r}" for r in regs],
            "modalidade": [rng.choice(MODALIDADES) for _ in range(N_OPS)],
            "uf": [rng.choice(UFS) for _ in range(N_OPS)],
            "cidade": ["Cidade Teste"] * N_OPS,
            "regiao_comercializacao": [int(rng.integers(1, 6)) for _ in range(N_OPS)],
            "data_registro_ans": ["2010-01-01"] * N_OPS,
        }
    )


def build_gastos(regs: list, rng: np.random.Generator) -> pd.DataFrame:
    """Uma linha por (periodo, operadora) com TODAS as colunas v1.2."""
    rows = []
    for periodo in PERIODOS:
        base = rng.uniform(5e7, 5e9, size=len(regs))
        receita = base * rng.uniform(1.2, 1.8, size=len(regs))
        gasto = base * rng.uniform(0.8, 1.0, size=len(regs))
        q_share = rng.uniform(0.2, 0.3, size=(len(regs), 3))
        q_share = np.column_stack([q_share, 1 - q_share.sum(axis=1)])
        rows.append(
            pd.DataFrame(
                {
                    "periodo": periodo,
                    "registro_ans": regs,
                    "razao_social": [f"OPERADORA TESTE {r} S/A" for r in regs],
                    "gasto_1T": gasto * q_share[:, 0],
                    "gasto_2T": gasto * q_share[:, 1],
                    "gasto_3T": gasto * q_share[:, 2],
                    "gasto_4T": gasto * q_share[:, 3],
                    "gasto_total": gasto,
                    "receita": receita,
                    "sinistros": gasto,
                    "lucro": receita * rng.uniform(-0.05, 0.15, size=len(regs)),
                    "patrimonio": receita * rng.uniform(0.1, 0.6, size=len(regs)),
                    "caixa": receita * rng.uniform(0.02, 0.2, size=len(regs)),
                    "obrigacoes_trabalhistas": receita * rng.uniform(0.01, 0.05, len(regs)),
                    "fornecedores": receita * rng.uniform(0.05, 0.25, len(regs)),
                    "despesas_administrativas": receita * rng.uniform(0.05, 0.15, len(regs)),
                    "pessoal": receita * rng.uniform(0.08, 0.25, len(regs)),
                    "judiciais": receita * rng.uniform(0.0, 0.02, len(regs)),
                    "provisoes": receita * rng.uniform(0.01, 0.08, len(regs)),
                    "glosas": receita * rng.uniform(0.0, 0.03, len(regs)),
                    "investimentos": receita * rng.uniform(0.01, 0.1, len(regs)),
                    "imobilizado": receita * rng.uniform(0.01, 0.08, len(regs)),
                    "intangivel": receita * rng.uniform(0.0, 0.03, len(regs)),
                    "goodwill": receita * rng.uniform(0.0, 0.02, len(regs)),
                    "it_softwares": receita * rng.uniform(0.0, 0.01, len(regs)),
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def upsert(engine, table: str, df: pd.DataFrame, conflict_cols: list):
    cols = list(df.columns)
    placeholders = ", ".join(f":{c}" for c in cols)
    if engine.dialect.name == "mysql":
        updates = ", ".join(f"{c} = VALUES({c})" for c in cols if c not in conflict_cols)
        sql = (
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {updates}"
        )
    else:
        updates = ", ".join(f"{c} = excluded.{c}" for c in cols if c not in conflict_cols)
        sql = (
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT ({', '.join(conflict_cols)}) DO UPDATE SET {updates}"
        )
    with engine.begin() as conn:
        conn.execute(text(sql), df.to_dict(orient="records"))


def main():
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)

    rng = np.random.default_rng(SEED)
    ops = build_operadoras(rng)
    gastos = build_gastos(list(ops["registro_ans"]), rng)

    with engine.begin() as conn:
        conn.execute(text("""
                CREATE TABLE IF NOT EXISTS operadoras (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    registro_ans VARCHAR(10) NOT NULL UNIQUE,
                    cnpj VARCHAR(14) NOT NULL,
                    razao_social VARCHAR(255) NOT NULL,
                    nome_fantasia VARCHAR(255),
                    modalidade VARCHAR(100),
                    uf CHAR(2),
                    cidade VARCHAR(100),
                    regiao_comercializacao INT,
                    data_registro_ans DATE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """))

    # garante tabela + colunas v1.2 mesmo se DDL do compose não rodou
    from etl.load import ANSLoader

    ANSLoader().criar_tabela_se_nao_existe()

    upsert(engine, "operadoras", ops, conflict_cols=["registro_ans"])
    upsert(
        engine,
        "gastos_assistenciais",
        gastos,
        conflict_cols=["periodo", "registro_ans"],
    )

    print(
        f"✅ seed CI: {len(ops)} operadoras, {len(gastos)} linhas de gastos "
        f"(períodos {PERIODOS}, schema v1.2 completo)"
    )


if __name__ == "__main__":
    main()
