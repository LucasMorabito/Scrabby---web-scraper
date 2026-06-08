import os
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from .llm_parser import llm_parse_products

BASE_URL = "https://www.mexx.com.ar"
SEARCH_URL = f"{BASE_URL}/buscar/"
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
    response = requests.get(
        SEARCH_URL,
        params={"p": keyword, "pagina": page},
        headers=HEADERS,
        timeout=15,
    )
    response.raise_for_status()
    return response.text


def parse_products(html: str, limit: int = 50) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    productos_encontrados = soup.select("div.card-body")
    if not productos_encontrados:
        return llm_parse_products(html=html, store="mexx", base_url="https://www.mexx.com.ar")
    
    products = []

    for tarjeta in productos_encontrados:
        link_tag = tarjeta.select_one("h4.card-title a")
        precio_tag = tarjeta.select_one("div.price h4 b")
        if not link_tag or not precio_tag:
            continue

        nombre = normalizar_texto(link_tag.get_text(" ", strip=True))
        precio = parse_precio(precio_tag.get_text(" ", strip=True))
        url_prod = urljoin(BASE_URL, link_tag.get("href", ""))

        if not nombre or precio is None or not url_prod:
            continue

        if es_valido(nombre, precio):
            products.append(
                {
                    "store": "mexx",
                    "name": nombre,
                    "price": precio,
                    "currency": "ARS",
                    "url": url_prod,
                }
            )

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
            print(f"Error al descargar Mexx (pagina {page}): {e}")
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
    print("Escaneando Mexx...")
    productos = scrape("placa de video")
    print(f"Encontrados: {len(productos)}\n")
    for p in productos[:10]:
        print(f"${p['price']:,.0f} - {p['name']}\n{p['url']}\n")