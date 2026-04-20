import json
import os
from scrappers.fravega import scrape as scrape_fravega
from scrappers.mercadolibre import scrape_search as scrape_ml
from database.database import save_products

def is_valid_product(product):
    """
    Filtra la basura de los resultados de búsqueda.
    Devuelve True si parece ser una placa de video real, False si es basura.
    """
    price = product.get("price")
    title = product.get("name", "").lower() # Pasamos a minúsculas para comparar fácil

    # 1. Filtro de Precio: Descartamos si no tiene precio o es absurdamente barato
    MINIMUM_REALISTIC_PRICE = 200000 
    if price is None or price < MINIMUM_REALISTIC_PRICE:
        return False

    # 2. FBlacklist
    blacklist = [
        "cooler", "ventilador", "caja", "cable", "adaptador", 
        "reparacion", "servicio", "fuente", "mother", "motherboard",
        "pasta termica", "soporte"
    ]
    
    for word in blacklist:
        if word in title:
            return False

    return True

def save_to_json(data, filename="data/products.json"):
    # Nos aseguramos de que la carpeta 'data/' exista para evitar errores de ruta
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            # indent=4: para que el archivo sea legible por humanos
            # ensure_ascii=False: para que los caracteres especiales y el símbolo $ se vean bien
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"\n¡Éxito! Datos guardados en {filename}")
    except Exception as e:
        print(f"\nError al guardar el archivo JSON: {e}")

def main():
    search_query = "rtx 3060 ti"
    print(f"🔍 Iniciando rastreo para: '{search_query}'...\n")
    
    # --- Extracción (Scraping) ---
    print("Obteniendo datos de Frávega...")
    try:
        fravega_results = scrape_fravega(keyword=search_query)
    except Exception as e:
        print(f"Error Frávega: {e}")
        fravega_results = []

    print("Obteniendo datos de Mercado Libre...")
    try:
        ml_results = scrape_ml(query=search_query)
    except Exception as e:
        print(f"Error ML: {e}")
        ml_results = []

    # --- Unificación y Procesamiento ---
    all_results = fravega_results + ml_results
    
    # Limpieza (usando el nuevo filtro) y Ordenamiento
    clean_results = [p for p in all_results if is_valid_product(p)]
    sorted_results = sorted(clean_results, key=lambda x: x["price"])

    # --- Persistencia (Guardar) ---
    if sorted_results:
        save_to_json(sorted_results)
        
        inserted = save_products(sorted_results)
        print(f"Guardados en base de datos: {inserted} productos")
        
        print(f"\n--- RESUMEN DE BÚSQUEDA ---")
        print(f"Total de productos: {len(sorted_results)}")
        cheapest_price = sorted_results[0]['price']
        cheapest_store = sorted_results[0]['store'].upper()
        print(f"Más barato: ${cheapest_price:,.0f} ({cheapest_store})")

if __name__ == "__main__":
    main()