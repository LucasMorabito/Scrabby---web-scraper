import json
import urllib.parse

from bs4 import BeautifulSoup

from scrappers.http_client import create_stealth_http_client

SEARCH_URL = "https://listado.mercadolibre.com.ar/{query}"
HTTP_CLIENT = create_stealth_http_client()


def _headers(accept: str = "text/html") -> dict[str, str]:
    return {
        "Accept": accept,
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
    }


def fetch_html(url: str) -> str:
    response = HTTP_CLIENT.get(url, timeout=15, headers=_headers())
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

        if products:
            return products

    return []


def scrape_search(query: str = "placas de video", limit: int = 50) -> list[dict]:
    safe_query = urllib.parse.quote(query.replace(" ", "-"))
    url = SEARCH_URL.format(query=safe_query)

    html = fetch_html(url)
    products = parse_products_ld_json(html)

    return products[:limit]


if __name__ == "__main__":
    products = scrape_search("rtx 3060 ti")
    for p in products:
        print(f"${p['price']} {p['currency']} - {p['name']}")
