from database.database import SessionLocal

def get_db():
    """
    Generador de dependencias para FastAPI.
    Crea una sesión de SQLAlchemy por cada request y la cierra al finalizar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()