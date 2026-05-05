from utils.security import verify_password


def get_user_by_username(username: str, db):
    cur = db.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = cur.fetchone()

        if not row:
            return None

        columns = [desc[0] for desc in cur.description]
        user = dict(zip(columns, row))

        return user
    finally:
        cur.close()


def authenticate_user(username: str, password: str, db):
    user = get_user_by_username(username, db)

    if not user:
        return None

    if not user["is_active"]:
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return user
