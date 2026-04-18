from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException, status

from app.clients.a2a import call_agent
from app.core.config import INVENTORY_BASE_URL, MARKET_INTELLIGENCE_BASE_URL, TAX_RATE
from app.core.db import persist_invoice
from app.core.utils import now_iso
from app.schemas.common import A2AContext
from app.schemas.invoice import InvoiceRequest


async def build_invoice(invoice_request: InvoiceRequest, context: A2AContext) -> dict:
    reservations = []
    line_items = []
    try:
        for item in invoice_request.items:
            inventory_check = await call_agent(
                INVENTORY_BASE_URL,
                "check_stock",
                {"product_id": item.product_id, "quantity": item.quantity},
                context,
            )
            if inventory_check["status"] != "success" or not inventory_check["result"]["is_available"]:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Insufficient stock for {item.product_id}")

        subtotal = 0.0
        market_summaries = []
        for item in invoice_request.items:
            market_result = None
            if invoice_request.include_market_insights:
                market_response = await call_agent(
                    MARKET_INTELLIGENCE_BASE_URL,
                    "pricing_support",
                    {"product_id": item.product_id},
                    context,
                )
                if market_response["status"] == "success":
                    market_result = market_response["result"]

            reservation = await call_agent(
                INVENTORY_BASE_URL,
                "reserve_stock",
                {"product_id": item.product_id, "quantity": item.quantity},
                context,
            )
            if reservation["status"] != "success":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Unable to reserve stock for {item.product_id}")

            reservations.append(item)
            product = reservation["result"]["product"]
            unit_price = market_result["recommended_price"] if invoice_request.include_market_insights and market_result else product["unit_price"]
            line_total = round(unit_price * item.quantity, 2)
            subtotal += line_total
            line_items.append(
                {
                    "product_id": item.product_id,
                    "product_name": product["product_name"],
                    "quantity": item.quantity,
                    "unit_price": round(unit_price, 2),
                    "line_total": line_total,
                    "pricing_source": "market_intelligence" if market_result else "inventory",
                }
            )
            if market_result:
                market_summaries.append(
                    {
                        "product_id": item.product_id,
                        "trend": market_result["trend"],
                        "recommended_price": market_result["recommended_price"],
                        "summary": market_result["summary"],
                        "citations": market_result.get("citations", []),
                    }
                )

        tax_amount = round(subtotal * TAX_RATE, 2)
        total_amount = round(subtotal + tax_amount, 2)
        result = {
            "invoice_id": f"INV-{uuid4().hex[:8].upper()}",
            "customer_name": invoice_request.customer_name,
            "items": line_items,
            "subtotal": round(subtotal, 2),
            "tax_rate": TAX_RATE,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "market_insight_status": "used" if invoice_request.include_market_insights else "skipped",
            "market_summaries": market_summaries,
            "generated_at": now_iso(),
        }
        persist_invoice(result, context)
        return result
    except Exception:
        for item in reservations:
            await call_agent(INVENTORY_BASE_URL, "release_stock", {"product_id": item.product_id, "quantity": item.quantity}, context)
        raise
