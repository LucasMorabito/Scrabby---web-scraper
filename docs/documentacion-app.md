# Documentacion tecnica de Scrabby

## 1. Descripcion general del sistema

### Proposito del proyecto

Scrabby es un sistema backend desarrollado en Python para obtener, almacenar y exponer informacion de precios de componentes de PC en tiendas argentinas. El proyecto combina un pipeline de scraping con una API construida en FastAPI. La API permite consultar productos persistidos en PostgreSQL y, en el estado actual del codigo, tambien incluye un flujo de login con JWT almacenado en cookie HTTP-only.

### Problema que resuelve

El sistema resuelve la necesidad de consultar y comparar precios de productos, especialmente placas de video, provenientes de diferentes tiendas. Actualmente obtiene datos desde Fravega y Mercado Libre, normaliza los resultados, filtra productos no relevantes, guarda una copia local en JSON y persiste los productos en una base PostgreSQL. Luego expone esos datos mediante endpoints REST.

### Alcance actual

El alcance actual incluye scraping, persistencia de productos, consultas REST sobre productos, resumen por tienda, comparacion por busqueda, obtencion del producto mas barato por tienda, login web con formulario HTML, generacion de JWT, almacenamiento del token en cookie HTTP-only, validacion de sesion para acceder al dashboard y logout. No se detectan endpoints de registro de usuarios, administracion de usuarios, refresh tokens, migraciones de base de datos ni pruebas automatizadas para autenticacion.

## 2. Arquitectura

### Organizacion del proyecto

El proyecto esta organizado en modulos con responsabilidades diferenciadas:

`api/main.py` crea la aplicacion FastAPI, define el health check y registra los routers de productos y usuarios.

`api/routers/products.py` contiene los endpoints REST de productos. Construye consultas SQL, valida parametros de ordenamiento, ejecuta queries contra PostgreSQL y devuelve respuestas modeladas con Pydantic.

`api/routers/auth.py` contiene las rutas web de autenticacion. Renderiza templates Jinja2, procesa el formulario de login, crea la cookie de sesion, protege el dashboard y ejecuta logout.

`api/services/auth.py` contiene la logica de autenticacion vinculada a base de datos. Busca usuarios por `username`, verifica si estan activos y valida la password usando el hash almacenado.

`api/security.py` centraliza la configuracion JWT. Define el nombre de la cookie, lee variables de entorno, genera tokens, decodifica tokens y obtiene el username desde la cookie.

`utils/security.py` contiene utilidades de seguridad relacionadas con passwords: hashing y verificacion con bcrypt mediante Passlib.

`api/schemas/` contiene modelos Pydantic usados para respuestas y estructuras de autenticacion.

`api/dependencies.py` define la dependencia `get_db`, que abre una conexion PostgreSQL por request y la cierra al finalizar.

`database/database.py` contiene la persistencia del pipeline de scraping, incluyendo la insercion y actualizacion de productos con `ON CONFLICT`.

`scrappers/` contiene los scrapers de Fravega y Mercado Libre.

`api/templates/` contiene templates HTML para login y dashboard.

`api/static/` existe como carpeta para archivos estaticos, aunque actualmente no se detecta montaje de `StaticFiles` en `api/main.py`.

`tests/` contiene pruebas automatizadas sobre la API de productos y health check.

### Responsabilidad de cada capa

La capa de routers recibe requests HTTP, valida parametros simples, delega acceso a datos mediante dependencias o servicios y construye respuestas HTTP. En productos, el router contiene directamente las consultas SQL. En autenticacion, el router delega la verificacion de credenciales en `api/services/auth.py` y la generacion/lectura de tokens en `api/security.py`.

La capa de services concentra reglas de negocio especificas de autenticacion. `authenticate_user` valida existencia del usuario, estado activo y password. Esta capa no devuelve respuestas HTTP; devuelve el usuario o `None`.

La capa de schemas define contratos de datos. `ProductResponse` y `StoreResponse` se usan como `response_model` en la API de productos. `TokenResponse`, `TokenData`, `UserLogin` y `UserInDB` existen como modelos de autenticacion, aunque el login actual devuelve una redireccion con cookie y no usa `TokenResponse` como `response_model`.

La capa de seguridad esta dividida entre JWT y password. `api/security.py` maneja tokens y cookies. `utils/security.py` maneja hashes de password.

La capa de persistencia del scraper esta en `database/database.py`, separada de la API REST. Usa `psycopg2` y SQL directo.

