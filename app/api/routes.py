from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Header

from app.core.config import INVENTORY_BASE_URL, MARKET_INTELLIGENCE_BASE_URL, SERVICE_NAME, SERVICE_PORT
from app.core.db import fetch_invoice
from app.core.security import require_agent_token, require_api_token
from app.core.utils import now_iso
from app.schemas.common import A2AError, A2AMeta, A2ARequest, A2AResponse, A2AContext
from app.schemas.invoice import InvoiceItemRequest, InvoiceRequest
from app.services.invoice_service import build_invoice


router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health() -> dict:
    from app.main import app
    db_available = app.state.db_available

    return {
        "status": "ok" if db_available else "degraded",
        "service": SERVICE_NAME,
        "port": SERVICE_PORT,
        "inventory_base_url": INVENTORY_BASE_URL,
        "market_base_url": MARKET_INTELLIGENCE_BASE_URL,
        "db_available": db_available,
        "timestamp": now_iso(),
    }


@router.get("/capabilities")
def capabilities() -> dict:
    return {"service": SERVICE_NAME, "intents": ["create_invoice"]}


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str, x_api_token: str | None = Header(default=None)) -> dict:
    require_api_token(x_api_token)
    return fetch_invoice(invoice_id)


@router.post("/invoices")
async def create_invoice(invoice_request: InvoiceRequest, x_api_token: str | None = Header(default=None)) -> dict:
    require_api_token(x_api_token)
    # Direct UI calls still get full trace/session ids so they line up with the rest of the system.
    context = A2AContext(
        session_id=invoice_request.session_id or str(uuid4()),
        workflow_id=invoice_request.workflow_id or str(uuid4()),
        trace_id=invoice_request.trace_id or str(uuid4()),
    )
    return await build_invoice(invoice_request, context)


@router.post("/a2a/request", response_model=A2AResponse)
async def a2a_request(request: A2ARequest, x_agent_token: str | None = Header(default=None)) -> A2AResponse:
    require_agent_token(x_agent_token)
    if request.intent != "create_invoice":
        return A2AResponse(
            request_id=request.request_id,
            status="failed",
            agent="invoice",
            result=None,
            error=A2AError(code="UNSUPPORTED_INTENT", message="Unsupported invoice intent", retriable=False),
            meta=A2AMeta(retry_count=0, timestamp=now_iso(), source_service=SERVICE_NAME, target_service="caller"),
        )

    try:
        payload_items = [InvoiceItemRequest(**item) for item in request.payload.get("items", [])]
        invoice_request = InvoiceRequest(
            items=payload_items,
            customer_name=request.payload.get("customer_name", "Internal Demo Customer"),
            include_market_insights=request.payload.get("include_market_insights", True),
            session_id=request.context.session_id,
            workflow_id=request.context.workflow_id,
            trace_id=request.context.trace_id,
        )
        result = await build_invoice(invoice_request, request.context)
        return A2AResponse(
            request_id=request.request_id,
            status="success",
            agent="invoice",
            result=result,
            error=None,
            meta=A2AMeta(retry_count=0, timestamp=now_iso(), source_service=SERVICE_NAME, target_service="caller"),
        )
    except Exception as exc:
        return A2AResponse(
            request_id=request.request_id,
            status="failed",
            agent="invoice",
            result=None,
            error=A2AError(code="INVOICE_ERROR", message=str(getattr(exc, "detail", exc)), retriable=False),
            meta=A2AMeta(retry_count=0, timestamp=now_iso(), source_service=SERVICE_NAME, target_service="caller"),
        )
