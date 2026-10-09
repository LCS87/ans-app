"""
F4.2 — Exportação Excel: múltiplas abas consolidadas (openpyxl/pandas).

Abas geradas: Resumo, Gastos, Financeiro, Operacional, Estrutura, Trimestral, Regional.
"""

import io
from typing import Optional

import pandas as pd


def _ranking_to_df(ranking: list, valores_key: bool = True) -> pd.DataFrame:
    rows = []
    for item in ranking:
        row = {
            "Posição": item.get("posicao"),
            "Registro ANS": item.get("registro_ans"),
            "Razão Social": item.get("razao_social"),
        }
        vals = item.get("valores") or {}
        if not vals and "valor_total" in item:
            vals = {"gasto_total": item["valor_total"]}
        if not vals and "valor" in item:
            vals = {"valor": item["valor"]}
        row.update(vals)
        if "outlier" in item:
            row["Outlier"] = "⚠️" if item["outlier"] else ""
        rows.append(row)
    return pd.DataFrame(rows)


def export_excel(
    summary: dict,
    gastos: dict,
    financeira: Optional[dict] = None,
    operacional: Optional[dict] = None,
    estrutura: Optional[dict] = None,
    trimestral: Optional[dict] = None,
    regional: Optional[dict] = None,
) -> bytes:
    """Monta um .xlsx em memória com todas as abas do dashboard."""
    buffer = io.BytesIO()

    resumo_df = pd.DataFrame(
        [{"Métrica": k, "Valor (R$)": v} for k, v in (summary.get("totais") or {}).items()]
    )

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        resumo_df.to_excel(writer, sheet_name="Resumo", index=False)
        _ranking_to_df(gastos.get("ranking", [])).to_excel(writer, sheet_name="Gastos", index=False)
        if financeira:
            _ranking_to_df(financeira.get("ranking", [])).to_excel(
                writer, sheet_name="Financeiro", index=False
            )
        if operacional:
            _ranking_to_df(operacional.get("ranking", [])).to_excel(
                writer, sheet_name="Operacional", index=False
            )
        if estrutura:
            _ranking_to_df(estrutura.get("ranking", [])).to_excel(
                writer, sheet_name="Estrutura", index=False
            )
        if trimestral:
            qt_rows = [
                {
                    "Registro ANS": s["registro_ans"],
                    "Razão Social": s["razao_social"],
                    **s.get("trimestres", {}),
                }
                for s in trimestral.get("series", [])
            ]
            pd.DataFrame(qt_rows).to_excel(writer, sheet_name="Trimestral", index=False)
        if regional:
            pd.DataFrame(regional.get("ufs", [])).to_excel(
                writer, sheet_name="Regional", index=False
            )

    buffer.seek(0)
    return buffer.read()
