import json

import requests

from bs4 import BeautifulSoup


SEARCH_URL = "https://listado.mercadolibre.com.ar/{query}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Mercado Libre API integration is intentionally disabled until the app is
# authorized for the intended API usage.
#
# import os
# from dotenv import load_dotenv
#
# load_dotenv()
#
# API_URL = "https://api.mercadolibre.com/sites/MLA/search"
# TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
# _ACCESS_TOKEN_CACHE = None
#
#
# class MercadoLibreAuthError(RuntimeError):
#     pass
#
#
# def _env(*names: str) -> str | None:
#     for name in names:
#         value = os.getenv(name)
#         if value:
#             return value
#
#     return None


def _headers(accept: str = "text/html") -> dict[str, str]:
    return {
        "Accept": accept,
        "User-Agent": USER_AGENT,
    }

# def _get_access_token() -> str | None:
#     return _ACCESS_TOKEN_CACHE or _env(
#         "MERCADOLIBRE_ACCESS_TOKEN",
#         "ML_ACCESS_TOKEN",
#         "ACCESS_TOKEN",
#     )
#
#
# def refresh_access_token() -> str:
#     global _ACCESS_TOKEN_CACHE
#
#     refresh_token = _env(
#         "MERCADOLIBRE_REFRESH_TOKEN",
#         "ML_REFRESH_TOKEN",
#         "REFRESH_TOKEN",
#     )
#     client_id = _env("MERCADOLIBRE_CLIENT_ID", "ML_CLIENT_ID", "APP_ID", "CLIENT_ID")
#     client_secret = _env(
#         "MERCADOLIBRE_CLIENT_SECRET",
#         "ML_CLIENT_SECRET",
#         "CLIENT_SECRET",
#     )
#
#     if not refresh_token or not client_id or not client_secret:
#         raise MercadoLibreAuthError(
#             "Faltan MERCADOLIBRE_REFRESH_TOKEN, APP_ID o CLIENT_SECRET"
#         )
#
#     response = requests.post(
#         TOKEN_URL,
#         data={
#             "grant_type": "refresh_token",
#             "client_id": client_id,
#             "client_secret": client_secret,
#             "refresh_token": refresh_token,
#         },
#         timeout=15,
#         headers={
#             "Accept": "application/json",
#             "User-Agent": USER_AGENT,
#         },
#     )
#     response.raise_for_status()
#     data = response.json()
#
#     access_token = data.get("access_token")
#     if not access_token:
#         raise MercadoLibreAuthError("Mercado Libre no devolvio access_token")
#
#     _ACCESS_TOKEN_CACHE = access_token
#     return access_token


def fetch_html(url: str) -> str:
    response = requests.get(url, timeout=15, headers=_headers())
    response.raise_for_status()
    return response.text


# def fetch_api_results(query: str, limit: int = 50) -> list[dict]:
#     params = {"q": query, "limit": limit}
#     response = requests.get(
#         API_URL,
#         params=params,
#         timeout=15,
#         headers=_headers("application/json"),
#     )
#
#     if response.status_code == 401:
#         try:
#             refresh_access_token()
#         except (MercadoLibreAuthError, requests.RequestException):
#             return []
#
#         response = requests.get(
#             API_URL,
#             params=params,
#             timeout=15,
#             headers=_headers("application/json"),
#         )
#
#     if response.status_code in {401, 403}:
#         return []
#
#     response.raise_for_status()
#     data = response.json()
#     return data.get("results", [])
#
#
# def parse_products_api(results: list[dict]) -> list[dict]:
#     products = []
#
#     for item in results:
#         if not isinstance(item, dict):
#             continue
#
#         title = item.get("title")
#         price = item.get("price")
#         url = item.get("permalink")
#
#         if not title or price is None or not url:
#             continue
#
#         products.append({
#             "store": "mercadolibre",
#             "name": title,
#             "price": price,
#             "currency": item.get("currency_id") or "ARS",
#             "url": url,
#         })
#
#     return products


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


def scrape_search(query: str = "placas de video", limit: int = 50) -> list[dict]:
    url = SEARCH_URL.format(query=query.replace(" ", "-"))
    html = fetch_html(url)
    return parse_products_ld_json(html)[:limit]


if __name__ == "__main__":
    products = scrape_search("placas de video")
    for p in products:
        print(p["price"], p["currency"], p["name"])
