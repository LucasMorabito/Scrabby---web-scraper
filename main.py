import argparse
import json
import os

from database.database import save_products
from scrappers.fravega import scrape as scrape_fravega
from scrappers.mercadolibre import scrape_search as scrape_ml


DEFAULT_SEARCH_QUERY = os.getenv("SCRABBY_SEARCH_QUERY", "placas de video")
DEFAULT_RESULT_LIMIT = int(os.getenv("SCRABBY_RESULT_LIMIT", "50"))


def parse_args():
    parser = argparse.ArgumentParser(description="Scrapea precios de componentes de PC.")
    parser.add_argument(
        "query",
        nargs="*",
        help="Termino de busqueda. Ejemplo: python main.py rtx 3060 ti",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_RESULT_LIMIT,
        help="Cantidad maxima de productos a pedir por tienda.",
    )
    return parser.parse_args()


def parse_price(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_valid_product(product):
    """
    Filtra basura de los resultados de busqueda.
    Devuelve True si parece ser una placa de video real.
    """
    price = parse_price(product.get("price"))
    title = product.get("name", "").lower()
    url = product.get("url")

    minimum_realistic_price = 200000
    if price is None or price < minimum_realistic_price or not url:
        return False

    blacklist = [
        "cooler", "ventilador", "caja", "cable", "adaptador",
        "reparacion", "servicio", "fuente", "mother", "motherboard",
        "pasta termica", "soporte",
    ]

    return not any(word in title for word in blacklist)


def normalize_product(product):
    normalized = dict(product)
    normalized["price"] = parse_price(product.get("price"))
    return normalized


def save_to_json(data, filename="data/products.json"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"\nExito: datos guardados en {filename}")
    except Exception as e:
        print(f"\nError al guardar el archivo JSON: {e}")


def main(search_query: str | None = None, limit: int | None = None):
    if search_query is None or limit is None:
        args = parse_args()
        search_query = search_query or " ".join(args.query) or DEFAULT_SEARCH_QUERY
        limit = limit or args.limit

    print(f"Iniciando rastreo para: '{search_query}'...\n")

    print("Obteniendo datos de Fravega...")
    try:
        fravega_results = scrape_fravega(keyword=search_query, size=limit)
    except Exception as e:
        print(f"Error Fravega: {e}")
        fravega_results = []

    print("Obteniendo datos de Mercado Libre...")
    try:
        ml_results = scrape_ml(query=search_query, limit=limit)
    except Exception as e:
        print(f"Error ML: {e}")
        ml_results = []

    all_results = fravega_results + ml_results
    clean_results = [
        normalize_product(p)
        for p in all_results
        if is_valid_product(p)
    ]
    sorted_results = sorted(clean_results, key=lambda x: x["price"])

    if sorted_results:
        save_to_json(sorted_results)

        inserted = save_products(sorted_results)
        print(f"Guardados en base de datos: {inserted} productos")

        print("\n--- RESUMEN DE BUSQUEDA ---")
        print(f"Total de productos: {len(sorted_results)}")
        cheapest_price = sorted_results[0]["price"]
        cheapest_store = sorted_results[0]["store"].upper()
        print(f"Mas barato: ${cheapest_price:,.0f} ({cheapest_store})")
    else:
        print("No se encontraron productos validos.")


if __name__ == "__main__":
    main()
