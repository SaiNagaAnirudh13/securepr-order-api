import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import admin, auth, orders, users
from app.api.dependencies import AppContext
from app.core.config import Settings
from app.core.errors import DomainError
from app.core.security import SessionManager
from app.database.connection import Database
from app.repositories.order_repository import OrderRepository
from app.repositories.user_repository import UserRepository
from app.services.order_service import OrderService
from app.services.user_service import UserService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    logging.basicConfig(level=getattr(logging, settings.log_level))
    database = Database(settings.database_path)
    sessions = SessionManager(settings.session_ttl_seconds)
    user_repository = UserRepository(database)
    order_repository = OrderRepository(database)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.initialize()
        yield
        database.close()

    application = FastAPI(
        title="Order and Account Management API",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.context = AppContext(
        users=UserService(user_repository, sessions),
        orders=OrderService(order_repository),
        sessions=sessions,
    )
    application.include_router(auth.router)
    application.include_router(users.router)
    application.include_router(orders.router)
    application.include_router(admin.router)

    @application.exception_handler(DomainError)
    async def handle_domain_error(_: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": str(error)},
            headers={"WWW-Authenticate": "Bearer"}
            if error.status_code == 401
            else None,
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Request validation failed",
                "details": [
                    {
                        "location": detail["loc"],
                        "message": detail["msg"],
                        "type": detail["type"],
                    }
                    for detail in error.errors()
                ],
            },
        )

    @application.get("/health", tags=["operations"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
