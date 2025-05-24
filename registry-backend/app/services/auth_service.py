# registry-backend/app/services/auth_service.py

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
from sqlalchemy.orm import Session
from app.models.user import User, APIKey
from app.config import settings
import logging


logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication and authorization."""
    
    def __init__(self):
        self.api_key_length = 64
        self.api_key_prefix = "qinter_"
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def generate_api_key(self) -> tuple[str, str]:
        """Generate a new API key and its hash."""
        # Generate random key
        key_bytes = secrets.token_bytes(self.api_key_length)
        key = self.api_key_prefix + key_bytes.hex()
        
        # Create hash for storage
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        return key, key_hash
    
    def verify_api_key(self, provided_key: str, stored_hash: str) -> bool:
        """Verify an API key against its stored hash."""
        provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
        return provided_hash == stored_hash
    
    async def create_user(
        self, 
        db: Session, 
        username: str, 
        email: str, 
        password: str,
        full_name: str = None
    ) -> User:
        """Create a new user account."""
        
        # Check if user already exists
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing:
            if existing.username == username:
                raise ValueError("Username already exists")
            else:
                raise ValueError("Email already exists")
        
        # Generate approval token for email verification
        approval_token = secrets.token_urlsafe(32)
        
        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=self.hash_password(password),
            full_name=full_name,
            approval_token=approval_token,
            registration_approved=False  # Requires approval
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"Created new user: {username} ({email})")
        return user
    
    async def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate a user by username/email and password."""
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user:
            return None
        
        if not self.verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
    
    async def create_api_key(
        self, 
        db: Session, 
        user_id: int, 
        name: str,
        scopes: list = None,
        expires_days: int = 365
    ) -> tuple[APIKey, str]:
        """Create a new API key for a user."""
        
        if scopes is None:
            scopes = ["read", "write"]
        
        # Generate API key
        key, key_hash = self.generate_api_key()
        key_prefix = key[:len(self.api_key_prefix) + 8]  # Show prefix + 8 chars
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        # Create API key record
        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes,
            expires_at=expires_at
        )
        
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        
        logger.info(f"Created API key '{name}' for user {user_id}")
        return api_key, key
    
    async def validate_api_key(self, db: Session, provided_key: str) -> Optional[APIKey]:
        """Validate an API key and return the associated record."""
        
        if not provided_key.startswith(self.api_key_prefix):
            return None
        
        # Get the prefix for efficient lookup
        key_prefix = provided_key[:len(self.api_key_prefix) + 8]
        
        # Find potential matches
        api_keys = db.query(APIKey).filter(
            APIKey.key_prefix == key_prefix,
            APIKey.is_active == True
        ).all()
        
        for api_key in api_keys:
            if self.verify_api_key(provided_key, api_key.key_hash):
                # Check expiration
                if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                    continue
                
                # Update usage stats
                api_key.last_used = datetime.utcnow()
                api_key.usage_count += 1
                db.commit()
                
                return api_key
        
        return None
    
    async def approve_user(self, db: Session, approval_token: str) -> bool:
        """Approve a user registration using their approval token."""
        user = db.query(User).filter(User.approval_token == approval_token).first()
        
        if not user:
            return False
        
        user.registration_approved = True
        user.is_verified = True
        user.approval_token = None  # Clear the token
        db.commit()
        
        logger.info(f"Approved user registration: {user.username}")
        return True
    
    def has_permission(self, api_key: APIKey, required_scope: str) -> bool:
        """Check if an API key has the required permission scope."""
        if not api_key.scopes:
            return False
        
        return required_scope in api_key.scopes


# Global auth service instance
auth_service = AuthService()