# Documentación técnica de Scrabby

## 1. Descripción general del sistema

### Introducción

Scrabby es un sistema backend desarrollado en Python que implementa un pipeline completo de scraping, procesamiento y exposición de datos de precios de hardware en tiempo casi real.

El sistema integra múltiples fuentes de e-commerce, normaliza la información obtenida y la expone mediante una API REST, permitiendo consultas, comparaciones y análisis de precios entre distintas tiendas.

Además, incorpora un sistema de autenticación basado en JWT con manejo de sesión mediante cookies HTTP-only, orientado a un flujo web simple.

Este proyecto fue desarrollado como parte de un proceso de formación en backend, con foco en aplicar prácticas reales de la industria como diseño modular, validación de datos, manejo de autenticación y despliegue.

---

### Problema que resuelve

El sistema aborda la necesidad de centralizar y comparar precios de productos (principalmente GPUs) provenientes de distintas tiendas online.

Actualmente obtiene datos desde Frávega y Mercado Libre, los normaliza, filtra resultados irrelevantes (como accesorios o precios inconsistentes), y los pone a disposición mediante una API.

---

### Alcance actual

Actualmente, el sistema permite:

- Ejecutar un pipeline de scraping automatizado
- Persistir productos en PostgreSQL
- Consultar productos mediante endpoints REST
- Filtrar, ordenar y paginar resultados
- Comparar precios entre tiendas
- Obtener resúmenes agregados por store
- Identificar el producto más barato por tienda
- Autenticarse mediante login web
- Generar y validar JWT
- Gestionar sesión mediante cookies HTTP-only
- Acceder a un dashboard protegido

No se incluyen aún:
- Registro de usuarios
- Refresh tokens
- Migraciones de base de datos
- Observabilidad avanzada
- Testing completo del sistema de autenticación

---

## 2. Arquitectura

### Organización del proyecto

El sistema está estructurado en módulos con responsabilidades claras:

- `api/main.py`: inicializa la aplicación FastAPI, registra routers y define el health check.
- `api/routers/products.py`: endpoints REST de productos, incluyendo lógica de consulta SQL.
- `api/routers/auth.py`: endpoints web de autenticación y renderizado de templates.
- `api/services/auth.py`: lógica de negocio de autenticación (validación de usuario y password).
- `api/security.py`: manejo de JWT, cookies y configuración de seguridad.
- `utils/security.py`: hashing y verificación de contraseñas con bcrypt.
- `api/schemas/`: modelos Pydantic para validación y serialización.
- `api/dependencies.py`: manejo de conexión a base de datos por request.
- `database/database.py`: persistencia del pipeline de scraping.
- `scrappers/`: scrapers de fuentes externas.
- `api/templates/`: vistas HTML (login y dashboard).
- `api/static/`: archivos estáticos (actualmente no utilizados).
- `tests/`: pruebas automatizadas de la API.

---

### Flujo del sistema

El flujo principal se divide en tres partes:

#### 1. Scraping
- Se consultan fuentes externas
- Se parsean y normalizan los datos
- Se filtran resultados irrelevantes
- Se guardan en JSON y PostgreSQL

#### 2. API
- FastAPI recibe requests
- Se inyecta conexión a DB
- Se ejecutan queries SQL
- Se transforman resultados a dict
- Pydantic valida la respuesta

#### 3. Autenticación
- Usuario envía formulario de login
- Se valida contra la base de datos
- Se genera JWT con claim `sub`
- Se guarda en cookie HTTP-only
- Se valida en cada acceso al dashboard

---

## 3. Stack tecnológico

El sistema utiliza:

- **Python**: lenguaje principal
- **FastAPI**: framework web y API REST
- **Uvicorn**: servidor ASGI
- **PostgreSQL**: base de datos relacional
- **psycopg2**: acceso a base de datos
- **Pydantic**: validación y tipado de datos
- **Requests**: consumo de fuentes externas
- **BeautifulSoup**: parsing HTML
- **Jinja2**: renderizado de templates
- **python-jose**: manejo de JWT
- **Passlib (bcrypt)**: hashing de contraseñas
- **python-dotenv**: manejo de variables de entorno
- **unittest + TestClient**: testing
- **Render**: despliegue

