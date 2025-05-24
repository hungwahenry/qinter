import yaml
import hashlib
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from datetime import datetime
from app.models.package import Package as PackageModel, PackageVersion, DownloadStat
from app.config import settings


class PackageService:
    """Service for package management operations."""
    
    async def get_package_by_name(self, db: Session, name: str) -> Optional[PackageModel]:
        """Get package by name."""
        return db.query(PackageModel).filter(PackageModel.name == name).first()
    
    async def get_packages(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 50,
        sort_by: str = "downloads"
    ) -> List[PackageModel]:
        """Get packages with pagination and sorting."""
        query = db.query(PackageModel).filter(PackageModel.is_active == True)
        
        if sort_by == "downloads":
            query = query.order_by(desc(PackageModel.download_count))
        elif sort_by == "rating":
            query = query.order_by(desc(PackageModel.rating_average))
        elif sort_by == "name":
            query = query.order_by(asc(PackageModel.name))
        elif sort_by == "updated":
            query = query.order_by(desc(PackageModel.updated_at))
        elif sort_by == "created":
            query = query.order_by(desc(PackageModel.created_at))
        else:
            query = query.order_by(desc(PackageModel.download_count))
        
        return query.offset(skip).limit(limit).all()
    
    async def get_packages_count(self, db: Session) -> int:
        """Get total count of active packages."""
        return db.query(PackageModel).filter(PackageModel.is_active == True).count()
    
    async def search_packages(
        self,
        db: Session,
        query: str,
        limit: int = 20,
        offset: int = 0,
        tags: Optional[List[str]] = None,
        targets: Optional[List[str]] = None,
        author: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search packages with full-text search and filters."""
        
        # Base query
        db_query = db.query(PackageModel).filter(PackageModel.is_active == True)
        
        # Text search
        if query:
            search_filter = or_(
                PackageModel.name.ilike(f"%{query}%"),
                PackageModel.description.ilike(f"%{query}%"),
                PackageModel.author.ilike(f"%{query}%")
            )
            db_query = db_query.filter(search_filter)
        
        # Tag filtering
        if tags:
            for tag in tags:
                db_query = db_query.filter(PackageModel.tags.contains([tag]))
        
        # Target filtering
        if targets:
            for target in targets:
                db_query = db_query.filter(PackageModel.targets.contains([target]))
        
        # Author filtering
        if author:
            db_query = db_query.filter(PackageModel.author.ilike(f"%{author}%"))
        
        # Execute query
        packages = db_query.offset(offset).limit(limit).all()
        
        # Convert to search results
        results = []
        for package in packages:
            relevance_score = self._calculate_relevance(package, query)
            
            result = {
                "id": package.id,
                "name": package.name,
                "display_name": package.display_name,
                "description": package.description,
                "author": package.author,
                "license": package.license,
                "homepage": package.homepage,
                "repository": package.repository,
                "tags": package.tags or [],
                "targets": package.targets or [],
                "download_count": package.download_count,
                "rating_average": package.rating_average,
                "rating_count": package.rating_count,
                "created_at": package.created_at,
                "updated_at": package.updated_at,
                "is_verified": package.is_verified,
                "relevance_score": relevance_score
            }
            results.append(result)
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return results
    
    async def get_package_info(self, db: Session, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed package information."""
        package = await self.get_package_by_name(db, name)
        
        if not package:
            return None
        
        # Get latest version
        latest_version = db.query(PackageVersion).filter(
            PackageVersion.package_id == package.id,
            PackageVersion.is_active == True
        ).order_by(desc(PackageVersion.created_at)).first()
        
        # Get all versions
        all_versions = db.query(PackageVersion).filter(
            PackageVersion.package_id == package.id,
            PackageVersion.is_active == True
        ).order_by(desc(PackageVersion.created_at)).all()
        
        return {
            "name": package.name,
            "display_name": package.display_name,
            "version": latest_version.version if latest_version else "unknown",
            "description": package.description,
            "author": package.author,
            "license": package.license,
            "homepage": package.homepage,
            "repository": package.repository,
            "tags": package.tags or [],
            "targets": package.targets or [],
            "dependencies": latest_version.dependencies if latest_version else [],
            "qinter_version": latest_version.qinter_version if latest_version else ">=1.0.0",
            "downloads": package.download_count,
            "rating": package.rating_average,
            "rating_count": package.rating_count,
            "last_updated": package.updated_at.isoformat() if package.updated_at else None,
            "file_size": latest_version.file_size if latest_version else None,
            "file_hash": latest_version.file_hash if latest_version else None,
            "is_verified": package.is_verified,
            "status": "available",
            "versions": [v.version for v in all_versions]
        }
    
    async def download_package(self, db: Session, name: str, version: str = "latest", user_ip: str = None, user_agent: str = None) -> Optional[str]:
        """Download package content from local storage."""
        package = await self.get_package_by_name(db, name)
        
        if not package:
            return None
        
        # Get from local storage
        from app.services.upload_service import upload_service
        content = await upload_service.get_uploaded_package_content(name, version)
        
        if content:
            try:
                await self._log_download(db, name, version, user_ip, user_agent)
                package.download_count += 1
                db.commit()
            except Exception as e:
                db.rollback()
                raise e
        
        return content
    
    async def get_download_stats(self, db: Session, package_name: str = None, days: int = 30) -> Dict[str, Any]:
        """Get download statistics."""
        query = db.query(DownloadStat)
        
        if package_name:
            package = await self.get_package_by_name(db, package_name)
            if package:
                query = query.filter(DownloadStat.package_id == package.id)
        
        # Filter by date range
        from datetime import datetime, timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(DownloadStat.downloaded_at >= start_date)
        
        total_downloads = query.count()
        
        # Group by day
        daily_downloads = db.query(
            func.date(DownloadStat.downloaded_at).label('date'),
            func.count(DownloadStat.id).label('count')
        ).filter(DownloadStat.downloaded_at >= start_date).group_by(
            func.date(DownloadStat.downloaded_at)
        ).all()
        
        return {
            "total_downloads": total_downloads,
            "daily_downloads": [{"date": str(d.date), "count": d.count} for d in daily_downloads],
            "period_days": days
        }
    
    def _calculate_relevance(self, package: PackageModel, query: str) -> float:
        """Calculate relevance score for search results."""
        if not query:
            return 1.0
        
        score = 0.0
        query_lower = query.lower()
        
        # Exact name match gets highest score
        if package.name.lower() == query_lower:
            score += 10.0
        elif query_lower in package.name.lower():
            score += 5.0
        
        # Description contains query
        if package.description and query_lower in package.description.lower():
            score += 2.0
        
        # Author contains query
        if package.author and query_lower in package.author.lower():
            score += 1.0
        
        # Tag matches
        if package.tags:
            for tag in package.tags:
                if query_lower in tag.lower():
                    score += 3.0
        
        # Target matches
        if package.targets:
            for target in package.targets:
                if query_lower in target.lower():
                    score += 4.0
        
        # Boost for popular packages
        score += min(package.download_count / 1000, 2.0)
        score += package.rating_average * 0.5
        
        # Boost for verified packages
        if package.is_verified:
            score += 1.0
        
        return score
    
    async def _log_download(self, db: Session, package_name: str, version: str, user_ip: str = None, user_agent: str = None):
        """Log package download for analytics."""
        package = await self.get_package_by_name(db, package_name)
        
        if package and settings.TRACK_DOWNLOADS:
            # Anonymize IP if required
            if settings.ANONYMIZE_IPS and user_ip:
                ip_parts = user_ip.split('.')
                if len(ip_parts) == 4:
                    user_ip = '.'.join(ip_parts[:3] + ['0'])
            
            download_stat = DownloadStat(
                package_id=package.id,
                user_ip=user_ip,
                user_agent=user_agent
            )
            db.add(download_stat)
            db.commit()


# Global package service instance
package_service = PackageService()