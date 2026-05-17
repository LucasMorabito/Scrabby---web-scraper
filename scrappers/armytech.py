import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

BASE_URL = "https://www.armytech.com.ar"
CATEGORY_URL = "https://www.armytech.com.ar/module/iqitsearch/searchiqit?s=placa+de+video"
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

    try:
        response = requests.get(CATEGORY_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error ArmyTech: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    tarjetas = soup.find_all("div", class_="product-description")

    if not tarjetas:
        print("No se encontraron tarjetas en ArmyTech")
        return []

    for tarjeta in tarjetas:
        titulo_tag = tarjeta.find("h3", class_="product-title")
        if not titulo_tag:
            continue
        link_tag = titulo_tag.find("a")
        if not link_tag:
            continue
        nombre = link_tag.get_text(strip=True)
        url_prod = link_tag.get("href", "")

        precio_tag = tarjeta.find("span", class_="product-price")
        if not precio_tag:
            continue
        try:
            precio = float(precio_tag.get("content", 0))
        except ValueError:
            continue

        if not precio:
            continue

        if keyword and keyword.lower() not in nombre.lower():
            continue

        if es_valido(nombre, precio):
            products.append({
                "store": "armytech",
                "name": nombre,
                "price": precio,
                "currency": "ARS",
                "url": url_prod,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })

        if len(products) >= size:
            break

    return products

if __name__ == "__main__":
    print("Escaneando ArmyTech...")
    productos = scrape()
    print(f"Encontrados: {len(productos)}\n")
    for p in productos[:5]:
        print(f"${p['price']:,.0f} - {p['name']}\n{p['url']}\n")