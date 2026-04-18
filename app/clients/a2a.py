from __future__ import annotations

from uuid import uuid4

import httpx

from app.core.db import record_trace
from app.core.security import make_headers
from app.schemas.common import A2AContext, A2ARequest


async def call_agent(base_url: str, intent: str, payload: dict, context: A2AContext) -> dict:
    request = A2ARequest(
        request_id=str(uuid4()),
        source_agent="invoice",
        target_agent=base_url,
        intent=intent,
        context=context,
        payload=payload,
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url}/api/v1/a2a/request",
            json=request.model_dump(),
            headers=make_headers(),
        )
        response.raise_for_status()
        result = response.json()
        record_trace(
            context=context,
            step_name=f"invoice_a2a_{intent}",
            step_type="a2a_call",
            status=result.get("status", "success"),
            input_payload={"base_url": base_url, "payload": payload},
            output_payload=result,
        )
        return result
