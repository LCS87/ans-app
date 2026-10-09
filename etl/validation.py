"""
Controle de qualidade (Data Quality Gate).

Valida se um ano novo é compatível com a série histórica ANTES de importar.
Regra do projeto: "ano como dimensão, com gate de qualidade".

Um ano só entra no banco se passar em todos os checks críticos (FAIL bloqueia).
"""

import pandas as pd


def _ultimo_valor(df: pd.DataFrame) -> pd.DataFrame:
    """Último valor não-zero por (REG_ANS, conta)."""
    nz = df[df["VL_SALDO_FINAL"] != 0]
    return nz.sort_values("TRIM").groupby(["REG_ANS", "CD_CONTA_CONTABIL"], as_index=False).tail(1)


def total_metodo_d(df_ramo: pd.DataFrame) -> float:
    """Soma Método D (híbrido) sobre um df do ramo 41 (com coluna TRIM)."""
    last = _ultimo_valor(df_ramo)
    total = 0.0
    for _, grp in last.groupby("REG_ANS"):
        contas = grp["CD_CONTA_CONTABIL"].tolist()
        valores = dict(zip(contas, grp["VL_SALDO_FINAL"]))
        s = set(contas)
        raizes = [c for c in contas if not any(c[:L] in s for L in range(1, len(c)))]
        for r in raizes:
            folhas = [
                c
                for c in contas
                if c != r
                and c.startswith(r)
                and not any(c[:L] in s for L in range(len(r) + 1, len(c)))
            ]
            if not folhas:
                total += valores[r]
            else:
                sf = sum(valores[f] for f in folhas)
                total += sf if (sf >= 0.9 * valores[r] or sf > valores[r]) else valores[r]
    return total


def validar_ano(ano: int, df_all: pd.DataFrame, total_base: float = None):
    """
    Executa o gate de qualidade sobre df_all (todos os trimestres, com TRIM).
    Retorna (veredito, lista_de_checks).
    """
    checks = []

    def add(nome, status, detalhe):
        checks.append({"check": nome, "status": status, "detalhe": detalhe})

    df = df_all.copy()
    df["CD_CONTA_CONTABIL"] = df["CD_CONTA_CONTABIL"].fillna("").str.strip()
    df["VL_SALDO_FINAL"] = pd.to_numeric(df["VL_SALDO_FINAL"], errors="coerce")

    # 1) Colunas obrigatórias
    faltando = {
        "REG_ANS",
        "CD_CONTA_CONTABIL",
        "DESCRICAO",
        "VL_SALDO_FINAL",
        "TRIM",
    } - set(df.columns)
    add(
        "colunas_obrigatorias",
        "FAIL" if faltando else "PASS",
        f"faltando={sorted(faltando)}" if faltando else "todas presentes",
    )

    # 2) REG_ANS válido
    pct_reg = (df["REG_ANS"].notna() & df["REG_ANS"].str.strip().str.isdigit()).mean() * 100
    add(
        "reg_ans_valido",
        "FAIL" if pct_reg < 90 else ("WARN" if pct_reg < 99 else "PASS"),
        f"{pct_reg:.1f}% de REG_ANS numéricos",
    )

    # 3) Valores numéricos válidos
    pct_nan = df["VL_SALDO_FINAL"].isna().mean() * 100
    add(
        "valores_numericos",
        "FAIL" if pct_nan > 10 else ("WARN" if pct_nan > 1 else "PASS"),
        f"{pct_nan:.2f}% de VL_SALDO_FINAL não numéricos",
    )

    # 4) Ramo 411 presente (sinistros existem)
    m411 = df["CD_CONTA_CONTABIL"].str.startswith("411")
    ops_411 = df[m411 & (df["VL_SALDO_FINAL"] != 0)]["REG_ANS"].nunique()
    add(
        "ramo_411_presente",
        "FAIL" if ops_411 < 100 else ("WARN" if ops_411 < 300 else "PASS"),
        f"{ops_411} operadoras com contas 411 não-zero",
    )

    # 5) Estrutura de códigos (folhas existem?)
    ramo = df[df["CD_CONTA_CONTABIL"].str.startswith("41")]
    lens = ramo["CD_CONTA_CONTABIL"].str.len()
    tem9 = (lens == 9).any()
    tem8 = (lens == 8).any()
    add(
        "estrutura_codigos",
        "PASS" if tem9 else ("WARN" if tem8 else "FAIL"),
        f"folhas 9d={tem9}, 8d={tem8}",
    )

    # 6) Volume plausível
    n = len(df)
    add(
        "volume_plausivel",
        "PASS" if 500_000 <= n <= 5_000_000 else "WARN",
        f"{n:,} linhas",
    )

    # 7) Sem duplicidades exatas
    dup = df.duplicated(subset=["REG_ANS", "CD_CONTA_CONTABIL", "TRIM"]).sum()
    add("sem_duplicidades", "WARN" if dup > 0 else "PASS", f"{dup:,} duplicatas exatas")

    # 8) Comparação com ano base (plausibilidade)
    if total_base:
        t = total_metodo_d(ramo)
        ratio = t / total_base if total_base else 0
        add(
            "comparacao_ano_base",
            (
                "FAIL"
                if (ratio > 10 or ratio < 0.1)
                else ("WARN" if (ratio > 3 or ratio < 0.3) else "PASS")
            ),
            f"total={t/1e9:.1f}Bi vs base={total_base/1e9:.1f}Bi ({ratio:.2f}x)",
        )

    # Veredito
    statuses = [c["status"] for c in checks]
    if "FAIL" in statuses:
        veredito = "BLOQUEADO"
    elif "WARN" in statuses:
        veredito = "APROVADO_COM_RESSALVAS"
    else:
        veredito = "APROVADO"

    return veredito, checks


def imprimir_relatorio(ano, veredito, checks):
    print(f"\n{'='*80}\n🔎 GATE DE QUALIDADE — ANO {ano}\n{'='*80}")
    for c in checks:
        icone = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[c["status"]]
        print(f"   {icone} {c['check']:<22} {c['status']:<6} {c['detalhe']}")
    print(f"\n   🏁 VEREDITO: {veredito}\n{'='*80}")
