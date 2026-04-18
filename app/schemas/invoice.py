from __future__ import annotations

from pydantic import BaseModel, Field


class InvoiceItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)


class InvoiceRequest(BaseModel):
    items: list[InvoiceItemRequest]
    customer_name: str = "Internal Demo Customer"
    include_market_insights: bool = True
