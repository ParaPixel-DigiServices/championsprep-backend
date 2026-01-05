"""
Authentication service.
Handles user registration, login, token management, and password operations.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    generate_random_token,
)
from app.core.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.db.supabase import supabase
from app.models.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    AuthResponse,
)

logger = logging.getLogger(__name__)


# ============================================================================
# AUTHENTICATION SERVICE
# ============================================================================

class AuthService:
    """Service for handling authentication operations."""
    
    @staticmethod
    async def register_user(data: UserRegisterRequest) -> AuthResponse:
        """
        Register a new user.
        
        Args:
            data: User registration data
        
        Returns:
            AuthResponse with user data and tokens
        
        Raises:
            ConflictError: If email already exists
            ValidationError: If data is invalid
        """
        try:
            # Check if user already exists
            existing_user = supabase.table("users").select("id").eq("email", data.email).execute()
            
            if existing_user.data:
                raise ConflictError(
                    resource="User with this email",
                    details={"email": data.email}
                )
            
            # Truncate password to 72 bytes for bcrypt compatibility
            password = data.password[:72]
            
            # Create user with Supabase Auth
            auth_response = supabase.auth.sign_up({
                "email": data.email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": data.full_name,
                        "role": data.role,
                    }
                }
            })
            
            if not auth_response.user:
                raise ValidationError(
                    message="Failed to create user account",
                    details={"error": "Supabase auth signup failed"}
                )
            
            user_id = auth_response.user.id
            
            # Insert user data into our users table
            user_data = {
                "id": user_id,
                "email": data.email,
                "full_name": data.full_name,
                "role": data.role,
                "phone": data.phone,
                "date_of_birth": str(data.date_of_birth) if data.date_of_birth else None,
                "grade_level": data.grade_level,
                "target_exam": data.target_exam,
                "is_active": True,
                "is_verified": False,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            user_result = supabase.table("users").insert(user_data).execute()
            
            if not user_result.data:
                # Rollback: Delete auth user if database insert fails
                try:
                    supabase.auth.admin.delete_user(user_id)
                except Exception:
                    pass
                raise ValidationError(message="Failed to create user profile")
            
            created_user = user_result.data[0]
            
            # Create user profile if student
            if data.role == "student":
                profile_data = {
                    "user_id": user_id,
                }
                
                supabase.table("user_profiles").insert(profile_data).execute()
                
                # Initialize coin balance
                coin_data = {
                    "user_id": user_id,
                    "balance": 100,  # Welcome bonus
                    "lifetime_earned": 100,
                }
                
                supabase.table("user_coins").insert(coin_data).execute()
            
            # Generate tokens
            tokens = AuthService._generate_tokens(created_user)
            
            # Update last login
            supabase.table("users").update({
                "last_login_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            
            # Convert to response models
            user_response = UserResponse(**created_user)
            
            logger.info(f"User registered successfully: {data.email}")
            
            return AuthResponse(
                user=user_response,
                tokens=tokens
            )
            
        except (ConflictError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            raise ValidationError(
                message="Failed to register user",
                details={"error": str(e)}
            )
    
    @staticmethod
    async def login_user(data: UserLoginRequest) -> AuthResponse:
        """
        Login user with email and password.
        
        Args:
            data: Login credentials
        
        Returns:
            AuthResponse with user data and tokens
        
        Raises:
            AuthenticationError: If credentials are invalid
        """
        try:
            # Authenticate with Supabase Auth
            auth_response = supabase.auth.sign_in_with_password({
                "email": data.email,
                "password": data.password
            })
            
            if not auth_response.user:
                raise AuthenticationError(
                    message="Invalid email or password",
                    details={"email": data.email}
                )
            
            user_id = auth_response.user.id
            
            # Get user data from our database
            user_result = supabase.table("users").select("*").eq("id", user_id).execute()
            
            if not user_result.data:
                raise AuthenticationError(message="User profile not found")
            
            user = user_result.data[0]
            
            # Check if user is active
            if not user.get("is_active", True):
                raise AuthenticationError(
                    message="Account is deactivated",
                    details={"status": "inactive"}
                )
            
            # Generate tokens
            tokens = AuthService._generate_tokens(user)
            
            # Update last login
            supabase.table("users").update({
                "last_login_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            
            # Convert to response models
            user_response = UserResponse(**user)
            
            logger.info(f"User logged in successfully: {data.email}")
            
            return AuthResponse(
                user=user_response,
                tokens=tokens
            )
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            raise AuthenticationError(
                message="Login failed",
                details={"error": str(e)}
            )
    
    @staticmethod
    async def refresh_token(refresh_token: str) -> TokenResponse:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
        
        Returns:
            New token pair
        
        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            # Decode and verify refresh token
            payload = decode_token(refresh_token)
            verify_token_type(payload, "refresh")
            
            user_id = payload.get("sub")
            
            # Get user data
            user_result = supabase.table("users").select("*").eq("id", user_id).execute()
            
            if not user_result.data:
                raise AuthenticationError(message="User not found")
            
            user = user_result.data[0]
            
            # Check if user is active
            if not user.get("is_active", True):
                raise AuthenticationError(message="Account is deactivated")
            
            # Generate new tokens
            tokens = AuthService._generate_tokens(user)
            
            logger.info(f"Token refreshed for user: {user['email']}")
            
            return tokens
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}", exc_info=True)
            raise AuthenticationError(
                message="Failed to refresh token",
                details={"error": str(e)}
            )
    
    @staticmethod
    async def logout_user(user_id: str) -> bool:
        """
        Logout user (invalidate Supabase session).
        
        Args:
            user_id: User ID
        
        Returns:
            True if successful
        """
        try:
            # Sign out from Supabase Auth
            supabase.auth.sign_out()
            
            logger.info(f"User logged out: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return False
    
    @staticmethod
    async def get_current_user(user_id: str) -> UserResponse:
        """
        Get current user data.
        
        Args:
            user_id: User ID from token
        
        Returns:
            User data
        
        Raises:
            NotFoundError: If user not found
        """
        try:
            user_result = supabase.table("users").select("*").eq("id", user_id).execute()
            
            if not user_result.data:
                raise NotFoundError(resource="User")
            
            user = user_result.data[0]
            
            return UserResponse(**user)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Get current user error: {str(e)}")
            raise NotFoundError(resource="User")
    
    @staticmethod
    async def change_password(user_id: str, current_password: str, new_password: str) -> bool:
        """
        Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
        
        Returns:
            True if successful
        
        Raises:
            AuthenticationError: If current password is incorrect
        """
        try:
            # Get user
            user_result = supabase.table("users").select("email").eq("id", user_id).execute()
            
            if not user_result.data:
                raise AuthenticationError(message="User not found")
            
            user = user_result.data[0]
            
            # Verify current password by attempting login
            try:
                supabase.auth.sign_in_with_password({
                    "email": user["email"],
                    "password": current_password
                })
            except Exception:
                raise AuthenticationError(message="Current password is incorrect")
            
            # Update password in Supabase Auth
            supabase.auth.update_user({
                "password": new_password
            })
            
            logger.info(f"Password changed for user: {user_id}")
            return True
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Change password error: {str(e)}")
            raise ValidationError(
                message="Failed to change password",
                details={"error": str(e)}
            )
    
    @staticmethod
    async def request_password_reset(email: str) -> bool:
        """
        Request password reset email.
        
        Args:
            email: User email
        
        Returns:
            True if email sent (always returns True for security)
        """
        try:
            # Check if user exists
            user_result = supabase.table("users").select("id").eq("email", email).execute()
            
            if user_result.data:
                # Send reset email via Supabase Auth
                supabase.auth.reset_password_for_email(email)
                logger.info(f"Password reset requested for: {email}")
            else:
                # For security, don't reveal if email doesn't exist
                logger.info(f"Password reset requested for non-existent email: {email}")
            
            return True
            
        except Exception as e:
            logger.error(f"Password reset request error: {str(e)}")
            # Still return True to not reveal if user exists
            return True
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    @staticmethod
    def _generate_tokens(user: Dict[str, Any]) -> TokenResponse:
        """
        Generate access and refresh tokens for user.
        
        Args:
            user: User data dictionary
        
        Returns:
            TokenResponse with both tokens
        """
        token_data = {
            "sub": str(user["id"]),
            "email": user["email"],
            "role": user["role"],
        }
        
        # Create access token
        access_token = create_access_token(token_data)
        
        # Create refresh token
        refresh_token = create_refresh_token(token_data)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )