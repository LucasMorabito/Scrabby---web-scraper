import requests


BASE_URL = "https://www.fravega.com/api/v2"

ZONES = [
    "03143339-1672-49fd-b5fc-6be4ed38f529",
    "086dfc51-259b-48b8-9413-6a38a48e8d02",
    "11a46c8a-6860-478f-8321-276aba2a61a3",
    "2", "25", "28", "29", "30"
]

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
      }
      pricing {
        salePrice
      }
    }
  }
}
"""

def scrape(keyword: str, size: int = 20) -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "content-type": "application/json",
        "origin": "https://www.fravega.com",
        "referer": f"https://www.fravega.com/l/?keyword={keyword.replace(' ', '+')}",
    }

    payload = {
        "operationName": "GetItems",
        "variables": {
            "filters": {
                "keywords": keyword,
                "zones": ZONES
            },
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

    r = requests.post(BASE_URL, json=payload, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()

    products = []
    for result in data.get("data", {}).get("items", {}).get("results", []):
        item = result.get("item", {})
        pricing = result.get("pricing", {})
        slug = item.get("slug", "")
        products.append({
            "store": "fravega",
            "name": item.get("title"),
            "price": pricing.get("salePrice"),
            "currency": "ARS",
            "url": f"https://www.fravega.com/p/{slug}/" if slug else None,
        })
    return products


if __name__ == "__main__":
    products = scrape("placas de video")
    for p in products:
        print(p["price"], p["currency"], p["name"])