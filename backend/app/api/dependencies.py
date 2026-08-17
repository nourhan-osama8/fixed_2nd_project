from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.core.constants import UserRole


bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:

    token = credentials.credentials.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    print("\n========== AUTH DEBUG ==========")
    print("TOKEN RECEIVED:", token[:30] + "..." if token else "EMPTY")
    print("TOKEN LENGTH:", len(token))

    payload = decode_access_token(token)

    print("DECODED PAYLOAD:", payload)
    print("================================\n")

    if not payload:
        raise UnauthorizedError("Invalid or expired token")

    user_id = payload.get("sub")

    print("USER ID FROM TOKEN:", user_id)

    if not user_id:
        raise UnauthorizedError("Invalid token payload")

    repo = UserRepository(db)

    user = repo.get_by_id(user_id)

    print("USER FROM DATABASE:", user.email if user else None)

    if not user:
        raise UnauthorizedError("User not found")

    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:

    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError("Admin access required")

    return current_user


def require_agent_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:

    if current_user.role not in (
        UserRole.ADMIN,
        UserRole.CALL_CENTER,
    ):
        raise ForbiddenError("Access denied")

    return current_user