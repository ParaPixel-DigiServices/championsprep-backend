"""
User profile API endpoints.
Handles user profile viewing, updating, and statistics.
"""

from fastapi import APIRouter, Depends, status
from typing import List

from app.models.user import (
    UserProfileUpdate,
    UserProfileResponse,
    UserStatsResponse,
    AcademicInfoUpdate,
    PreferencesUpdate,
    UserListItem,
    UserListResponse,
    ProfileCompletionRequest,
)
from app.models.auth import UserResponse, MessageResponse
from app.services.user_service import UserService, AdminUserService
from app.api.v1.dependencies import get_current_user, require_admin
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/users", tags=["Users"])


# ============================================================================
# USER PROFILE ENDPOINTS
# ============================================================================

@router.post(
    "/profile/complete",
    response_model=UserProfileResponse,
    summary="Complete profile setup",
    description="Complete profile setup (first-time only) - locks grade & board"
)
async def complete_profile(
    data: ProfileCompletionRequest,
    current_user: UserResponse = Depends(get_current_user)
) -> UserProfileResponse:
    """
    Complete profile setup (first-time only).
    
    **IMPORTANT:** This is a ONE-TIME operation. Once completed:
    - Grade level is LOCKED
    - Board is LOCKED
    - These cannot be changed by user (admin approval required)
    
    **Required fields:**
    - grade_level (11 or 12)
    - board (default: CBSE)
    - subjects (array of selected subjects)
    - preferred_language
    
    **Optional fields:**
    - school_name
    - target_exam
    - study_hours_per_day
    
    **Use this endpoint:**
    - On first login
    - Before accessing any learning features
    
    **Requires:** Valid access token
    """
    return await UserService.complete_profile(current_user.id, data)


@router.get(
    "/profile",
    response_model=UserProfileResponse,
    summary="Get user profile",
    description="Get complete user profile with statistics"
)
async def get_profile(
    current_user: UserResponse = Depends(get_current_user)
) -> UserProfileResponse:
    """
    Get current user's complete profile.
    
    **Includes:**
    - Basic user info
    - Academic information (for students)
    - Study statistics
    - Preferences
    
    **Requires:** Valid access token
    """
    return await UserService.get_user_profile(current_user.id)


@router.put(
    "/profile",
    response_model=UserProfileResponse,
    summary="Update user profile",
    description="Update user profile information"
)
async def update_profile(
    data: UserProfileUpdate,
    current_user: UserResponse = Depends(get_current_user)
) -> UserProfileResponse:
    """
    Update user profile.
    
    **Can update:**
    - Full name
    - Phone number
    - Date of birth
    - Avatar URL
    - Grade level (students)
    - Target exam (students)
    - Learning pace
    - Language preference
    - Timezone
    
    **Only non-null fields** will be updated.
    
    **Requires:** Valid access token
    """
    return await UserService.update_user_profile(current_user.id, data)


@router.put(
    "/profile/academic",
    response_model=UserProfileResponse,
    summary="Update academic information",
    description="Update student's academic details"
)
async def update_academic_info(
    data: AcademicInfoUpdate,
    current_user: UserResponse = Depends(get_current_user)
) -> UserProfileResponse:
    """
    Update academic information (students only).
    
    **Can update:**
    - School name
    - Board (e.g., CBSE)
    - Subjects
    - Study hours per day
    - Preferred study time
    - Target score
    - Exam date
    
    **Requires:** Valid access token
    """
    return await UserService.update_academic_info(current_user.id, data)


@router.put(
    "/profile/preferences",
    response_model=UserProfileResponse,
    summary="Update preferences",
    description="Update user preferences"
)
async def update_preferences(
    data: PreferencesUpdate,
    current_user: UserResponse = Depends(get_current_user)
) -> UserProfileResponse:
    """
    Update user preferences.
    
    **Can update:**
    - Preferred language
    - Timezone
    
    **Requires:** Valid access token
    """
    return await UserService.update_preferences(current_user.id, data)


@router.get(
    "/stats",
    response_model=UserStatsResponse,
    summary="Get user statistics",
    description="Get user's study statistics and progress"
)
async def get_stats(
    current_user: UserResponse = Depends(get_current_user)
) -> UserStatsResponse:
    """
    Get user statistics.
    
    **Includes:**
    - Total study time
    - Questions attempted/correct
    - Accuracy percentage
    - Current & longest streak
    - Total sessions
    - Achievements earned
    
    **Requires:** Valid access token
    """
    return await UserService.get_user_stats(current_user.id)


# ============================================================================
# ADMIN USER MANAGEMENT
# ============================================================================

@router.get(
    "/admin/list",
    response_model=UserListResponse,
    summary="List all users (Admin)",
    description="Get paginated list of all users"
)
async def list_users(
    role: str = None,
    page: int = 1,
    page_size: int = 50,
    current_user: UserResponse = Depends(require_admin)
) -> UserListResponse:
    """
    Get paginated list of users (admin only).
    
    **Query Parameters:**
    - `role`: Filter by role (student, parent, admin)
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 50, max: 100)
    
    **Returns:**
    - List of users
    - Total count
    - Pagination info
    
    **Requires:** Admin role
    """
    # Validate page size
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size
    
    users, total = await AdminUserService.get_all_users(
        role=role,
        limit=page_size,
        offset=offset
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return UserListResponse(
        users=users,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post(
    "/admin/create",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create admin user",
    description="Create a new admin user account"
)
async def create_admin_user(
    email: str,
    full_name: str,
    password: str,
    current_user: UserResponse = Depends(require_admin)
) -> UserResponse:
    """
    Create admin user (admin only).
    
    **Body:**
    - `email`: Admin email
    - `full_name`: Admin full name
    - `password`: Admin password (min 8 chars)
    
    **Returns:**
    - Created admin user data
    
    **Requires:** Admin role
    
    **Note:** Admin users are auto-confirmed and don't need email verification.
    """
    return await AdminUserService.create_admin_user(email, full_name, password)


@router.post(
    "/admin/{user_id}/deactivate",
    response_model=MessageResponse,
    summary="Deactivate user (Admin)",
    description="Deactivate a user account"
)
async def deactivate_user(
    user_id: str,
    current_user: UserResponse = Depends(require_admin)
) -> MessageResponse:
    """
    Deactivate user account (admin only).
    
    **Effect:**
    - User cannot login
    - Existing sessions remain valid until expiry
    - Data is preserved
    
    **Requires:** Admin role
    """
    success = await AdminUserService.deactivate_user(user_id)
    
    if success:
        return MessageResponse(
            message="User deactivated successfully",
            success=True
        )
    else:
        return MessageResponse(
            message="Failed to deactivate user",
            success=False
        )


@router.post(
    "/admin/{user_id}/activate",
    response_model=MessageResponse,
    summary="Activate user (Admin)",
    description="Activate a deactivated user account"
)
async def activate_user(
    user_id: str,
    current_user: UserResponse = Depends(require_admin)
) -> MessageResponse:
    """
    Activate user account (admin only).
    
    **Effect:**
    - User can login again
    
    **Requires:** Admin role
    """
    success = await AdminUserService.activate_user(user_id)
    
    if success:
        return MessageResponse(
            message="User activated successfully",
            success=True
        )
    else:
        return MessageResponse(
            message="Failed to activate user",
            success=False
        )