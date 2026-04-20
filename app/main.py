from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Invoice startup mirrors the other services so local runs and compose behave the same way.
    try:
        init_db()
        app.state.db_available = True
    except Exception:
        app.state.db_available = False
        raise
    yield


app = FastAPI(title="Invoice Agent", version="0.2.0", lifespan=lifespan)
app.state.db_available = False
app.include_router(router)
