import bcrypt

def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando bcrypt.
    bcrypt requiere bytes, así que codificamos el string, generamos la sal,
    hasheamos, y lo devolvemos como string para guardarlo en la DB.
    """
    # bcrypt.gensalt() genera una "sal" aleatoria única para este hash
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    # Lo decodificamos a string para que la base de datos lo guarde como VARCHAR/TEXT
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica que la contraseña plana coincida con el hash de la base de datos.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except ValueError:
        # ValueError ocurre si hashed_password no tiene el formato válido de bcrypt
        return False