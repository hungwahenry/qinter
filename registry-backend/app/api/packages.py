# registry-backend/app/api/packages.py
# Standard library imports
import time
from typing import List, Optional

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

# Local imports
from app.database.supabase import get_db
from app.services.package_service import package_service
from app.schemas.package import Package as PackageSchema, PackageList, PackageSearchResponse
from app.models.package import Package as PackageModel

router = APIRouter()


@router.get("/", response_model=PackageList)
async def list_packages(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    sort: str = Query("downloads", regex="^(downloads|rating|name|updated|created)$"),
    db: Session = Depends(get_db)
):
    """List all packages with pagination and sorting."""
    packages = await package_service.get_packages(db, skip=skip, limit=limit, sort_by=sort)
    total = db.query(PackageModel).filter(PackageModel.is_active == True).count()
    
    return PackageList(
        packages=packages,
        total=total,
        limit=limit,
        offset=skip
    )


@router.get("/search", response_model=PackageSearchResponse)
async def search_packages(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags to filter by"),
    targets: Optional[str] = Query(None, description="Comma-separated list of exception types to filter by"),
    db: Session = Depends(get_db)
):
    """Search for packages in the registry."""
    start_time = time.time()
    
    # Parse comma-separated filters
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else None
    target_list = [target.strip() for target in targets.split(",")] if targets else None
    
    # Perform search
    results = await package_service.search_packages(
        db=db,
        query=q,
        limit=limit,
        offset=offset,
        tags=tag_list,
        targets=target_list
    )
    
    # Calculate search time
    took_ms = int((time.time() - start_time) * 1000)
    
    return PackageSearchResponse(
        query=q,
        packages=results,
        total=len(results),
        took_ms=took_ms
    )


@router.get("/{package_name}")
async def get_package_info(
    package_name: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific package."""
    package_info = await package_service.get_package_info(db, package_name)
    
    if not package_info:
        raise HTTPException(status_code=404, detail="Package not found")
    
    return package_info


@router.get("/{package_name}/download")
async def download_package(
    package_name: str,
    version: str = Query("latest", description="Package version to download"),
    db: Session = Depends(get_db)
):
    """Download a package's YAML content."""
    content = await package_service.download_package(db, package_name, version)
    
    if not content:
        raise HTTPException(status_code=404, detail="Package or version not found")
    
    # Get package info for metadata
    package_info = await package_service.get_package_info(db, package_name)
    
    return {
        "content": content,
        "metadata": {
            "name": package_name,
            "version": package_info.get("version", version) if package_info else version,
            "qinter_version": package_info.get("qinter_version", ">=1.0.0") if package_info else ">=1.0.0"
        }
    }