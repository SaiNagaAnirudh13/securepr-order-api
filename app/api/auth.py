from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import AppContext, get_context, get_current_user
from app.models.user import User
from app.schemas.user import LoginRequest, LoginResponse, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(
    payload: UserCreate,
    context: Annotated[AppContext, Depends(get_context)],
) -> UserResponse:
    user = context.users.register(
        email=str(payload.email),
        password=payload.password,
        display_name=payload.display_name,
    )
    return UserResponse.from_model(user)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    context: Annotated[AppContext, Depends(get_context)],
) -> LoginResponse:
    token = context.users.login(email=str(payload.email), password=payload.password)
    return LoginResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_authenticated_account(
    user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.from_model(user)
