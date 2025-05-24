# Standard library imports
import logging

# Third-party imports
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Local imports
from app.config import settings
from app.api import packages, health, versions, stats, registry, validation, auth, upload
from app.database.supabase import test_connection, get_connection_info
from app.database.migrations import run_migrations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Qinter Package Registry",
    version="1.0.0",
    description="Upload-only registry for Qinter explanation packages",
    docs_url="/docs" if settings.DEBUG else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])
app.include_router(upload.router, prefix=f"{settings.API_V1_STR}/upload", tags=["upload"])
app.include_router(packages.router, prefix=f"{settings.API_V1_STR}/packages", tags=["packages"])
app.include_router(versions.router, prefix=f"{settings.API_V1_STR}/packages", tags=["versions"])
app.include_router(stats.router, prefix=f"{settings.API_V1_STR}/stats", tags=["statistics"])
app.include_router(registry.router, prefix=f"{settings.API_V1_STR}/registry", tags=["registry"])
app.include_router(validation.router, prefix=f"{settings.API_V1_STR}/validate", tags=["validation"])
app.include_router(health.router, prefix="/health", tags=["health"])


@app.get("/")
async def root():
    """Root endpoint with API overview."""
    return {
        "service": "Qinter Package Registry",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "type": "upload-only",
        "endpoints": {
            "health": "/health",
            "authentication": f"{settings.API_V1_STR}/auth",
            "upload": f"{settings.API_V1_STR}/upload",
            "packages": f"{settings.API_V1_STR}/packages",
            "search": f"{settings.API_V1_STR}/packages/search",
            "statistics": f"{settings.API_V1_STR}/stats",
            "registry": f"{settings.API_V1_STR}/registry",
            "validation": f"{settings.API_V1_STR}/validate",
            "docs": "/docs" if settings.DEBUG else "disabled"
        },
        "features": {
            "package_management": True,
            "user_authentication": True,
            "package_upload": True,
            "version_tracking": True,
            "search": True,
            "statistics": True,
            "validation": True,
            "download_tracking": True,
            "github_integration": False  # Explicitly disabled
        },
        "authentication": {
            "type": "API Key",
            "registration": "open_with_approval",
            "scopes": ["read", "write", "delete"]
        }
    }


@app.on_event("startup")
async def startup_event():
    """Validate configuration and initialize services on startup."""
    logger.info("🚀 Starting Qinter Registry API (Upload-Only)")
    
    # Validate configuration
    config_errors = settings.validate_configuration()
    if config_errors:
        logger.error("❌ Configuration validation failed:")
        for error in config_errors:
            logger.error(f"   - {error}")
        raise HTTPException(status_code=500, detail="Configuration validation failed")
    
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Run database migrations
    if not run_migrations():
        logger.error("❌ Database migration failed")
        raise HTTPException(status_code=500, detail="Database migration failed")
    
    # Test database connection
    if test_connection():
        logger.info("✅ Database connection successful")
        logger.info(f"Database info: {get_connection_info()}")
    else:
        logger.error("❌ Database connection failed")
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    # Initialize upload storage
    try:
        from app.services.upload_service import upload_service
        storage_stats = upload_service.get_storage_stats()
        logger.info(f"✅ Storage initialized: {storage_stats['upload_directory']}")
        logger.info(f"📦 Current storage: {storage_stats['package_count']} packages, {storage_stats['total_size_mb']} MB")
    except Exception as e:
        logger.error(f"❌ Storage initialization failed: {e}")
        raise HTTPException(status_code=500, detail="Storage initialization failed")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("🛑 Shutting down Qinter Registry API")