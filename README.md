# Invoice Agent

Invoice generation service for pricing, totals, taxes, and downstream stock-aware billing workflows.

## What This Service Does

- generates invoices from product and quantity inputs
- validates and reserves stock through the Inventory Agent
- optionally incorporates Market Intelligence pricing guidance
- calculates subtotal, tax, and grand total
- persists structured invoice results in PostgreSQL
- returns invoice outputs suitable for downstream use

## Default Port

`8002`

## Local Base URL

`http://localhost:8002`

## Depends On

- `inventory-agent` on `8001`
- `market-intelligence-agent` on `8003`
- PostgreSQL on `5432`

## PostgreSQL Requirement

This service expects PostgreSQL to already be running before startup.

Recommended local database settings:

- host: `localhost`
- port: `5432`
- database: `workfall_multi_agent`
- user: `workfall`
- password: `workfall`

Tables are created automatically on startup. You do not need to manually create Invoice tables if the configured database is reachable and the user has permission to create tables.

## Tech Used Here

- FastAPI
- PostgreSQL via `psycopg`
- A2A-style downstream calls to Inventory and Market Intelligence

## Environment Setup

1. Copy the example file:

```powershell
copy .env.example .env
```

2. Update values if needed, especially:

- `DATABASE_URL`
- `INVENTORY_BASE_URL`
- `MARKET_INTELLIGENCE_BASE_URL`

Example:

```env
DATABASE_URL=postgresql://workfall:workfall@localhost:5432/workfall_multi_agent
```

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run Locally

```powershell
uvicorn app.main:app --reload --port 8002
```

## Key Endpoints

- `GET /api/v1/health`
- `GET /api/v1/capabilities`
- `GET /api/v1/invoices/{invoice_id}`
- `POST /api/v1/invoices`
- `POST /api/v1/a2a/request`

## Repo Structure

```text
invoice-agent/
  app/
    api/
    clients/
    core/
    schemas/
    services/
  tests/
  .env.example
  requirements.txt
  .gitignore
  README.md
```

## Notes

- invoices reserve stock before finalizing the result
- market insight usage is explicit in `market_insight_status`
- invoice outputs include downstream workflow metadata for tracing
