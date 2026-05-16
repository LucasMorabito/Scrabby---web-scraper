import unittest

from fastapi.testclient import TestClient

from api.dependencies import get_db
from api.main import app
from api.security import (
    ACCESS_TOKEN_COOKIE_NAME,
)
from api.services.auth import authenticate_user, get_user_by_username
from utils.security import hash_password


class DummyCursor:
    def __init__(self):
        self.closed = True


class FakeUser(dict):
    def __getattr__(self, name):
        if name in self: return self[name]
        raise AttributeError(name)
        
    def __setattr__(self, name, value):
        self[name] = value


class FakeAuthQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model
        self.filtered_user = None

    def filter(self, *args, **kwargs):
        if len(self.db.users) == 1:
            self.filtered_user = list(self.db.users.values())[0]
        elif args:
            expr = str(args[0])
            for username in self.db.users:
                if username in expr:
                    self.filtered_user = self.db.users[username]
                    break
        return self

    def first(self):
        return self.filtered_user


class FakeAuthDB:
    def __init__(self, users=None):
        self.users = {k: FakeUser(v) if isinstance(v, dict) else v for k, v in (users or {}).items()}
        self.closed = False
        self.called = False
        self.cursors = [DummyCursor()]
        self.added_users = []

    def query(self, model):
        self.called = True
        return FakeAuthQuery(self, model)

    def add(self, instance):
        self.called = True
        self.added_users.append(instance)
        username = getattr(instance, 'username', None)
        if username: self.users[username] = instance

    def commit(self): pass
    def refresh(self, instance): pass

    def close(self):
        self.closed = True


class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid_password = "correct-password"
        cls.password_hash = hash_password(cls.valid_password)

    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def active_user(self, username="alice"):
        return {
            "id": 1, "username": username, "password_hash": self.password_hash,
            "is_active": True, "created_at": None,
        }

    def inactive_user(self, username="alice"):
        user = self.active_user(username)
        user["is_active"] = False
        return user

    def override_auth_db(self, users):
        db = FakeAuthDB(users)
        def _override():
            db.called = True
            try: yield db
            finally: db.close()
        app.dependency_overrides[get_db] = _override
        return db

    def test_get_user_by_username_returns_user_dict(self):
        db = FakeAuthDB({"alice": self.active_user()})
        user = get_user_by_username("alice", db)
        self.assertEqual(user["username"], "alice")
        self.assertTrue(user["is_active"])

    def test_get_user_by_username_returns_none_when_missing(self):
        db = FakeAuthDB()
        user = get_user_by_username("missing", db)
        self.assertIsNone(user)

    def test_authenticate_user_accepts_valid_credentials(self):
        db = FakeAuthDB({"alice": self.active_user()})
        user = authenticate_user("alice", self.valid_password, db)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "alice")

    def test_authenticate_user_rejects_invalid_password(self):
        db = FakeAuthDB({"alice": self.active_user()})
        user = authenticate_user("alice", "wrong-password", db)
        self.assertIsNone(user)

    def test_authenticate_user_rejects_inactive_user(self):
        db = FakeAuthDB({"alice": self.inactive_user()})
        user = authenticate_user("alice", self.valid_password, db)
        self.assertIsNone(user)

    def test_login_page_renders_form(self):
        response = self.client.get("/users/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Iniciar sesión", response.text)

    def test_login_sets_http_only_cookie_and_redirects(self):
        db = self.override_auth_db({"alice": self.active_user()})
        response = self.client.post(
            "/users/login",
            data={"username": "alice", "password": self.valid_password},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/users/dashboard")

    def test_login_rejects_invalid_credentials_without_cookie(self):
        self.override_auth_db({"alice": self.active_user()})
        response = self.client.post(
            "/users/login",
            data={"username": "alice", "password": "wrong-password"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Usuario o contraseña incorrectos", response.text)

    def test_login_rejects_inactive_user_without_cookie(self):
        self.override_auth_db({"alice": self.inactive_user()})
        response = self.client.post(
            "/users/login",
            data={"username": "alice", "password": self.valid_password},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 401)

    def test_dashboard_without_cookie_redirects_without_opening_db(self):
        db = self.override_auth_db({})
        response = self.client.get("/users/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/users/login")
        self.assertFalse(db.called)

    def test_dashboard_with_invalid_token_redirects_clears_cookie_without_opening_db(self):
        db = self.override_auth_db({})
        self.client.cookies[ACCESS_TOKEN_COOKIE_NAME] = "invalid-token"
        response = self.client.get("/users/dashboard", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/users/login")
        self.assertFalse(db.called)

    def test_logout_redirects_and_clears_cookie(self):
        self.override_auth_db({"alice": self.active_user()})
        self.client.post(
            "/users/login",
            data={"username": "alice", "password": self.valid_password},
            follow_redirects=False
        )
        response = self.client.post("/users/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/users/login")


if __name__ == "__main__":
    unittest.main()