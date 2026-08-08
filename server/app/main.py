from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import agents, calls, leads, organization, roster

app = FastAPI(title="CallEvals — Sahil Phase 0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roster.router)
app.include_router(calls.router)
app.include_router(agents.router)
app.include_router(leads.router)
app.include_router(organization.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
