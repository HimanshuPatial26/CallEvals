from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import agents, calls, leads, org, settings as settings_router

app = FastAPI(title="CallEvals — Sahil Phase 0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calls.router)
app.include_router(agents.router)
app.include_router(leads.router)
app.include_router(org.router)
app.include_router(settings_router.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    """No frontend served from here — this is an API-only backend, the React
    app is a separate deployment. Exists so hitting the bare domain in a
    browser (e.g. right after a deploy, to sanity-check it's up) shows
    something useful instead of a bare 404."""
    return {"service": "CallEvals API", "health": "/api/health", "docs": "/docs"}
