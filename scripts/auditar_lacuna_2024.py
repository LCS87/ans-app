"""Fase 1 / Tarefa 1.5 — Auditoria quantitativa da Lacuna ANS 2024.

Investiga divergências entre o total histórico reportado (ex.: acumulado oficial)
e o total recalculado pelo Método D a partir das demonstrações de 2024,
detalhando as causas por operadora:

  1. Operadoras ausentes no ano (registros que existiam em 2023 e sumiram);
  2. Contas 411 zeradas ou faltantes (sub-ramo sem lançamento);
  3. Trimestres incompletos (operadora com <4 TRIM publicados);
  4. Divergência raiz vs. folhas (41 != soma(411x)) — indício de retrancação.

Uso:
    python scripts/auditar_lacuna_2024.py [--ano 2024 --base 2023]

O script lê os ZIPs extraídos em `data/demonstracoes` via etl.extract e imprime
um relatório Markdown no stdout + grava em `data/relatorios/lacuna_<ano>.md`.
Se os dados locais não existirem, sai com código 2 e mensagem clara (não falha
em produção/CI onde os arquivos grandes não estão versionados).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from etl.extract import ANSExtractor  # noqa: E402
from etl.validation import total_metodo_d  # noqa: E402


def _carregar(df: pd.DataFrame) -> pd.DataFrame:
    """Garante colunas numéricas e limpa duplicatas exatas."""
    df = df.copy()
    df["VL_SALDO_FINAL"] = pd.to_numeric(df["VL_SALDO_FINAL"], errors="coerce").fillna(0.0)
    df["CD_CONTA_CONTABIL"] = df["CD_CONTA_CONTABIL"].astype(str).str.strip()
    return df.drop_duplicates(subset=["REG_ANS", "CD_CONTA_CONTABIL", "TRIM"])


def auditar(df_ano: pd.DataFrame, df_base: pd.DataFrame | None) -> dict:
    ramo = _carregar(df_ano)
    ramo = ramo[ramo["CD_CONTA_CONTABIL"].str.startswith("41")]

    ops = {r for r in ramo["REG_ANS"].unique()}
    achados: dict = {
        "ano_total_metodo_d": float(total_metodo_d(ramo)),
        "operadoras": len(ops),
    }

    # 1) Operadoras ausentes vs. ano base
    if df_base is not None and len(df_base):
        base = _carregar(df_base)
        base = base[base["CD_CONTA_CONTABIL"].str.startswith("41")]
        ops_base = set(base["REG_ANS"].unique())
        sumidas = sorted(ops_base - ops)
        achados["operadoras_ausentes_no_ano"] = len(sumidas)
        achados["amostra_ausentes"] = sumidas[:20]

    # 2) Contas 411 zeradas/faltantes
    tem411 = set(ramo[ramo["CD_CONTA_CONTABIL"].str.startswith("411")]["REG_ANS"].unique())
    sem411 = sorted(ops - tem411)
    achados["operadoras_sem_conta_411"] = len(sem411)
    achados["amostra_sem_411"] = sem411[:20]

    # 3) Trimestres incompletos
    trims = ramo.groupby("REG_ANS")["TRIM"].nunique()
    incompletas = sorted(trims[trims < 4].index.tolist())
    achados["operadoras_trim_incompleto"] = len(incompletas)
    achados["amostra_trim_incompleto"] = incompletas[:20]

    # 4) Divergência raiz vs. folhas por operadora (no último trim disponível)
    ult = ramo.sort_values("TRIM").groupby("REG_ANS")["TRIM"].last()
    div = []
    for reg, t in ult.items():
        rec = ramo[(ramo["REG_ANS"] == reg) & (ramo["TRIM"] == t)]
        raiz = rec[rec["CD_CONTA_CONTABIL"] == "41"]["VL_SALDO_FINAL"].sum()
        folhas = rec[rec["CD_CONTA_CONTABIL"].str.len() >= 8]["VL_SALDO_FINAL"].sum()
        if raiz and folhas and abs(raiz - folhas) / max(raiz, folhas) > 0.05:
            div.append((reg, float(raiz), float(folhas)))
    achados["divergencias_raiz_folhas"] = len(div)
    achados["amostra_divergencias"] = div[:10]
    return achados


def relatorio_md(ano: int, a: dict) -> str:
    linhas = [
        f"# Relatório de Auditoria — Lacuna ANS {ano}",
        "",
        f"- Total Método D recalculado: **R$ {a['ano_total_metodo_d']:,.2f}**",
        f"- Operadoras com dados no ano: **{a['operadoras']}**",
    ]
    if "operadoras_ausentes_no_ano" in a:
        linhas.append(
            f"- Operadoras do ano-base ausentes neste ano: **{a['operadoras_ausentes_no_ano']}**"
        )
        if a.get("amostra_ausentes"):
            linhas.append(f"  - Amostra: {', '.join(a['amostra_ausentes'])}")
    linhas.append(
        f"- Operadoras sem conta 411 (sub-ramo sinistros): **{a['operadoras_sem_conta_411']}**"
    )
    if a.get("amostra_sem_411"):
        linhas.append(f"  - Amostra: {', '.join(a['amostra_sem_411'])}")
    linhas.append(f"- Operadoras com menos de 4 trimestres: **{a['operadoras_trim_incompleto']}**")
    if a.get("amostra_trim_incompleto"):
        linhas.append(f"  - Amostra: {', '.join(a['amostra_trim_incompleto'])}")
    linhas.append(f"- Divergências raiz(41) vs. folhas (>5%): **{a['divergencias_raiz_folhas']}**")
    for reg, r, f in a.get("amostra_divergencias", []):
        linhas.append(f"  - REG {reg}: raiz={r:,.0f} folhas={f:,.0f}")
    return "\n".join(linhas) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ano", type=int, default=2024)
    ap.add_argument("--base", type=int, default=2023)
    args = ap.parse_args()

    extractor = ANSExtractor()
    try:
        df_ano = extractor.processar_ano(args.ano)
    except (FileNotFoundError, Exception) as e:
        if not isinstance(e, FileNotFoundError):
            raise
        print(f"[ERRO] Dados locais de {args.ano} não encontrados em data/. Rode o ETL primeiro.")
        return 2

    df_base = None
    try:
        df_base = extractor.processar_ano(args.base)
    except Exception:
        print(f"[AVISO] Ano-base {args.base} indisponível; check de ausências será pulado.")

    a = auditar(df_ano, df_base)
    md = relatorio_md(args.ano, a)
    out = ROOT / "data" / "relatorios"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"lacuna_{args.ano}.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
