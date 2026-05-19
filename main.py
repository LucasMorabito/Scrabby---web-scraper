import argparse
import json
import os

from database.crud import save_products 
from scrappers.fravega import scrape as scrape_fravega
from scrappers.mercadolibre import scrape_search as scrape_ml
from scrappers.mexx import scrape as scrape_mexx
from scrappers.quantumhardstore import scrape as scrape_quantum
from scrappers.tech710 import scrape as scrape_710tech
from scrappers.armytech import scrape as scrape_armytech
from scrappers.rockethard import scrape as scrape_rockethard


DEFAULT_SEARCH_QUERY = os.getenv("SCRABBY_SEARCH_QUERY", "placa de video")
DEFAULT_RESULT_LIMIT = int(os.getenv("SCRABBY_RESULT_LIMIT", "50"))
MINIMUM_PRICE = float(os.getenv("SCRABBY_MIN_PRICE", "100000"))


def parse_args():
    parser = argparse.ArgumentParser(description="Scrapea precios de componentes de PC.")
    parser.add_argument("query", nargs="*", help="Término de búsqueda. Ejemplo: python main.py rtx 3060 ti")
    parser.add_argument("--limit", type=int, default=DEFAULT_RESULT_LIMIT, help="Cantidad máxima por tienda.")
    parser.add_argument("--min-price", type=float, default=MINIMUM_PRICE, help="Precio mínimo realista.")
    return parser.parse_args()


def parse_price(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_valid_product(product, min_price):
    """Filtra basura de los resultados de búsqueda."""
    price = parse_price(product.get("price"))
    title = product.get("name", "").lower()
    url = product.get("url")

    if price is None or price < min_price or not url:
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
    
    if "name" in normalized and normalized["name"]:
        clean_name = str(normalized["name"]).encode("utf-8", errors="ignore").decode("utf-8")
        normalized["name"] = clean_name[:255]
        
    if "url" in normalized and normalized["url"]:
        clean_url = str(normalized["url"]).encode("utf-8", errors="ignore").decode("utf-8")
        normalized["url"] = clean_url[:512]
        
    return normalized


def save_to_json(data, filename="data/products.json"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"\nÉxito: datos guardados en {filename}")
    except Exception as e:
        print(f"\nError al guardar el archivo JSON: {e}")


def main():
    args = parse_args()
    search_query = " ".join(args.query) or DEFAULT_SEARCH_QUERY
    limit = args.limit
    min_price = args.min_price

    print(f"Iniciando rastreo para: '{search_query}'...\n")

    print("Obteniendo datos de Frávega...")
    try:
        fravega_results = scrape_fravega(keyword=search_query, size=limit)
    except Exception as e:
        print(f"Error Frávega: {e.__class__.__name__} - {e}")
        fravega_results = []

    print("Obteniendo datos de Mercado Libre...")
    try:
        ml_results = scrape_ml(query=search_query, limit=limit)
    except Exception as e:
        print(f"Error ML: {e.__class__.__name__} - {e}")
        ml_results = []

    print("Obteniendo datos de Mexx...")
    try:
        mexx_results = scrape_mexx(keyword=search_query, size=limit)
    except Exception as e:
        print(f"Error Mexx: {e.__class__.__name__} - {e}")
        mexx_results = []

    print("Obteniendo datos de Quantum Hardstore...")
    try:
        quantum_results = scrape_quantum(keyword=search_query, size=limit)
    except Exception as e:
        print(f"Error Quantum Hardstore: {e.__class__.__name__} - {e}")
        quantum_results = []

    print("Obteniendo datos de 710Tech...")
    try:
        tech710_results = scrape_710tech(keyword=search_query, size=limit)
    except Exception as e:
        print(f"Error 710Tech: {e.__class__.__name__} - {e}")
        tech710_results = []

    print("Obteniendo datos de ArmyTech...")
    try:
        armytech_results = scrape_armytech(keyword=search_query, size=limit)
    except Exception as e:
        print(f"Error ArmyTech: {e.__class__.__name__} - {e}")
        armytech_results = []

    print("Obteniendo datos de Rocket Hard...")
    try:
        rockethard_results = scrape_rockethard(keyword=search_query, size=limit)
    except Exception as e:
        print(f"Error Rocket Hard: {e.__class__.__name__} - {e}")
        rockethard_results = []

    # Consolidamos el pool completo con las 7 fuentes distribuidas
    all_results = (
        fravega_results + 
        ml_results + 
        mexx_results + 
        quantum_results + 
        tech710_results +
        armytech_results +
        rockethard_results
    )
    print("\n--- PRODUCTOS OBTENIDOS POR TIENDA ---")
    print(f"Frávega: {len(fravega_results)}")
    print(f"Mercado Libre: {len(ml_results)}")
    print(f"Mexx: {len(mexx_results)}")
    print(f"Quantum Hardstore: {len(quantum_results)}")
    print(f"710Tech: {len(tech710_results)}")
    print(f"ArmyTech: {len(armytech_results)}")
    print(f"Rocket Hard: {len(rockethard_results)}")

    print(f"\nTotal bruto recolectado: {len(all_results)}")
    clean_results = [
        normalize_product(p)
        for p in all_results
        if is_valid_product(p, min_price)
    ]
    
    print(f"Total válido luego de filtros: {len(clean_results)}")
    print(f"Productos descartados: {len(all_results) - len(clean_results)}")
    
    sorted_results = sorted(clean_results, key=lambda x: x["price"])

    if sorted_results:
        save_to_json(sorted_results)
        try:
            inserted = save_products(sorted_results)
            print(f"Guardados en base de datos: {inserted} productos")
        except Exception as db_error:
            print(f"\nError crítico al insertar en la Base de Datos: {db_error}")

        print("\n--- RESUMEN DE BÚSQUEDA ---")
        print(f"Total de productos válidos: {len(sorted_results)}")
        cheapest_price = sorted_results[0]["price"]
        cheapest_store = sorted_results[0]["store"].upper()
        print(f"Más barato: ${cheapest_price:,.0f} ({cheapest_store})")
    else:
        print("No se encontraron productos válidos.")


if __name__ == "__main__":
    main()