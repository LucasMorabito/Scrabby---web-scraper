# Scrabby

Scrabby es un scraper y una API para comparar precios de componentes de PC en tiendas argentinas. El proyecto obtiene productos desde distintas fuentes, filtra resultados irrelevantes, guarda un snapshot local en JSON, persiste la informacion en PostgreSQL y la expone mediante FastAPI.

## Caracteristicas

- Scraping de productos desde Mercado Libre y Fravega.
- Filtrado de publicaciones irrelevantes segun precio minimo y palabras blacklist.
- Persistencia de resultados en `data/products.json`.
- Persistencia de productos en PostgreSQL con `upsert` por `url`.
- API REST con documentacion interactiva en Swagger.

## Arquitectura

El proyecto esta dividido en dos partes: el pipeline de scraping y la API de consulta.

### Pipeline de scraping

1. [main.py](/c:/Users/Usuario/Desktop/IT/Proyectos/Scrabby/main.py:1) orquesta el proceso completo.
2. [scrappers/fravega.py](/c:/Users/Usuario/Desktop/IT/Proyectos/Scrabby/scrappers/fravega.py:1) consulta la API de Fravega y normaliza productos.
3. [scrappers/mercadolibre.py](/c:/Users/Usuario/Desktop/IT/Proyectos/Scrabby/scrappers/mercadolibre.py:1) obtiene HTML, parsea `ld+json` y normaliza productos.
4. [main.py](/c:/Users/Usuario/Desktop/IT/Proyectos/Scrabby/main.py:7) filtra resultados con `is_valid_product`.
5. [main.py](/c:/Users/Usuario/Desktop/IT/Proyectos/Scrabby/main.py:33) guarda el snapshot en `data/products.json`.
6. [database/database.py](/c:/Users/Usuario/Desktop/IT/Proyectos/Scrabby/database/database.py:10) inserta o actualiza la tabla `products`.

### API

1. [api/main.py](/c:/Users/Usuario/Desktop/IT/Proyectos/Scrabby/api/main.py:1) crea la app FastAPI y registra el router.
2. [api/routers/products.py](/c:/Users/Usuario/Desktop/IT/Proyectos/Scrabby/api/routers/products.py:1) expone los endpoints de consulta.
3. [api/dependencies.py](/c:/Users/Usuario/Desktop/IT/Proyectos/Scrabby/api/dependencies.py:1) administra la conexion a base de datos por request.
4. [api/schemas/product.py](/c:/Users/Usuario/Desktop/IT/Proyectos/Scrabby/api/schemas/product.py:1) y [api/schemas/store.py](/c:/Users/Usuario/Desktop/IT/Proyectos/Scrabby/api/schemas/store.py:1) definen los modelos de respuesta.

## Estructura del proyecto

