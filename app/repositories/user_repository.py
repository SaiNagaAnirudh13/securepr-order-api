import sqlite3
from datetime import datetime

from app.core.errors import ConflictError
from app.database.connection import Database
from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def create(
        self, email: str, display_name: str, password_hash: str, role: UserRole
    ) -> User:
        try:
            with self._database.transaction() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (email, display_name, password_hash, role)
                    VALUES (?, ?, ?, ?)
                    """,
                    (email, display_name, password_hash, role.value),
                )
                row = connection.execute(
                    "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
                ).fetchone()
        except sqlite3.IntegrityError as exc:
            if "users.email" in str(exc):
                raise ConflictError(
                    "An account with this email already exists"
                ) from exc
            raise
        return self._to_user(row)

    def get_by_id(self, user_id: int) -> User | None:
        with self._database.read() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return self._to_user(row) if row is not None else None

    def get_by_email(self, email: str) -> User | None:
        with self._database.read() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
        return self._to_user(row) if row is not None else None

    def list_users(self) -> list[User]:
        with self._database.read() as connection:
            rows = connection.execute(
                "SELECT * FROM users ORDER BY id"
            ).fetchall()
        return [self._to_user(row) for row in rows]

    def update_display_name(self, user_id: int, display_name: str) -> User | None:
        with self._database.transaction() as connection:
            connection.execute(
                "UPDATE users SET display_name = ? WHERE id = ?",
                (display_name, user_id),
            )
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return self._to_user(row) if row is not None else None

    @staticmethod
    def _to_user(row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            display_name=row["display_name"],
            password_hash=row["password_hash"],
            role=UserRole(row["role"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
