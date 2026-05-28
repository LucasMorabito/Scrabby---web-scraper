# Scrabby

Scrabby is a Full Stack price intelligence platform focused on PC hardware tracking across Argentine e-commerce stores.

The system combines large-scale web scraping, PostgreSQL persistence, historical price tracking, authentication, rate limiting, and a REST API built with FastAPI.

It currently aggregates products from multiple stores including Mercado Libre, Frávega, Mexx, Quantum Hardstore, 710Tech, ArmyTech, and Rocket Hard.

---

# Features

## Price Aggregation Engine

* Multi-store GPU price scraping.
* Parallel scraping pipeline.
* Product normalization and deduplication.
* Invalid product filtering (accessories, unrealistic prices, duplicates).
* Historical price tracking.

## Backend API

* REST API built with FastAPI.
* Interactive Swagger/OpenAPI documentation.
* Pagination, filtering, sorting, and search.
* Store comparison endpoints.
* Cheapest-product aggregation endpoints.
* JSON + HTML dual responses depending on client type.

## Authentication & Security

* JWT authentication.
* Session cookies with:

  * `HttpOnly`
  * `SameSite=Lax`
  * `Secure` in production
* Protected dashboard routes.
* Favorite products system.
* Global exception handlers.
* Standardized API error responses.
* Rate limiting with SlowAPI.
* Strict CORS configuration.

## Infrastructure

* PostgreSQL + SQLAlchemy ORM.
* Alembic database migrations.
* Automated daily scraping with GitHub Actions.
* Render deployment.
* TLS impersonation for WAF avoidance using `curl_cffi`.

---

# Live API

Production URL:

```text
https://scrabby-api.onrender.com
```

Swagger Documentation:

```text
https://scrabby-api.onrender.com/docs
```

---

# Tech Stack

## Backend

* Python
* FastAPI
* Uvicorn
* SQLAlchemy
* PostgreSQL
* psycopg2-binary
* Alembic
* Pydantic

## Scraping

* curl_cffi
* BeautifulSoup4

## Security

* PyJWT
* Passlib (bcrypt)
* SlowAPI

## Frontend

* Jinja2
* Tailwind CSS
* DaisyUI
* Alpine.js

## DevOps & Deployment

* Docker
* GitHub Actions
* Render
* Supabase PostgreSQL

---

# Architecture

```text
Scrabby/
│
├── api/
│   ├── core/
│   │   └── handlers.py
│   ├── routers/
│   │   ├── auth.py
│   │   └── products.py
│   ├── services/
│   ├── templates/
│   ├── limiter.py
│   ├── dependencies.py
│   ├── security.py
│   └── main.py
│
├── database/
│   ├── database.py
│   ├── models.py
│   ├── crud.py
│   └── migrations/
│
├── scrappers/
│   ├── http_client.py
│   ├── mercadolibre.py
│   ├── fravega.py
│   ├── mexx.py
│   ├── quantumhardstore.py
│   ├── armytech.py
│   ├── rockethard.py
│   └── tech710.py
│
├── tests/
│
├── data/
│   └── products.json
│
├── main.py
├── requirements.txt
├── Dockerfile
└── render.yaml
```

---

# Installation

## Requirements

* Python 3.11+
* PostgreSQL
* Git

---

## Clone the repository

```bash
git clone <repository-url>
cd Scrabby
```

---

## Create virtual environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Install dependencies

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/scrabby

SECRET_KEY=your_secret_key
ALGORITHM=HS256
TOKEN_SECONDS_EXPIRE=3600

ALLOWED_ORIGINS=http://127.0.0.1:8000

SCRABBY_SEARCH_QUERY=placas de video
SCRABBY_RESULT_LIMIT=50
SCRABBY_MIN_PRICE=100000

SCRABBY_TLS_IMPERSONATE=chrome136
SCRABBY_HTTP_TIMEOUT=15
SCRABBY_HTTP_MAX_ATTEMPTS=3
```

---

# Database Migrations

Apply migrations:

```bash
alembic upgrade head
```

Create a new migration:

```bash
alembic revision -m "describe change"
```

If the database schema already exists manually:

```bash
alembic stamp head
```

---

# Running the Scraper

Default execution:

```bash
python main.py
```

Custom search:

```bash
python main.py rtx 4070
```

Custom limit:

```bash
python main.py "placas de video" --limit 100
```

---

# Running the API

Development server:

```bash
uvicorn api.main:app --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# Main Endpoints

## Health Check

```http
GET /health
GET /health/db
```

---

## Products

```http
GET /products/
GET /products/compare/
GET /products/stores/
GET /products/cheapest/
GET /products/{id}
GET /products/{id}/history
```

Features:

* Pagination
* Filtering
* Search
* Sorting
* Historical tracking

---

## Authentication

```http
POST /users/login
POST /users/register
POST /users/logout
GET /users/dashboard
```

---

# Standardized Error Responses

Example:

```json
{
  "success": false,
  "error": {
    "type": "validation_error",
    "code": 422,
    "message": "Validation error",
    "details": []
  },
  "method": "GET",
  "timestamp": "2026-05-09T01:41:34.381132",
  "path": "/products/"
}
```

---

# Security Features

* JWT authentication.
* Secure cookie handling.
* Strict CORS policy.
* Rate limiting.
* Brute-force protection.
* Anti-DoS protection.
* TLS fingerprint impersonation.
* Global exception handling.

---

# Automated Scraping

GitHub Actions runs scheduled scraping jobs daily to refresh the production database automatically.

Workflow location:

```text
.github/workflows/
```

---

# Testing

Run unit tests:

```bash
python -m unittest discover tests
```

---

# Project Goals

Scrabby was created as a learning-oriented backend engineering project focused on:

* Scalable API architecture.
* High-volume data persistence.
* Real-world scraping challenges.
* Security best practices.
* Production deployment workflows.
* ORM optimization.
* Modular backend design.

---

# Author

Lucas Morabito
Backend Developer focused on Python and FastAPI.

Portfolio:

```text
https://lucasmorabito.vercel.app/
```
