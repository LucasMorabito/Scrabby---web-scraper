import unittest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from fastapi.testclient import TestClient

from api.dependencies import get_db
from api.main import app
from utils.security import verify_password


class FakeUser(dict):
    def __getattr__(self, name):
        if name in self: return self[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


class FakeRegisterQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self.filtered_user = None

    def filter(self, *args, **kwargs):
        if args:
            expr = str(args[0])
            for username in self.db.users:
                if username in expr:
                    self.filtered_user = self.db.users[username]
                    break
        return self

    def first(self):
        return self.filtered_user


class RegisterDB:
    def __init__(self):
        self.users = {}
        self.next_id = 1
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
        self._pending_user = None

    def query(self, model):
        return FakeRegisterQuery(self, model)

    def add(self, instance):
        username = getattr(instance, "username", None)
        password_hash = getattr(instance, "password_hash", None)
        self._pending_user = FakeUser({
            "id": self.next_id, "username": username, "password_hash": password_hash,
            "is_active": True, "created_at": datetime(2026, 5, 13, tzinfo=timezone.utc),
        })

    def commit(self):
        if self._pending_user:
            username = self._pending_user["username"]
            if username in self.users:
                raise IntegrityError("mock statement", "mock params", "orig exception")
            
            self.users[username] = self._pending_user
            self.next_id += 1
            self._pending_user = None
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1
        self._pending_user = None

    def refresh(self, instance):
        if self._pending_user:
            for k, v in self._pending_user.items():
                setattr(instance, k, v)

    def close(self):
        self.closed = True


class TestRegister(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db = RegisterDB()

        def override_db():
            try: yield self.db
            finally: self.db.close()

        app.dependency_overrides[get_db] = override_db

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_register_happy_path_creates_user_with_hashed_password(self):
        response = self.client.post(
            "/users/register",
            data={"username": "new_user", "password": "secure-password", "confirm_password": "secure-password"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/users/login")
        self.assertTrue(verify_password("secure-password", self.db.users["new_user"]["password_hash"]))
        self.assertEqual(self.db.commits, 1)

    def test_register_duplicate_username_returns_400(self):
        payload = {"username": "new_user", "password": "secure-password", "confirm_password": "secure-password"}
        self.client.post("/users/register", data=payload, follow_redirects=False)
        duplicate_response = self.client.post("/users/register", data=payload, follow_redirects=False)

        self.assertEqual(duplicate_response.status_code, 400)
        self.assertIn("El nombre de usuario ya se encuentra registrado.", duplicate_response.text)
        self.assertEqual(self.db.commits, 1)
        self.assertGreaterEqual(self.db.rollbacks, 1)


if __name__ == "__main__":
    unittest.main()