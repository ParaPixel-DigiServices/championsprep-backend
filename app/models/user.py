"""
Pydantic models for user data.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date


# ============================================================================
# USER PROFILE MODELS
# ============================================================================

class UserProfileUpdate(BaseModel):
    """User profile update request."""
    
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    avatar_url: Optional[str] = None
    
    # Student specific
    grade_level: Optional[int] = Field(None, ge=1, le=12)
    target_exam: Optional[str] = Field(None, max_length=100)
    learning_pace: Optional[str] = Field(None, pattern="^(slow|moderate|fast)$")
    
    # Preferences
    preferred_language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)


class UserProfileResponse(BaseModel):
    """Extended user profile response."""
    
    # Basic user info
    id: str
    email: str
    full_name: str
    role: str
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    
    # Student specific
    grade_level: Optional[int] = None
    target_exam: Optional[str] = None
    learning_pace: Optional[str] = None
    
    # Academic info (from user_profiles table)
    school_name: Optional[str] = None
    board: Optional[str] = None
    subjects: Optional[list[str]] = None
    study_hours_per_day: Optional[int] = None
    preferred_study_time: Optional[str] = None
    target_score: Optional[int] = None
    exam_date: Optional[date] = None
    
    # Statistics
    total_study_time_minutes: int = 0
    total_questions_attempted: int = 0
    total_questions_correct: int = 0
    current_streak_days: int = 0
    longest_streak_days: int = 0
    
    # Status
    is_active: bool
    is_verified: bool
    
    # Preferences
    preferred_language: str = "en"
    timezone: str = "UTC"
    
    # Timestamps
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


class UserStatsResponse(BaseModel):
    """User statistics response."""
    
    total_study_time_minutes: int
    total_questions_attempted: int
    total_questions_correct: int
    accuracy_percentage: float
    current_streak_days: int
    longest_streak_days: int
    total_sessions: int
    achievements_earned: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_study_time_minutes": 1250,
                "total_questions_attempted": 500,
                "total_questions_correct": 425,
                "accuracy_percentage": 85.0,
                "current_streak_days": 7,
                "longest_streak_days": 14,
                "total_sessions": 25,
                "achievements_earned": 5
            }
        }
    }


# ============================================================================
# USER LIST/ADMIN MODELS
# ============================================================================

class UserListItem(BaseModel):
    """User list item for admin."""
    
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated user list response."""
    
    users: list[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# ACADEMIC INFO MODELS
# ============================================================================

class AcademicInfoUpdate(BaseModel):
    """Update academic information."""
    
    school_name: Optional[str] = Field(None, max_length=255)
    board: Optional[str] = Field(None, max_length=100)
    subjects: Optional[list[str]] = None
    study_hours_per_day: Optional[int] = Field(None, ge=0, le=24)
    preferred_study_time: Optional[str] = None
    target_score: Optional[int] = Field(None, ge=0, le=100)
    exam_date: Optional[date] = None


class PreferencesUpdate(BaseModel):
    """Update user preferences."""
    
    preferred_language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)