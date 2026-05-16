import json
import random
import urllib.parse
import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://listado.mercadolibre.com.ar/{query}"

# Ampliamos la lista para rotar la huella digital y evadir bloqueos básicos
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]


def _headers(accept: str = "text/html") -> dict[str, str]:
    # Elegimos un User-Agent al azar en cada petición
    return {
        "Accept": accept,
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7", # Agregamos esto para parecer más reales
    }


def fetch_html(url: str) -> str:
    response = requests.get(url, timeout=15, headers=_headers())
    response.raise_for_status()
    return response.text


def parse_products_ld_json(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
            
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if not isinstance(data, dict) or "@graph" not in data:
            continue

        products = []
        for item in data["@graph"]:
            if not isinstance(item, dict) or item.get("@type") != "Product":
                continue
                
            offers = item.get("offers", {})
            products.append({
                "store": "mercadolibre",
                "name": item.get("name"),
                "price": offers.get("price"),
                "currency": offers.get("priceCurrency"),
                "url": offers.get("url"),
            })
            
        if products: # Si encontramos productos en este script, los devolvemos y cortamos el bucle
            return products

    return []


def scrape_search(query: str = "placas de video", limit: int = 50) -> list[dict]:
    # urllib.parse.quote asegura que cualquier símbolo raro en la búsqueda se procese bien en la URL
    safe_query = urllib.parse.quote(query.replace(" ", "-"))
    url = SEARCH_URL.format(query=safe_query)
    
    html = fetch_html(url)
    products = parse_products_ld_json(html)
    
    # Aseguramos devolver exactamente hasta el límite solicitado
    return products[:limit]


if __name__ == "__main__":
    products = scrape_search("rtx 3060 ti")
    for p in products:
        print(f"${p['price']} {p['currency']} - {p['name']}")