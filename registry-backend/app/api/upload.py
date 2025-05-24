# registry-backend/app/api/upload.py - New file
# Standard library imports
from datetime import datetime
from typing import Optional, List

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Local imports
from app.database.supabase import get_db
from app.models.user import User
from app.models.package import Package as PackageModel, PackageVersion
from app.dependencies.auth import get_current_user, require_write, require_delete
from app.services.upload_service import upload_service
from app.services.package_service import package_service

router = APIRouter()


class UploadResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    package: Optional[dict] = None
    errors: List[str] = []
    warnings: List[str] = []


@router.post("/packages", response_model=UploadResponse)
async def upload_package(
    file: UploadFile = File(..., description="Package YAML file"),
    force_update: bool = Form(False, description="Force update if version exists"),
    current_user: User = Depends(get_current_user),
    _write_permission = Depends(require_write),
    db: Session = Depends(get_db)
):
    """Upload a new package or update an existing one."""
    
    if not current_user.registration_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your registration is not approved yet"
        )
    
    result = await upload_service.upload_package(
        db=db,
        file=file,
        user=current_user,
        force_update=force_update
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Package upload failed",
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", [])
            }
        )
    
    return UploadResponse(**result)


@router.post("/packages/validate")
async def validate_package_file(
    file: UploadFile = File(..., description="Package YAML file to validate"),
    current_user: User = Depends(get_current_user)
):
    """Validate a package file without uploading it."""
    
    validation_result = await upload_service.validate_upload_file(file)
    
    return {
        "valid": validation_result["valid"],
        "errors": validation_result.get("errors", []),
        "warnings": validation_result.get("warnings", []),
        "metadata": validation_result.get("metadata", {}),
        "file_info": {
            "filename": file.filename,
            "size": file.size,
            "content_type": file.content_type
        }
    }


@router.get("/packages/{package_name}/ownership")
async def check_package_ownership(
    package_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check ownership and permissions for a package."""
    
    package = await package_service.get_package_by_name(db, package_name)
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    
    can_modify = package.owner_id == current_user.id
    owner = db.query(User).filter(User.id == package.owner_id).first()
    
    return {
        "package_name": package_name,
        "owner_username": owner.username if owner else "unknown",
        "owner_id": package.owner_id,
        "can_modify": can_modify
    }


@router.put("/packages/{package_name}")
async def update_package(
    package_name: str,
    file: UploadFile = File(..., description="Updated package YAML file"),
    current_user: User = Depends(get_current_user),
    _write_permission = Depends(require_write),
    db: Session = Depends(get_db)
):
    """Update an existing package."""
    
    package = await package_service.get_package_by_name(db, package_name)
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    
    if package.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't own this package"
        )
    
    result = await upload_service.upload_package(
        db=db,
        file=file,
        user=current_user,
        force_update=True
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Package update failed",
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", [])
            }
        )
    
    return UploadResponse(**result)


@router.delete("/packages/{package_name}")
async def delete_package(
    package_name: str,
    current_user: User = Depends(get_current_user),
    _delete_permission = Depends(require_delete),
    db: Session = Depends(get_db)
):
    """Delete a package (soft delete)."""
    
    package = await package_service.get_package_by_name(db, package_name)
    
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    
    if package.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't own this package"
        )
    
    # Soft delete
    package.is_active = False
    
    # Deactivate all versions
    db.query(PackageVersion).filter(
        PackageVersion.package_id == package.id
    ).update({"is_active": False})
    
    db.commit()
    
    # Clean up files
    await upload_service.delete_package_files(package_name)
    
    return {
        "message": f"Package '{package_name}' deleted successfully",
        "package_name": package_name,
        "deleted_at": datetime.utcnow().isoformat()
    }


@router.get("/my-packages")
async def list_my_packages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List packages owned by the current user."""
    
    packages = db.query(PackageModel).filter(
        PackageModel.owner_id == current_user.id,
        PackageModel.is_active == True
    ).order_by(PackageModel.updated_at.desc()).all()
    
    return {
        "packages": [
            {
                "name": pkg.name,
                "display_name": pkg.display_name,
                "description": pkg.description,
                "download_count": pkg.download_count,
                "created_at": pkg.created_at.isoformat(),
                "updated_at": pkg.updated_at.isoformat() if pkg.updated_at else None,
                "is_verified": pkg.is_verified
            }
            for pkg in packages
        ],
        "total": len(packages)
    }


@router.get("/storage/stats")
async def get_storage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get storage usage statistics."""
    
    # Get user's package count and total downloads
    user_packages = db.query(PackageModel).filter(
        PackageModel.owner_id == current_user.id,
        PackageModel.is_active == True
    ).all()
    
    total_downloads = sum(pkg.download_count for pkg in user_packages)
    
    # Get global storage stats
    storage_stats = upload_service.get_storage_stats()
    
    return {
        "user_stats": {
            "package_count": len(user_packages),
            "total_downloads": total_downloads,
            "packages": [pkg.name for pkg in user_packages]
        },
        "global_storage": storage_stats
    }