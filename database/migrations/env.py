import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

config = context.config

# Configura los logs de Alembic según el archivo .ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Carga las variables de entorno
load_dotenv()

# Al estar en None, le decimos a Alembic que NO use autogeneración de modelos ORM.
# Las migraciones se escribirán con SQL crudo (op.execute).
target_metadata = None


def get_database_url() -> str:
    """Obtiene y formatea la URL de la base de datos para que sea compatible con SQLAlchemy."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is required to run migrations")

    # Parche crítico para compatibilidad con plataformas en la nube (Render/Heroku)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return database_url


def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline'.
    Esto configura el contexto solo con una URL y no crea un Engine.
    Emite comandos SQL crudos a la salida estándar en lugar de a una DB.
    """
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online'.
    En este escenario necesitamos crear un Engine y asociar una conexión al contexto.
    """
    configuration = config.get_section(config.config_ini_section, {})
    
    # Sobrescribimos dinámicamente la URL del .ini con nuestra variable de entorno segura
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()