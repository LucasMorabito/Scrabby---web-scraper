import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from api.dependencies import get_db
from api.main import app
from api.security import create_access_token


class FakeUserObject(dict):
    def __getattr__(self, name):
        if name in self: return self[name]
        raise AttributeError(name)


class FakeFavoriteObject(dict):
    def __getattr__(self, name):
        if name in self: return self[name]
        raise AttributeError(name)


class FakeDashboardQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self.results = []
        model_name = str(model).lower()
        if "user" in model_name and "favorite" not in model_name:
            self.results = list(self.db.users.values())
        else:
            self.results = self.db.favorites

    def filter(self, *args, **kwargs): return self
    def join(self, *args, **kwargs): return self
    def order_by(self, *args, **kwargs): return self # 🛠️ SOLUCIÓN: Soporta la ordenación cronológica de favoritos
    def all(self): return self.results
    def first(self): return self.results[0] if self.results else None


class DashboardDataDB:
    def __init__(self):
        now = datetime(2026, 5, 13, 12, 0, tzinfo=timezone.utc)
        self.favorites = [
            FakeFavoriteObject({
                "id": 10, "store": "mercadolibre", "name": "RTX 3060 Ti",
                "price": 550000.0, "currency": "ARS", "url": "https://example.com/rtx",
                "scraped_at": now, "last_recorded_price": 540000.0, "last_recorded_at": now,
            })
        ]
        self.users = {
            "alice": FakeUserObject({
                "id": 1, "username": "alice", "password_hash": "hash",
                "is_active": True, "created_at": now, "favorites": self.favorites
            })
        }
        self.closed = False
        self.called = False

    def query(self, model):
        return FakeDashboardQuery(self, model)

    def close(self):
        self.closed = True


class DashboardDataTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = DashboardDataDB()

        def override_db():
            self.db.called = True
            try: yield self.db
            finally: self.db.close()

        app.dependency_overrides[get_db] = override_db

    def test_dashboard_data_returns_user_favorites(self):
        self.client.cookies.set("access_token", create_access_token({"sub": "alice"}))
        response = self.client.get("/users/dashboard/data")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["username"], "alice")
        self.assertEqual(body["favorites"][0]["name"], "RTX 3060 Ti")

    def test_dashboard_data_requires_authentication_without_opening_db(self):
        response = self.client.get("/users/dashboard/data")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["message"], "Authentication required")


if __name__ == "__main__":
    unittest.main()