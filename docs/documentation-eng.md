# Scrabby — Technical Documentation

## Table of Contents

* [Overview](#overview)
* [Architecture](#architecture)
* [Technology Stack](#technology-stack)
* [Database](#database)
* [API](#api)
* [Security](#security)
* [Error Handling](#error-handling)
* [Deployment](#deployment)
* [Testing](#testing)
* [Design Decisions](#design-decisions)

---

# Overview

## Introduction

Scrabby is a Python-based backend system that implements a complete scraping, processing, and price exposure pipeline for PC hardware products.

The platform aggregates data from multiple e-commerce sources, normalizes product information, stores historical price variations, and exposes the data through a REST API for querying and comparison.

The project also includes:

* JWT authentication
* HTTP-only session cookies
* Rate limiting protections
* Standardized API error handling
* PostgreSQL persistence with optimized bulk upserts

---

## Current Sources

Currently integrated stores:

* Frávega
* Mercado Libre
* Mexx
* Quantum Hardstore
* 710Tech
* ArmyTech
* Rocket Hard

---

## Current Features

### Scraping Pipeline

* Multi-store scraping
* TLS impersonation using `curl_cffi`
* Retry & backoff strategies
* Product normalization and filtering

### Persistence Layer

* Bulk upserts with PostgreSQL
* Historical price tracking
* ORM models with SQLAlchemy

### API Features

* Product listing and filtering
* Pagination
* Store comparison
* Cheapest product detection
* HTML + JSON dual responses

### Authentication & Security

* JWT authentication
* Secure session cookies
* Rate limiting with SlowAPI
* CORS protection

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

## Request Flow

### 1. Scraping

The system performs concurrent requests against multiple stores using a centralized HTTP client configured with TLS impersonation.

### 2. Processing

Products are normalized, filtered, and deduplicated in memory.

### 3. Persistence

Data is inserted using PostgreSQL bulk upserts:

```sql
INSERT ... ON CONFLICT DO UPDATE
```

Historical prices are registered during the same transaction.

### 4. API Exposure

FastAPI exposes the processed data through REST endpoints protected by:

* Rate limiting
* Authentication middleware
* Exception handlers
* CORS validation

---

# Technology Stack

| Technology    | Purpose             |
| ------------- | ------------------- |
| Python        | Main language       |
| FastAPI       | Backend framework   |
| PostgreSQL    | Database            |
| SQLAlchemy    | ORM                 |
| Alembic       | Database migrations |
| curl_cffi     | TLS impersonation   |
| SlowAPI       | Rate limiting       |
| BeautifulSoup | HTML parsing        |
| Jinja2        | HTML rendering      |
| PyJWT         | Authentication      |
| Passlib       | Password hashing    |
| Docker        | Containerization    |
| Render        | Deployment          |

---

# Security

## Authentication

* JWT-based sessions
* HTTP-only cookies
* SameSite protection
* Dynamic Secure flag in production

## API Protection

* Strict CORS policy
* Rate limiting
* Brute-force mitigation
* Abuse prevention for public endpoints

---

# Deployment

## API

The API is deployed on Render using:

```yaml
uvicorn api.main:app
```

## Scheduled Scraping

GitHub Actions runs periodic scraping jobs inside isolated Docker containers.

---

# Testing

Run the test suite with:

```bash
python -m unittest discover tests
```

The test environment mocks HTTP requests to avoid hitting real stores during CI execution.

---

# Design Decisions

## SQLAlchemy + PostgreSQL Dialect Features

The project uses PostgreSQL-specific optimizations such as:

* `ON CONFLICT`
* `RETURNING`
* Bulk operations

This allows efficient persistence without loading the full dataset into memory.

## Centralized HTTP Client

A shared HTTP client keeps a consistent TLS/browser fingerprint across all scrapers, reducing anti-bot blocks.

## Dual Response Strategy

Endpoints such as `/products/` dynamically return:

* HTML templates for browsers
* JSON responses for API consumers

based on the request headers.
