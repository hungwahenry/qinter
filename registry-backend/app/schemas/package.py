"""
registry-backend/app/schemas/package.py
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class PackageBase(BaseModel):
    """Base package schema."""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = None
    description: str
    author: str
    license: str
    homepage: Optional[str] = None
    repository: Optional[str] = None
    tags: List[str] = []
    targets: List[str] = []


class PackageCreate(PackageBase):
    """Package creation schema."""
    version: str
    qinter_version: str
    file_content: str  # YAML content
    dependencies: List[str] = []


class PackageUpdate(BaseModel):
    """Package update schema."""
    description: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    tags: Optional[List[str]] = None


class PackageVersion(BaseModel):
    """Package version schema."""
    version: str
    qinter_version: str
    file_path: str
    file_size: Optional[int] = None
    dependencies: List[str] = []
    created_at: datetime
    is_active: bool = True
    
    class Config:
        from_attributes = True


class Package(PackageBase):
    """Complete package schema."""
    id: int
    download_count: int = 0
    rating_average: float = 0.0
    rating_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_verified: bool = False
    is_active: bool = True
    
    # Latest version info
    latest_version: Optional[PackageVersion] = None
    
    class Config:
        from_attributes = True


class PackageList(BaseModel):
    """Package list response schema."""
    packages: List[Package]
    total: int
    limit: int
    offset: int


class PackageSearchResult(Package):
    """Search result with relevance score."""
    relevance_score: float = 0.0


class PackageSearchResponse(BaseModel):
    """Search response schema."""
    query: str
    packages: List[PackageSearchResult]
    total: int
    took_ms: int


class PackageDownload(BaseModel):
    """Package download response."""
    content: str  # YAML content
    metadata: PackageVersion
    download_url: str