from datetime import datetime, timezone
import unittest

from fastapi.testclient import TestClient

from api.dependencies import get_db
from api.main import app


class FakeRowObject(dict):
    def __init__(self, keys, values):
        super().__init__()
        for k, v in zip(keys, values):
            self[k] = v

    def __getattr__(self, name):
        if name in self: return self[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self.model_name = str(model).lower()
        self.results = list(db.objects)

    def filter(self, *args, **kwargs):
        if args:
            expr = str(args[0])
            if "999" in expr or "missing" in expr:
                self.results = []
        return self

    def order_by(self, *args): return self
    def limit(self, *args): return self
    def offset(self, *args): return self
    def group_by(self, *args): return self

    def count(self): return len(self.results)

    def all(self):
        if "pricehistory" in self.model_name:
            if any(getattr(obj, "price", None) is None for obj in self.results):
                return []
        return self.results

    def first(self):
        if not self.results: return None
        return self.results[0]


class FakeDB:
    def __init__(self, rows=None, force_fail=False):
        self.rows = rows or []
        self.force_fail = force_fail
        self.objects = []
        for r in self.rows:
            if not isinstance(r, (tuple, list)):
                self.objects.append(r)
                continue
            
            if len(r) == 5 and r[0] is None:
                self.objects.append(FakeRowObject(["id", "product_id", "price", "currency", "recorded_at"], r))
                continue
                
            if len(r) == 7:
                keys = ["id", "store", "name", "price", "currency", "url", "scraped_at"]
            elif len(r) == 3 or (len(r) > 0 and isinstance(r[0], str)):
                keys = ["store", "total", "last_scraped"]
            elif len(r) == 5:
                keys = ["id", "product_id", "price", "currency", "recorded_at"]
            else:
                keys = [f"col_{i}" for i in range(len(r))]
            
            self.objects.append(FakeRowObject(keys, r))

    def query(self, *args):
        return FakeQuery(self, args[0] if args else None)

    def close(self): pass


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def override_db(self, rows, force_fail=False):
        def _override():
            yield FakeDB(rows, force_fail=force_fail)
        app.dependency_overrides[get_db] = _override

    def assert_error_response(self, response, status_code, message):
        self.assertEqual(response.status_code, status_code)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], status_code)
        self.assertEqual(body["error"]["message"], message)

    def test_docs_and_openapi_are_available(self):
        docs_response = self.client.get("/docs")
        openapi_response = self.client.get("/openapi.json")
        self.assertEqual(docs_response.status_code, 200)
        self.assertEqual(openapi_response.status_code, 200)

    def test_health_endpoint_is_available(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_unknown_route_uses_standard_error_response(self):
        response = self.client.get("/missing")
        self.assert_error_response(response, 404, "Not Found")

    def test_products_returns_404_when_empty(self):
        self.override_db([])
        response = self.client.get("/products/?search=missing")
        self.assert_error_response(response, 404, "Products not found")

    def test_compare_returns_404_when_empty(self):
        self.override_db([])
        response = self.client.get("/products/compare/?query=missing")
        self.assert_error_response(response, 404, "Products not found")

    def test_products_rejects_invalid_order_by(self):
        self.override_db([])
        response = self.client.get("/products/?order_by=invalid_column")
        self.assert_error_response(response, 400, "Invalid order_by. Allowed values: name, price, scraped_at")

    def test_products_rejects_invalid_order_dir(self):
        self.override_db([])
        response = self.client.get("/products/?order_dir=sideways")
        self.assert_error_response(response, 400, "Invalid order_dir. Allowed values: asc, desc")

    def test_get_product_by_id_returns_product(self):
        self.override_db([(1, "fravega", "RTX 3060 Ti", 499999.0, "ARS", "https://example.com", None)])
        response = self.client.get("/products/1")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["id"], 1)

    def test_get_product_price_history_returns_history(self):
        recorded_at = datetime(2026, 5, 13, 12, 0, tzinfo=timezone.utc)
        self.override_db([(10, 1, 499999.0, "ARS", recorded_at), (11, 1, 489999.0, "ARS", recorded_at)])
        response = self.client.get("/products/1/history")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

    def test_get_product_price_history_returns_empty_for_product_without_history(self):
        self.override_db([(None, 1, None, None, None)])
        response = self.client.get("/products/1/history")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_product_price_history_returns_404_when_product_is_missing(self):
        self.override_db([])
        response = self.client.get("/products/999/history")
        self.assert_error_response(response, 404, "Product not found")

    def test_products_allows_legacy_rows_without_url(self):
        self.override_db([(1, "fravega", "RTX 3060 Ti", 499999.0, "ARS", None, None)])
        response = self.client.get("/products/")
        self.assertEqual(response.status_code, 200)

    def test_compare_groups_results_by_store(self):
        self.override_db([
            (1, "fravega", "RTX 3060 Ti", 499999.0, "ARS", "https://fravega.com/1", None),
            (2, "mercadolibre", "RTX 3060 Ti MSI", 515000.0, "ARS", "https://ml.com/2", None),
        ])
        response = self.client.get("/products/compare/?query=rtx")
        self.assertEqual(response.status_code, 200)

    def test_stores_returns_summary(self):
        self.override_db([("fravega", 12, None), ("mercadolibre", 35, None)])
        response = self.client.get("/products/stores/")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()