import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def fetch_page(url: str) -> str:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def find_pdf_links(html: str, base_url: str) -> dict:
    """Procura links para Anexo I e Anexo II e retorna dict {"anexo_i": url, "anexo_ii": url}
    Procura por padrões de texto no texto do link.
    """
    soup = BeautifulSoup(html, "html.parser")
    links = {"anexo_i": None, "anexo_ii": None}

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = (a.get_text() or "").strip().upper()
        if "ANEXO I" in text or "ANEXO 1" in text or "ANEXOI" in text:
            if href.lower().endswith('.pdf'):
                links["anexo_i"] = urljoin(base_url, href)
        if "ANEXO II" in text or "ANEXO 2" in text or "ANEXOII" in text:
            if href.lower().endswith('.pdf'):
                links["anexo_ii"] = urljoin(base_url, href)

    # fallback: procurar por PDFs mencionando 'ANEXO' nas proximidades (texto pai)
    if not links["anexo_i"] or not links["anexo_ii"]:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.lower().endswith('.pdf'):
                continue
            parent_text = (a.parent.get_text() or "").upper()
            if "ANEXO I" in parent_text or "ANEXO 1" in parent_text:
                links.setdefault("anexo_i", urljoin(base_url, href))
            if "ANEXO II" in parent_text or "ANEXO 2" in parent_text:
                links.setdefault("anexo_ii", urljoin(base_url, href))

    return links
