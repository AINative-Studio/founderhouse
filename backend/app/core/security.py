"""
Security Module
Handles authentication, authorization, and JWT token management
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError

from app.config import get_settings

logger = logging.getLogger(__name__)

# Security scheme for Bearer token authentication
security = HTTPBearer()


class TokenData(BaseModel):
    """Structure of decoded JWT token data"""
    user_id: UUID
    workspace_id: Optional[UUID] = None
    role: Optional[str] = None
    exp: Optional[datetime] = None


class AuthUser(BaseModel):
    """Authenticated user information"""
    user_id: UUID
    workspace_id: Optional[UUID] = None
    role: str = "member"
    email: Optional[str] = None


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )

    logger.debug(f"Created access token for user: {data.get('user_id')}")
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """
    Verify and decode JWT token

    Args:
        token: JWT token string

    Returns:
        TokenData object with decoded claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_data = TokenData(
            user_id=UUID(user_id),
            workspace_id=UUID(payload.get("workspace_id")) if payload.get("workspace_id") else None,
            role=payload.get("role"),
            exp=datetime.fromtimestamp(payload.get("exp")) if payload.get("exp") else None
        )

        logger.debug(f"Token verified for user: {user_id}")
        return token_data

    except (JWTError, ValidationError, ValueError) as e:
        logger.warning(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthUser:
    """
    Dependency to get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer credentials from request header

    Returns:
        AuthUser object with user information

    Raises:
        HTTPException: If authentication fails

    Usage:
        @app.get("/protected")
        async def protected_route(user: AuthUser = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    token = credentials.credentials
    token_data = verify_token(token)

    user = AuthUser(
        user_id=token_data.user_id,
        workspace_id=token_data.workspace_id,
        role=token_data.role or "member"
    )

    return user


async def get_current_active_user(
    current_user: AuthUser = Depends(get_current_user)
) -> AuthUser:
    """
    Dependency to get current active user
    Can be extended to check if user is active/enabled

    Args:
        current_user: Current authenticated user

    Returns:
        AuthUser if active

    Raises:
        HTTPException: If user is not active
    """
    # Add additional checks here if needed (e.g., is_active flag)
    return current_user


def require_role(required_role: str):
    """
    Dependency factory to require specific role

    Args:
        required_role: Required role (owner, admin, member, viewer)

    Returns:
        Dependency function that checks role

    Usage:
        @app.delete("/admin/resource")
        async def admin_only(user: AuthUser = Depends(require_role("admin"))):
            return {"message": "Admin access granted"}
    """
    async def role_checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        role_hierarchy = {
            "owner": 4,
            "admin": 3,
            "member": 2,
            "viewer": 1,
            "service": 0
        }

        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        if user_level < required_level:
            logger.warning(
                f"Access denied: User {user.user_id} with role {user.role} "
                f"attempted to access resource requiring {required_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )

        return user

    return role_checker


async def verify_workspace_access(
    workspace_id: UUID,
    user: AuthUser = Depends(get_current_user)
) -> bool:
    """
    Verify user has access to specific workspace

    Args:
        workspace_id: Workspace UUID to check access
        user: Current authenticated user

    Returns:
        True if user has access

    Raises:
        HTTPException: If access is denied
    """
    # In a real implementation, query the database to verify workspace membership
    # For now, we check if the token's workspace_id matches
    if user.workspace_id and user.workspace_id != workspace_id:
        logger.warning(
            f"Workspace access denied: User {user.user_id} "
            f"attempted to access workspace {workspace_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this workspace"
        )

    return True


# API Key authentication (for service-to-service)

async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Verify API key for service-to-service authentication

    Args:
        credentials: HTTP Bearer credentials (API key)

    Returns:
        Dictionary with API key metadata

    Raises:
        HTTPException: If API key is invalid
    """
    api_key = credentials.credentials

    # In production, validate API key against database
    # For now, this is a placeholder
    if not api_key.startswith("sk_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("API key verified")
    return {
        "api_key": api_key,
        "type": "service",
        "validated_at": datetime.utcnow()
    }


# Password hashing utilities (if needed for custom auth)

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    # Using Supabase Auth, so this may not be needed
    # But included for completeness
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to verify against

    Returns:
        True if password matches
    """
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain_password, hashed_password)
