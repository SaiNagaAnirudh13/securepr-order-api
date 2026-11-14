from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    AppContext,
    get_context,
    get_current_user,
    require_admin,
)
from app.core.errors import NotFoundError
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def read_my_account(
    user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.from_model(user)


@router.patch("/me", response_model=UserResponse)
def update_my_account(
    payload: UserUpdate,
    user: Annotated[User, Depends(get_current_user)],
    context: Annotated[AppContext, Depends(get_context)],
) -> UserResponse:
    updated = context.users.update_display_name(
        user.id, payload.display_name
    )
    return UserResponse.from_model(updated)


@router.get("/{user_id}", response_model=UserResponse)
def read_account(
    user_id: int,
    _: Annotated[User, Depends(require_admin)],
    context: Annotated[AppContext, Depends(get_context)],
) -> UserResponse:
    user = context.users.get_user(user_id)
    if user is None:
        raise NotFoundError("Account not found")
    return UserResponse.from_model(user)
