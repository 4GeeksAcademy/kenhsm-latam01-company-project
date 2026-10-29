"""FastAPI application for Brasaland Supplier Directory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

try:
    from .database import init_db
    from .routes import suppliers
except ImportError:
    from database import init_db
    from routes import suppliers

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield

app = FastAPI(
    title="Brasaland Supplier Directory API",
    description="API for managing Brasaland supplier directory",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Brasaland Supplier Directory API"}
