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

# Configure CORS using settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.origins_list,
    allow_credentials=settings.cors.allow_credentials,
    allow_methods=settings.cors.allow_methods,
    allow_headers=settings.cors.allow_headers,
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
