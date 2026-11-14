from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import AppContext, get_context, get_current_user
from app.models.user import User
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    user: Annotated[User, Depends(get_current_user)],
    context: Annotated[AppContext, Depends(get_context)],
) -> OrderResponse:
    order = context.orders.create_order(user.id, payload.items)
    return OrderResponse.from_model(order)


@router.get("", response_model=list[OrderResponse])
def list_my_orders(
    user: Annotated[User, Depends(get_current_user)],
    context: Annotated[AppContext, Depends(get_context)],
) -> list[OrderResponse]:
    return [
        OrderResponse.from_model(order)
        for order in context.orders.list_for_user(user.id)
    ]


@router.get("/{order_id}", response_model=OrderResponse)
def read_order(
    order_id: int,
    user: Annotated[User, Depends(get_current_user)],
    context: Annotated[AppContext, Depends(get_context)],
) -> OrderResponse:
    return OrderResponse.from_model(context.orders.get_order(order_id, user))


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    user: Annotated[User, Depends(get_current_user)],
    context: Annotated[AppContext, Depends(get_context)],
) -> OrderResponse:
    order = context.orders.update_status(order_id, payload.status, user)
    return OrderResponse.from_model(order)
