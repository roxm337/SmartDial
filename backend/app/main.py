from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import configure_logging, get_settings
from app.db import init_db
from app.routes.agents import router as agents_router
from app.routes.calls import router as calls_router
from app.routes.campaigns import router as campaigns_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    init_db()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router)
app.include_router(campaigns_router)
app.include_router(calls_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
