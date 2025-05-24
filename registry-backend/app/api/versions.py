# registry-backend/app/api/versions.py

# Standard library imports
from typing import List, Optional

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Local imports
from app.database.supabase import get_db
from app.models.package import Package as PackageModel, PackageVersion
from app.services.package_service import package_service

router = APIRouter()


@router.get("/{package_name}/versions")
async def get_package_versions(
    package_name: str,
    db: Session = Depends(get_db)
):
    """Get all versions of a package."""
    # Check if package exists
    package = await package_service.get_package_by_name(db, package_name)
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Get all versions
    versions = db.query(PackageVersion).filter(
        PackageVersion.package_id == package.id,
        PackageVersion.is_active == True
    ).order_by(PackageVersion.created_at.desc()).all()
    
    return {
        "package_name": package_name,
        "versions": [
            {
                "version": v.version,
                "qinter_version": v.qinter_version,
                "file_size": v.file_size,
                "file_hash": v.file_hash,
                "created_at": v.created_at.isoformat(),
                "dependencies": v.dependencies or [],
                "changelog": v.changelog,
                "is_active": v.is_active
            }
            for v in versions
        ],
        "total_versions": len(versions)
    }


@router.get("/{package_name}/versions/{version}")
async def get_package_version_info(
    package_name: str,
    version: str,
    db: Session = Depends(get_db)
):
    """Get specific version information."""
    # Check if package exists
    package = await package_service.get_package_by_name(db, package_name)
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Get specific version
    version_info = db.query(PackageVersion).filter(
        PackageVersion.package_id == package.id,
        PackageVersion.version == version,
        PackageVersion.is_active == True
    ).first()
    
    if not version_info:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return {
        "package_name": package_name,
        "version": version_info.version,
        "qinter_version": version_info.qinter_version,
        "file_size": version_info.file_size,
        "file_hash": version_info.file_hash,
        "file_path": version_info.file_path,
        "created_at": version_info.created_at.isoformat(),
        "dependencies": version_info.dependencies or [],
        "changelog": version_info.changelog,
        "is_active": version_info.is_active
    }


@router.get("/{package_name}/latest")
async def get_latest_version(
    package_name: str,
    db: Session = Depends(get_db)
):
    """Get the latest version of a package."""
    # Check if package exists
    package = await package_service.get_package_by_name(db, package_name)
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Get latest version
    latest = db.query(PackageVersion).filter(
        PackageVersion.package_id == package.id,
        PackageVersion.is_active == True
    ).order_by(PackageVersion.created_at.desc()).first()
    
    if not latest:
        raise HTTPException(status_code=404, detail="No versions found")
    
    return {
        "package_name": package_name,
        "version": latest.version,
        "qinter_version": latest.qinter_version,
        "file_size": latest.file_size,
        "file_hash": latest.file_hash,
        "created_at": latest.created_at.isoformat(),
        "dependencies": latest.dependencies or [],
        "changelog": latest.changelog,
        "is_latest": True
    }


@router.get("/{package_name}/versions/{version}/download")
async def download_package_version(
    package_name: str,
    version: str,
    db: Session = Depends(get_db)
):
    """Download a specific version of a package."""
    # Check if package exists
    package = await package_service.get_package_by_name(db, package_name)
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Check if version exists
    version_info = db.query(PackageVersion).filter(
        PackageVersion.package_id == package.id,
        PackageVersion.version == version,
        PackageVersion.is_active == True
    ).first()
    
    if not version_info:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Get content from upload service
    content = await package_service.download_package(db, package_name, version)
    
    if not content:
        raise HTTPException(status_code=404, detail="Package content not found")
    
    return {
        "content": content,
        "metadata": {
            "name": package_name,
            "version": version_info.version,
            "qinter_version": version_info.qinter_version,
            "file_size": version_info.file_size,
            "file_hash": version_info.file_hash,
            "dependencies": version_info.dependencies or [],
            "created_at": version_info.created_at.isoformat()
        }
    }


