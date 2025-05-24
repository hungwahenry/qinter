# registry-backend/app/dependencies/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database.supabase import get_db
from app.models.user import User, APIKey
from app.services.auth_service import auth_service

security = HTTPBearer()


async def get_current_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> APIKey:
    """Get the current API key from the Authorization header."""
    
    api_key = await auth_service.validate_api_key(db, credentials.credentials)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return api_key


async def get_current_user(
    api_key: APIKey = Depends(get_current_api_key),
    db: Session = Depends(get_db)
) -> User:
    """Get the current user from the API key."""
    
    user = db.query(User).filter(User.id == api_key.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    if not user.registration_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User registration not approved yet"
        )
    
    return user


def require_scope(required_scope: str):
    """Dependency factory to require specific API key scopes."""
    
    def scope_checker(api_key: APIKey = Depends(get_current_api_key)):
        if not auth_service.has_permission(api_key, required_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {required_scope}"
            )
        return api_key
    
    return scope_checker


# Common permission dependencies
require_read = require_scope("read")
require_write = require_scope("write")
require_delete = require_scope("delete")