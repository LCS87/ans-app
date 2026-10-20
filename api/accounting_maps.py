"""
Mapas de contas contábeis ANS (DOC 275) para as abas Financeira, Operacional
e Estrutura.

Todos os mapeamentos abaixo foram conferidos contra o **dado bruto** da ANS
(4T de 2023 a 2026) e contra as identidades contábeis do balanço. Nenhum
código aqui é suposição: cada linha documenta a conta real encontrada no
layout DOC 275 e o total de mercado que ela representa em 2025.

Plano de contas observado (nível 1 e 2, com total de mercado em 2025):

  1    ATIVO                                       R$ 306,95 Bi
  2    PASSIVO (sintético = passivo + PL)           R$ 306,77 Bi
  3    RECEITAS                                     R$ 398,84 Bi
  4    DESPESAS                                     R$ 368,38 Bi
  6    CONTAS DE DESTINAÇÃO/APURAÇÃO DE RESULTADO   R$  15,26 Bi
       61  IMPOSTOS E PARTICIPAÇÕES SOBRE O LUCRO    R$   6,03 Bi
       69  APURAÇÃO DO RESULTADO                     R$   9,24 Bi
  12   ATIVO CIRCULANTE                             R$ 160,37 Bi
       121 DISPONÍVEL (caixa, bancos)                R$   4,65 Bi
       122 APLICAÇÕES FINANCEIRAS                    R$ 114,62 Bi
  21   PASSIVO CIRCULANTE                           R$ 104,30 Bi
       211 PROVISÕES TÉCNICAS (circulante)           R$  70,81 Bi
  23   PASSIVO NÃO CIRCULANTE                       R$  53,95 Bi
       231 PROVISÕES TÉCNICAS (não circulante)       R$  11,69 Bi
  25   PATRIMÔNIO LÍQUIDO / PATRIMÔNIO SOCIAL        R$ 148,52 Bi
  256  LUCROS/PREJUÍZOS ACUMULADOS                  R$   1,30 Bi
  31   RECEITAS COM OPERAÇÕES DE ASSISTÊNCIA À SAÚDE R$ 355,71 Bi
  41   EVENTOS INDENIZÁVEIS LÍQUIDOS / SINISTROS     R$ 282,17 Bi
  44   OUTRAS DESPESAS OPERACIONAIS                 R$  31,76 Bi
  46   DESPESAS ADMINISTRATIVAS                     R$  32,32 Bi
       461 PESSOAL PRÓPRIO                          R$  14,06 Bi
       462 SERVIÇOS DE TERCEIROS                     R$   7,57 Bi
       463 LOCALIZAÇÃO E FUNCIONAMENTO               R$   5,09 Bi
       464 PUBLICIDADE E PROPAGANDA                  R$   1,40 Bi
       465 TRIBUTOS                                  R$   0,67 Bi
       466 MULTAS ADMINISTRATIVAS                    R$   0,72 Bi
       468 DESPESAS ADMINISTRATIVAS DIVERSAS         R$   2,80 Bi
  132  INVESTIMENTOS                                R$  38,57 Bi
  133  IMOBILIZADO                                  R$  31,68 Bi
  134  INTANGÍVEL                                   R$  19,97 Bi
       132139013 GOODWILL (9 operadoras)             R$   3,58 Bi
       134129011 SISTEMAS DE COMPUTAÇÃO              R$   6,01 Bi

Semântica do resultado do exercício
----------------------------------
A conta ``69`` (APURAÇÃO DO RESULTADO) **é** o resultado do período: ela
coincide com ``3 - 4 - 61`` em 610 das 651 operadoras que a reportam em 2025.
A conta ``6`` é o **pai** de ``61`` e ``69`` (6 = 61 + 69), por isso usar
``6`` como despesa do exercício contaria o resultado duas vezes.

Regra adotada pelo pipeline (P1) — **uniforme para todas as operadoras**:

    lucro = 3 (Receitas) - 4 (Despesas) - 61 (Impostos sobre o lucro)
    (usa a conta 69 apenas quando a operadora não publica 3/4/61)

Uniformidade importa: um ranking que mistura "resultado publicado" e
"resultado derivado" não é comparável entre linhas.

Observações que evitam leituras erradas:

* ``25`` é o **Patrimônio Líquido** (não lucro líquido). O lucro acumulado
  é ``256`` (R$ 1,30 Bi em 2025) — uma ordem de grandeza menor.
* ``12`` é o **Ativo Circulante** (R$ 160,37 Bi), não caixa. O caixa real
  é ``121`` (Disponível) somado a ``122`` (Aplicações Financeiras).
* ``21`` é o **Passivo Circulante** e ``23`` o **Passivo Não Circulante**
  (não "obrigações trabalhistas" / "fornecedores").
* A identidade do balanço é ``1 = 21 + 23 + 25``.
* ``468`` são despesas administrativas diversas (não judiciais) e ``463``
  é localização e funcionamento (não glosas).
"""

