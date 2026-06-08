import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from .llm_parser import llm_parse_products

BASE_URL = "https://710tech.com.ar"
CATEGORY_URL = f"{BASE_URL}/placas-de-video/nuevo"
PRECIO_MINIMO = float(os.getenv("SCRABBY_MIN_PRICE", 100000))
BLACKLIST = ["cooler", "ventilador", "cable", "adaptador", "soporte", "pasta", "riser", "water block"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def es_valido(nombre: str, precio: float) -> bool:
    if precio < PRECIO_MINIMO:
        return False
    return not any(p in nombre.lower() for p in BLACKLIST)

def scrape(keyword: str = "", size: int = 50) -> list[dict]:
    products = []
    page = 1
    MAX_PAGES = 10 # limite de seguridad
    
    while len(products) < size:
        url = f"{CATEGORY_URL}?pagina={page}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"Error 710Tech (página {page}): {e}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        tarjetas = soup.find_all("div", attrs={"data-nombre": True, "data-precio": True})

        if not tarjetas:
            return llm_parse_products(html=response.text, store="710tech", base_url="https://www.710tech.com.ar")
        
        # Detectar si estamos en la misma página (loop infinito)
        nombres_pagina = {t.get("data-nombre") for t in tarjetas}
        if page > 1 and nombres_pagina == nombres_pagina_anterior:
            break  # El sitio está devolviendo siempre la misma página
        
        nombres_pagina_anterior = nombres_pagina
        
        for tarjeta in tarjetas:
            nombre = tarjeta.get("data-nombre", "").strip()
            precio_str = tarjeta.get("data-precio", "0")

            try:
                precio = float(precio_str)
            except ValueError:
                continue

            # Filtro por keyword si se especificó
            if keyword and keyword.lower() not in nombre.lower():
                continue

            link_tag = tarjeta.find("a", href=True)
            url_prod = link_tag["href"] if link_tag else ""

            if es_valido(nombre, precio):
                products.append({
                    "store": "710tech",
                    "name": nombre,
                    "price": precio,
                    "currency": "ARS",
                    "url": url_prod,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })

            if len(products) >= size:
                break

        page += 1

    return products

if __name__ == "__main__":
    print("Escaneando 710Tech...")
    productos = scrape()
    print(f"Encontrados: {len(productos)}\n")
    for p in productos[:5]:
        print(f"${p['price']:,.0f} - {p['name']}\n{p['url']}\n")