---

## 4. Base de datos

### Tabla `products`

La tabla central del sistema, almacena productos scrapeados.

Campos principales:
- `id`: identificador único
- `store`: tienda de origen
- `name`: nombre del producto
- `price`: precio
- `currency`: moneda
- `url`: identificador único del producto
- `scraped_at`: timestamp de actualización

Se utiliza `ON CONFLICT (url)` para evitar duplicados y mantener los datos actualizados.

---

### Tabla `users`

Gestiona autenticación.

Campos:
- `id`
- `username`
- `password_hash`
- `is_active`
- `created_at`

---

## 5. API REST

Endpoints principales:

- `GET /health` → estado del sistema  
- `GET /products/` → listado con filtros  
- `GET /products/compare/` → comparación por tienda  
- `GET /products/stores/` → resumen por store  
- `GET /products/cheapest/` → producto más barato por tienda  
- `GET /products/{id}` → detalle de producto  

Endpoints de autenticación:

- `GET /users/login` → formulario HTML  
- `POST /users/login` → login + JWT  
- `GET /users/dashboard` → vista protegida  
- `POST /users/logout` → cierre de sesión  

---

## 6. Sistema de autenticación

### Flujo

1. Usuario envía credenciales
2. Se valida contra DB
3. Se genera JWT con `sub`
4. Se guarda en cookie HTTP-only
5. Se valida en cada request protegida

---

### Seguridad

- Hashing con bcrypt
- JWT firmado con `SECRET_KEY`
- Expiración configurable
- Cookie con `httponly=True` y `samesite=lax`

---

## 7. Manejo de errores

- `HTTPException` para errores REST
- `400` → validación de parámetros
- `404` → recurso no encontrado
- `401` → login inválido (HTML)

En autenticación:
- Se re-renderiza el login en lugar de devolver JSON

---

## 8. Templates y estáticos

Se usa Jinja2 para:

- `login.html`
- `dashboard.html`

Los archivos estáticos existen pero aún no están montados con `StaticFiles`.

---

## 9. Deploy

### Render

Configuración:
- `uvicorn api.main:app`
- variables de entorno (`DATABASE_URL`, `SECRET_KEY`)
- health check `/health`

---

### Docker

El contenedor actual ejecuta el scraper, no la API.

---

## 10. Testing

Se utilizan:

- `unittest`
- `TestClient`

Incluye:
- health check
- validaciones de parámetros
- endpoints de productos

No incluye:
- autenticación
- JWT
- scraping

---

## 11. Decisiones de diseño

- Uso de **SQL directo** en lugar de ORM para mayor control y simplicidad en el MVP.
- Uso de **JWT en cookies HTTP-only** en lugar de headers para facilitar un flujo web tradicional.
- Separación en capas (`routers`, `services`, `utils`) para mantener responsabilidades claras.
- Uso de **FastAPI** por su tipado, validación automática y generación de documentación.
- Estrategia de **upsert** basada en URL para evitar duplicados.

---

## 12. Posibles mejoras

### Arquitectura
- Implementar migraciones (Alembic)
- Separar capa de acceso a datos

### Seguridad
- Activar `secure=True` en cookies
- Agregar protección CSRF

### Funcionalidad
- Histórico de precios
- Más tiendas
- Configuración dinámica de scraping

### Testing
- Tests de autenticación
- Tests de JWT

### DevOps
- Logging estructurado
- Observabilidad
- Pipeline CI/CD completo

---

## Conclusión

Scrabby representa una base sólida de backend moderno, integrando scraping, persistencia, API REST y autenticación.

El proyecto demuestra comprensión del ciclo completo de desarrollo backend, desde la obtención de datos hasta su exposición segura, y establece una base escalable para futuras mejoras.