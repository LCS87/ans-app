from etl.scraping.utils_parse_links import fetch_page

BASE_URL = "https://www.gov.br/ans/pt-br/assuntos/consumidor/o-que-o-seu-plano-de-saude-deve-cobrir-1/o-que-e-o-rol-de-procedimentos-e-evento-em-saude"
html = fetch_page(BASE_URL)

from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')

with open('etl/scraping/debug_links.txt', 'w', encoding='utf-8') as f:
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = (a.get_text(strip=True) or '')
        f.write(f"TEXT: {text}\nHREF: {href}\n---\n")

print('Dump de links salvo em etl/scraping/debug_links.txt')
