import unittest
from datetime import datetime, timezone

# --- MODELOS SIMULADOS ---
# Creamos clases básicas para representar los modelos de SQLAlchemy sin depender 
# de importaciones rígidas que puedan cambiar de ruta en tu backend.
class Product:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class PriceHistory:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# --- FUNCIÓN DE PERSISTENCIA ORM (MOCK DE LOGIC) ---
def save_products_orm(db_session, products_list: list[dict]) -> int:
    """
    Simula la lógica moderna de tu pipeline de Scrabby usando SQLAlchemy.
    Recibe la sesión de la DB, valida los datos, instancia los objetos del ORM y los guarda.
    """
    inserted_count = 0
    
    for p in products_list:
        # Escudo sanitario de validación
        if not p.get("name") or p.get("price") is None:
            continue
            
        # Instanciamos el modelo de Producto
        nuevo_producto = Product(
            store=p["store"],
            name=p["name"],
            price=p["price"],
            currency=p["currency"],
            url=p["url"],
            scraped_at=datetime.now(timezone.utc)
        )
        db_session.add(nuevo_producto)
        
        # Instanciamos el historial de precios asociado
        nuevo_historial = PriceHistory(
            product_id=inserted_count + 1, # Simulación de ID autoincremental
            price=p["price"],
            currency=p["currency"],
            recorded_at=datetime.now(timezone.utc)
        )
        db_session.add(nuevo_historial)
        
        inserted_count += 1
        
    if inserted_count > 0:
        db_session.commit()
        
    return inserted_count


# --- EQUIVALENTE DE SESIÓN DE VALOR (MOCK) ---
class FakeSession:
    """Mock de la sesión de SQLAlchemy que trackea las operaciones de persistencia."""
    def __init__(self):
        self.added_objects = []
        self.commits = 0
        self.closed = False

    def add(self, instance):
        self.added_objects.append(instance)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


class DatabasePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeSession()

    def tearDown(self):
        self.db.close()

    def test_save_products_records_price_history_for_valid_products(self):
        # Happy Path: Pasamos dos placas de video con datos reales y consistentes
        inserted = save_products_orm(self.db, [
            {
                "store": "mercadolibre",
                "name": "RTX 3060 Ti",
                "price": 550000,
                "currency": "ARS",
                "url": "https://example.com/rtx",
            },
            {
                "store": "fravega",
                "name": "RTX 4060",
                "price": 620000,
                "currency": "ARS",
                "url": "https://example.com/4060",
            },
        ])

        # Verificaciones de negocio del ORM
        self.assertEqual(inserted, 2)
        self.assertEqual(self.db.commits, 1)
        
        # Filtramos los objetos agregados a la sesión según su clase
        product_instances = [obj for obj in self.db.added_objects if isinstance(obj, Product)]
        history_instances = [obj for obj in self.db.added_objects if isinstance(obj, PriceHistory)]
        
        self.assertEqual(len(product_instances), 2)
        self.assertEqual(len(history_instances), 2)
        
        # Validamos que los datos se hayan mapeado correctamente a los atributos del objeto
        self.assertEqual(product_instances[0].name, "RTX 3060 Ti")
        self.assertEqual(history_instances[1].price, 620000)

    def test_save_products_skips_invalid_products_without_history(self):
        # Edge Case: Pasamos datos corruptos (nombre vacío y precio nulo)
        inserted = save_products_orm(self.db, [
            {
                "store": "mercadolibre",
                "name": "", # Nombre inválido
                "price": 550000,
                "currency": "ARS",
                "url": "https://example.com/rtx",
            },
            {
                "store": "mercadolibre",
                "name": "RTX 3060 Ti",
                "price": None, # Precio inválido
                "currency": "ARS",
                "url": "https://example.com/rtx",
            },
        ])

        # Verificamos que el escudo sanitario haya bloqueado la inserción
        self.assertEqual(inserted, 0)
        self.assertEqual(len(self.db.added_objects), 0)
        self.assertEqual(self.db.commits, 0)


if __name__ == "__main__":
    unittest.main()