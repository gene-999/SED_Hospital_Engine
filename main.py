from contextlib import asynccontextmanager

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.mongodb import init_db
from app.workers.expiry import expire_reservations

from app.api.auth import router as auth_router
from app.api.hospitals import router as hospitals_router
from app.api.wards import router as wards_router
from app.api.beds import router as beds_router
from app.api.reservations import router as reservations_router
from app.api.search import router as search_router
from app.api.websocket import router as ws_router
from app.api.vapi import router as vapi_router

scheduler = AsyncIOScheduler()


async def _self_ping() -> None:
    """Hits our own /ping endpoint so Render doesn't spin down the dyno."""
    if not settings.RENDER_EXTERNAL_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.get(f"{settings.RENDER_EXTERNAL_URL}/ping")
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    scheduler.add_job(expire_reservations, "interval", minutes=1, id="expiry_job")
    # Ping every 10 minutes — well within Render's 15-min idle timeout
    scheduler.add_job(_self_ping, "interval", minutes=10, id="self_ping")
    scheduler.start()

    yield

    scheduler.shutdown()


app = FastAPI(
    title=settings.APP_NAME,
    description="Hospital bed reservation system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(hospitals_router)
app.include_router(wards_router)
app.include_router(beds_router)
app.include_router(reservations_router)
app.include_router(search_router)
app.include_router(ws_router)
app.include_router(vapi_router)


@app.get("/", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/ping", tags=["health"])
async def ping() -> dict:
    return {"pong": True}
