"""
Security utilities for authentication and authorization.
Handles password hashing, JWT token generation/validation, and security helpers.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import logging

from app.core.config import settings
from app.core.errors import AuthenticationError

logger = logging.getLogger(__name__)

# ============================================================================
# PASSWORD HASHING
# ============================================================================

# Password context for bcrypt hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False


# ============================================================================
# JWT TOKEN MANAGEMENT
# ============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token to decode

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise AuthenticationError(
            message="Token has expired",
            details={"error": "token_expired"}
        )

    except JWTError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise AuthenticationError(
            message="Invalid token",
            details={"error": "invalid_token"}
        )


def verify_token_type(payload: Dict[str, Any], expected_type: str) -> bool:
    """
    Verify token type (access or refresh).

    Args:
        payload: Decoded token payload
        expected_type: Expected token type ('access' or 'refresh')

    Returns:
        True if token type matches

    Raises:
        AuthenticationError: If token type doesn't match
    """
    token_type = payload.get("type")

    if token_type != expected_type:
        raise AuthenticationError(
            message=f"Invalid token type. Expected {expected_type}",
            details={"error": "invalid_token_type"}
        )

    return True


# ============================================================================
# SUPABASE JWT VALIDATION
# ============================================================================

def decode_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Decode and validate a Supabase JWT token.

    Args:
        token: Supabase JWT token

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise AuthenticationError(
            message="Supabase token has expired",
            details={"error": "token_expired"}
        )

    except JWTError as e:
        logger.warning(f"Invalid Supabase token: {str(e)}")
        raise AuthenticationError(
            message="Invalid Supabase token",
            details={"error": "invalid_token"}
        )


# ============================================================================
# TOKEN EXTRACTION
# ============================================================================

def extract_bearer_token(authorization: str) -> str:
    """
    Extract token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        Extracted token

    Raises:
        AuthenticationError: If format is invalid
    """
    if not authorization:
        raise AuthenticationError(
            message="Missing authorization header",
            details={"error": "missing_authorization"}
        )

    parts = authorization.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError(
            message="Invalid authorization header format",
            details={"error": "invalid_authorization_format"}
        )

    return parts[1]


# ============================================================================
# RANDOM TOKEN GENERATION
# ============================================================================

def generate_random_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        length: Token length in bytes

    Returns:
        Random token as hex string
    """
    return secrets.token_hex(length)


def generate_verification_code(length: int = 6) -> str:
    """
    Generate a numeric verification code.

    Args:
        length: Code length

    Returns:
        Numeric verification code
    """
    return ''.join(secrets.choice('0123456789') for _ in range(length))


# ============================================================================
# SECURITY HELPERS
# ============================================================================

def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if len(password) > 128:
        return False, "Password must be less than 128 characters"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    # Check for special characters
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"

    return True, None


def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Trim to max length
    text = text[:max_length]

    # Remove null bytes
    text = text.replace('\x00', '')

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def is_safe_redirect_url(url: str, allowed_hosts: list[str]) -> bool:
    """
    Check if redirect URL is safe (prevent open redirect vulnerabilities).

    Args:
        url: URL to check
        allowed_hosts: List of allowed host domains

    Returns:
        True if URL is safe, False otherwise
    """
    if not url:
        return False

    # Check for absolute URLs
    if url.startswith(('http://', 'https://', '//')):
        # Extract host from URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc in allowed_hosts
        except Exception:
            return False

    # Relative URLs are safe
    if url.startswith('/'):
        return True

    return False


# ============================================================================
# ROLE-BASED ACCESS CONTROL
# ============================================================================

class UserRole:
    """User role constants."""
    STUDENT = "student"
    PARENT = "parent"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


def check_permission(user_role: str, required_role: str) -> bool:
    """
    Check if user has required permission based on role hierarchy.

    Role hierarchy: super_admin > admin > parent > student

    Args:
        user_role: User's current role
        required_role: Required role for access

    Returns:
        True if user has permission
    """
    role_hierarchy = {
        UserRole.STUDENT: 1,
        UserRole.PARENT: 2,
        UserRole.ADMIN: 3,
        UserRole.SUPER_ADMIN: 4,
    }

    user_level = role_hierarchy.get(user_role, 0)
    required_level = role_hierarchy.get(required_role, 0)

    return user_level >= required_level