### Flujo de datos dentro del sistema

En el flujo de scraping, `main.py` define la busqueda fija `rtx 3060 ti`, ejecuta los scrapers de Fravega y Mercado Libre, concatena resultados, aplica filtros por precio y palabras bloqueadas, ordena por precio, guarda un archivo `data/products.json` y persiste los datos mediante `save_products`.

En el flujo REST de productos, FastAPI recibe la request, inyecta una conexion con `get_db`, el router ejecuta SQL contra la tabla `products`, convierte filas a diccionarios con `_fetch_as_dicts` y Pydantic valida la forma de salida.

En el flujo de autenticacion, el navegador envia el formulario `POST /users/login`, el router llama a `authenticate_user`, el service consulta la tabla `users` y verifica el password hash. Si las credenciales son validas, se crea un JWT con claim `sub`, se guarda en la cookie `access_token` y se redirige al dashboard. Para acceder a `/users/dashboard`, el router lee el username desde la cookie, consulta la DB para confirmar que el usuario exista y este activo, y renderiza el template.

## 3. Stack tecnologico

El backend usa Python como lenguaje principal. La version declarada en `.python-version` es 3.12, Render configura `PYTHON_VERSION=3.12.13` y el `Dockerfile` usa `python:3.11-slim`.

FastAPI se usa para crear la aplicacion web, definir routers, manejar dependencias y generar documentacion OpenAPI automatica.

Uvicorn se usa como servidor ASGI en la configuracion de Render.

Pydantic se usa para definir modelos de respuesta y estructuras de datos.

PostgreSQL es la base de datos relacional. El acceso se realiza con `psycopg2-binary` y SQL directo.

python-dotenv carga variables desde `.env` en entorno local.

Requests se usa para consumir sitios externos durante el scraping.

BeautifulSoup se usa para parsear HTML de Mercado Libre.

Jinja2 se usa para renderizar templates HTML.

python-jose se usa para codificar y decodificar JWT.

Passlib con bcrypt se usa para hashear y verificar passwords.

python-multipart permite que FastAPI procese formularios `Form`.

unittest y `fastapi.testclient.TestClient` se usan en la suite de pruebas actual.

Docker y Render estan presentes como mecanismos de despliegue/configuracion.

## 4. Base de datos

### Conexion

La conexion se configura mediante la variable de entorno `DATABASE_URL`. La API abre conexiones en `api/dependencies.py` usando `psycopg2.connect(os.getenv("DATABASE_URL"))`. El pipeline de scraping usa una funcion similar en `database/database.py`.

No se detectan migraciones ni scripts `CREATE TABLE` en el repositorio. Las tablas documentadas a continuacion fueron detectadas en la base PostgreSQL configurada.

### Tabla `products`

La tabla `products` almacena productos obtenidos por scraping.

| Campo | Tipo PostgreSQL | Nulable | Default | Uso en codigo |
| --- | --- | --- | --- | --- |
| `id` | integer | NO | `nextval('products_id_seq'::regclass)` | Identificador primario. |
| `store` | character varying | NO | None | Tienda de origen, por ejemplo `fravega` o `mercadolibre`. |
| `name` | text | NO | None | Nombre del producto. |
| `price` | numeric | NO | None | Precio usado para ordenar y comparar. |
| `currency` | character varying | YES | `'ARS'` | Moneda del precio. |
| `url` | text | YES | None | URL del producto; tiene constraint unico. |
| `scraped_at` | timestamp without time zone | YES | `now()` | Fecha de scraping/actualizacion. |

Constraints detectadas: primary key `products_pkey` sobre `id` y unique `products_url_key` sobre `url`.

### Tabla `users`

La tabla `users` almacena usuarios del sistema de autenticacion.

| Campo | Tipo PostgreSQL | Nulable | Default | Uso en codigo |
| --- | --- | --- | --- | --- |
| `id` | integer | NO | `nextval('users_id_seq'::regclass)` | Identificador primario. |
| `username` | character varying | NO | None | Nombre de usuario usado para login y claim `sub` del JWT. |
| `password_hash` | text | NO | None | Hash bcrypt de la password. |
| `is_active` | boolean | YES | `true` | Controla si el usuario puede autenticarse y acceder al dashboard. |
| `created_at` | timestamp without time zone | YES | `now()` | Fecha de creacion. |

Constraints detectadas: primary key `users_pkey` sobre `id` y unique `users_username_key` sobre `username`.

### Logica de persistencia

