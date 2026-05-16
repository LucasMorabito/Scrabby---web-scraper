import random
import urllib.parse
import requests

BASE_URL = "https://www.fravega.com/api/v2"

ZONES = [
    "03143339-1672-49fd-b5fc-6be4ed38f529",
    "086dfc51-259b-48b8-9413-6a38a48e8d02",
    "11a46c8a-6860-478f-8321-276aba2a61a3",
    "2", "25", "28", "29", "30"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
]

# La llave maestra de GraphQL (Extrae el EAN si existe)
GRAPHQL_QUERY = """
query GetItems($filters: Filters, $presentationFilters: PresentationFilters, $pagination: Pagination, $sorting: SortOption) {
  items(
    filters: $filters
    presentationFilters: $presentationFilters
    pagination: $pagination
    sorting: $sorting
  ) {
    total
    results {
      item {
        title
        slug
        gtin {
          ... on EAN {
            number
          }
        }
      }
      pricing {
        salePrice
      }
    }
  }
}
"""

def scrape(keyword: str, size: int = 20) -> list[dict]:
    safe_keyword = urllib.parse.quote_plus(keyword)
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "content-type": "application/json",
        "origin": "https://www.fravega.com",
        "referer": f"https://www.fravega.com/l/?keyword={safe_keyword}",
        "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    payload = {
        "operationName": "GetItems",
        "variables": {
            "filters": {"keywords": keyword, "zones": ZONES},
            "presentationFilters": {
                "priceChannel": "fravega-ecommerce",
                "cockadeTag": "listing",
                "stockZoneIds": ZONES
            },
            "pagination": {"size": size, "from": 0},
            "sorting": "TOTAL_SALES_IN_LAST_30_DAYS",
            "sessionId": None
        },
        "query": GRAPHQL_QUERY
    }

    try:
        r = requests.post(BASE_URL, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Error de conexión con GraphQL Frávega: {e}")
        return []

    if "errors" in data:
        print(f"Error interno en GraphQL de Frávega: {data['errors'][0].get('message')}")
        return []

    products = []
    for result in data.get("data", {}).get("items", {}).get("results", []):
        item = result.get("item", {})
        pricing = result.get("pricing", {})
        
        title = item.get("title")
        sale_price = pricing.get("salePrice")
        slug = item.get("slug", "")
        
        # Extraemos el EAN (si el vendedor se dignó a cargarlo)
        gtin_data = item.get("gtin") or {}
        item_number = gtin_data.get("number", "")
        
        if not title or not sale_price:
            continue
            
        # 🚀 LA MAGIA DEL FALLBACK:
        if item_number:
            # Plan A: URL Directa
            product_url = f"https://www.fravega.com/p/{slug}-{item_number}/"
        else:
            # Plan B: Búsqueda exacta (Graceful Degradation)
            exact_title_encoded = urllib.parse.quote_plus(title)
            product_url = f"https://www.fravega.com/l/?keyword={exact_title_encoded}"
            
        products.append({
            "store": "fravega",
            "name": title,
            "price": sale_price,
            "currency": "ARS",
            "url": product_url, 
        })
        
    return products

if __name__ == "__main__":
    products = scrape("placas de video")
    print(f"Encontrados: {len(products)}\n")
    for p in products[:5]:
        print(f"${p['price']} {p['currency']} - {p['name']}\nLink: {p['url']}\n")