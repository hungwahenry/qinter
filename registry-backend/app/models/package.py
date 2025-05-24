from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.supabase import Base


class Package(Base):
    __tablename__ = "packages"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    display_name = Column(String(100))
    description = Column(Text)
    author = Column(String(100), index=True)
    license = Column(String(50))
    homepage = Column(String(255))
    repository = Column(String(255))
    tags = Column(JSON, default=list)
    targets = Column(JSON, default=list)
    
    # Ownership (required for upload-only system)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Now required
    
    # Metadata
    download_count = Column(Integer, default=0)
    rating_average = Column(Integer, default=0)
    rating_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Status
    is_verified = Column(Boolean, default=True)  # Auto-verify uploaded packages
    is_active = Column(Boolean, default=True)
    
    # Relationships
    versions = relationship("PackageVersion", back_populates="package", cascade="all, delete-orphan")
    owner = relationship("User", back_populates="packages")
    download_stats = relationship("DownloadStat", back_populates="package")


class PackageVersion(Base):
    __tablename__ = "package_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
    
    version = Column(String(20), nullable=False, index=True)
    qinter_version = Column(String(20), nullable=False)
    
    # File information (only local storage)
    file_path = Column(String(500), nullable=False)  # Always required
    file_size = Column(Integer)
    file_hash = Column(String(64))
    
    # Metadata
    dependencies = Column(JSON, default=list)
    changelog = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    package = relationship("Package", back_populates="versions")
    download_stats = relationship("DownloadStat", back_populates="version")


class DownloadStat(Base):
    __tablename__ = "download_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("package_versions.id"))
    
    # Request information
    user_ip = Column(String(45))
    user_agent = Column(Text)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"))
    
    # Timestamp
    downloaded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    package = relationship("Package", back_populates="download_stats")
    version = relationship("PackageVersion", back_populates="download_stats")
    api_key = relationship("APIKey", back_populates="download_stats")