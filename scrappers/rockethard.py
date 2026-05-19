import os
from urllib.parse import urljoin
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

BASE_URL = "https://rockethard.com.ar"
SEARCH_URL = f"{BASE_URL}/buscar/"

PRECIO_MINIMO = float(os.getenv("SCRABBY_MIN_PRICE", 100000))

BLACKLIST = [
    "cooler",
    "ventilador",
    "cable",
    "adaptador",
    "soporte",
    "pasta",
    "riser",
    "water block",
    "outlet"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://www.google.com/"
}


def es_valido(nombre: str, precio: float) -> bool:
    if precio < PRECIO_MINIMO:
        return False
    return not any(p in nombre.lower() for p in BLACKLIST)


def scrape(keyword: str = "", size: int = 50) -> list[dict]:
    products = []
    seen_urls = set()
    page = 1
    search_keyword = keyword if keyword else "placa de video"

    while len(products) < size:
        try:
            response = cffi_requests.get(
                SEARCH_URL,
                params={"q": search_keyword, "pagina": page},
                headers=HEADERS,
                impersonate="chrome120",
                timeout=15
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Error RocketHard (página {page}): {e}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        tarjetas = soup.find_all("div", attrs={"data-nombre": True, "data-precio": True})

        if not tarjetas:
            break

        new_products_found = 0
        for tarjeta in tarjetas:
            nombre = tarjeta.get("data-nombre", "").strip()

            try:
                precio = float(tarjeta.get("data-precio", 0))
            except ValueError:
                continue

            if keyword and keyword.lower() not in nombre.lower():
                if keyword.lower() not in ["placa de video", "placas de video"]:
                    continue

            link_tag = tarjeta.find("a", href=True)
            url_prod = link_tag["href"] if link_tag else ""

            if url_prod and not url_prod.startswith("http"):
                url_prod = urljoin(BASE_URL, url_prod)

            if url_prod in seen_urls:
                continue

            if es_valido(nombre, precio):
                seen_urls.add(url_prod)
                product = {
                    "store": "rockethard",
                    "name": nombre,
                    "price": precio,
                    "currency": "ARS",
                    "url": url_prod,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }
                products.append(product)
                new_products_found += 1

            if len(products) >= size:
                break

        if new_products_found == 0:
            break

        page += 1

    return products


if __name__ == "__main__":
    print("Escaneando RocketHard...")
    productos = scrape()
    print(f"\n--- RESULTADO FINAL ---")
    print(f"Encontrados: {len(productos)}\n")
    for p in productos[:5]:
        print(f"${p['price']:,.0f} - {p['name']}\n{p['url']}\n")