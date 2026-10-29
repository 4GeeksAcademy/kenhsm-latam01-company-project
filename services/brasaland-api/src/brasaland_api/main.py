"""FastAPI application entrypoint: registers all module routers."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path


from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from brasaland_api.core.config import get_settings
from brasaland_api.core.schemas import HealthOut
from brasaland_api.core.db import init_inventory_db
from brasaland_api.modules.agent.router import router as agent_router
from brasaland_api.modules.agent.chat import router as agent_chat_router
from brasaland_api.modules.auth.router import router as auth_router
from brasaland_api.modules.hr.router import router as hr_router
from brasaland_api.modules.knowledge.router import router as knowledge_router
from brasaland_api.modules.operations.router import router as operations_router
from brasaland_api.modules.profiles.router import router as profiles_router
from brasaland_api.modules.supply_chain.router import router as supply_chain_router
from brasaland_api.modules.telemetry.router import router as telemetry_router
from brasaland_api.modules.tasks import router as tasks_router
from brasaland_api.modules.users.router import router as users_router
from brasaland_api.modules.incidents.router import router as incidents_router
from brasaland_api.modules.rfp_intake.router import router as rfp_intake_router
from brasaland_api.modules.inventory.router import router as inventory_router
from services.reporting.router import router as reporting_router

settings = get_settings()
if settings.supabase_url:
    os.environ.setdefault("SUPABASE_URL", settings.supabase_url)
for variable_name, secret in (
    ("SUPABASE_SECRET_KEY", settings.supabase_secret_key),
    ("SUPABASE_SERVICE_ROLE_KEY", settings.supabase_service_role_key),
):
    if secret:
        os.environ.setdefault(variable_name, secret.get_secret_value())

app = FastAPI(title="Brasaland API", version="0.1.0")
timing_logger = logging.getLogger("api.timing")
timing_logger.setLevel(logging.INFO)
if not timing_logger.handlers:
    timing_handler = logging.StreamHandler()
    timing_handler.setFormatter(logging.Formatter("%(message)s"))
    timing_logger.addHandler(timing_handler)
timing_logger.propagate = False


@app.on_event("startup")
async def startup_event():
    """Initialize inventory database on startup."""
    try:
        init_inventory_db()
        logging.info("Inventory database initialized successfully.")
    except Exception as e:
        logging.warning(f"Could not initialize inventory database: {e}")


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    timing_logger.info(
        "%s %s -> %s | %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Ha ocurrido un error interno. Inténtalo de nuevo más tarde."})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    fields = {".".join(str(part) for part in item["loc"] if part != "body"): "Revisa este campo." for item in error.errors()}
    return JSONResponse(status_code=400, content={"detail": {"message": "La solicitud contiene datos inválidos.", "fields": fields}})

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(agent_chat_router)
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(operations_router)
app.include_router(incidents_router)
app.include_router(rfp_intake_router)
app.include_router(supply_chain_router)
app.include_router(inventory_router)
app.include_router(hr_router)
app.include_router(telemetry_router)
app.include_router(tasks_router)
app.include_router(knowledge_router)
app.include_router(reporting_router)


@app.get("/health", response_model=HealthOut, tags=["health"])
def health_check() -> HealthOut:
    return HealthOut(status="ok")
