import unittest
from unittest.mock import patch

from database.database import save_products


class FakePersistenceCursor:
    def __init__(self):
        self.executed = []
        self.next_product_id = 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        product_id = self.next_product_id
        self.next_product_id += 1
        return (product_id,)


class FakePersistenceConnection:
    def __init__(self):
        self.cursor_instance = FakePersistenceCursor()
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed = True


class DatabasePersistenceTests(unittest.TestCase):
    @patch("database.database.get_connection")
    def test_save_products_records_price_history_for_valid_products(self, mock_connection):
        conn = FakePersistenceConnection()
        mock_connection.return_value = conn

        inserted = save_products([
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

        self.assertEqual(inserted, 2)
        product_writes = [
            query for query, _params in conn.cursor_instance.executed
            if "INSERT INTO products" in query
        ]
        history_writes = [
            query for query, _params in conn.cursor_instance.executed
            if "INSERT INTO price_history" in query
        ]
        self.assertEqual(len(product_writes), 2)
        self.assertEqual(len(history_writes), 2)
        self.assertTrue(conn.closed)

    @patch("database.database.get_connection")
    def test_save_products_skips_invalid_products_without_history(self, mock_connection):
        conn = FakePersistenceConnection()
        mock_connection.return_value = conn

        inserted = save_products([
            {
                "store": "mercadolibre",
                "name": "",
                "price": 550000,
                "currency": "ARS",
                "url": "https://example.com/rtx",
            },
            {
                "store": "mercadolibre",
                "name": "RTX 3060 Ti",
                "price": None,
                "currency": "ARS",
                "url": "https://example.com/rtx",
            },
        ])

        self.assertEqual(inserted, 0)
        self.assertEqual(conn.cursor_instance.executed, [])
        self.assertTrue(conn.closed)


if __name__ == "__main__":
    unittest.main()
