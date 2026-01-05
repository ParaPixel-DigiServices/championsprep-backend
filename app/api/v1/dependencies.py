"""
Authentication dependencies for FastAPI routes.
Provides current user injection and role-based access control.
"""

from typing import Optional
from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import decode_token, extract_bearer_token, check_permission, UserRole
from app.core.errors import AuthenticationError, AuthorizationError
from app.services.auth_service import AuthService
from app.models.auth import UserResponse
import logging

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


# ============================================================================
# CURRENT USER DEPENDENCY
# ============================================================================

async def get_current_user(
    authorization: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserResponse:
    """
    Get current authenticated user from JWT token.
    
    Args:
        authorization: Authorization header
        credentials: HTTP Bearer credentials
    
    Returns:
        Current user data
    
    Raises:
        AuthenticationError: If token is invalid or user not found
    
    Usage:
        @app.get("/protected")
        async def protected_route(current_user: UserResponse = Depends(get_current_user)):
            return {"user_id": current_user.id}
    """
    # Try to get token from Authorization header
    token = None
    
    if credentials:
        token = credentials.credentials
    elif authorization:
        try:
            token = extract_bearer_token(authorization)
        except AuthenticationError:
            pass
    
    if not token:
        raise AuthenticationError(
            message="Missing authentication token",
            details={"error": "no_token"}
        )
    
    try:
        # Decode and validate token
        payload = decode_token(token)
        
        # Verify it's an access token
        if payload.get("type") != "access":
            raise AuthenticationError(
                message="Invalid token type",
                details={"error": "invalid_token_type"}
            )
        
        # Extract user ID
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError(
                message="Invalid token payload",
                details={"error": "missing_user_id"}
            )
        
        # Get user data
        user = await AuthService.get_current_user(user_id)
        
        return user
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}", exc_info=True)
        raise AuthenticationError(
            message="Authentication failed",
            details={"error": str(e)}
        )


# ============================================================================
# OPTIONAL USER DEPENDENCY
# ============================================================================

async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserResponse]:
    """
    Get current user if authenticated, None otherwise.
    Use for optional authentication.
    
    Args:
        authorization: Authorization header
        credentials: HTTP Bearer credentials
    
    Returns:
        Current user data or None
    
    Usage:
        @app.get("/public-or-private")
        async def route(current_user: Optional[UserResponse] = Depends(get_current_user_optional)):
            if current_user:
                return {"message": f"Hello {current_user.full_name}"}
            return {"message": "Hello guest"}
    """
    try:
        return await get_current_user(authorization, credentials)
    except AuthenticationError:
        return None


# ============================================================================
# ROLE-BASED ACCESS CONTROL
# ============================================================================

def require_role(required_role: str):
    """
    Dependency factory for role-based access control.
    
    Args:
        required_role: Minimum required role
    
    Returns:
        Dependency function
    
    Usage:
        @app.get("/admin-only")
        async def admin_route(current_user: UserResponse = Depends(require_role(UserRole.ADMIN))):
            return {"message": "Admin access granted"}
    """
    async def role_checker(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        """Check if user has required role."""
        if not check_permission(current_user.role, required_role):
            raise AuthorizationError(
                message=f"Requires {required_role} role or higher",
                details={
                    "user_role": current_user.role,
                    "required_role": required_role
                }
            )
        return current_user
    
    return role_checker


# ============================================================================
# SPECIFIC ROLE DEPENDENCIES
# ============================================================================

async def require_student(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Require student role or higher.
    
    Usage:
        @app.get("/student")
        async def student_route(current_user: UserResponse = Depends(require_student)):
            return {"message": "Student access"}
    """
    if not check_permission(current_user.role, UserRole.STUDENT):
        raise AuthorizationError(message="Student access required")
    return current_user


async def require_parent(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Require parent role or higher.
    
    Usage:
        @app.get("/parent")
        async def parent_route(current_user: UserResponse = Depends(require_parent)):
            return {"message": "Parent access"}
    """
    if not check_permission(current_user.role, UserRole.PARENT):
        raise AuthorizationError(message="Parent access required")
    return current_user


async def require_admin(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Require admin role or higher.
    
    Usage:
        @app.get("/admin")
        async def admin_route(current_user: UserResponse = Depends(require_admin)):
            return {"message": "Admin access"}
    """
    if not check_permission(current_user.role, UserRole.ADMIN):
        raise AuthorizationError(message="Admin access required")
    return current_user


async def require_super_admin(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Require super admin role.
    
    Usage:
        @app.get("/super-admin")
        async def super_admin_route(current_user: UserResponse = Depends(require_super_admin)):
            return {"message": "Super admin access"}
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise AuthorizationError(message="Super admin access required")
    return current_user


# ============================================================================
# ACTIVE USER CHECK
# ============================================================================

async def require_active_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Require active user account.
    
    Usage:
        @app.get("/active-only")
        async def active_route(current_user: UserResponse = Depends(require_active_user)):
            return {"message": "Active user access"}
    """
    if not current_user.is_active:
        raise AuthorizationError(
            message="Account is deactivated",
            details={"status": "inactive"}
        )
    return current_user


async def require_verified_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Require verified email.
    
    Usage:
        @app.get("/verified-only")
        async def verified_route(current_user: UserResponse = Depends(require_verified_user)):
            return {"message": "Verified user access"}
    """
    if not current_user.is_verified:
        raise AuthorizationError(
            message="Email verification required",
            details={"verified": False}
        )
    return current_user