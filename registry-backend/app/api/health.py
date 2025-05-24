"""
registry-backend/app/api/health.py
"""
# Third-party imports
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

# Local imports
from app.database.supabase import get_db
from app.config import settings

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "qinter-registry",
        "version": "1.0.0"
    }


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check."""
    # Test database
    db.execute(text("SELECT 1"))
    
    # Test storage
    from app.services.upload_service import upload_service
    storage_stats = upload_service.get_storage_stats()
    storage_healthy = "error" not in storage_stats
    
    return {
        "status": "healthy" if storage_healthy else "degraded",
        "service": "qinter-registry",
        "checks": {
            "database": "healthy",
            "storage": "healthy" if storage_healthy else "degraded"
        },
        "storage_info": storage_stats
    }