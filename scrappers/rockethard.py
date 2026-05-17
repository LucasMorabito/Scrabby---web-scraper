import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

BASE_URL = "https://rockethard.com.ar"
CATEGORY_URL = f"{BASE_URL}/hardware/placa-de-video"
PRECIO_MINIMO = float(os.getenv("SCRABBY_MIN_PRICE", 100000))
BLACKLIST = ["cooler", "ventilador", "cable", "adaptador", "soporte", "pasta", "riser", "water block", "outlet"]

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

    while len(products) < size:
        url = f"{CATEGORY_URL}?pagina={page}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"Error RocketHard (página {page}): {e}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        tarjetas = soup.find_all("div", attrs={"data-nombre": True, "data-precio": True})

        if not tarjetas:
            break

        for tarjeta in tarjetas:
            nombre = tarjeta.get("data-nombre", "").strip()
            try:
                precio = float(tarjeta.get("data-precio", 0))
            except ValueError:
                continue

            if keyword and keyword.lower() not in nombre.lower():
                continue

            link_tag = tarjeta.find("a", href=True)
            url_prod = link_tag["href"] if link_tag else ""

            if es_valido(nombre, precio):
                products.append({
                    "store": "rockethard",
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
    print("Escaneando RocketHard...")
    productos = scrape()
    print(f"Encontrados: {len(productos)}\n")
    for p in productos[:5]:
        print(f"${p['price']:,.0f} - {p['name']}\n{p['url']}\n")