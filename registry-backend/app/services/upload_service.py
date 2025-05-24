# registry-backend/app/services/upload_service.py - New file
# Standard library imports
import hashlib
import os
import shutil
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Third-party imports
from fastapi import UploadFile
from sqlalchemy.orm import Session

# Local imports
from app.models.package import Package as PackageModel, PackageVersion
from app.models.user import User
from app.utils.validation import validate_package_yaml, get_validation_errors
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class UploadService:
    """Service for handling package uploads and local file management."""
    
    def __init__(self):
        self.upload_directory = Path.home() / ".qinter" / "registry" / "uploads"
        self.upload_directory.mkdir(parents=True, exist_ok=True)
        
        # Allowed file extensions
        self.allowed_extensions = {'.yaml', '.yml'}
        
        # Maximum file size
        self.max_file_size = settings.MAX_PACKAGE_SIZE_MB * 1024 * 1024
    
    def _get_package_directory(self, package_name: str) -> Path:
        """Get the directory for a specific package."""
        package_dir = self.upload_directory / package_name
        package_dir.mkdir(parents=True, exist_ok=True)
        return package_dir
    
    def _get_package_file_path(self, package_name: str, version: str) -> Path:
        """Get the file path for a specific package version."""
        package_dir = self._get_package_directory(package_name)
        return package_dir / f"{package_name}-{version}.yaml"
    
    async def validate_upload_file(self, file: UploadFile) -> Dict[str, Any]:
        """Validate an uploaded file before processing."""
        errors = []
        warnings = []
        
        # Check file extension
        if not file.filename.lower().endswith(('.yaml', '.yml')):
            errors.append("File must have .yaml or .yml extension")
        
        # Check file size
        if file.size and file.size > self.max_file_size:
            errors.append(f"File size ({file.size} bytes) exceeds maximum allowed size ({self.max_file_size} bytes)")
        
        # Read and validate content
        try:
            content = await file.read()
            await file.seek(0)
            
            if len(content) == 0:
                errors.append("File is empty")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Decode content
            yaml_content = content.decode('utf-8')
            
            # Validate YAML syntax
            try:
                yaml_data = yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                errors.append(f"Invalid YAML syntax: {str(e)}")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Validate package structure
            validation_errors = get_validation_errors(yaml_content)
            errors.extend(validation_errors)
            
            # Additional validations
            if yaml_data:
                metadata = yaml_data.get('metadata', {})
                
                if not metadata.get('name'):
                    errors.append("Package name is required")
                
                if not metadata.get('version'):
                    errors.append("Package version is required")
                
                package_name = metadata.get('name', '')
                if not self._is_valid_package_name(package_name):
                    errors.append("Invalid package name format")
                
                # Check for sensitive information
                sensitive_warnings = self._check_sensitive_content(yaml_content)
                warnings.extend(sensitive_warnings)
            
        except UnicodeDecodeError:
            errors.append("File must be valid UTF-8 encoded text")
        except Exception as e:
            errors.append(f"Unexpected error validating file: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "metadata": yaml_data.get('metadata', {}) if 'yaml_data' in locals() else None
        }
    
    async def upload_package(
        self,
        db: Session,
        file: UploadFile,
        user: User,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """Upload and process a package file."""
        
        # Validate file
        validation_result = await self.validate_upload_file(file)
        if not validation_result["valid"]:
            return {
                "success": False,
                "errors": validation_result["errors"],
                "warnings": validation_result.get("warnings", [])
            }
        
        try:
            # Read file content
            content = await file.read()
            yaml_content = content.decode('utf-8')
            package_data = yaml.safe_load(yaml_content)
            metadata = package_data["metadata"]
            
            package_name = metadata["name"]
            version = metadata["version"]
            
            # Check if package exists
            from app.services.package_service import package_service
            existing_package = await package_service.get_package_by_name(db, package_name)
            
            if existing_package:
                # Check ownership
                if existing_package.owner_id != user.id:
                    return {
                        "success": False,
                        "errors": [f"Package '{package_name}' is owned by another user"],
                        "warnings": []
                    }
                
                # Check if version already exists
                existing_version = db.query(PackageVersion).filter(
                    PackageVersion.package_id == existing_package.id,
                    PackageVersion.version == version,
                    PackageVersion.is_active == True
                ).first()
                
                if existing_version and not force_update:
                    return {
                        "success": False,
                        "errors": [f"Version '{version}' already exists. Use force_update=true to overwrite"],
                        "warnings": []
                    }
            
            # Save file to local storage
            file_path = await self._save_package_file(package_name, version, yaml_content)
            file_hash = self._calculate_file_hash(yaml_content)
            
            # Create or update package in database
            if existing_package:
                package = existing_package
                # Update metadata
                package.description = metadata["description"]
                package.tags = metadata.get("tags", [])
                package.targets = metadata["targets"]
                package.license = metadata.get("license", "Unknown")
                package.homepage = metadata.get("homepage")
                package.repository = metadata.get("repository")
            else:
                # Create new package
                package = PackageModel(
                    name=package_name,
                    display_name=metadata.get("display_name", package_name),
                    description=metadata["description"],
                    author=metadata["author"],
                    license=metadata.get("license", "Unknown"),
                    homepage=metadata.get("homepage"),
                    repository=metadata.get("repository"),
                    tags=metadata.get("tags", []),
                    targets=metadata["targets"],
                    owner_id=user.id,
                    is_verified=True
                )
                db.add(package)
                db.flush()
            
            # Create or update version
            if existing_package and force_update:
                # Find and update existing version
                existing_version = db.query(PackageVersion).filter(
                    PackageVersion.package_id == package.id,
                    PackageVersion.version == version
                ).first()
                
                if existing_version:
                    existing_version.file_path = str(file_path)
                    existing_version.file_size = len(content)
                    existing_version.file_hash = file_hash
                    existing_version.dependencies = metadata.get("dependencies", [])
                    existing_version.qinter_version = metadata.get("qinter_version", ">=1.0.0")
                else:
                    # Create new version
                    version_record = PackageVersion(
                        package_id=package.id,
                        version=version,
                        qinter_version=metadata.get("qinter_version", ">=1.0.0"),
                        file_path=str(file_path),
                        file_size=len(content),
                        file_hash=file_hash,
                        dependencies=metadata.get("dependencies", [])
                    )
                    db.add(version_record)
            else:
                # Create new version
                version_record = PackageVersion(
                    package_id=package.id,
                    version=version,
                    qinter_version=metadata.get("qinter_version", ">=1.0.0"),
                    file_path=str(file_path),
                    file_size=len(content),
                    file_hash=file_hash,
                    dependencies=metadata.get("dependencies", [])
                )
                db.add(version_record)
            
            db.commit()
            
            logger.info(f"Successfully uploaded package {package_name} v{version} by user {user.username}")
            
            return {
                "success": True,
                "message": f"Package '{package_name}' version '{version}' uploaded successfully",
                "package": {
                    "name": package_name,
                    "version": version,
                    "author": metadata["author"],
                    "description": metadata["description"],
                    "file_size": len(content),
                    "file_hash": file_hash
                },
                "warnings": validation_result.get("warnings", [])
            }
            
        except Exception as e:
            logger.error(f"Error uploading package: {str(e)}")
            return {
                "success": False,
                "errors": [f"Upload failed: {str(e)}"],
                "warnings": []
            }
    
    async def _save_package_file(self, package_name: str, version: str, content: str) -> Path:
        """Save package file to local storage."""
        file_path = self._get_package_file_path(package_name, version)
        
        # Create backup if file exists
        if file_path.exists():
            backup_path = file_path.with_suffix(f'.backup.{int(time.time())}.yaml')
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
        
        # Write new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved package file: {file_path}")
        return file_path
    
    async def get_uploaded_package_content(self, package_name: str, version: str) -> Optional[str]:
        """Get content of an uploaded package file."""
        file_path = self._get_package_file_path(package_name, version)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading package file {file_path}: {e}")
            return None
    
    async def delete_package_files(self, package_name: str, version: str = None) -> bool:
        """Delete package files from local storage."""
        try:
            if version:
                # Delete specific version
                file_path = self._get_package_file_path(package_name, version)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted package file: {file_path}")
            else:
                # Delete entire package directory
                package_dir = self._get_package_directory(package_name)
                if package_dir.exists():
                    shutil.rmtree(package_dir)
                    logger.info(f"Deleted package directory: {package_dir}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting package files: {e}")
            return False
    
    def _is_valid_package_name(self, name: str) -> bool:
        """Validate package name format."""
        import re
        pattern = r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$'
        return bool(re.match(pattern, name)) and 3 <= len(name) <= 50
    
    def _check_sensitive_content(self, content: str) -> list:
        """Check for potentially sensitive information."""
        warnings = []
        content_lower = content.lower()
        
        sensitive_patterns = [
            ('password', 'Possible password found'),
            ('secret', 'Possible secret found'), 
            ('token', 'Possible token found'),
            ('api_key', 'Possible API key found'),
            ('private_key', 'Possible private key found')
        ]
        
        for pattern, warning in sensitive_patterns:
            if pattern in content_lower:
                warnings.append(warning)
        
        return warnings
    
    def _calculate_file_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage usage statistics."""
        total_size = 0
        file_count = 0
        package_count = 0
        
        try:
            if self.upload_directory.exists():
                for package_dir in self.upload_directory.iterdir():
                    if package_dir.is_dir():
                        package_count += 1
                        for file_path in package_dir.glob("*.yaml"):
                            if file_path.is_file():
                                total_size += file_path.stat().st_size
                                file_count += 1
            
            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "package_count": package_count,
                "upload_directory": str(self.upload_directory)
            }
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {"error": str(e)}


# Global upload service instance
upload_service = UploadService()