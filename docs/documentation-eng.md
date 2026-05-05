# Scrabby Technical Documentation

## 1. System Overview

### Introduction

Scrabby is a backend system developed in Python that implements a complete pipeline for scraping, processing, and exposing hardware price data in near real-time.

The system integrates multiple e-commerce sources, normalizes the collected data, and exposes it through a REST API, enabling queries, comparisons, and price analysis across different stores.

Additionally, it includes a JWT-based authentication system with session management using HTTP-only cookies, designed for a simple web-based flow.

This project was developed as part of a backend learning process, focusing on applying real-world practices such as modular architecture, data validation, authentication, and deployment.

---

### Problem Statement

The system addresses the need to centralize and compare product prices (mainly GPUs) across different online stores.

Currently, it collects data from Frávega and Mercado Libre, normalizes it, filters out irrelevant results (such as accessories or inconsistent pricing), and makes it available through an API.

---

### Current Scope

The system currently supports:

- Automated scraping pipeline execution  
- Product persistence in PostgreSQL  
- Product querying via REST endpoints  
- Filtering, sorting, and pagination  
- Price comparison across stores  
- Aggregated summaries by store  
- Identification of the cheapest product per store  
- Web-based authentication flow  
- JWT generation and validation  
- Session management using HTTP-only cookies  
- Access to a protected dashboard  

Not yet included:

- User registration  
- Refresh tokens  
- Database migrations  
- Advanced observability  
- Full authentication testing  

---

## 2. Architecture

### Project Structure

The system is organized into modular components with clear responsibilities:

- `api/main.py`: initializes the FastAPI app, registers routers, and defines the health check  
- `api/routers/products.py`: product REST endpoints and SQL queries  
- `api/routers/auth.py`: authentication routes and template rendering  
- `api/services/auth.py`: authentication business logic  
- `api/security.py`: JWT handling and security configuration  
- `utils/security.py`: password hashing and verification (bcrypt)  
- `api/schemas/`: Pydantic models for validation and serialization  
- `api/dependencies.py`: database connection per request  
- `database/database.py`: scraping persistence logic  
- `scrappers/`: external data scrapers  
- `api/templates/`: HTML templates  
- `api/static/`: static files (currently unused)  
- `tests/`: automated tests  

---

### System Flow

The system operates in three main flows:

#### 1. Scraping
- External sources are queried  
- Data is parsed and normalized  
- Irrelevant results are filtered  
- Data is stored in JSON and PostgreSQL  

#### 2. API
- FastAPI receives requests  
- Database connection is injected  
- SQL queries are executed  
- Results are transformed into dictionaries  
- Pydantic validates responses  

#### 3. Authentication
- User submits login form  
- Credentials are validated against the database  
- JWT is generated with `sub` claim  
- Token is stored in HTTP-only cookie  
- Token is validated for protected routes  

---

## 3. Tech Stack

The system uses:

- **Python**: main programming language  
- **FastAPI**: web framework and REST API  
- **Uvicorn**: ASGI server  
- **PostgreSQL**: relational database  
- **psycopg2**: database access  
- **Pydantic**: data validation and typing  
- **Requests**: HTTP client for scraping  
- **BeautifulSoup**: HTML parsing  
- **Jinja2**: template rendering  
- **python-jose**: JWT handling  
- **Passlib (bcrypt)**: password hashing  
- **python-dotenv**: environment variables  
- **unittest + TestClient**: testing  
- **Render**: deployment platform  

---

## 4. Database

### `products` Table

Core table that stores scraped products.

Main fields:
- `id`: unique identifier  
- `store`: source store  
- `name`: product name  
- `price`: product price  
- `currency`: currency  
- `url`: unique product identifier  
- `scraped_at`: last update timestamp  

An `ON CONFLICT (url)` strategy is used to prevent duplicates and keep data updated.

---

### `users` Table

Handles authentication.

Fields:
- `id`  
- `username`  
- `password_hash`  
- `is_active`  
- `created_at`  

---

## 5. REST API

Main endpoints:

- `GET /health` → system status  
- `GET /products/` → product listing with filters  
- `GET /products/compare/` → grouped comparison by store  
- `GET /products/stores/` → store summary  
- `GET /products/cheapest/` → cheapest product per store  
- `GET /products/{id}` → product detail  

Authentication endpoints:

- `GET /users/login` → login form  
- `POST /users/login` → login + JWT  
- `GET /users/dashboard` → protected view  
- `POST /users/logout` → logout  

---

## 6. Authentication System

### Flow

1. User submits credentials  
2. Credentials are validated against the database  
3. JWT is generated with `sub` claim  
4. Token is stored in an HTTP-only cookie  
5. Token is validated on protected requests  

---

### Security

- Password hashing with bcrypt  
- JWT signed using `SECRET_KEY`  
- Configurable expiration  
- Cookie settings: `httponly=True`, `samesite=lax`  

---

## 7. Error Handling

- `HTTPException` for API errors  
- `400` → invalid parameters  
- `404` → resource not found  
- `401` → invalid login (HTML response)  

Authentication uses HTML responses instead of JSON for user-facing flows.

---

## 8. Templates and Static Files

Jinja2 is used for:

- `login.html`  
- `dashboard.html`  

Static files exist but are not yet mounted using `StaticFiles`.

---

## 9. Deployment

### Render

Configuration includes:

- `uvicorn api.main:app`  
- environment variables (`DATABASE_URL`, `SECRET_KEY`)  
- health check endpoint `/health`  

---

### Docker

The current Docker setup runs the scraper, not the API.

---

## 10. Testing

Testing stack:

- `unittest`  
- `FastAPI TestClient`  

Covered areas:
- health check  
- parameter validation  
- product endpoints  

Not covered:
- authentication  
- JWT  
- scraping  

---

## 11. Design Decisions

- **Raw SQL over ORM** to maintain control and simplicity in the MVP  
- **JWT stored in HTTP-only cookies** for a simpler web-based authentication flow  
- Modular separation (`routers`, `services`, `utils`) for maintainability  
- FastAPI chosen for strong typing, validation, and auto-generated docs  
- **Upsert strategy using URL** to prevent duplicates  

---

## 12. Future Improvements

### Architecture
- Add migrations (Alembic)  
- Introduce a data access layer  

### Security
- Enable `secure=True` in cookies  
- Add CSRF protection  

### Features
- Price history tracking  
- More stores  
- Configurable scraping  

### Testing
- Authentication tests  
- JWT validation tests  

### DevOps
- Structured logging  
- Observability  
- Full CI/CD pipeline  

---

## Conclusion

Scrabby provides a solid foundation for a modern backend system, integrating scraping, persistence, REST API, and authentication.

The project demonstrates an understanding of the full backend lifecycle, from data acquisition to secure data exposure, and establishes a scalable base for future improvements.