@router.get("/{package_name}/versions/compare")
async def compare_package_versions(
    package_name: str,
    version1: str,
    version2: str,
    db: Session = Depends(get_db)
):
    """Compare two versions of a package."""
    # Check if package exists
    package = await package_service.get_package_by_name(db, package_name)
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Get both versions
    v1 = db.query(PackageVersion).filter(
        PackageVersion.package_id == package.id,
        PackageVersion.version == version1,
        PackageVersion.is_active == True
    ).first()
    
    v2 = db.query(PackageVersion).filter(
        PackageVersion.package_id == package.id,
        PackageVersion.version == version2,
        PackageVersion.is_active == True
    ).first()
    
    if not v1:
        raise HTTPException(status_code=404, detail=f"Version {version1} not found")
    
    if not v2:
        raise HTTPException(status_code=404, detail=f"Version {version2} not found")
    
    # Compare basic metadata
    comparison = {
        "package_name": package_name,
        "version1": {
            "version": v1.version,
            "qinter_version": v1.qinter_version,
            "file_size": v1.file_size,
            "dependencies": v1.dependencies or [],
            "created_at": v1.created_at.isoformat()
        },
        "version2": {
            "version": v2.version,
            "qinter_version": v2.qinter_version,
            "file_size": v2.file_size,
            "dependencies": v2.dependencies or [],
            "created_at": v2.created_at.isoformat()
        },
        "differences": {
            "qinter_version_changed": v1.qinter_version != v2.qinter_version,
            "file_size_changed": v1.file_size != v2.file_size,
            "file_size_difference": (v2.file_size or 0) - (v1.file_size or 0),
            "dependencies_changed": (v1.dependencies or []) != (v2.dependencies or []),
            "newer_version": v2.version if v2.created_at > v1.created_at else v1.version
        }
    }
    
    # Analyze dependency changes
    deps1 = set(v1.dependencies or [])
    deps2 = set(v2.dependencies or [])
    
    comparison["differences"]["dependency_changes"] = {
        "added": list(deps2 - deps1),
        "removed": list(deps1 - deps2),
        "unchanged": list(deps1 & deps2)
    }
    
    return comparison


@router.delete("/{package_name}/versions/{version}")
async def delete_package_version(
    package_name: str,
    version: str,
    db: Session = Depends(get_db)
):
    """
    Soft delete a specific version of a package.
    Note: This endpoint would typically require authentication and ownership checks.
    """
    # Check if package exists
    package = await package_service.get_package_by_name(db, package_name)
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Get the version
    version_info = db.query(PackageVersion).filter(
        PackageVersion.package_id == package.id,
        PackageVersion.version == version,
        PackageVersion.is_active == True
    ).first()
    
    if not version_info:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Check if this is the only version
    active_versions_count = db.query(PackageVersion).filter(
        PackageVersion.package_id == package.id,
        PackageVersion.is_active == True
    ).count()
    
    if active_versions_count <= 1:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete the last version of a package. Delete the package instead."
        )
    
    # Soft delete the version
    version_info.is_active = False
    db.commit()
    
    return {
        "message": f"Version {version} of package {package_name} has been deleted",
        "package_name": package_name,
        "deleted_version": version,
        "remaining_versions": active_versions_count - 1
    }


@router.get("/{package_name}/changelog")
async def get_package_changelog(
    package_name: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get changelog/version history for a package."""
    # Check if package exists
    package = await package_service.get_package_by_name(db, package_name)
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Get versions with changelog
    versions = db.query(PackageVersion).filter(
        PackageVersion.package_id == package.id,
        PackageVersion.is_active == True
    ).order_by(PackageVersion.created_at.desc()).limit(limit).all()
    
    changelog_entries = []
    for v in versions:
        entry = {
            "version": v.version,
            "qinter_version": v.qinter_version,
            "created_at": v.created_at.isoformat(),
            "changelog": v.changelog,
            "file_size": v.file_size,
            "dependencies": v.dependencies or []
        }
        changelog_entries.append(entry)
    
    return {
        "package_name": package_name,
        "total_versions": len(versions),
        "changelog": changelog_entries
    }