`database/database.py` implementa `save_products(products: list[dict]) -> int`. Si la lista esta vacia devuelve `0`. Para cada producto ejecuta:

```sql
INSERT INTO products (store, name, price, currency, url)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (url)
DO UPDATE SET
    price = EXCLUDED.price,
    scraped_at = NOW()
```

La logica usa `url` como clave de deduplicacion. Si ya existe un producto con la misma URL, actualiza precio y timestamp. La funcion incrementa el contador `inserted` por cada producto procesado, aunque el nombre puede inducir a pensar que solo cuenta inserciones nuevas; en realidad tambien cuenta actualizaciones ejecutadas.

## 5. API REST

### `GET /health`

Endpoint definido en `api/main.py`. Devuelve el estado basico de la aplicacion.

Respuesta esperada:

```json
{"status": "ok"}
```

### `GET /products/`

Devuelve una lista de productos.

Parametros de query:

| Parametro | Tipo | Default | Descripcion |
| --- | --- | --- | --- |
| `search` | string opcional | `None` | Filtra por coincidencia parcial en `name` usando `ILIKE`. |
| `store` | string opcional | `None` | Filtra por tienda exacta. |
| `limit` | int | `20` | Limite de filas. |
| `offset` | int | `0` | Desplazamiento para paginacion. |
| `order_by` | string | `price` | Campo de orden. Solo admite `price`, `name`, `scraped_at`. |
| `order_dir` | string | `asc` | Direccion de orden. Solo admite `asc` o `desc`. |

Respuesta exitosa: lista de `ProductResponse`.

Errores implementados: `400` si `order_by` u `order_dir` son invalidos; `404` si no hay productos.

### `GET /products/compare/`

Compara productos por busqueda y agrupa resultados por tienda.

Parametro requerido: `query`, usado en `WHERE name ILIKE %s`.

Respuesta exitosa: diccionario donde cada clave es una tienda y cada valor es una lista de productos.

Error implementado: `404` si no se encuentran productos.

### `GET /products/stores/`

Devuelve un resumen por tienda.

Consulta ejecutada:

```sql
SELECT store, COUNT(*) as total, MAX(scraped_at) as last_scraped
FROM products
GROUP BY store
```

Respuesta exitosa: lista de `StoreResponse`, con `store`, `total` y `last_scraped`.

### `GET /products/cheapest/`

Devuelve el producto mas barato por tienda.

Usa `DISTINCT ON (store)`, una caracteristica especifica de PostgreSQL:

```sql
SELECT DISTINCT ON (store) id, store, name, price, currency, url, scraped_at
FROM products
ORDER BY store, price ASC
```

Respuesta exitosa: lista de `ProductResponse`.

### `GET /products/{id}`

Devuelve un producto por identificador.

Parametro de ruta: `id` como entero.

Respuesta exitosa: un `ProductResponse`.

Error implementado: `404` con detalle `Producto no encontrado` si no hay coincidencias.

### `GET /users/login`

Renderiza el formulario HTML de login usando `api/templates/login.html`.

Respuesta exitosa: HTML.

### `POST /users/login`

Procesa el formulario de login.

Campos de formulario:

| Campo | Tipo | Descripcion |
| --- | --- | --- |
| `username` | string | Nombre de usuario. |
| `password` | string | Password en texto plano enviada por el formulario. |

Si las credenciales son invalidas, devuelve `login.html` con status `401` y el mensaje `Usuario o contrasena incorrectos`.

Si las credenciales son validas, crea un JWT con `sub=<username>`, lo guarda en cookie HTTP-only `access_token` y redirige con status `303` a `/users/dashboard`.

### `GET /users/dashboard`

Renderiza el dashboard HTML protegido.

Entrada: cookie `access_token`.

Si la cookie no existe, el token es invalido o el payload no contiene `sub`, redirige a `/users/login` con status `303`. Si el token contiene un usuario inexistente o inactivo, tambien redirige a login y borra la cookie. Si la sesion es valida, renderiza `dashboard.html` con el `username`.

### `POST /users/logout`

Cierra la sesion. Redirige a `/users/login` con status `303` y elimina la cookie `access_token`.

### Documentacion automatica

FastAPI expone automaticamente `/docs`, `/redoc` y `/openapi.json`. Los tests actuales verifican disponibilidad de `/docs` y `/openapi.json`.

## 6. Sistema de autenticacion

### Flujo de login implementado

