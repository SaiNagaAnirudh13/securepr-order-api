from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import AppContext, get_context, require_admin
from app.models.user import User
from app.schemas.order import OrderBulkStatusUpdate, OrderResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/admin", tags=["administration"])


@router.get("/users", response_model=list[UserResponse])
def list_users(
    _: Annotated[User, Depends(require_admin)],
    context: Annotated[AppContext, Depends(get_context)],
) -> list[UserResponse]:
    return [
        UserResponse.from_model(user) for user in context.users.list_users()
    ]


@router.get("/orders", response_model=list[OrderResponse])
def list_all_orders(
    _: Annotated[User, Depends(require_admin)],
    context: Annotated[AppContext, Depends(get_context)],
) -> list[OrderResponse]:
    return [
        OrderResponse.from_model(order)
        for order in context.orders.list_all()
    ]


@router.patch("/orders/bulk-status", response_model=list[OrderResponse])
def bulk_update_order_statuses(
    payload: OrderBulkStatusUpdate,
    user: Annotated[User, Depends(require_admin)],
    context: Annotated[AppContext, Depends(get_context)],
) -> list[OrderResponse]:
    orders = context.orders.bulk_update_statuses(
        payload.order_ids, payload.status, user
    )
    return [OrderResponse.from_model(order) for order in orders]
