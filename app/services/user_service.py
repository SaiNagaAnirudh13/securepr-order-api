import logging

from app.core.errors import NotFoundError
from app.core.security import SessionManager, hash_password, require_valid_login
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    def __init__(
        self, repository: UserRepository, sessions: SessionManager
    ) -> None:
        self._repository = repository
        self._sessions = sessions

    def register(
        self,
        email: str,
        password: str,
        display_name: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        user = self._repository.create(
            email=email.strip().lower(),
            display_name=display_name,
            password_hash=hash_password(password),
            role=role,
        )
        logger.info("Account registered", extra={"user_id": user.id})
        return user

    def login(self, email: str, password: str) -> str:
        user = self._repository.get_by_email(email.strip().lower())
        require_valid_login(
            user.password_hash if user is not None else None, password
        )
        assert user is not None
        return self._sessions.create(user.id)

    def get_user(self, user_id: int) -> User | None:
        return self._repository.get_by_id(user_id)

    def list_users(self) -> list[User]:
        return self._repository.list_users()

    def update_display_name(self, user_id: int, display_name: str) -> User:
        updated = self._repository.update_display_name(user_id, display_name)
        if updated is None:
            raise NotFoundError("Account not found")
        logger.info("Account profile updated", extra={"user_id": user_id})
        return updated