```text
Scrabby/
|-- api/
|   |-- main.py
|   |-- dependencies.py
|   |-- routers/
|   |   `-- products.py
|   `-- schemas/
|       |-- product.py
|       `-- store.py
|-- database/
|   `-- database.py
|-- data/
|   `-- products.json
|-- scrappers/
|   |-- fravega.py
|   `-- mercadolibre.py
|-- utils/
|-- main.py
|-- requirements.txt
`-- Dockerfile
```

## Requisitos

- Python 3.12
- PostgreSQL
- Variable de entorno `DATABASE_URL`

Ejemplo:

```env
DATABASE_URL=postgresql://usuario:password@localhost:5432/scrabby
```

## Instalacion

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar el scraper

```bash
python main.py
```

El scraper:

1. Consulta las tiendas configuradas.
2. Filtra productos no validos.
3. Ordena por precio.
4. Guarda un JSON local.
5. Inserta o actualiza la base de datos.

## Ejecutar la API

```bash
venv\Scripts\uvicorn api.main:app --reload
```

Swagger queda disponible en:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

Base URL local:

```text
http://127.0.0.1:8000
```

### GET `/products/`

Lista productos con filtros, paginacion y ordenamiento.

Query params:

- `search`: coincidencia parcial sobre `name`.
- `store`: filtro por tienda.
- `limit`: cantidad maxima de resultados. Default `20`.
- `offset`: desplazamiento para paginacion. Default `0`.
- `order_by`: `price`, `name` o `scraped_at`.
- `order_dir`: `asc` o `desc`.

Ejemplos:

```http
GET /products/
GET /products/?search=rtx
GET /products/?store=fravega&order_by=name&order_dir=desc
GET /products/?search=3060&limit=10&offset=20
```

Respuesta:

```json
[
  {
    "id": 1,
    "store": "fravega",
    "name": "Placa De Video RTX 3060 Ti",
    "price": 499999.0,
    "currency": "ARS",
    "url": "https://www.fravega.com/p/ejemplo/",
    "scraped_at": "2026-04-24T10:00:00"
  }
]
```

Errores:

- `400` si `order_by` o `order_dir` son invalidos.
- `404` si no se encontraron productos.

### GET `/products/compare/`

Busca productos por nombre y agrupa los resultados por tienda.

Ejemplo:

```http
GET /products/compare/?query=rtx%203060
```

Respuesta:

```json
{
  "fravega": [
    {
      "id": 1,
      "store": "fravega",
      "name": "Placa De Video RTX 3060 Ti",
      "price": 499999.0,
      "currency": "ARS",
      "url": "https://www.fravega.com/p/ejemplo/",
      "scraped_at": "2026-04-24T10:00:00"
    }
  ],
  "mercadolibre": [
    {
      "id": 2,
      "store": "mercadolibre",
      "name": "RTX 3060 Ti MSI",
      "price": 515000.0,
      "currency": "ARS",
      "url": "https://articulo.mercadolibre.com.ar/ejemplo",
      "scraped_at": "2026-04-24T10:05:00"
    }
  ]
}
```

Errores:

- `404` si no se encontraron productos.

### GET `/products/stores/`

Devuelve el resumen de productos por tienda.

Ejemplo:

```http
GET /products/stores/
```

Respuesta:

```json
[
  {
    "store": "fravega",
    "total": 12,
    "last_scraped": "2026-04-24T10:00:00"
  },
  {
    "store": "mercadolibre",
    "total": 35,
    "last_scraped": "2026-04-24T10:05:00"
  }
]
```

### GET `/products/cheapest/`

Devuelve el producto mas barato de cada tienda.

Ejemplo:

```http
GET /products/cheapest/
```

Respuesta:

```json
[
  {
    "id": 1,
    "store": "fravega",
    "name": "Placa De Video RTX 3060 Ti",
    "price": 499999.0,
    "currency": "ARS",
    "url": "https://www.fravega.com/p/ejemplo/",
    "scraped_at": "2026-04-24T10:00:00"
  },
  {
    "id": 2,
    "store": "mercadolibre",
    "name": "RTX 3060 Ti MSI",
    "price": 515000.0,
    "currency": "ARS",
    "url": "https://articulo.mercadolibre.com.ar/ejemplo",
    "scraped_at": "2026-04-24T10:05:00"
  }
]
```

### GET `/products/{id}`

Devuelve un producto especifico por su ID.

Ejemplo:

```http
GET /products/1
```

Respuesta:

```json
{
  "id": 1,
  "store": "fravega",
  "name": "Placa De Video RTX 3060 Ti",
  "price": 499999.0,
  "currency": "ARS",
  "url": "https://www.fravega.com/p/ejemplo/",
  "scraped_at": "2026-04-24T10:00:00"
}
```

Errores:

- `404` si el producto no existe.

## Modelo de datos

La API trabaja sobre una tabla `products` con estas columnas:

- `id`
- `store`
- `name`
- `price`
- `currency`
- `url`
- `scraped_at`

La capa de persistencia usa `ON CONFLICT (url)` para actualizar precio y fecha de scraping cuando un producto ya existe.

## Notas

- El endpoint `/products/cheapest/` usa `DISTINCT ON (store)`, una caracteristica especifica de PostgreSQL.
- Swagger se genera automaticamente desde los `response_model` y la metadata definida en FastAPI.
- El scraper principal actualmente usa la query fija `rtx 3060 ti` en [main.py](/c:/Users/Usuario/Desktop/IT/Proyectos/Scrabby/main.py:47).
