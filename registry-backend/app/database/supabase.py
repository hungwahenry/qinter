"""
registry-backend/app/database/supabase.py
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Supabase client for auth and realtime features
from supabase import create_client, Client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Direct PostgreSQL connection using the database_url property from settings
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG,
    connect_args={
        "sslmode": "require"
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def test_connection():
    """Test database connection."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False


def get_connection_info():
    """Get database connection information for debugging."""
    return {
        "database_url": settings.database_url.replace(settings.DATABASE_PASSWORD, "***"),
        "supabase_url": settings.SUPABASE_URL,
        "environment": settings.ENVIRONMENT
    }