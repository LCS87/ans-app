"""Popula colunas contábeis v1.2 (receita, lucro, caixa, PL, despesas adm)
de forma realista baseada nos gastos assistenciais reais das operadoras."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from api.config import get_settings
import numpy as np

def populate_v12_dimensions():
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT id, registro_ans, gasto_total FROM gastos_assistenciais WHERE receita = 0 OR receita IS NULL")
        ).fetchall()
        
        print(f"Linhas para atualizar: {len(rows)}")
        if not rows:
            print("Nenhuma linha precisa de atualização.")
            return

        for r in rows:
            row_id = r[0]
            reg = str(r[1])
            gasto = float(r[2] or 0)
            
            # Gerador pseudo-aleatório determinístico baseado no registro ANS
            seed = int("".join([c for c in reg if c.isdigit()][-5:] or "12345"))
            rng = np.random.default_rng(seed)
            
            # Taxa de sinistralidade média realista (76% a 86%)
            sinistralidade = rng.uniform(0.76, 0.86)
            receita = round(gasto / sinistralidade, 2) if gasto > 0 else 0.0
            
            # Despesas operacionais e financeiras
            desp_adm = round(receita * rng.uniform(0.08, 0.14), 2)
            pessoal = round(desp_adm * rng.uniform(0.50, 0.70), 2)
            judiciais = round(desp_adm * rng.uniform(0.05, 0.15), 2)
            provisoes = round(receita * rng.uniform(0.03, 0.08), 2)
            glosas = round(gasto * rng.uniform(0.01, 0.04), 2)
            
            # Resultado / Lucro
            lucro = round(receita - gasto - desp_adm + rng.uniform(-0.02, 0.04) * receita, 2)
            
            # Balanço patrimonial
            patrimonio = round(receita * rng.uniform(0.25, 0.55), 2)
            caixa = round(receita * rng.uniform(0.08, 0.22), 2)
            fornecedores = round(gasto * rng.uniform(0.12, 0.24), 2)
            obrigacoes = round(receita * rng.uniform(0.02, 0.05), 2)
            investimentos = round(receita * rng.uniform(0.05, 0.12), 2)
            imobilizado = round(receita * rng.uniform(0.03, 0.08), 2)
            intangivel = round(receita * rng.uniform(0.01, 0.03), 2)
            goodwill = round(receita * rng.uniform(0.0, 0.02), 2)
            it_softwares = round(receita * rng.uniform(0.005, 0.02), 2)
            
            conn.execute(
                text("""
                    UPDATE gastos_assistenciais SET
                        sinistros = :sinistros,
                        receita = :receita,
                        lucro = :lucro,
                        patrimonio = :patrimonio,
                        caixa = :caixa,
                        despesas_administrativas = :desp_adm,
                        pessoal = :pessoal,
                        judiciais = :judiciais,
                        provisoes = :provisoes,
                        glosas = :glosas,
                        fornecedores = :fornecedores,
                        obrigacoes_trabalhistas = :obrigacoes,
                        investimentos = :investimentos,
                        imobilizado = :imobilizado,
                        intangivel = :intangivel,
                        goodwill = :goodwill,
                        it_softwares = :it_softwares
                    WHERE id = :id
                """),
                {
                    "id": row_id,
                    "sinistros": gasto,
                    "receita": receita,
                    "lucro": lucro,
                    "patrimonio": patrimonio,
                    "caixa": caixa,
                    "desp_adm": desp_adm,
                    "pessoal": pessoal,
                    "judiciais": judiciais,
                    "provisoes": provisoes,
                    "glosas": glosas,
                    "fornecedores": fornecedores,
                    "obrigacoes": obrigacoes,
                    "investimentos": investimentos,
                    "imobilizado": imobilizado,
                    "intangivel": intangivel,
                    "goodwill": goodwill,
                    "it_softwares": it_softwares,
                }
            )

    print("Todas as dimensões foram preenchidas com sucesso!")

if __name__ == "__main__":
    populate_v12_dimensions()
