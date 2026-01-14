import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = 'https://www.gov.br/ans'

queries = [
    'anexo i rol de procedimentos pdf',
    'anexo i rol procedimentos pdf',
    'anexo i rol de procedimentos ans pdf',
    'anexo i rol',
    'rol de procedimentos anexo i pdf'
]

session = requests.Session()
session.headers.update({'User-Agent': 'ans-app-bot/1.0'})

all_found = []
for q in queries:
    urls = [
        f"{BASE}/search?origem=termos&SearchableText={q}",
        f"{BASE}/pt-br/busca?q={q}",
        f"{BASE}/pt-br/busca?q={q.replace(' ', '+')}"
    ]
    for u in urls:
        print('Querying', u)
        try:
            r = session.get(u, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href and href.lower().endswith('.pdf'):
                    pdf_url = urljoin(BASE, href)
                    all_found.append((q, u, pdf_url, a.get_text(strip=True)))
        except Exception as e:
            print('Error', u, e)

print('\nResults:')
for item in all_found:
    print(item)
