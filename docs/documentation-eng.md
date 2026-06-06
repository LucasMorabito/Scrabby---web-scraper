# Scrabby — Technical Documentation

## Table of Contents

* [Overview](#overview)
* [Architecture](#architecture)
* [Technology Stack](#technology-stack)
* [Database](#database)
* [REST API](#rest-api)
* [Security](#security)
* [Error Handling](#error-handling)
* [Deployment](#deployment)
* [Testing](#testing)
* [Design Decisions](#design-decisions)

---

# Overview

## Introduction

Scrabby is a Python-based backend system that implements a complete scraping, processing, and hardware price exposure pipeline in near real time.

The platform integrates multiple e-commerce sources, normalizes the collected information, and exposes it through a REST API to perform queries, comparisons, and price analysis across different stores.

The project also includes:

* JWT-based authentication
* Session management using HTTP-only cookies
* Abuse protection through Rate Limiting
* Distributed caching with Redis
* Error monitoring and tracking through Sentry
* Standardized error handling
* Optimized PostgreSQL persistence

---

## Integrated Stores

The system currently collects data from:

* Frávega
* Mercado Libre
* Mexx
* Quantum Hardstore
* 710Tech
* ArmyTech
* Rocket Hard

---

## Current Features

### Performance & Observability

* Redis-based caching for frequently accessed queries
* Reduced load on PostgreSQL
* Centralized error monitoring with Sentry
* Production exception traceability

### Scraping Pipeline

* Multi-store distributed scraping
* TLS impersonation using `curl_cffi`
* Retry and backoff strategies
* Product filtering and normalization

### Persistence

* PostgreSQL Bulk Upserts
* Automatic price history tracking
* ORM persistence with SQLAlchemy

### REST API

* Product listing and search
* Advanced pagination
* Store comparison
* Cheapest product detection
* Dual HTML + JSON responses

### Security & Authentication

* JWT Authentication
* Secure cookies (`HttpOnly`, `SameSite`, `Secure`)
* Rate Limiting with SlowAPI
* Strict CORS policy

---

# Architecture

## Project Structure

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

## System Flow

### 1. Data Collection

The system performs concurrent scraping across multiple stores using a centralized HTTP client configured with TLS Impersonation.

### 2. Processing

Products are:

* Normalized
* Filtered
* Deduplicated in memory

before being persisted.

### 3. Persistence

Data is stored using Bulk Upserts powered by PostgreSQL-specific features:

```sql
INSERT ... ON CONFLICT DO UPDATE
```

During the same transaction, price history records are also created.

### 4. API Exposure

FastAPI exposes the data through REST endpoints protected by:

* Redis Cache
* Rate Limiting
* Authentication Middleware
* Exception Handlers
* CORS Validation
* Sentry Monitoring

---

# Technology Stack

| Technology       | Purpose                      |
| ---------------- | ---------------------------- |
| Python           | Primary language             |
| FastAPI          | Backend framework            |
| Uvicorn          | ASGI server                  |
| PostgreSQL       | Database                     |
| SQLAlchemy       | ORM                          |
| Alembic          | Migrations                   |
| Redis            | Distributed cache            |
| Sentry           | Observability and monitoring |
| psycopg2-binary  | PostgreSQL driver            |
| curl_cffi        | TLS Impersonation            |
| SlowAPI          | Rate Limiting                |
| BeautifulSoup    | HTML parsing                 |
| Jinja2           | HTML rendering               |
| PyJWT            | JWT Authentication           |
| Passlib (bcrypt) | Password hashing             |
| Docker           | Containerization             |
| Render           | Deployment                   |

---

# Database

## `products` Table

Stores the current state of each scraped product.

Main features:

* URL-based deduplication
* Automatic price updates
* Scraping timestamp
* Indexed columns for optimized queries

---

## `price_history` Table

Automatically records every detected price change during update operations.

---

## `users` Table

Manages credentials and access to the administrative dashboard.

---

## `user_favorites` Table

Implements a many-to-many relationship between users and favorite products.

---

# Cache

## Redis

Scrabby uses Redis as a caching layer to temporarily store frequently accessed queries and reduce PostgreSQL load.

Benefits:

* Lower response latency
* Fewer repetitive database queries
* Better user experience under load

The system automatically invalidates relevant cache entries whenever data is updated through new scraping processes.

---

# REST API

## Main Endpoints

| Method | Endpoint              | Description                  |
| ------ | --------------------- | ---------------------------- |
| GET    | `/health`             | General system status        |
| GET    | `/health/db`          | PostgreSQL connection status |
| GET    | `/products/`          | Paginated product listing    |
| GET    | `/products/compare/`  | Store comparison             |
| GET    | `/products/stores/`   | Store summary                |
| GET    | `/products/cheapest/` | Cheapest product per store   |

---

## User Endpoints

| Method   | Endpoint                          | Description         |
| -------- | --------------------------------- | ------------------- |
| GET/POST | `/users/login`                    | User login          |
| POST     | `/users/register`                 | User registration   |
| GET      | `/users/dashboard`                | Protected dashboard |
| POST     | `/users/dashboard/favorites/{id}` | Add favorite        |
| DELETE   | `/users/dashboard/favorites/{id}` | Remove favorite     |
| POST     | `/users/logout`                   | User logout         |

---

# Security

## Authentication

Authentication is implemented through JWT tokens stored in secure cookies:

* `HttpOnly`
* `SameSite="lax"`
* `Secure=True` in production

---

## API Protection

### Strict CORS

The API only accepts requests from domains defined in:

```env
ALLOWED_ORIGINS
```

---

### Rate Limiting

Abuse protection:

* Login: `5 requests/min`
* Registration: `3 requests/min`
* Public endpoints: `30 requests/min`

---

## Anti-Bot Mitigation

The system uses TLS Impersonation and consistent fingerprints to reduce automated blocking by target stores.

---

# Observability

## Sentry

The system integrates Sentry for production error and exception monitoring.

Capabilities:

* Automatic capture of unhandled exceptions
* Complete error traceability
* Request context information
* Real-time alerts

This enables rapid detection of failures in endpoints, scraping processes, and database operations.

---

# Error Handling

The API implements global handlers to provide consistent responses.

## Standard Format

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

## HTTP 429 Handling

When rate limits are exceeded:

* API clients receive JSON responses
* Browsers receive a user-friendly HTML page (`error429.html`)

---

# Deployment

## API

The API is deployed on Render using:

```yaml
uvicorn api.main:app
```

---

## Scheduled Scraping

GitHub Actions executes automated scraping jobs using ephemeral Docker containers.

---

## Environment Variables

### Infrastructure

```env
REDIS_URL=

SENTRY_DSN=
```

### Database

```env
DATABASE_URL=
```

### Security

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

### HTTP Client

```env
SCRABBY_TLS_IMPERSONATE=

SCRABBY_HTTP_TIMEOUT=

SCRABBY_HTTP_MAX_ATTEMPTS=
```

---

# Testing

The test suite uses:

* `unittest`
* `FastAPI TestClient`
* HTTP client mocking

## Running Tests

```bash
python -m unittest discover tests
```

---

# Design Decisions

## SQLAlchemy + Native PostgreSQL

The project combines ORM capabilities with advanced PostgreSQL dialect features:

* `ON CONFLICT`
* `RETURNING`
* Bulk Operations

This enables efficient processing of large data volumes without unnecessary memory consumption.

---

## Centralized HTTP Client

All outgoing requests use a shared HTTP client to maintain a consistent TLS fingerprint and reduce anti-bot blocking.

---

## Dual JSON/HTML Responses

Endpoints such as `/products/` automatically detect the client type through HTTP headers and return:

* JSON for API consumers
* Rendered HTML for web browsers

---

# Conclusion

Scrabby is a backend project focused on the efficient collection, processing, and exposure of hardware pricing data in real time.

The system integrates distributed scraping, optimized persistence, secure authentication, and protection mechanisms commonly found in modern APIs, while maintaining a modular architecture designed for future scalability.
