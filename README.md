# Invoice Agent

Invoice generation service for pricing, taxes, totals, and downstream invoice output.

## Responsibilities

- validate stock through Inventory Agent
- incorporate pricing context and market insight data
- compute item totals, taxes, and final invoice totals
- return structured invoice outputs
- persist generated invoices in PostgreSQL

## Default Port

`8002`

## Local Run Target

`http://localhost:8002`

## Planned Dependencies

- FastAPI
- Uvicorn
- Pydantic
- httpx
- pytest

## Run Locally

```bash
uvicorn app.main:app --reload --port 8002
```

## Key Endpoints

- `GET /api/v1/health`
- `GET /api/v1/capabilities`
- `POST /api/v1/invoices`
- `POST /api/v1/a2a/request`

## Repo Layout

```text
invoice-agent/
  app/
    api/
    clients/
    core/
    models/
    schemas/
    services/
    agents/
    graphs/
  tests/
  .env.example
  requirements.txt
  .gitignore
  README.md
```
