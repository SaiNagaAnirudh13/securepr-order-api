from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import AuthenticationError, AuthorizationError
from app.core.security import SessionManager
from app.models.user import User
from app.services.order_service import OrderService
from app.services.user_service import UserService


@dataclass(frozen=True)
class AppContext:
    users: UserService
    orders: OrderService
    sessions: SessionManager


bearer_scheme = HTTPBearer(auto_error=False)


def get_context(request: Request) -> AppContext:
    return request.app.state.context


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    context: Annotated[AppContext, Depends(get_context)],
) -> User:
    if credentials is None:
        raise AuthenticationError("A bearer token is required")
    user_id = context.sessions.resolve(credentials.credentials)
    if user_id is None:
        raise AuthenticationError("The bearer token is invalid or expired")
    user = context.users.get_user(user_id)
    if user is None:
        raise AuthenticationError(
            "The account associated with this token no longer exists"
        )
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "admin":
        raise AuthorizationError("Administrator access is required")
    return user
