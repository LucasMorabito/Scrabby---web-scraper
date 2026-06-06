# Scrabby — Documentación Técnica

## Tabla de Contenidos

* [Descripción General](#descripción-general)
* [Arquitectura](#arquitectura)
* [Stack Tecnológico](#stack-tecnológico)
* [Base de Datos](#base-de-datos)
* [API REST](#api-rest)
* [Seguridad](#seguridad)
* [Manejo de Errores](#manejo-de-errores)
* [Despliegue](#despliegue)
* [Testing](#testing)
* [Decisiones de Diseño](#decisiones-de-diseño)

---

# Descripción General

## Introducción

Scrabby es un sistema backend desarrollado en Python que implementa un pipeline completo de scraping, procesamiento y exposición de datos de precios de hardware en tiempo casi real.

La plataforma integra múltiples fuentes de e-commerce, normaliza la información obtenida y la expone mediante una API REST para realizar consultas, comparaciones y análisis de precios entre distintas tiendas.

El proyecto también incorpora:

* Autenticación basada en JWT
* Manejo de sesión mediante cookies HTTP-only
* Protección contra abuso mediante Rate Limiting
* Caché distribuida con Redis
* Monitoreo y captura de errores mediante Sentry
* Manejo estandarizado de errores
* Persistencia optimizada en PostgreSQL

---

## Tiendas Integradas

Actualmente el sistema obtiene datos desde:

* Frávega
* Mercado Libre
* Mexx
* Quantum Hardstore
* 710Tech
* ArmyTech
* Rocket Hard

---

## Funcionalidades Actuales

### Rendimiento y Observabilidad

* Caché de consultas frecuentes mediante Redis
* Reducción de carga sobre PostgreSQL
* Monitoreo centralizado de errores con Sentry
* Trazabilidad de excepciones en producción

### Pipeline de Scraping

* Scraping distribuido multi-tienda
* Suplantación TLS mediante `curl_cffi`
* Estrategias de retry y backoff
* Filtrado y normalización de productos

### Persistencia

* Bulk Upserts sobre PostgreSQL
* Historial automático de precios
* Persistencia ORM con SQLAlchemy

### API REST

* Listado y búsqueda de productos
* Paginación avanzada
* Comparación entre tiendas
* Obtención de productos más baratos
* Respuestas duales HTML + JSON

### Seguridad y Autenticación

* JWT Authentication
* Cookies seguras (`HttpOnly`, `SameSite`, `Secure`)
* Rate Limiting con SlowAPI
* Política CORS estricta

---

# Arquitectura

## Organización del Proyecto

```text
api/
├── routers/
├── services/
├── core/
├── templates/
├── limiter.py
├── cache.py
└── security.py

database/
├── models.py
├── crud.py
└── database.py

scrappers/
├── http_client.py
└── ...

tests/
```

---

## Flujo del Sistema

### 1. Recolección de Datos

El sistema ejecuta scraping concurrente sobre múltiples tiendas utilizando un cliente HTTP centralizado configurado con TLS Impersonation.

### 2. Procesamiento

Los productos son:

* Normalizados
* Filtrados
* Deduplicados en memoria

antes de persistirse.

### 3. Persistencia

Los datos se almacenan mediante Bulk Upserts utilizando características específicas de PostgreSQL:

```sql
INSERT ... ON CONFLICT DO UPDATE
```

Durante la misma transacción también se registra el historial de precios.

### 4. Exposición de API

FastAPI expone la información mediante endpoints REST protegidos por:

* Redis Cache
* Rate Limiting
* Middleware de autenticación
* Exception Handlers
* Validación CORS
* Monitoreo con Sentry

---

# Stack Tecnológico

| Tecnología       | Uso                         |
| ---------------- | --------------------------- |
| Python           | Lenguaje principal          |
| FastAPI          | Framework backend           |
| Uvicorn          | Servidor ASGI               |
| PostgreSQL       | Base de datos               |
| SQLAlchemy       | ORM                         |
| Alembic          | Migraciones                 |
| Redis            | Caché distribuida           |
| Sentry           | Observabilidad y monitoreo  |
| psycopg2-binary  | Driver PostgreSQL           |
| curl_cffi        | TLS Impersonation           |
| SlowAPI          | Rate Limiting               |
| BeautifulSoup    | Parsing HTML                |
| Jinja2           | Renderizado HTML            |
| PyJWT            | JWT Authentication          |
| Passlib (bcrypt) | Hashing de contraseñas      |
| Docker           | Contenedorización           |
| Render           | Despliegue                  |

---

# Base de Datos

## Tabla `products`

Almacena el estado actual de cada producto scrapeado.

Características principales:

* Deduplicación por URL
* Actualización automática de precios
* Timestamp de scraping
* Índices para optimizar búsquedas

---

## Tabla `price_history`

Registra automáticamente cada variación de precio detectada durante los procesos de actualización.

---

## Tabla `users`

Gestiona credenciales y acceso al dashboard administrativo.

---

## Tabla `user_favorites`

Implementa una relación muchos-a-muchos entre usuarios y productos favoritos.

---

# Caché

## Redis

Scrabby utiliza Redis como capa de caché para almacenar temporalmente consultas frecuentes y reducir la carga sobre PostgreSQL.

Beneficios:

* Menor latencia de respuesta
* Menor cantidad de consultas repetidas a la base de datos
* Mejor experiencia de usuario bajo carga

El sistema invalida automáticamente las entradas relevantes cuando los datos son actualizados mediante nuevos procesos de scraping.

---

# API REST

## Endpoints Principales

| Método | Endpoint              | Descripción                       |
| ------ | --------------------- | --------------------------------- |
| GET    | `/health`             | Estado general del sistema        |
| GET    | `/health/db`          | Estado de conexión con PostgreSQL |
| GET    | `/products/`          | Listado paginado de productos     |
| GET    | `/products/compare/`  | Comparación entre tiendas         |
| GET    | `/products/stores/`   | Resumen por tienda                |
| GET    | `/products/cheapest/` | Producto más barato por tienda    |

---

## Endpoints de Usuario

| Método   | Endpoint                          | Descripción         |
| -------- | --------------------------------- | ------------------- |
| GET/POST | `/users/login`                    | Inicio de sesión    |
| POST     | `/users/register`                 | Registro de usuario |
| GET      | `/users/dashboard`                | Dashboard protegido |
| POST     | `/users/dashboard/favorites/{id}` | Agregar favorito    |
| DELETE   | `/users/dashboard/favorites/{id}` | Eliminar favorito   |
| POST     | `/users/logout`                   | Cierre de sesión    |

---

# Seguridad

## Autenticación

La autenticación se implementa mediante JWT almacenado en cookies seguras:

* `HttpOnly`
* `SameSite="lax"`
* `Secure=True` en producción

---

## Protección de API

### CORS Estricto

La API únicamente acepta requests provenientes de dominios definidos en:

```env
ALLOWED_ORIGINS
```

---

### Rate Limiting

Protección contra abuso:

* Login: `5 requests/min`
* Registro: `3 requests/min`
* Endpoints públicos: `30 requests/min`

---

## Mitigación Anti-Bot

El sistema utiliza TLS Impersonation y fingerprints consistentes para reducir bloqueos automáticos por parte de tiendas objetivo.

---

# Observabilidad

## Sentry

El sistema integra Sentry para el monitoreo de errores y excepciones en producción.

Capacidades:

* Captura automática de excepciones no controladas
* Trazabilidad completa de errores
* Información contextual de requests
* Alertas en tiempo real

Esto permite detectar rápidamente fallos en endpoints, procesos de scraping y operaciones de base de datos.

---

# Manejo de Errores

La API implementa handlers globales para devolver respuestas consistentes.

## Formato estándar

```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "Product not found"
  },
  "method": "GET",
  "path": "/products/99",
  "timestamp": "2026-05-09T01:41:34"
}
```

---

## Manejo de Error 429

Cuando se excede el límite de peticiones:

* Clientes API reciben JSON
* Navegadores reciben una vista HTML amigable (`error429.html`)

---

# Despliegue

## API

La API se despliega en Render utilizando:

```yaml
uvicorn api.main:app
```

---

## Scraping Programado

GitHub Actions ejecuta procesos automáticos de scraping mediante contenedores Docker efímeros.

---

## Variables de Entorno

### Infraestructura

```env
REDIS_URL=
SENTRY_DSN=
```

### Base de Datos

```env
DATABASE_URL=
```

### Seguridad

```env
SECRET_KEY=
ALGORITHM=
TOKEN_SECONDS_EXPIRE=
ALLOWED_ORIGINS=
```

### Scraping

```env
SCRABBY_SEARCH_QUERY=
SCRABBY_RESULT_LIMIT=
SCRABBY_MIN_PRICE=
```

### Cliente HTTP

```env
SCRABBY_TLS_IMPERSONATE=
SCRABBY_HTTP_TIMEOUT=
SCRABBY_HTTP_MAX_ATTEMPTS=
```

---

# Testing

La suite de pruebas utiliza:

* `unittest`
* `FastAPI TestClient`
* Mocking del cliente HTTP

## Ejecutar tests

```bash
python -m unittest discover tests
```

---

# Decisiones de Diseño

## SQLAlchemy + PostgreSQL Nativo

El proyecto combina ORM con características avanzadas del dialecto PostgreSQL:

* `ON CONFLICT`
* `RETURNING`
* Bulk Operations

Esto permite procesar grandes volúmenes de datos sin consumir memoria innecesariamente.

---

## Cliente HTTP Centralizado

Todas las requests salientes utilizan un cliente HTTP compartido para mantener una huella TLS homogénea y reducir bloqueos anti-bot.

---

## Respuestas Dual JSON/HTML

Endpoints como `/products/` detectan automáticamente el tipo de cliente mediante los headers HTTP y responden con:

* JSON para consumo API
* HTML renderizado para navegadores

---

# Conclusión

Scrabby es un proyecto backend orientado a la recolección, procesamiento y exposición eficiente de datos de hardware en tiempo real.

El sistema integra scraping distribuido, persistencia optimizada, autenticación segura y mecanismos de protección típicos de APIs modernas, manteniendo una arquitectura modular preparada para seguir escalando.