El login se implementa como flujo web con templates y cookie, no como API Bearer pura. El usuario accede a `/users/login`, envia el formulario por `POST`, el backend valida credenciales en PostgreSQL y, si son correctas, genera un JWT.

El JWT se setea en la cookie `access_token` con las propiedades:

`httponly=True`, lo que impide acceso directo desde JavaScript.

`max_age=TOKEN_SECONDS_EXPIRE`, usando la configuracion de expiracion del token.

`samesite="lax"`, reduciendo exposicion a ciertos escenarios cross-site.

No se detecta `secure=True`, por lo que la cookie puede funcionar en HTTP local. En produccion HTTPS deberia evaluarse habilitar `secure=True`.

### Hashing de contrasenas

`utils/security.py` configura:

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

`hash_password` genera hashes bcrypt. `verify_password` compara la password plana contra el hash almacenado. Si el hash no puede identificarse, captura `UnknownHashError` y devuelve `False` para evitar un error 500.

La tabla `users` espera que `password_hash` ya contenga un hash compatible. No existe endpoint de registro ni creacion de usuarios en el codigo actual.

### Generacion y validacion de JWT

`api/security.py` carga:

`SECRET_KEY`, obligatorio. Si falta, la aplicacion lanza `RuntimeError("SECRET_KEY is not configured")`.

`ALGORITHM`, con default `HS256`.

`TOKEN_SECONDS_EXPIRE`, con default `900`.

`create_access_token(data)` copia el payload recibido, agrega `exp` con `datetime.utcnow() + timedelta(seconds=TOKEN_SECONDS_EXPIRE)` y firma el token con `python-jose`.

`decode_access_token(token)` intenta decodificar el JWT. Si `python-jose` lanza `JWTError`, devuelve `None`.

`get_current_username(request)` lee la cookie `access_token`, decodifica el JWT y devuelve el claim `sub`. Si falta la cookie, el token es invalido o falta `sub`, devuelve `None`.

### Uso del payload

El payload actual usa el claim `sub` para guardar el username:

```python
token = create_access_token({"sub": user["username"]})
```

El dashboard usa ese `sub` para buscar nuevamente al usuario en base de datos y validar que exista y este activo.

## 7. Manejo de errores

El manejo de errores combina `HTTPException`, respuestas HTML con status especifico y redirecciones.

En productos se usan `HTTPException`:

`400` para parametros de ordenamiento invalidos.

`404` cuando una busqueda no devuelve productos o cuando no existe el producto por id.

En autenticacion, el login invalido devuelve `TemplateResponse` con status `401` en lugar de `HTTPException`, porque el flujo es HTML y debe volver a renderizar el formulario con un mensaje.

El dashboard no autenticado no devuelve `401`; redirige con `303` a `/users/login`. Si el token apunta a un usuario inexistente o inactivo, tambien redirige y borra la cookie.

En scraping, `main.py` captura excepciones de Fravega y Mercado Libre por separado, imprime el error y continua con lista vacia. `save_to_json` tambien captura excepciones al escribir el archivo.

Las conexiones y cursores de DB se cierran con bloques `finally` o context managers.

## 8. Renderizado de templates y archivos estaticos

El proyecto usa `Jinja2Templates(directory="api/templates")` en `api/routers/auth.py`.

Templates detectados:

`login.html` contiene el formulario de login y renderiza un mensaje si existe la variable `error`.

`dashboard.html` muestra `Dashboard`, un saludo con `{{ username }}` y un formulario POST para logout.

`base.html` existe, pero actualmente esta vacio.

La carpeta `api/static/css/auth.css` existe, pero el archivo esta vacio. No se detecta en `api/main.py` el montaje de archivos estaticos con `StaticFiles`, ni enlaces CSS desde los templates actuales.

## 9. Deploy

### Render

`render.yaml` configura un servicio web llamado `scrabby-api`.

Configuracion detectada:

`runtime: python`.

`buildCommand: pip install -r requirements.txt`.

`startCommand: uvicorn api.main:app --host 0.0.0.0 --port $PORT`.

`healthCheckPath: /health`.

`autoDeployTrigger: commit`.

Variables configuradas en Render: `PYTHON_VERSION=3.12.13` y `DATABASE_URL` con `sync: false`.

El codigo tambien requiere `SECRET_KEY` para arrancar correctamente. `ALGORITHM` y `TOKEN_SECONDS_EXPIRE` tienen defaults, pero pueden configurarse por entorno.

### Docker

