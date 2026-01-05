"""
Pydantic models for authentication.
Request and response schemas for auth endpoints.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
import re


# ============================================================================
# REQUEST MODELS
# ============================================================================

class UserRegisterRequest(BaseModel):
    """User registration request."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=72, description="User password")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    role: str = Field(default="student", description="User role")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    
    # Student specific
    grade_level: Optional[int] = Field(None, ge=1, le=12, description="Grade level (1-12)")
    target_exam: Optional[str] = Field(None, max_length=100, description="Target exam")
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is one of allowed values."""
        allowed_roles = ["student", "parent", "admin"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format."""
        if v is None:
            return v
        
        # Remove spaces and dashes
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        
        # Check if it's digits only and reasonable length
        if not cleaned.isdigit() or len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError("Phone number must be 10-15 digits")
        
        return v


class UserLoginRequest(BaseModel):
    """User login request."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    
    refresh_token: str = Field(..., description="Refresh token")


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    
    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    
    token: str = Field(..., description="Reset token from email")
    new_password: str = Field(..., min_length=8, max_length=72, description="New password")
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        return v


class ChangePasswordRequest(BaseModel):
    """Change password request (for authenticated users)."""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=72, description="New password")
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        return v


class EmailVerificationRequest(BaseModel):
    """Email verification request."""
    
    token: str = Field(..., description="Verification token from email")


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class TokenResponse(BaseModel):
    """Token response model."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class UserResponse(BaseModel):
    """User response model."""
    
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="Full name")
    role: str = Field(..., description="User role")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    phone: Optional[str] = Field(None, description="Phone number")
    date_of_birth: Optional[str] = Field(None, description="Date of birth")
    
    # Student specific
    grade_level: Optional[int] = Field(None, description="Grade level")
    target_exam: Optional[str] = Field(None, description="Target exam")
    
    # Status
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verified status")
    email_verified_at: Optional[datetime] = Field(None, description="Email verification timestamp")
    
    # Preferences
    preferred_language: str = Field(default="en", description="Preferred language")
    
    # Timestamps
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "student@example.com",
                "full_name": "John Doe",
                "role": "student",
                "avatar_url": None,
                "phone": "+1234567890",
                "date_of_birth": "2005-01-15",
                "grade_level": 11,
                "target_exam": "JEE",
                "is_active": True,
                "is_verified": True,
                "email_verified_at": "2024-01-01T00:00:00Z",
                "preferred_language": "en",
                "created_at": "2024-01-01T00:00:00Z",
                "last_login_at": "2024-01-05T12:00:00Z"
            }
        }
    }


class AuthResponse(BaseModel):
    """Complete authentication response."""
    
    user: UserResponse = Field(..., description="User data")
    tokens: TokenResponse = Field(..., description="Authentication tokens")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "student@example.com",
                    "full_name": "John Doe",
                    "role": "student",
                    "is_active": True,
                    "is_verified": True,
                    "created_at": "2024-01-01T00:00:00Z"
                },
                "tokens": {
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                    "token_type": "bearer",
                    "expires_in": 1800
                }
            }
        }
    }


class MessageResponse(BaseModel):
    """Generic message response."""
    
    message: str = Field(..., description="Response message")
    success: bool = Field(default=True, description="Operation success status")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Operation completed successfully",
                "success": True
            }
        }
    }


# ============================================================================
# INTERNAL MODELS (Not exposed in API)
# ============================================================================

class TokenPayload(BaseModel):
    """JWT token payload."""
    
    sub: str = Field(..., description="Subject (user_id)")
    email: str = Field(..., description="User email")
    role: str = Field(..., description="User role")
    type: str = Field(..., description="Token type (access or refresh)")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")