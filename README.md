# Scrabby

Scrabby is a scraper and API for comparing PC component prices across Argentine stores. The project fetches products from multiple sources, filters irrelevant results, saves a local JSON snapshot, stores the data in PostgreSQL, and exposes it through FastAPI.

Documentation: /docs/documentacion-app.md
## Features

- Product scraping from Mercado Libre and Fravega.
- Result filtering based on minimum price and blacklist keywords.
- Local snapshot persistence in `data/products.json`.
- PostgreSQL persistence with `upsert` behavior based on `url`.
- REST API with interactive Swagger documentation.

## Architecture

The project is split into two main parts: the scraping pipeline and the API layer.

### Scraping pipeline

1. [main.py](/Scrabby/main.py:1) orchestrates the full process.
2. [scrappers/fravega.py](/Scrabby/scrappers/fravega.py:1) queries Fravega's API and normalizes products.
3. [scrappers/mercadolibre.py](/Scrabby/scrappers/mercadolibre.py:1) tries Mercado Libre's JSON search API, falls back to HTML `ld+json`, and normalizes products.
4. [main.py](/Scrabby/main.py:7) filters results with `is_valid_product`.
5. [main.py](/Scrabby/main.py:33) saves a local snapshot in `data/products.json`.
6. [database/database.py](/Scrabby/database/database.py:10) inserts or updates records in the `products` table.

### API layer

1. [api/main.py](/Scrabby/api/main.py:1) creates the FastAPI app and registers the router.
2. [api/routers/products.py](/Scrabby/api/routers/products.py:1) exposes the API endpoints.
3. [api/dependencies.py](/Scrabby/api/dependencies.py:1) manages one database connection per request.
4. [api/schemas/product.py](/Scrabby/api/schemas/product.py:1) and [api/schemas/store.py](/Scrabby/api/schemas/store.py:1) define the response models.

## Project structure

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

## Requirements

- Python 3.12
- PostgreSQL
- `DATABASE_URL` environment variable
- Optional Mercado Libre credentials if public search requests are blocked

Example:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/scrabby
SCRABBY_SEARCH_QUERY=placas de video
SCRABBY_RESULT_LIMIT=50
MERCADOLIBRE_ACCESS_TOKEN=
MERCADOLIBRE_REFRESH_TOKEN=
MERCADOLIBRE_CLIENT_ID=
MERCADOLIBRE_CLIENT_SECRET=
```

## Installation

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run the scraper

```bash
python main.py
```

You can override the default search at runtime:

```bash
python main.py rtx 3060 ti
python main.py "placas de video" --limit 100
```

The scraper:

1. Queries the configured stores.
2. Filters invalid products.
3. Sorts them by price.
4. Saves a local JSON file.
5. Inserts or updates the database.

## Run the API

```bash
venv\Scripts\uvicorn api.main:app --reload
```

Swagger UI is available at:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

Local base URL:

```text
http://127.0.0.1:8000
```

### GET `/products/`

Returns products with filtering, pagination, and sorting.

Query params:

- `search`: partial match against `name`.
- `store`: filter by store.
- `limit`: maximum number of results. Default `20`.
- `offset`: pagination offset. Default `0`.
- `order_by`: `price`, `name`, or `scraped_at`.
- `order_dir`: `asc` or `desc`.

Examples:

```http
GET /products/
GET /products/?search=rtx
GET /products/?store=fravega&order_by=name&order_dir=desc
GET /products/?search=3060&limit=10&offset=20
```

Response:

```json
[
  {
    "id": 1,
    "store": "fravega",
    "name": "RTX 3060 Ti Graphics Card",
    "price": 499999.0,
    "currency": "ARS",
    "url": "https://www.fravega.com/p/example/",
    "scraped_at": "2026-04-24T10:00:00"
  }
]
```

Errors:

- `400` if `order_by` or `order_dir` are invalid.
- `404` if no products are found.

### GET `/products/compare/`

Searches products by name and groups them by store.

Example:

```http
GET /products/compare/?query=rtx%203060
```

Response:

```json
{
  "fravega": [
    {
      "id": 1,
      "store": "fravega",
      "name": "RTX 3060 Ti Graphics Card",
      "price": 499999.0,
      "currency": "ARS",
      "url": "https://www.fravega.com/p/example/",
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
      "url": "https://articulo.mercadolibre.com.ar/example",
      "scraped_at": "2026-04-24T10:05:00"
    }
  ]
}
```

Errors:

- `404` if no products are found.

### GET `/products/stores/`

Returns a store-level summary of products.

Example:

```http
GET /products/stores/
```

Response:

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

Returns the cheapest product for each store.

Example:

```http
GET /products/cheapest/
```

Response:

```json
[
  {
    "id": 1,
    "store": "fravega",
    "name": "RTX 3060 Ti Graphics Card",
    "price": 499999.0,
    "currency": "ARS",
    "url": "https://www.fravega.com/p/example/",
    "scraped_at": "2026-04-24T10:00:00"
  },
  {
    "id": 2,
    "store": "mercadolibre",
    "name": "RTX 3060 Ti MSI",
    "price": 515000.0,
    "currency": "ARS",
    "url": "https://articulo.mercadolibre.com.ar/example",
    "scraped_at": "2026-04-24T10:05:00"
  }
]
```

### GET `/products/{id}`

Returns a specific product by ID.

Example:

```http
GET /products/1
```

Response:

```json
{
  "id": 1,
  "store": "fravega",
  "name": "RTX 3060 Ti Graphics Card",
  "price": 499999.0,
  "currency": "ARS",
  "url": "https://www.fravega.com/p/example/",
  "scraped_at": "2026-04-24T10:00:00"
}
```

Errors:

- `404` if the product does not exist.

## Data model

The API works against a `products` table with these columns:

- `id`
- `store`
- `name`
- `price`
- `currency`
- `url`
- `scraped_at`

The persistence layer uses `ON CONFLICT (url)` to update existing prices and scrape timestamps.

## Notes

- `/products/cheapest/` uses `DISTINCT ON (store)`, which is PostgreSQL-specific.
- Swagger is generated automatically from FastAPI metadata and `response_model` declarations.
- The main scraper defaults to `SCRABBY_SEARCH_QUERY` or `placas de video`; you can also pass the query as CLI arguments.
- Mercado Libre may return `401`/`403` from its API depending on access policy. Set `MERCADOLIBRE_ACCESS_TOKEN`; if it expires, the scraper can refresh it using `MERCADOLIBRE_REFRESH_TOKEN`, `MERCADOLIBRE_CLIENT_ID`, and `MERCADOLIBRE_CLIENT_SECRET`. It also accepts the shorter env names `ACCESS_TOKEN`, `REFRESH_TOKEN`, `APP_ID`, and `CLIENT_SECRET`.