`Dockerfile` usa `python:3.11-slim`, instala dependencias y ejecuta:

```dockerfile
CMD ["python", "main.py"]
```

Ese comando ejecuta el pipeline de scraping, no la API FastAPI. Para correr la API en Docker, el comando deberia alinearse con el start command de Render o exponerse explicitamente con Uvicorn.

### Archivos ignorados

`.gitignore` excluye `.env`, `__pycache__/`, `venv/` y `data/`.

`.dockerignore` excluye `.env`, `venv/`, `__pycache__/`, `.git/` y `data/`.

## 10. Testing

La suite actual esta en `tests/test_api.py` y usa `unittest` con `fastapi.testclient.TestClient`.

Para evitar depender de la base real, los tests sobrescriben la dependencia `get_db` con una DB falsa (`FakeDB`) y un cursor falso (`FakeCursor`). Esto permite probar los endpoints de productos sin conectarse a PostgreSQL.

Cobertura funcional actual:

Disponibilidad de `/docs` y `/openapi.json`.

Disponibilidad de `/health`.

Respuesta `404` cuando `/products/` no devuelve resultados.

Respuesta `404` cuando `/products/compare/` no devuelve resultados.

Validacion de `order_by` invalido con `400`.

Validacion de `order_dir` invalido con `400`.

Obtencion de producto por id.

Agrupacion de comparacion por tienda.

Resumen de tiendas.

Ejecucion verificada en el workspace:

```text
Ran 9 tests in 0.055s
OK
```

No se detectan tests automatizados para login, JWT, cookies, dashboard, logout, scrapers ni persistencia `save_products`.

## 11. Posibles mejoras tecnicas

La base de datos deberia tener migraciones versionadas. Actualmente el repositorio consume tablas existentes, pero no define formalmente su creacion. Alembic u otra herramienta permitiria reproducir ambientes y revisar cambios de esquema.

La configuracion podria centralizarse con `pydantic-settings`, especialmente `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `TOKEN_SECONDS_EXPIRE` y flags de entorno como `COOKIE_SECURE`. Esto evitaria lecturas dispersas de `os.getenv`.

La API podria usar un pool de conexiones o una capa de acceso a datos mas consistente. Actualmente se abre una conexion por request y los routers contienen SQL directo. Para un proyecto pequeno esto funciona, pero a medida que crezca convendria extraer repositorios o servicios de consulta.

El login deberia contar con tests automatizados. Los casos minimos son login exitoso, login invalido, dashboard sin cookie, dashboard con cookie valida, usuario inactivo y logout.

El sistema de autenticacion no tiene endpoint de registro ni comando documentado para crear usuarios. Para evitar passwords planas, deberia existir un flujo controlado que use `hash_password`.

En produccion, la cookie de autenticacion deberia evaluarse con `secure=True` bajo HTTPS. Tambien podria agregarse proteccion CSRF para formularios POST, ya que se usa cookie para autenticacion.

El dashboard redirige correctamente ante sesion invalida, pero no registra eventos ni intentos fallidos. Agregar logging estructurado ayudaria al diagnostico.

Los parametros `limit` y `offset` no tienen validaciones de minimo o maximo. Se podria restringir `limit` para evitar consultas grandes.

La respuesta `404` para listas vacias en productos es una decision implementada actualmente. Otra opcion comun en APIs REST es devolver `200` con lista vacia, lo cual podria simplificar clientes si ese comportamiento se desea.

El archivo `api/static/css/auth.css` esta vacio y no se monta `StaticFiles`. Si se desea estilizar login/dashboard, habria que montar estaticos en `api/main.py` y enlazar CSS desde los templates.

El `Dockerfile` ejecuta el scraper con `python main.py`, mientras que Render ejecuta la API con Uvicorn. Conviene decidir si la imagen Docker representa el scraper, la API o ambos, y ajustar el comando.

Los textos de algunos archivos muestran problemas de codificacion historicos en comentarios o mensajes. Conviene normalizar archivos fuente a UTF-8 y evitar mojibake antes de documentar o distribuir el proyecto.

La persistencia `save_products` devuelve cantidad de productos procesados, no necesariamente inserciones nuevas. Renombrar la variable o documentar ese comportamiento evitaria ambiguedad.

La seguridad de JWT podria extenderse con rotacion de secreto, expiraciones por entorno, refresh tokens si el producto lo requiere y invalidacion de sesiones. Actualmente la validacion se apoya en expiracion del token y verificacion del usuario activo en DB.
