# registry-backend/app/api/stats.py - New file for statistics

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Optional
from app.database.supabase import get_db
from app.models.package import Package as PackageModel, DownloadStat

router = APIRouter()


@router.get("/packages/{package_name}/stats")
async def get_package_stats(
    package_name: str,
    days: int = Query(30, ge=1, le=365, description="Number of days for statistics"),
    db: Session = Depends(get_db)
):
    """Get statistics for a specific package."""
    # Check if package exists
    package = db.query(PackageModel).filter(PackageModel.name == package_name).first()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get download stats
    download_query = db.query(DownloadStat).filter(
        DownloadStat.package_id == package.id,
        DownloadStat.downloaded_at >= start_date
    )
    
    total_downloads = download_query.count()
    
    # Daily downloads
    daily_downloads = db.query(
        func.date(DownloadStat.downloaded_at).label('date'),
        func.count(DownloadStat.id).label('count')
    ).filter(
        DownloadStat.package_id == package.id,
        DownloadStat.downloaded_at >= start_date
    ).group_by(
        func.date(DownloadStat.downloaded_at)
    ).order_by('date').all()
    
    return {
        "package_name": package_name,
        "period_days": days,
        "total_downloads": total_downloads,
        "total_downloads_all_time": package.download_count,
        "daily_downloads": [
            {"date": str(day.date), "downloads": day.count}
            for day in daily_downloads
        ],
        "rating_average": package.rating_average,
        "rating_count": package.rating_count,
        "is_verified": package.is_verified
    }


@router.get("/downloads")
async def get_global_download_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days for statistics"),
    db: Session = Depends(get_db)
):
    """Get global download statistics."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Total downloads in period
    total_downloads = db.query(DownloadStat).filter(
        DownloadStat.downloaded_at >= start_date
    ).count()
    
    # Most downloaded packages
    popular_packages = db.query(
        PackageModel.name,
        PackageModel.download_count,
        func.count(DownloadStat.id).label('recent_downloads')
    ).join(
        DownloadStat, PackageModel.id == DownloadStat.package_id
    ).filter(
        DownloadStat.downloaded_at >= start_date
    ).group_by(
        PackageModel.id, PackageModel.name, PackageModel.download_count
    ).order_by(
        desc('recent_downloads')
    ).limit(10).all()
    
    # Daily download trends
    daily_downloads = db.query(
        func.date(DownloadStat.downloaded_at).label('date'),
        func.count(DownloadStat.id).label('count')
    ).filter(
        DownloadStat.downloaded_at >= start_date
    ).group_by(
        func.date(DownloadStat.downloaded_at)
    ).order_by('date').all()
    
    return {
        "period_days": days,
        "total_downloads": total_downloads,
        "daily_downloads": [
            {"date": str(day.date), "downloads": day.count}
            for day in daily_downloads
        ],
        "popular_packages": [
            {
                "name": pkg.name,
                "total_downloads": pkg.download_count,
                "recent_downloads": pkg.recent_downloads
            }
            for pkg in popular_packages
        ]
    }


@router.get("/popular")
async def get_popular_packages(
    limit: int = Query(20, ge=1, le=100, description="Number of packages to return"),
    days: int = Query(30, ge=1, le=365, description="Period for popularity calculation"),
    db: Session = Depends(get_db)
):
    """Get most popular packages."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get packages by recent download activity
    popular = db.query(
        PackageModel,
        func.count(DownloadStat.id).label('recent_downloads')
    ).outerjoin(
        DownloadStat, 
        (PackageModel.id == DownloadStat.package_id) & 
        (DownloadStat.downloaded_at >= start_date)
    ).filter(
        PackageModel.is_active == True
    ).group_by(
        PackageModel.id
    ).order_by(
        desc('recent_downloads'),
        desc(PackageModel.download_count)
    ).limit(limit).all()
    
    return {
        "period_days": days,
        "packages": [
            {
                "name": pkg.PackageModel.name,
                "description": pkg.PackageModel.description,
                "author": pkg.PackageModel.author,
                "total_downloads": pkg.PackageModel.download_count,
                "recent_downloads": pkg.recent_downloads,
                "rating_average": pkg.PackageModel.rating_average,
                "is_verified": pkg.PackageModel.is_verified,
                "tags": pkg.PackageModel.tags or [],
                "targets": pkg.PackageModel.targets or []
            }
            for pkg in popular
        ]
    }