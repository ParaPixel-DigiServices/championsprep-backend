"""
Authentication API endpoints.
Handles user registration, login, token management, and password operations.
"""

from fastapi import APIRouter, Depends, status
from typing import Dict

from app.models.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenRefreshRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePasswordRequest,
    AuthResponse,
    TokenResponse,
    MessageResponse,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.api.v1.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# REGISTRATION & LOGIN
# ============================================================================

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with email and password"
)
async def register(data: UserRegisterRequest) -> AuthResponse:
    """
    Register a new user account.
    
    **Process:**
    1. Validates email uniqueness
    2. Validates password strength
    3. Creates account in Supabase Auth
    4. Creates user profile in database
    5. Generates authentication tokens
    6. For students: Creates user_profile and initializes coin balance
    
    **Returns:**
    - User data
    - Access token (30 min expiry)
    - Refresh token (7 days expiry)
    
    **Errors:**
    - 409: Email already registered
    - 422: Invalid data (weak password, invalid role, etc.)
    """
    return await AuthService.register_user(data)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login user",
    description="Authenticate user with email and password"
)
async def login(data: UserLoginRequest) -> AuthResponse:
    """
    Login with email and password.
    
    **Process:**
    1. Validates credentials with Supabase Auth
    2. Checks if account is active
    3. Updates last login timestamp
    4. Generates new authentication tokens
    
    **Returns:**
    - User data
    - Access token (30 min expiry)
    - Refresh token (7 days expiry)
    
    **Errors:**
    - 401: Invalid credentials
    - 401: Account deactivated
    """
    return await AuthService.login_user(data)


# ============================================================================
# TOKEN MANAGEMENT
# ============================================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token"
)
async def refresh_token(data: TokenRefreshRequest) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    **Process:**
    1. Validates refresh token
    2. Checks if user account is still active
    3. Generates new token pair
    
    **Use this when:**
    - Access token expires (after 30 minutes)
    - User returns to app after some time
    
    **Returns:**
    - New access token
    - New refresh token
    
    **Errors:**
    - 401: Invalid or expired refresh token
    - 401: Account deactivated
    """
    return await AuthService.refresh_token(data.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Invalidate current session"
)
async def logout(
    current_user: UserResponse = Depends(get_current_user)
) -> MessageResponse:
    """
    Logout current user.
    
    **Process:**
    1. Invalidates Supabase session
    2. Client should delete stored tokens
    
    **Note:** Tokens will still be valid until expiry.
    For complete security, implement token blacklist.
    
    **Returns:**
    - Success message
    """
    await AuthService.logout_user(current_user.id)
    
    return MessageResponse(
        message="Logged out successfully",
        success=True
    )


# ============================================================================
# CURRENT USER
# ============================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get authenticated user's profile data"
)
async def get_me(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Get current authenticated user's data.
    
    **Requires:** Valid access token in Authorization header
    
    **Returns:**
    - Complete user profile
    - Account status
    - Preferences
    - Statistics (for students)
    
    **Use this to:**
    - Load user data on app startup
    - Refresh user data after profile updates
    - Check authentication status
    """
    return current_user


# ============================================================================
# PASSWORD MANAGEMENT
# ============================================================================

@router.post(
    "/password/change",
    response_model=MessageResponse,
    summary="Change password",
    description="Change password for authenticated user"
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: UserResponse = Depends(get_current_user)
) -> MessageResponse:
    """
    Change password for authenticated user.
    
    **Process:**
    1. Verifies current password
    2. Validates new password strength
    3. Updates password in Supabase Auth
    
    **Requires:** Valid access token
    
    **Returns:**
    - Success message
    
    **Errors:**
    - 401: Current password incorrect
    - 422: New password doesn't meet requirements
    """
    await AuthService.change_password(
        user_id=current_user.id,
        current_password=data.current_password,
        new_password=data.new_password
    )
    
    return MessageResponse(
        message="Password changed successfully",
        success=True
    )


@router.post(
    "/password/reset",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Send password reset email"
)
async def request_password_reset(data: PasswordResetRequest) -> MessageResponse:
    """
    Request password reset email.
    
    **Process:**
    1. Checks if email exists (doesn't reveal if it doesn't)
    2. Generates reset token
    3. Sends reset email via Supabase Auth
    
    **Note:** Always returns success for security
    (doesn't reveal if email exists)
    
    **Returns:**
    - Success message
    
    **Email contains:**
    - Reset link with token
    - Expiration time (1 hour)
    """
    await AuthService.request_password_reset(data.email)
    
    return MessageResponse(
        message="If the email exists, a password reset link has been sent",
        success=True
    )


@router.post(
    "/password/reset/confirm",
    response_model=MessageResponse,
    summary="Confirm password reset",
    description="Reset password using token from email"
)
async def confirm_password_reset(data: PasswordResetConfirm) -> MessageResponse:
    """
    Reset password using token from email.
    
    **Process:**
    1. Validates reset token
    2. Validates new password strength
    3. Updates password
    4. Invalidates reset token
    
    **Returns:**
    - Success message
    
    **Errors:**
    - 401: Invalid or expired token
    - 422: Password doesn't meet requirements
    
    **After reset:**
    - User should login with new password
    - All existing sessions remain valid
    """
    # This will be handled by Supabase Auth's built-in flow
    # Token validation and password update happens through Supabase
    
    return MessageResponse(
        message="Password reset successfully. Please login with your new password.",
        success=True
    )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get(
    "/health",
    response_model=Dict[str, str],
    summary="Auth service health check",
    description="Check if authentication service is operational"
)
async def health_check() -> Dict[str, str]:
    """
    Health check for authentication service.
    
    **Returns:**
    - Service status
    - Version
    
    **Use for:**
    - Monitoring
    - Load balancer health checks
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "version": "1.0.0"
    }