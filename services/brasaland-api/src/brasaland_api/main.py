"""FastAPI application entrypoint: registers all module routers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from brasaland_api.core.config import get_settings
<<<<<<< HEAD
from brasaland_api.core.schemas import HealthOut
=======
>>>>>>> origin/main
from brasaland_api.modules.auth.router import router as auth_router
from brasaland_api.modules.hr.router import router as hr_router
from brasaland_api.modules.operations.router import router as operations_router
from brasaland_api.modules.profiles.router import router as profiles_router
from brasaland_api.modules.supply_chain.router import router as supply_chain_router
from brasaland_api.modules.users.router import router as users_router
from brasaland_api.modules.incidents.router import router as incidents_router

app = FastAPI(title="Brasaland API", version="0.1.0")


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
app.include_router(incidents_router)


<<<<<<< HEAD
@app.get("/health", response_model=HealthOut, tags=["health"])
def health_check() -> HealthOut:
    return HealthOut(status="ok")
=======
@app.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok"}
>>>>>>> origin/main
