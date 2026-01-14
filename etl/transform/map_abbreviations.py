import re
from typing import Dict

import pdfplumber


def extract_od_amb_legend(pdf_path: str) -> Dict[str, str]:
    """Extrai do PDF um mapa de abreviações para descrições.

    Objetivo: encontrar no rodapé/legenda algo como:
    - "OD: ..." / "OD - ..."
    - "AMB: ..." / "AMB - ..."

    Observação: o PDF do Anexo I pode variar ao longo do tempo. Por isso,
    a função tenta padrões comuns e, se falhar, retorna um fallback.
    """

    legend: Dict[str, str] = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Normalmente a legenda fica nas páginas finais, mas isso pode mudar.
            # Varremos as últimas 5 páginas para ser mais robusto.
            pages = pdf.pages[-5:] if len(pdf.pages) >= 5 else pdf.pages

            for page in pages:
                text = page.extract_text() or ""
                if not text:
                    continue

                # Normaliza espaços
                text = re.sub(r"\s+", " ", text)

                # Padrões típicos: "OD - ..." / "OD: ..."
                for abbr in ("OD", "AMB"):
                    if abbr in legend:
                        continue

                    m = re.search(rf"\b{abbr}\b\s*[-:]\s*([^.;\n]+)", text, flags=re.IGNORECASE)
                    if m:
                        legend[abbr] = m.group(1).strip()

                if "OD" in legend and "AMB" in legend:
                    break

    except Exception:
        # Mantém comportamento tolerante a falhas
        pass

    # Fallback (caso a legenda não seja encontrada no PDF)
    legend.setdefault("OD", "Odontológico")
    legend.setdefault("AMB", "Ambulatorial")

    return legend


def replace_od_amb_values(df, legend: Dict[str, str]):
    """Substitui valores abreviados OD/AMB nas colunas correspondentes, se existirem."""

    if df is None or df.empty:
        return df

    if "od" in df.columns and "OD" in legend:
        df["od"] = df["od"].fillna("").astype(str).replace({"OD": legend["OD"]})

    if "amb" in df.columns and "AMB" in legend:
        df["amb"] = df["amb"].fillna("").astype(str).replace({"AMB": legend["AMB"]})

    return df
