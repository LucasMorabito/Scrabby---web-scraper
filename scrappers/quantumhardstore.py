import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests

from bs4 import BeautifulSoup

BASE_URL = "https://quantumhardstore.com"
SEARCH_URL = f"{BASE_URL}/search/"
PRECIO_MINIMO = float(os.getenv("SCRABBY_MIN_PRICE", 100000))
BLACKLIST = [
    "adaptador",
    "cable",
    "cooler",
    "disco",
    "fuente",
    "gabinete",
    "hdd",
    "memoria",
    "mother",
    "motherboard",
    "pasta",
    "procesador",
    "riser",
    "soporte",
    "ssd",
    "ventilador",
    "water block",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7",
}


def normalizar_texto(texto: str) -> str:
    return " ".join(texto.split())


def es_valido(nombre: str, precio: float) -> bool:
    if precio < PRECIO_MINIMO:
        return False

    nombre_lower = nombre.lower()
    return not any(palabra in nombre_lower for palabra in BLACKLIST)


def parse_precio(texto: str | int | float | None) -> float | None:
    if texto is None:
        return None
    if isinstance(texto, (int, float)):
        return float(texto)

    match = re.search(r"(\d[\d\.,]*)", texto)
    if not match:
        return None

    numero = match.group(1)
    if "," in numero:
        numero = numero.replace(".", "").replace(",", ".")
    else:
        numero = numero.replace(".", "")

    try:
        return float(numero)
    except ValueError:
        return None


def fetch_html(keyword: str, page: int) -> str:
    search_keyword = "video" if keyword.lower() in ["placa de video", "placas de video"] else keyword
    response = requests.get(
        SEARCH_URL,
        params={"q": search_keyword, "page": page},
        headers=HEADERS,
        timeout=15,
    )
    response.raise_for_status()
    return response.text


def _variants_from_article(articulo) -> list[dict]:
    raw_variants = articulo.get("data-variants")
    if not raw_variants:
        container = articulo.find(attrs={"data-variants": True})
        raw_variants = container.get("data-variants") if container else None

    if not raw_variants:
        return []

    try:
        variants = json.loads(raw_variants)
    except json.JSONDecodeError:
        return []

    return variants if isinstance(variants, list) else []


def _price_from_variant(variant: dict) -> float | None:
    # Quantum publica un precio menor de contado/transferencia y otro de tarjeta.
    discounted = parse_precio(variant.get("price_with_payment_discount_short"))
    return discounted or parse_precio(variant.get("promotional_price_number")) or parse_precio(
        variant.get("price_number")
    )


def parse_products(html: str, limit: int = 50) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    products = []
    for articulo in soup.select("a.q-pcard, article.js-item-product"):
        link = articulo if articulo.name == "a" else articulo.select_one("a[href]")
        nombre = normalizar_texto(
            (link.get("title") if link else None)
            or (link.get("aria-label") if link else None)
            or articulo.get("title")
            or articulo.get("aria-label")
            or ""
        )
        url_prod = link.get("href", "") if link else articulo.get("href", "")
        url_prod = urljoin(BASE_URL, url_prod)
        variants = _variants_from_article(articulo)
        if not variants:
            continue
        variant = variants[0]
        if variant.get("available") is False or variant.get("stock") == 0:
            continue
        precio = _price_from_variant(variant)
        if not nombre or precio is None:
            continue
        if es_valido(nombre, precio):
            products.append({
                "store": "quantum",
                "name": nombre,
                "price": precio,
                "currency": "ARS",
                "url": url_prod,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })
        if len(products) >= limit:
            break
    return products


def scrape(keyword: str, size: int = 50, max_pages: int = 3) -> list[dict]:
    products = []
    seen_urls = set()

    for page in range(1, max_pages + 1):
        try:
            html = fetch_html(keyword, page)
        except Exception as e:
            print(f"Error Quantum Hardstore (pagina {page}): {e}")
            break

        page_products = parse_products(html, limit=size)
        if not page_products:
            break

        new_products = 0
        for product in page_products:
            url = product["url"]
            if url in seen_urls:
                continue

            seen_urls.add(url)
            products.append(product)
            new_products += 1

            if len(products) >= size:
                return products

        if new_products == 0:
            break

    return products


if __name__ == "__main__":
    print("Escaneando Quantum Hardstore...")
    productos = scrape("placa de video")
    print(f"Encontrados: {len(productos)}\n")
    for p in productos[:5]:
        print(f"${p['price']:,.0f} - {p['name']}\n{p['url']}\n")
