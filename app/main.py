import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app import storage
from app.config import get_settings
from app.routers import (
    admin_permissions,
    areas,
    auth,
    categories,
    messages,
    notifications,
    org_units,
    posts,
)

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())

@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        storage.ensure_bucket()
    except Exception as e:  # noqa: BLE001 - don't crash API if storage is slow to come up
        logging.getLogger("startup").warning("bucket ensure failed: %s", e)
    yield


app = FastAPI(title="Nobojatra Portal API", version="0.1.0", lifespan=lifespan)


class NoStoreMiddleware(BaseHTTPMiddleware):
    """spec 11.2: content responses must not be cached anywhere. Blanket the API;
    the frontend serves its own hashed static assets separately."""

    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("Cache-Control", "no-store")
        return resp


app.add_middleware(NoStoreMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, areas, org_units, categories, posts, messages, notifications, admin_permissions):
    app.include_router(r.router)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}
