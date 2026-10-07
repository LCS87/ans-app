"""
F4.1 — Exportação PDF: relatório institucional com gráficos renderizados.

Renderiza gráficos com matplotlib (PNG em memória) e monta o PDF com ReportLab,
dispensando dependências de sistema (WeasyPrint/gtk) — ideal p/ CI e deploy.
"""

import io
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _bar_chart_png(title: str, labels: list, values: list, color="#1f77b4") -> bytes:
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.barh(range(len(labels)), values, color=color)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels([l[:35] for l in labels], fontsize=7)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=10)
    ax.tick_params(axis="x", labelsize=7)
    try:
        import matplotlib.ticker as mticker

        ax.xaxis.set_major_formatter(
            mticker.FuncFormatter(lambda t, _: f"{t/1e9:.1f}B")
        )
    except Exception:
        pass
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _section_ranking(story, styles, data: Optional[dict], chart_color: str):
    if not data or not data.get("ranking"):
        return
    story.append(Paragraph(data.get("label", data.get("dimensao", "Ranking")), styles["h2"]))
    primary = data.get("primary_metric", "gasto_total")
    top = data["ranking"][:10]
    labels = [r["razao_social"] for r in top]
    values = [(r.get("valores") or {}).get(primary, r.get("valor_total", 0)) for r in top]
    img = Image(io.BytesIO(_bar_chart_png(f"Top 10 — {primary}", labels, values, chart_color)))
    img.width, img.height = 17 * cm, 6.8 * cm
    story.append(img)
    story.append(Spacer(1, 0.4 * cm))

    table_data = [["#", "Registro", "Operadora", "Valor"]] + [
        [str(r["posicao"]), r["registro_ans"], r["razao_social"][:40],
         _fmt_brl((r.get("valores") or {}).get(primary, r.get("valor_total", 0)))]
        for r in top
    ]
    t = Table(table_data, colWidths=[1 * cm, 2.2 * cm, 8.3 * cm, 5.5 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5fb4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f4f8")]),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 0.8 * cm))


def export_pdf(
    periodo: str,
    summary: dict,
    gastos: dict,
    financeira: Optional[dict] = None,
    operacional: Optional[dict] = None,
    estrutura: Optional[dict] = None,
) -> bytes:
    """Gera o PDF institucional do período e retorna os bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        title=f"ANS Intelligence — Relatório {periodo}",
        author="ANS Intelligence",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1x", parent=styles["Title"], fontSize=18)
    h2 = ParagraphStyle("h2x", parent=styles["Heading2"], fontSize=13)
    body = styles["BodyText"]
    story_styles = {"h2": h2}

    story = [
        Paragraph(f"ANS Intelligence — Relatório Contábil {periodo}", h1),
        Paragraph(
            "Metodologia D (híbrida): consolidação das demonstrações contábeis "
            "(DOC 275/ANS) sem dupla contagem de contas sintéticas.",
            body,
        ),
        Spacer(1, 0.6 * cm),
    ]

    totais = summary.get("totais") or {}
    if totais:
        kv = [["Métrica", "Total do período"]] + [
            [k.replace("_", " ").title(), _fmt_brl(v)] for k, v in totais.items()
        ]
        t = Table(kv, colWidths=[8 * cm, 9 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5fb4")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ]
            )
        )
        story += [Paragraph("Resumo Executivo", h2), t, Spacer(1, 0.8 * cm)]

    _section_ranking(story, story_styles, gastos, "#1f77b4")
    _section_ranking(story, story_styles, financeira, "#2e7d32")
    story.append(PageBreak())
    _section_ranking(story, story_styles, operacional, "#ef6c00")
    _section_ranking(story, story_styles, estrutura, "#6a1b9a")

    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            "Fonte: Dados abertos ANS (Demonstrações Contábeis + CADOP). "
            "Gerado automaticamente por ANS Intelligence v1.2.",
            body,
        )
    )

    doc.build(story)
    buf.seek(0)
    return buf.read()
