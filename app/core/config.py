from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

SERVICE_NAME = os.getenv("SERVICE_NAME", "invoice-agent")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8002"))
INVENTORY_BASE_URL = os.getenv("INVENTORY_BASE_URL", "http://localhost:8001")
MARKET_INTELLIGENCE_BASE_URL = os.getenv("MARKET_INTELLIGENCE_BASE_URL", "http://localhost:8003")
A2A_SHARED_TOKEN = os.getenv("A2A_SHARED_TOKEN", "")
TAX_RATE = float(os.getenv("TAX_RATE", "0.18"))
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://workfall:workfall@localhost:5432/workfall_multi_agent",
)
