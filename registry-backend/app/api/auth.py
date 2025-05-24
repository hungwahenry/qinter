# registry-backend/app/api/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database.supabase import get_db
from app.models.user import User, APIKey
from app.services.auth_service import auth_service
from app.dependencies.auth import get_current_user, get_current_api_key
from pydantic import BaseModel, EmailStr

router = APIRouter()


# Request/Response models
class UserRegistration(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str  # Can be username or email
    password: str


class APIKeyCreate(BaseModel):
    name: str
    scopes: List[str] = ["read", "write"]
    expires_days: int = 365


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    usage_count: int
    is_active: bool


class APIKeyCreated(APIKeyResponse):
    api_key: str  # Only shown once during creation


class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    website: Optional[str]
    is_verified: bool
    registration_approved: bool
    created_at: datetime
    last_login: Optional[datetime]


@router.post("/register", response_model=dict)
async def register_user(
    registration: UserRegistration,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    User will need to verify their email before they can use the API.
    """
    try:
        user = await auth_service.create_user(
            db=db,
            username=registration.username,
            email=registration.email,
            password=registration.password,
            full_name=registration.full_name
        )
        
        return {
            "message": "Registration successful",
            "username": user.username,
            "email": user.email,
            "approval_required": True,
            "next_steps": [
                "Check your email for verification instructions",
                "Wait for account approval",
                "Create API keys after approval"
            ]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/verify/{approval_token}")
async def verify_registration(
    approval_token: str,
    db: Session = Depends(get_db)
):
    """Verify user registration with approval token from email."""
    
    success = await auth_service.approve_user(db, approval_token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired approval token"
        )
    
    return {
        "message": "Account verified and approved successfully",
        "next_steps": [
            "You can now create API keys",
            "Use API keys to upload packages"
        ]
    }


@router.get("/me", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile."""
    return current_user


@router.post("/api-keys", response_model=APIKeyCreated)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new API key."""
    
    # Validate scopes
    valid_scopes = ["read", "write", "delete"]
    invalid_scopes = [s for s in api_key_data.scopes if s not in valid_scopes]
    if invalid_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scopes: {invalid_scopes}. Valid scopes: {valid_scopes}"
        )
    
    # Create API key
    api_key_record, api_key = await auth_service.create_api_key(
        db=db,
        user_id=current_user.id,
        name=api_key_data.name,
        scopes=api_key_data.scopes,
        expires_days=api_key_data.expires_days
    )
    
    return APIKeyCreated(
        id=api_key_record.id,
        name=api_key_record.name,
        key_prefix=api_key_record.key_prefix,
        scopes=api_key_record.scopes,
        created_at=api_key_record.created_at,
        expires_at=api_key_record.expires_at,
        last_used=api_key_record.last_used,
        usage_count=api_key_record.usage_count,
        is_active=api_key_record.is_active,
        api_key=api_key  # Only shown during creation
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's API keys."""
    
    api_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).order_by(APIKey.created_at.desc()).all()
    
    return api_keys


@router.delete("/api-keys/{api_key_id}")
async def revoke_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an API key."""
    
    api_key = db.query(APIKey).filter(
        APIKey.id == api_key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Soft delete
    api_key.is_active = False
    db.commit()
    
    return {"message": "API key revoked successfully"}


@router.get("/test")
async def test_authentication(
    current_user: User = Depends(get_current_user),
    api_key: APIKey = Depends(get_current_api_key)
):
    """Test endpoint to verify authentication works."""
    return {
        "message": "Authentication successful",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email
        },
        "api_key": {
            "id": api_key.id,
            "name": api_key.name,
            "scopes": api_key.scopes
        }
    }