# Tests de autenticacion, Alembic y schema SQL

Este documento resume los cambios realizados para fortalecer el sistema de autenticacion y formalizar el manejo del schema de base de datos.

## 1. Tests de autenticacion

Se agrego una suite especifica en `tests/test_auth.py` para cubrir el flujo web de autenticacion basado en JWT y cookies HTTP-only.

### Cobertura agregada

Los tests validan:

- busqueda de usuario por username;
- cierre correcto del cursor en consultas de usuario;
- autenticacion exitosa con password valida;
- rechazo de password invalida;
- rechazo de usuarios inactivos;
- render del formulario de login;
- login exitoso con redirect a `/users/dashboard`;
- creacion de cookie `access_token`;
- atributos de seguridad de la cookie: `HttpOnly`, `Max-Age` y `SameSite=lax`;
- decodificacion del JWT y claim `sub`;
- login invalido sin setear cookie;
- dashboard sin cookie, redirigiendo a login;
- dashboard con token invalido, limpiando cookie y redirigiendo a login;
- dashboard con usuario activo, renderizando la vista protegida;
- dashboard con usuario inexistente, limpiando cookie;
- logout con redirect y eliminacion de cookie.

Tambien se agrego `tests/__init__.py` para que `python -m unittest discover` detecte la suite completa desde la raiz del proyecto.

### Cambios de implementacion necesarios

Se ajusto `api/routers/auth.py` para que el dashboard no abra una conexion a la base de datos antes de validar si existe una sesion.

Antes, FastAPI resolvia la dependencia `db=Depends(get_db)` antes de ejecutar la funcion del endpoint. Eso implicaba que una request sin cookie podia intentar abrir una conexion a la base de datos innecesariamente.

Ahora el flujo es:

1. leer cookie;
2. validar JWT;
3. si no hay usuario valido, redirigir a login sin tocar DB;
4. si hay usuario valido, abrir DB y buscar el usuario;
5. si el usuario no existe o esta inactivo, limpiar cookie y redirigir.

Se agrego `open_db_connection()` en `api/dependencies.py` para reutilizar el mismo manejo de errores de conexion fuera del patron generator de `get_db()`.

Tambien se actualizo `api/security.py` para generar expiraciones JWT con `datetime.now(timezone.utc)` en lugar de `datetime.utcnow()`, evitando warnings de deprecacion y usando fechas UTC timezone-aware.

### Comandos de validacion

```bash
venv\Scripts\python.exe -m unittest tests.test_auth
venv\Scripts\python.exe -m unittest discover
venv\Scripts\python.exe -m compileall api tests
```

Resultado validado:

- `tests.test_auth`: 14 tests OK.
- suite completa: 31 tests OK.
- compilacion de `api` y `tests`: OK.

## 2. Alembic

Se agrego Alembic para versionar cambios de base de datos.

Archivos agregados:

- `alembic.ini`;
- `database/migrations/env.py`;
- `database/migrations/script.py.mako`;
- `database/migrations/versions/0001_initial_schema.py`.

Dependencias agregadas a `requirements.txt`:

- `alembic==1.18.4`;
- `SQLAlchemy==2.0.49`;
- `Mako==1.3.12`;
- `greenlet==3.5.0`.

### Configuracion

Alembic lee `DATABASE_URL` desde el entorno o desde `.env`, usando `python-dotenv`.

El archivo `database/migrations/env.py` tambien normaliza URLs que empiecen con `postgres://` a `postgresql://`, para compatibilidad con algunas plataformas.

El proyecto sigue usando SQL directo con `psycopg2`. Alembic se usa solo para migraciones; no se introdujo ORM en la logica de negocio.

### Migracion inicial

La migracion `0001_initial_schema` crea:

- tabla `products`;
- tabla `users`;
- indices para consultas frecuentes de productos;
- constraints con nombres explicitos.

La tabla `products` incluye:

- `id`;
- `store`;
- `name`;
- `price`;
- `currency`;
- `url`;
- `scraped_at`;
- constraint `uq_products_url`, necesaria para el `ON CONFLICT (url)` usado por el scraper.

La columna `url` se mantiene nullable para conservar compatibilidad con filas legacy que el API ya soporta.

La tabla `users` incluye:

- `id`;
- `username`;
- `password_hash`;
- `is_active`;
- `created_at`;
- constraint `uq_users_username`, necesaria para implementar register correctamente sin duplicados.

### Comandos Alembic

Ver migracion head:

```bash
venv\Scripts\python.exe -m alembic heads
```

Generar SQL sin aplicarlo:

```bash
venv\Scripts\python.exe -m alembic upgrade head --sql
```

Aplicar migraciones en una base vacia:

```bash
venv\Scripts\python.exe -m alembic upgrade head
```

Marcar una base existente como ya migrada:

```bash
venv\Scripts\python.exe -m alembic stamp head
```

Crear una nueva migracion manual:

```bash
venv\Scripts\python.exe -m alembic revision -m "describe change"
```

## 3. schema.sql

Se completo `schema.sql` como snapshot legible del schema esperado.

Este archivo no reemplaza Alembic. Su objetivo es servir como referencia rapida para entender la estructura actual de la base de datos.

La fuente operativa para evolucionar la DB desde ahora debe ser Alembic.

Regla recomendada:

- cambios nuevos de DB: crear nueva migracion Alembic;
- luego actualizar `schema.sql` para que siga reflejando el estado final esperado.

## 4. Supabase

No se aplicaron migraciones reales contra Supabase automaticamente.

Que hacer depende del estado actual de tu base:

- Si la base esta vacia, correr `alembic upgrade head`.
- Si ya creaste manualmente `products` y `users` y coinciden con `schema.sql`, correr `alembic stamp head`.
- Si no estas seguro de si coinciden, comparar primero columnas, tipos, constraints e indices antes de ejecutar `upgrade`.

No conviene correr `upgrade head` sobre una base que ya tiene las tablas, porque la migracion inicial intenta crearlas y podria fallar.

## 5. Estado final

El proyecto ahora tiene:

- tests de autenticacion separados y ejecutables;
- discovery de tests funcionando desde la raiz;
- migraciones Alembic iniciales;
- schema SQL documentado;
- dependencias necesarias fijadas;
- README actualizado con comandos basicos.