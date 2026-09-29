"""FastAPI application entrypoint: registers all module routers."""

from __future__ import annotations

import logging
import time


from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request

from brasaland_api.core.config import get_settings
from brasaland_api.core.schemas import HealthOut
from brasaland_api.modules.auth.router import router as auth_router
from brasaland_api.modules.hr.router import router as hr_router
from brasaland_api.modules.operations.router import router as operations_router
from brasaland_api.modules.profiles.router import router as profiles_router
from brasaland_api.modules.supply_chain.router import router as supply_chain_router
from brasaland_api.modules.telemetry.router import router as telemetry_router
from brasaland_api.modules.users.router import router as users_router
from brasaland_api.modules.incidents.router import router as incidents_router

app = FastAPI(title="Brasaland API", version="0.1.0")
timing_logger = logging.getLogger("api.timing")
timing_logger.setLevel(logging.INFO)
if not timing_logger.handlers:
    timing_handler = logging.StreamHandler()
    timing_handler.setFormatter(logging.Formatter("%(message)s"))
    timing_logger.addHandler(timing_handler)
timing_logger.propagate = False


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
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(operations_router)
app.include_router(supply_chain_router)
app.include_router(hr_router)
app.include_router(telemetry_router)


@app.get("/health", response_model=HealthOut, tags=["health"])
def health_check() -> HealthOut:
    return HealthOut(status="ok")
