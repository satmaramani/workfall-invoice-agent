from __future__ import annotations

from typing import Any

import psycopg
from fastapi import HTTPException, status
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import DATABASE_URL, SERVICE_NAME
from app.schemas.common import A2AContext


def get_connection() -> psycopg.Connection[Any]:
    try:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    except psycopg.Error as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Invoice database unavailable: {exc}",
        ) from exc


def init_db() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS invoices (
                    invoice_id TEXT PRIMARY KEY,
                    customer_name TEXT NOT NULL,
                    subtotal NUMERIC(12, 2) NOT NULL,
                    tax_rate NUMERIC(6, 4) NOT NULL,
                    tax_amount NUMERIC(12, 2) NOT NULL,
                    total_amount NUMERIC(12, 2) NOT NULL,
                    market_insight_status TEXT NOT NULL,
                    market_summaries JSONB NOT NULL DEFAULT '[]'::jsonb,
                    session_id TEXT,
                    workflow_id TEXT,
                    trace_id TEXT,
                    generated_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS invoice_items (
                    id BIGSERIAL PRIMARY KEY,
                    invoice_id TEXT NOT NULL REFERENCES invoices(invoice_id) ON DELETE CASCADE,
                    product_id TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price NUMERIC(12, 2) NOT NULL,
                    line_total NUMERIC(12, 2) NOT NULL,
                    pricing_source TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_traces (
                    id BIGSERIAL PRIMARY KEY,
                    service_name TEXT NOT NULL,
                    session_id TEXT,
                    workflow_id TEXT,
                    trace_id TEXT,
                    step_name TEXT NOT NULL,
                    step_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_payload JSONB,
                    output_payload JSONB,
                    error_message TEXT,
                    model_name TEXT,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        conn.commit()


def record_trace(
    *,
    context: A2AContext | None,
    step_name: str,
    step_type: str,
    status: str,
    input_payload: dict | None = None,
    output_payload: dict | None = None,
    error_message: str | None = None,
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workflow_traces (
                    service_name, session_id, workflow_id, trace_id,
                    step_name, step_type, status, input_payload, output_payload, error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    SERVICE_NAME,
                    context.session_id if context else None,
                    context.workflow_id if context else None,
                    context.trace_id if context else None,
                    step_name,
                    step_type,
                    status,
                    Jsonb(input_payload) if input_payload is not None else None,
                    Jsonb(output_payload) if output_payload is not None else None,
                    error_message,
                ),
            )
        conn.commit()


def persist_invoice(result: dict, context: A2AContext) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO invoices (
                    invoice_id, customer_name, subtotal, tax_rate, tax_amount, total_amount,
                    market_insight_status, market_summaries, session_id, workflow_id, trace_id, generated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    result["invoice_id"],
                    result["customer_name"],
                    result["subtotal"],
                    result["tax_rate"],
                    result["tax_amount"],
                    result["total_amount"],
                    result["market_insight_status"],
                    Jsonb(result["market_summaries"]),
                    context.session_id,
                    context.workflow_id,
                    context.trace_id,
                    result["generated_at"],
                ),
            )
            for item in result["items"]:
                cur.execute(
                    """
                    INSERT INTO invoice_items (
                        invoice_id, product_id, product_name, quantity, unit_price, line_total, pricing_source
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        result["invoice_id"],
                        item["product_id"],
                        item["product_name"],
                        item["quantity"],
                        item["unit_price"],
                        item["line_total"],
                        item["pricing_source"],
                    ),
                )
        conn.commit()
    record_trace(context=context, step_name="persist_invoice", step_type="db_write", status="success", input_payload={"invoice_id": result["invoice_id"]})


def fetch_invoice(invoice_id: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM invoices WHERE invoice_id = %s", (invoice_id,))
            invoice = cur.fetchone()
            if not invoice:
                raise HTTPException(status_code=404, detail="Invoice not found")
            cur.execute(
                """
                SELECT product_id, product_name, quantity, unit_price, line_total, pricing_source
                FROM invoice_items
                WHERE invoice_id = %s
                ORDER BY id ASC
                """,
                (invoice_id,),
            )
            items = cur.fetchall()
    return {
        "invoice_id": invoice["invoice_id"],
        "customer_name": invoice["customer_name"],
        "subtotal": float(invoice["subtotal"]),
        "tax_rate": float(invoice["tax_rate"]),
        "tax_amount": float(invoice["tax_amount"]),
        "total_amount": float(invoice["total_amount"]),
        "market_insight_status": invoice["market_insight_status"],
        "market_summaries": invoice["market_summaries"],
        "generated_at": invoice["generated_at"].isoformat(),
        "items": [
            {
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "quantity": item["quantity"],
                "unit_price": float(item["unit_price"]),
                "line_total": float(item["line_total"]),
                "pricing_source": item["pricing_source"],
            }
            for item in items
        ],
    }
