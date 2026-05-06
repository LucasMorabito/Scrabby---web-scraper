import unittest

from fastapi.testclient import TestClient

from api.dependencies import get_db
from api.main import app


PRODUCT_COLUMNS = [
    ("id",),
    ("store",),
    ("name",),
    ("price",),
    ("currency",),
    ("url",),
    ("scraped_at",),
]

STORE_COLUMNS = [
    ("store",),
    ("total",),
    ("last_scraped",),
]


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.description = PRODUCT_COLUMNS
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))
        if "COUNT(*) as total" in query:
            self.description = STORE_COLUMNS
        else:
            self.description = PRODUCT_COLUMNS

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class FakeDB:
    def __init__(self, rows=None):
        self.rows = rows or []

    def cursor(self):
        return FakeCursor(self.rows)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def override_db(self, rows):
        def _override():
            yield FakeDB(rows)

        app.dependency_overrides[get_db] = _override

    def test_docs_and_openapi_are_available(self):
        docs_response = self.client.get("/docs")
        openapi_response = self.client.get("/openapi.json")

        self.assertEqual(docs_response.status_code, 200)
        self.assertEqual(openapi_response.status_code, 200)

        paths = openapi_response.json()["paths"]
        self.assertIn("/products/cheapest/", paths)
        self.assertIn("/products/stores/", paths)
        self.assertIn("/products/{id}", paths)

    def test_health_endpoint_is_available(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_products_returns_404_when_empty(self):
        self.override_db([])

        response = self.client.get("/products/?search=missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "No se encontraron productos")

    def test_compare_returns_404_when_empty(self):
        self.override_db([])

        response = self.client.get("/products/compare/?query=missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "No se encontraron productos")

    def test_products_rejects_invalid_order_by(self):
        self.override_db([])

        response = self.client.get("/products/?order_by=invalid_column")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "order_by invalido")

    def test_products_rejects_invalid_order_dir(self):
        self.override_db([])

        response = self.client.get("/products/?order_dir=sideways")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "order_dir invalido")

    def test_get_product_by_id_returns_product(self):
        self.override_db([
            (1, "fravega", "RTX 3060 Ti", 499999.0, "ARS", "https://example.com", None)
        ])

        response = self.client.get("/products/1")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["id"], 1)
        self.assertEqual(body["store"], "fravega")

    def test_products_allows_legacy_rows_without_url(self):
        self.override_db([
            (1, "fravega", "RTX 3060 Ti", 499999.0, "ARS", None, None)
        ])

        response = self.client.get("/products/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsNone(body[0]["url"])

    def test_compare_groups_results_by_store(self):
        self.override_db([
            (1, "fravega", "RTX 3060 Ti", 499999.0, "ARS", "https://fravega.com/1", None),
            (2, "mercadolibre", "RTX 3060 Ti MSI", 515000.0, "ARS", "https://ml.com/2", None),
        ])

        response = self.client.get("/products/compare/?query=rtx")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("fravega", body)
        self.assertIn("mercadolibre", body)
        self.assertEqual(body["fravega"][0]["id"], 1)

    def test_stores_returns_summary(self):
        self.override_db([
            ("fravega", 12, None),
            ("mercadolibre", 35, None),
        ])

        response = self.client.get("/products/stores/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 2)
        self.assertEqual(body[0]["store"], "fravega")
        self.assertEqual(body[0]["total"], 12)


if __name__ == "__main__":
    unittest.main()
