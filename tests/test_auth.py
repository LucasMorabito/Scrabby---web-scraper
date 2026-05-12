import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.dependencies import get_db
from api.main import app
from api.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    TOKEN_SECONDS_EXPIRE,
    create_access_token,
    decode_access_token,
)
from api.services.auth import authenticate_user, get_user_by_username
from utils.security import hash_password


USER_COLUMNS = [
    ("id",),
    ("username",),
    ("password_hash",),
    ("is_active",),
    ("created_at",),
]


class FakeAuthCursor:
    def __init__(self, users):
        self.users = users
        self.description = USER_COLUMNS
        self.closed = False
        self.row = None

    def execute(self, query, params=None):
        username = params[0] if params else None
        user = self.users.get(username)
        self.row = self._row_from_user(user) if user else None

    def fetchone(self):
        return self.row

    def close(self):
        self.closed = True

    @staticmethod
    def _row_from_user(user):
        return (
            user["id"],
            user["username"],
            user["password_hash"],
            user["is_active"],
            user.get("created_at"),
        )


class FakeAuthDB:
    def __init__(self, users=None):
        self.users = users or {}
        self.closed = False
        self.cursors = []

    def cursor(self):
        cursor = FakeAuthCursor(self.users)
        self.cursors.append(cursor)
        return cursor

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
            "id": 1,
            "username": username,
            "password_hash": self.password_hash,
            "is_active": True,
            "created_at": None,
        }

    def inactive_user(self, username="alice"):
        user = self.active_user(username)
        user["is_active"] = False
        return user

    def override_auth_db(self, users):
        db = FakeAuthDB(users)

        def _override():
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = _override
        return db

    def test_get_user_by_username_returns_user_dict(self):
        db = FakeAuthDB({"alice": self.active_user()})

        user = get_user_by_username("alice", db)

        self.assertEqual(user["username"], "alice")
        self.assertTrue(user["is_active"])
        self.assertTrue(db.cursors[0].closed)

    def test_get_user_by_username_returns_none_when_missing(self):
        db = FakeAuthDB()

        user = get_user_by_username("missing", db)

        self.assertIsNone(user)
        self.assertTrue(db.cursors[0].closed)

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
        self.assertIn("Login", response.text)
        self.assertIn('action="/users/login"', response.text)

    def test_login_sets_http_only_cookie_and_redirects(self):
        db = self.override_auth_db({"alice": self.active_user()})

        response = self.client.post(
            "/users/login",
            data={"username": "alice", "password": self.valid_password},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/users/dashboard")
        self.assertTrue(db.closed)

        set_cookie = response.headers["set-cookie"]
        self.assertIn(f"{ACCESS_TOKEN_COOKIE_NAME}=", set_cookie)
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn(f"Max-Age={TOKEN_SECONDS_EXPIRE}", set_cookie)
        self.assertIn("SameSite=lax", set_cookie)

        token = response.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
        payload = decode_access_token(token)
        self.assertEqual(payload["sub"], "alice")

    def test_login_rejects_invalid_credentials_without_cookie(self):
        self.override_auth_db({"alice": self.active_user()})

        response = self.client.post(
            "/users/login",
            data={"username": "alice", "password": "wrong-password"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("Usuario o contrasena incorrectos", response.text)
        self.assertNotIn("set-cookie", response.headers)

    def test_login_rejects_inactive_user_without_cookie(self):
        self.override_auth_db({"alice": self.inactive_user()})

        response = self.client.post(
            "/users/login",
            data={"username": "alice", "password": self.valid_password},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("set-cookie", response.headers)

    def test_dashboard_without_cookie_redirects_without_opening_db(self):
        with patch("api.routers.auth.open_db_connection") as mock_open_db:
            response = self.client.get("/users/dashboard", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/users/login")
        self.assertNotIn("set-cookie", response.headers)
        mock_open_db.assert_not_called()

    def test_dashboard_with_invalid_token_redirects_clears_cookie_without_opening_db(self):
        self.client.cookies.set(ACCESS_TOKEN_COOKIE_NAME, "invalid-token")

        with patch("api.routers.auth.open_db_connection") as mock_open_db:
            response = self.client.get("/users/dashboard", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/users/login")
        self.assertIn(f"{ACCESS_TOKEN_COOKIE_NAME}=", response.headers["set-cookie"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])
        mock_open_db.assert_not_called()

    def test_dashboard_renders_for_active_user(self):
        db = FakeAuthDB({"alice": self.active_user()})
        token = create_access_token({"sub": "alice"})
        self.client.cookies.set(ACCESS_TOKEN_COOKIE_NAME, token)

        with patch("api.routers.auth.open_db_connection", return_value=db):
            response = self.client.get("/users/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Bienvenido, alice", response.text)
        self.assertTrue(db.closed)
        self.assertTrue(db.cursors[0].closed)

    def test_dashboard_clears_cookie_when_user_is_missing(self):
        db = FakeAuthDB()
        token = create_access_token({"sub": "missing"})
        self.client.cookies.set(ACCESS_TOKEN_COOKIE_NAME, token)

        with patch("api.routers.auth.open_db_connection", return_value=db):
            response = self.client.get("/users/dashboard", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/users/login")
        self.assertIn(f"{ACCESS_TOKEN_COOKIE_NAME}=", response.headers["set-cookie"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])
        self.assertTrue(db.closed)

    def test_logout_redirects_and_clears_cookie(self):
        self.client.cookies.set(
            ACCESS_TOKEN_COOKIE_NAME,
            create_access_token({"sub": "alice"}),
        )

        response = self.client.post("/users/logout", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/users/login")
        self.assertIn(f"{ACCESS_TOKEN_COOKIE_NAME}=", response.headers["set-cookie"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])


if __name__ == "__main__":
    unittest.main()
