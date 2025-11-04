from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import artifacts_router
from .api.preservation import router as preservation_router
from .api.collections import router as collections_router
from .factory import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Digital preservation system for cultural heritage artifacts",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Alternative dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Include API routers
app.include_router(artifacts_router)
app.include_router(preservation_router)
app.include_router(collections_router)


@app.get("/")
def read_root():
    return {
        "message": "Griot and Grits Digital Preservation API",
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "artifacts": "/artifacts",
            "preservation": "/preservation",
            "collections": "/collections" if settings.globus.enabled else None,
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "storage": {
            "hot": settings.storage.endpoint,
            "archive_enabled": settings.globus.enabled,
        },
    }
