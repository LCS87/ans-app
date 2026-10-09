"""
Mapas de contas contábeis ANS (DOC 275) para as abas Financeira, Operacional e Estrutura.

Cada dimensão é definida por:
  - ``prefix``: prefixo do plano de contas usado pelo ETL genérico (Método D);
  - ``columns``: mapeia o nome da coluna no banco -> código/prefixo da conta;
  - ``aggregates``: métricas derivadas calculadas na API (ex.: sinistralidade = 41/31).

Códigos usados (plano ANS):
  31   Receita com Operações de Planos de Saúde
  41   Eventos/Sinistros (despesas assistenciais)
  12   Caixa / Equivalentes de caixa (ativo circulante)
  21   Obrigações Trabalhistas
  23   Fornecedores / Obrigações a pagar
  25   Lucro Líquido do exercício
  256  Resultado acumulado (Lucros/Prejuízos acumulados)
  44   Provisões técnicas (PEONA/PSSLA etc.)
  46   Despesas Administrativas
  461  Despesas com Pessoal (quadro próprio)
  468  Despesas Judiciais / Contingências
  132  Investimentos
  133  Imobilizado
  134  Intangível
  132139013  Goodwill (ágio por aquisição — conta específica)
  134129011  Softwares / IT (conta específica de tecnologia)
"""

from typing import Dict

DIMENSION_GASTOS = "gastos"
DIMENSION_FINANCEIRA = "financeira"
DIMENSION_OPERACIONAL = "operacional"
DIMENSION_ESTRUTURA = "estrutura"

# Prefixos de nível-1 aceitos pelo gate de dimensões
VALID_PREFIXES = {"31", "41", "44", "46", "12", "21", "23", "25", "411"}

DIMENSIONS: Dict[str, dict] = {
    DIMENSION_GASTOS: {
        "label": "Gastos Assistenciais",
        "icon": "🏥",
        "sort_by": "gasto_total",
        "prefix": "41",
        "columns": {"gasto_total": "41"},
        "aggregates": {},
    },
    DIMENSION_FINANCEIRA: {
        "label": "Financeiro",
        "icon": "🏦",
        "sort_by": "receita",
        "prefix": "31",
        "columns": {
            "receita": "31",  # Receita com operações de planos
            "lucro": "25",  # Lucro líquido do exercício
            "patrimonio": "256",  # Resultado/lucros acumulados (proxy de PL)
            "caixa": "12",  # Caixa e equivalentes
            "obrigacoes_trabalhistas": "21",
            "fornecedores": "23",
            "sinistros": "41",  # base para sinistralidade
        },
        "aggregates": {
            # Sinistralidade = Eventos/Sinistros (41) / Receita (31)
            "sinistralidade": ("sinistros", "receita"),
            # Endividamento = (Obrigações trabalhistas 21 + Fornecedores 23) / Receita (31)
            "endividamento": ("dividas", "receita"),
        },
        "derived": {"dividas": ("obrigacoes_trabalhistas", "fornecedores")},
    },
    DIMENSION_OPERACIONAL: {
        "label": "Operacional",
        "icon": "⚙️",
        "sort_by": "despesas_administrativas",
        "prefix": "46",
        "columns": {
            "despesas_administrativas": "46",
            "pessoal": "461",
            "judiciais": "468",
            "provisoes": "44",
            "glosas": "463",  # ressarcimentos/glosas quando reportado
        },
        "aggregates": {
            # Custo administrativo relativo à receita não disponível nesta
            # dimensão; mantido como valor absoluto.
        },
        "derived": {},
    },
    DIMENSION_ESTRUTURA: {
        "label": "Estrutura",
        "icon": "🏗️",
        "sort_by": "imobilizado",
        "prefix": "13",
        "columns": {
            "investimentos": "132",
            "imobilizado": "133",
            "intangivel": "134",
            "goodwill": "132139013",
            "it_softwares": "134129011",
        },
        "aggregates": {},
        "derived": {},
    },
}


def get_dimension(name: str) -> dict:
    """Retorna o mapa da dimensão ou levanta KeyError amigável."""
    if name not in DIMENSIONS:
        raise KeyError(f"Dimensão '{name}' inválida. Válidas: {sorted(DIMENSIONS)}")
    return DIMENSIONS[name]


# ----------------------------------------------------------------------
# Prefixos "guarda-chuva" por dimensão (F2.4 / job multi-dimensão).
# Cada dicionário é {coluna_de_banco: prefixo_conta} e abrange TODAS as
# contas que a dimensão precisa carregar — inclusive as que vivem em
# outros ramos do plano de contas (ex.: caixa 11/12 no ativo, lucro 25 no
# resultado). O Método D lida com qualquer prefixo; os valores abaixo são
# os aceitos pelo layout ANS (DOC 275) observado nas bases 2022-2024.
# ----------------------------------------------------------------------
DIMENSION_LOAD_PREFIXES: Dict[str, Dict[str, str]] = {
    DIMENSION_GASTOS: {"gasto_total": "41"},
    DIMENSION_FINANCEIRA: {
        "receita": "31",
        "sinistros": "41",
        "lucro": "25",
        "patrimonio": "256",
        # Caixa: tenta 12 (layout antigo); em 275 é subconta de 11 → 11 cobre.
        "caixa": "11",
        "obrigacoes_trabalhistas": "21",
        "fornecedores": "23",
    },
    DIMENSION_OPERACIONAL: {
        "despesas_administrativas": "46",
        "pessoal": "461",
        "judiciais": "468",
        "provisoes": "44",
        "glosas": "463",
    },
    DIMENSION_ESTRUTURA: {
        "investimentos": "132",
        "imobilizado": "133",
        "intangivel": "134",
        "goodwill": "132139013",
        "it_softwares": "134129011",
    },
}


def load_prefixes(dimension: str) -> Dict[str, str]:
    """Prefixos de extração para o job multi-dimensão do pipeline."""
    if dimension not in DIMENSION_LOAD_PREFIXES:
        raise KeyError(
            f"Dimensão '{dimension}' inválida. " f"Válidas: {sorted(DIMENSION_LOAD_PREFIXES)}"
        )
    return DIMENSION_LOAD_PREFIXES[dimension]
