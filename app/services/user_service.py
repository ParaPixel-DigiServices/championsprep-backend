"""
User service.
Handles user profile management, statistics, and admin operations.
"""

from typing import Optional, List
from datetime import datetime
import logging

from app.core.errors import NotFoundError, ValidationError, AuthorizationError
from app.db.supabase import supabase
from app.models.user import (
    UserProfileUpdate,
    UserProfileResponse,
    UserStatsResponse,
    AcademicInfoUpdate,
    PreferencesUpdate,
    UserListItem,
    ProfileCompletionRequest,
)
from app.models.auth import UserResponse

logger = logging.getLogger(__name__)


# ============================================================================
# USER SERVICE
# ============================================================================

class UserService:
    """Service for handling user profile operations."""
    
    @staticmethod
    async def complete_profile(user_id: str, data: ProfileCompletionRequest) -> UserProfileResponse:
        """
        Complete user profile setup (first-time only).
        This locks grade_level and board - they cannot be changed later by user.
        
        Args:
            user_id: User ID
            data: Profile completion data
        
        Returns:
            Complete user profile
        
        Raises:
            ValidationError: If profile already completed or update fails
        """
        try:
            # Check if profile already completed
            user_result = supabase.table("users").select("profile_completed, grade_level, board").eq("id", user_id).execute()
            
            if not user_result.data:
                raise NotFoundError(resource="User")
            
            user = user_result.data[0]
            
            # If profile already completed, don't allow changes to grade/board
            if user.get("profile_completed"):
                raise ValidationError(
                    message="Profile already completed. Grade and board are locked.",
                    details={
                        "locked_fields": ["grade_level", "board"],
                        "contact": "Contact admin to change these fields"
                    }
                )
            
            # Update users table
            user_updates = {
                "grade_level": data.grade_level,
                "board": data.board,
                "preferred_language": data.preferred_language,
                "target_exam": data.target_exam,
                "profile_completed": True,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            supabase.table("users").update(user_updates).eq("id", user_id).execute()
            
            # Update user_profiles table (if student)
            profile_updates = {
                "school_name": data.school_name,
                "board": data.board,
                "subjects": data.subjects,
                "study_hours_per_day": data.study_hours_per_day,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            supabase.table("user_profiles").update(profile_updates).eq("user_id", user_id).execute()
            
            logger.info(f"Profile completed for user: {user_id} (Grade: {data.grade_level}, Board: {data.board})")
            
            # Return updated profile
            return await UserService.get_user_profile(user_id)
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Complete profile error: {str(e)}", exc_info=True)
            raise ValidationError(
                message="Failed to complete profile",
                details={"error": str(e)}
            )
    
    @staticmethod
    async def get_user_profile(user_id: str) -> UserProfileResponse:
        """
        Get complete user profile with stats.
        
        Args:
            user_id: User ID
        
        Returns:
            Complete user profile with statistics
        
        Raises:
            NotFoundError: If user not found
        """
        try:
            # Get user data
            user_result = supabase.table("users").select("*").eq("id", user_id).execute()
            
            if not user_result.data:
                raise NotFoundError(resource="User")
            
            user = user_result.data[0]
            
            # Get profile data (if student)
            profile_data = {}
            if user.get("role") == "student":
                profile_result = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
                
                if profile_result.data:
                    profile_data = profile_result.data[0]
            
            # Merge user and profile data
            combined_data = {**user, **profile_data}
            
            return UserProfileResponse(**combined_data)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Get user profile error: {str(e)}", exc_info=True)
            raise NotFoundError(resource="User")
    
    @staticmethod
    async def update_user_profile(user_id: str, data: UserProfileUpdate) -> UserProfileResponse:
        """
        Update user profile.
        
        Args:
            user_id: User ID
            data: Profile update data
        
        Returns:
            Updated user profile
        
        Raises:
            NotFoundError: If user not found
            ValidationError: If trying to change locked fields
        """
        try:
            # Check if user is trying to change locked fields
            user_check = supabase.table("users").select("profile_completed, grade_level, board").eq("id", user_id).execute()
            
            if user_check.data and user_check.data[0].get("profile_completed"):
                # Profile is completed - grade_level and board are locked
                if data.grade_level is not None:
                    raise ValidationError(
                        message="Cannot change grade level after profile completion",
                        details={"locked_field": "grade_level", "contact_admin": True}
                    )
            
            # Prepare update data (only non-None fields)
            user_updates = {}
            profile_updates = {}
            
            # Fields that go in users table
            if data.full_name is not None:
                user_updates["full_name"] = data.full_name
            if data.phone is not None:
                user_updates["phone"] = data.phone
            if data.date_of_birth is not None:
                user_updates["date_of_birth"] = str(data.date_of_birth)
            if data.avatar_url is not None:
                user_updates["avatar_url"] = data.avatar_url
            # grade_level is locked after profile completion
            if data.target_exam is not None:
                user_updates["target_exam"] = data.target_exam
            if data.learning_pace is not None:
                user_updates["learning_pace"] = data.learning_pace
            if data.preferred_language is not None:
                user_updates["preferred_language"] = data.preferred_language
            if data.timezone is not None:
                user_updates["timezone"] = data.timezone
            
            # Update users table
            if user_updates:
                user_updates["updated_at"] = datetime.utcnow().isoformat()
                supabase.table("users").update(user_updates).eq("id", user_id).execute()
            
            # Get updated profile
            return await UserService.get_user_profile(user_id)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Update user profile error: {str(e)}", exc_info=True)
            raise ValidationError(
                message="Failed to update profile",
                details={"error": str(e)}
            )
    
    @staticmethod
    async def update_academic_info(user_id: str, data: AcademicInfoUpdate) -> UserProfileResponse:
        """
        Update academic information.
        
        Args:
            user_id: User ID
            data: Academic info update data
        
        Returns:
            Updated user profile
        
        Raises:
            NotFoundError: If user not found
        """
        try:
            # Prepare update data (only non-None fields)
            updates = {}
            
            if data.school_name is not None:
                updates["school_name"] = data.school_name
            if data.board is not None:
                updates["board"] = data.board
            if data.subjects is not None:
                updates["subjects"] = data.subjects
            if data.study_hours_per_day is not None:
                updates["study_hours_per_day"] = data.study_hours_per_day
            if data.preferred_study_time is not None:
                updates["preferred_study_time"] = data.preferred_study_time
            if data.target_score is not None:
                updates["target_score"] = data.target_score
            if data.exam_date is not None:
                updates["exam_date"] = str(data.exam_date)
            
            # Update user_profiles table
            if updates:
                updates["updated_at"] = datetime.utcnow().isoformat()
                supabase.table("user_profiles").update(updates).eq("user_id", user_id).execute()
            
            # Get updated profile
            return await UserService.get_user_profile(user_id)
            
        except Exception as e:
            logger.error(f"Update academic info error: {str(e)}", exc_info=True)
            raise ValidationError(
                message="Failed to update academic information",
                details={"error": str(e)}
            )
    
    @staticmethod
    async def update_preferences(user_id: str, data: PreferencesUpdate) -> UserProfileResponse:
        """
        Update user preferences.
        
        Args:
            user_id: User ID
            data: Preferences update data
        
        Returns:
            Updated user profile
        """
        try:
            updates = {}
            
            if data.preferred_language is not None:
                updates["preferred_language"] = data.preferred_language
            if data.timezone is not None:
                updates["timezone"] = data.timezone
            
            if updates:
                updates["updated_at"] = datetime.utcnow().isoformat()
                supabase.table("users").update(updates).eq("id", user_id).execute()
            
            return await UserService.get_user_profile(user_id)
            
        except Exception as e:
            logger.error(f"Update preferences error: {str(e)}", exc_info=True)
            raise ValidationError(
                message="Failed to update preferences",
                details={"error": str(e)}
            )
    
    @staticmethod
    async def get_user_stats(user_id: str) -> UserStatsResponse:
        """
        Get user statistics.
        
        Args:
            user_id: User ID
        
        Returns:
            User statistics
        """
        try:
            # Use the user_stats view we created
            stats_result = supabase.table("user_stats").select("*").eq("user_id", user_id).execute()
            
            if not stats_result.data:
                # Return default stats if no data yet
                return UserStatsResponse(
                    total_study_time_minutes=0,
                    total_questions_attempted=0,
                    total_questions_correct=0,
                    accuracy_percentage=0.0,
                    current_streak_days=0,
                    longest_streak_days=0,
                    total_sessions=0,
                    achievements_earned=0
                )
            
            stats = stats_result.data[0]
            
            return UserStatsResponse(**stats)
            
        except Exception as e:
            logger.error(f"Get user stats error: {str(e)}", exc_info=True)
            # Return default stats on error
            return UserStatsResponse(
                total_study_time_minutes=0,
                total_questions_attempted=0,
                total_questions_correct=0,
                accuracy_percentage=0.0,
                current_streak_days=0,
                longest_streak_days=0,
                total_sessions=0,
                achievements_earned=0
            )


# ============================================================================
# ADMIN USER OPERATIONS
# ============================================================================

class AdminUserService:
    """Service for admin user management operations."""
    
    @staticmethod
    async def get_all_users(
        role: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[UserListItem], int]:
        """
        Get paginated list of users (admin only).
        
        Args:
            role: Filter by role (optional)
            limit: Number of users per page
            offset: Offset for pagination
        
        Returns:
            Tuple of (users list, total count)
        """
        try:
            # Build query
            query = supabase.table("users").select("*", count="exact")
            
            if role:
                query = query.eq("role", role)
            
            # Execute with pagination
            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            users = [UserListItem(**user) for user in result.data]
            total = result.count or 0
            
            return users, total
            
        except Exception as e:
            logger.error(f"Get all users error: {str(e)}", exc_info=True)
            return [], 0
    
    @staticmethod
    async def create_admin_user(email: str, full_name: str, password: str) -> UserResponse:
        """
        Create admin user (super admin only).
        
        Args:
            email: Admin email
            full_name: Admin full name
            password: Admin password
        
        Returns:
            Created admin user
        
        Raises:
            ValidationError: If creation fails
        """
        try:
            # Create user with Supabase Auth
            auth_response = supabase.auth.admin.create_user({
                "email": email,
                "password": password[:72],  # Truncate to 72 bytes
                "email_confirm": True,  # Auto-confirm admin users
                "user_metadata": {
                    "full_name": full_name,
                    "role": "admin"
                }
            })
            
            if not auth_response.user:
                raise ValidationError(message="Failed to create admin user")
            
            user_id = auth_response.user.id
            
            # Insert into users table
            user_data = {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "role": "admin",
                "is_active": True,
                "is_verified": True,
                "email_verified_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            result = supabase.table("users").insert(user_data).execute()
            
            if not result.data:
                raise ValidationError(message="Failed to create admin profile")
            
            logger.info(f"Admin user created: {email}")
            
            return UserResponse(**result.data[0])
            
        except Exception as e:
            logger.error(f"Create admin user error: {str(e)}", exc_info=True)
            raise ValidationError(
                message="Failed to create admin user",
                details={"error": str(e)}
            )
    
    @staticmethod
    async def deactivate_user(user_id: str) -> bool:
        """
        Deactivate user account (admin only).
        
        Args:
            user_id: User ID to deactivate
        
        Returns:
            True if successful
        """
        try:
            supabase.table("users").update({
                "is_active": False,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            
            logger.info(f"User deactivated: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Deactivate user error: {str(e)}")
            return False
    
    @staticmethod
    async def activate_user(user_id: str) -> bool:
        """
        Activate user account (admin only).
        
        Args:
            user_id: User ID to activate
        
        Returns:
            True if successful
        """
        try:
            supabase.table("users").update({
                "is_active": True,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            
            logger.info(f"User activated: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Activate user error: {str(e)}")
            return False