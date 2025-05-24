from sqlalchemy import create_engine, text
from app.database.supabase import Base, engine
from app.models.package import Package, PackageVersion, DownloadStat
from app.models.user import User, APIKey
import logging

logger = logging.getLogger(__name__)

def create_indexes():
    """Create additional indexes for better performance."""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_packages_author ON packages(author);",
        "CREATE INDEX IF NOT EXISTS idx_package_versions_version ON package_versions(version);",
        "CREATE INDEX IF NOT EXISTS idx_download_stats_downloaded_at ON download_stats(downloaded_at);",
        "CREATE INDEX IF NOT EXISTS idx_packages_tags ON packages USING gin (tags);",
        "CREATE INDEX IF NOT EXISTS idx_packages_targets ON packages USING gin (targets);"
    ]
    
    try:
        with engine.connect() as conn:
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    logger.info(f"Created index: {index_sql}")
                except Exception as e:
                    logger.warning(f"Index creation failed (may already exist): {e}")
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        return False

def run_migrations():
    """Run database migrations."""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        
        # Create additional indexes
        create_indexes()
        logger.info("✅ Database indexes created successfully")
        
        return True
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False