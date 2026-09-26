"""FastAPI application entrypoint: registers all module routers."""

from __future__ import annotations

from fastapi import FastAPI

from brasaland_api.modules.auth.router import router as auth_router
from brasaland_api.modules.hr.router import router as hr_router
from brasaland_api.modules.operations.router import router as operations_router
from brasaland_api.modules.profiles.router import router as profiles_router
from brasaland_api.modules.supply_chain.router import router as supply_chain_router
from brasaland_api.modules.users.router import router as users_router

app = FastAPI(title="Brasaland API", version="0.1.0")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(operations_router)
app.include_router(supply_chain_router)
app.include_router(hr_router)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok"}