from typing import Dict, Iterable, Union

DIMENSION_GASTOS = "gastos"
DIMENSION_FINANCEIRA = "financeira"
DIMENSION_OPERACIONAL = "operacional"
DIMENSION_ESTRUTURA = "estrutura"

# Prefixos de nível-1 aceitos pelo gate de dimensões
VALID_PREFIXES = {"1", "3", "4", "6", "25", "31", "41", "44", "46", "61", "69"}

# Um prefixo pode ser uma tupla: a coluna soma o Método D de cada prefixo.
Prefixo = Union[str, Iterable[str]]


def achatar_prefixos(prefixos: Dict[str, Prefixo]) -> list:
    """Achata ``{coluna: prefixo}`` em uma lista de prefixos únicos."""
    saida = []
    for valor in prefixos.values():
        if isinstance(valor, str):
            saida.append(valor)
        else:
            saida.extend(list(valor))
    return list(dict.fromkeys(saida))


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
            "receita": "31",  # Receitas com operações de assistência à saúde
            "sinistros": "41",  # Eventos indenizáveis líquidos
            # 69 = Apuração do Resultado; quando ausente, 3 - 4 - 61.
            "lucro": "69",
            "patrimonio": "25",  # Patrimônio líquido / patrimônio social
            # Liquidez imediata: 121 (Disponível) + 122 (Aplicações Financeiras).
            "caixa": ("121", "122"),
            "passivo_circulante": "21",
            "passivo_nao_circulante": "23",
            "ativo_total": "1",
        },
        "aggregates": {
            # Sinistralidade = Eventos/Sinistros (41) / Receita com planos (31)
            "sinistralidade": ("sinistros", "receita"),
            # Endividamento = Passivo total (21 + 23) / Ativo total (1)
            "endividamento": ("passivo_total", "ativo_total"),
            # Margem de lucro = Resultado do exercício / Receita com planos
            "margem_lucro": ("lucro", "receita"),
        },
        "derived": {"passivo_total": ("passivo_circulante", "passivo_nao_circulante")},
    },
    DIMENSION_OPERACIONAL: {
        "label": "Operacional",
        "icon": "⚙️",
        "sort_by": "despesas_administrativas",
        "prefix": "46",
        "columns": {
            "despesas_administrativas": "46",
            "pessoal": "461",
            "servicos_terceiros": "462",
            "localizacao_funcionamento": "463",
            "publicidade": "464",
            "tributos_operacionais": "465",
            "multas": "466",
            "adm_diversas": "468",
            "outras_despesas_operacionais": "44",
            # Provisões técnicas de assistência à saúde (circulante + não circulante)
            "provisoes_tecnicas": ("211", "231"),
        },
        "aggregates": {},
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
# Cada dicionário é {coluna_de_banco: prefixo_de_conta} e abrange TODAS as
# contas que a dimensão precisa carregar — inclusive as que vivem em
# outros ramos do plano de contas (ex.: caixa 121/122 no ativo, PL 25 no
# passivo, resultado 69 na apuração). O Método D lida com qualquer prefixo;
# os valores abaixo são os aceitos pelo layout ANS (DOC 275) 2023-2026.
# ----------------------------------------------------------------------
DIMENSION_LOAD_PREFIXES: Dict[str, Dict[str, Prefixo]] = {
    DIMENSION_GASTOS: {"gasto_total": "41"},
    DIMENSION_FINANCEIRA: {
        "receita": "31",
        "sinistros": "41",
        "lucro": "69",
        "patrimonio": "25",
        # 121 (Disponível) + 122 (Aplicações Financeiras).
        "caixa": ("121", "122"),
        "passivo_circulante": "21",
        "passivo_nao_circulante": "23",
        "ativo_total": "1",
    },
    DIMENSION_OPERACIONAL: {
        "despesas_administrativas": "46",
        "pessoal": "461",
        "servicos_terceiros": "462",
        "localizacao_funcionamento": "463",
        "publicidade": "464",
        "tributos_operacionais": "465",
        "multas": "466",
        "adm_diversas": "468",
        "outras_despesas_operacionais": "44",
        "provisoes_tecnicas": ("211", "231"),
    },
    DIMENSION_ESTRUTURA: {
        "investimentos": "132",
        "imobilizado": "133",
        "intangivel": "134",
        "goodwill": "132139013",
        "it_softwares": "134129011",
    },
}


def load_prefixes(dimension: str) -> Dict[str, Prefixo]:
    """Prefixos de extração para o job multi-dimensão do pipeline."""
    if dimension not in DIMENSION_LOAD_PREFIXES:
        raise KeyError(
            f"Dimensão '{dimension}' inválida. " f"Válidas: {sorted(DIMENSION_LOAD_PREFIXES)}"
        )
    return DIMENSION_LOAD_PREFIXES[dimension]
