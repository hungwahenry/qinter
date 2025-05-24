# registry-backend/app/api/registry.py - New file for registry management
# Standard library imports
from datetime import datetime

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

# Local imports
from app.config import settings
from app.database.supabase import get_db
from app.models.package import Package as PackageModel, PackageVersion, DownloadStat

router = APIRouter()


@router.get("/info")
async def get_registry_info(db: Session = Depends(get_db)):
    """Get registry information and statistics."""
    
    # Package counts
    total_packages = db.query(PackageModel).filter(PackageModel.is_active == True).count()
    verified_packages = db.query(PackageModel).filter(
        PackageModel.is_active == True,
        PackageModel.is_verified == True
    ).count()
    
    # Version counts
    total_versions = db.query(PackageVersion).filter(PackageVersion.is_active == True).count()
    
    # Download counts
    total_downloads = db.query(func.sum(PackageModel.download_count)).scalar() or 0
    
    # Exception types covered
    exception_types = db.query(PackageModel.targets).filter(
        PackageModel.is_active == True,
        PackageModel.targets.isnot(None)
    ).all()
    
    all_types = set()
    for types_list in exception_types:
        if types_list[0]:
            all_types.update(types_list[0])
    
    # Popular tags
    all_tags = db.query(PackageModel.tags).filter(
        PackageModel.is_active == True,
        PackageModel.tags.isnot(None)
    ).all()
    
    tag_counts = {}
    for tags_list in all_tags:
        if tags_list[0]:
            for tag in tags_list[0]:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    popular_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "registry": {
            "name": "Qinter Package Registry",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "type": "upload-only"  # Indicate this is upload-only
        },
        "statistics": {
            "packages": {
                "total": total_packages,
                "verified": verified_packages,
                "unverified": total_packages - verified_packages
            },
            "versions": {
                "total": total_versions,
                "average_per_package": round(total_versions / max(total_packages, 1), 2)
            },
            "downloads": {
                "total": total_downloads,
                "average_per_package": round(total_downloads / max(total_packages, 1), 2)
            },
            "coverage": {
                "exception_types": sorted(list(all_types)),
                "exception_types_count": len(all_types)
            },
            "tags": {
                "popular": [{"tag": tag, "count": count} for tag, count in popular_tags],
                "total_unique": len(tag_counts)
            }
        },
        "storage": {
            "type": "local_filesystem",
            "location": str(settings.upload_directory) if hasattr(settings, 'upload_directory') else "~/.qinter/registry/uploads"
        }
    }


@router.get("/status")
async def get_registry_status(db: Session = Depends(get_db)):
    """Get detailed registry status."""
    
    # Test database connection
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
        db_error = None
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)
    
    # Test local storage
    try:
        from app.services.upload_service import upload_service
        storage_stats = upload_service.get_storage_stats()
        storage_status = "healthy" if "error" not in storage_stats else "unhealthy"
        storage_error = storage_stats.get("error")
    except Exception as e:
        storage_status = "unhealthy"
        storage_error = str(e)
    
    # Overall status
    overall_status = "healthy" if db_status == "healthy" and storage_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": {
                "status": db_status,
                "error": db_error
            },
            "storage": {
                "status": storage_status,
                "error": storage_error
            }
        }
    }