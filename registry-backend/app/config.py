"""
registry-backend/app/config.py
"""

from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Qinter Package Registry"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Registry API for Qinter explanation packages"
    
    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str
    DATABASE_PASSWORD: str
    
    # Timeout Configuration
    HTTP_REQUEST_TIMEOUT: int = 30
    HTTP_CONNECT_TIMEOUT: int = 10
    
    # Environment
    ENVIRONMENT: str
    DEBUG: bool = False
    
    # CORS
    CORS_ORIGINS: List[str]
    
    # Cache & Performance
    CACHE_EXPIRE_SECONDS: int = 300
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # Package Management
    MAX_PACKAGE_SIZE_MB: int = 5
    
    # Search Configuration
    SEARCH_MAX_RESULTS: int = 100
    SEARCH_DEFAULT_LIMIT: int = 20
    
    # Analytics
    TRACK_DOWNLOADS: bool = True
    ANONYMIZE_IPS: bool = True
    
    @property
    def database_url(self) -> str:
        """Build PostgreSQL connection URL from Supabase configuration."""
        project_ref = self.SUPABASE_URL.replace("https://", "").replace(".supabase.co", "")
        return f"postgresql://postgres:{self.DATABASE_PASSWORD}@db.{project_ref}.supabase.co:5432/postgres"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT.lower() == "production"
    
    def validate_configuration(self) -> List[str]:
        """Validate configuration and return any errors."""
        errors = []
        
        # Required fields validation
        required_fields = [
            ('SECRET_KEY', self.SECRET_KEY),
            ('SUPABASE_URL', self.SUPABASE_URL),
            ('SUPABASE_ANON_KEY', self.SUPABASE_ANON_KEY),
            ('DATABASE_PASSWORD', self.DATABASE_PASSWORD)
        ]
        
        for field_name, field_value in required_fields:
            if not field_value or field_value.strip() == "":
                errors.append(f"Missing required configuration: {field_name}")
        
        # Validate URL formats
        if self.SUPABASE_URL and not self.SUPABASE_URL.startswith('https://'):
            errors.append("SUPABASE_URL must start with https://")
        
        if self.SUPABASE_URL and not self.SUPABASE_URL.endswith('.supabase.co'):
            errors.append("SUPABASE_URL must end with .supabase.co")
        
        return errors
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

# Validate configuration on startup
config_errors = settings.validate_configuration()
if config_errors:
    print("❌ Configuration errors found:")
    for error in config_errors:
        print(f"   - {error}")
    print("\n💡 Please check your .env file and ensure all required values are set.")