import json

import requests

from bs4 import BeautifulSoup


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, timeout=15, headers=headers)
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

        # Buscamos el que tiene @graph con lista de productos
        if not isinstance(data, dict) or "@graph" not in data:
            continue

        products = []
        for item in data["@graph"]:
            if not isinstance(item, dict):
                continue
            if item.get("@type") != "Product":
                continue
            offers = item.get("offers", {})
            products.append({
                "store": "mercadolibre",
                "name": item.get("name"),
                "price": offers.get("price"),
                "currency": offers.get("priceCurrency"),
                "url": offers.get("url"),
            })
        return products

    return []


def scrape_search(query: str = "placas de video") -> list[dict]:
    url = f"https://listado.mercadolibre.com.ar/{query.replace(' ', '-')}"
    html = fetch_html(url)
    return parse_products_ld_json(html)


if __name__ == "__main__":
    products = scrape_search("placas de video")
    for p in products:
        print(p["price"], p["currency"], p["name"])