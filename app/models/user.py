from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


@dataclass(frozen=True)
class User:
    id: int
    email: str
    display_name: str
    password_hash: str
    role: UserRole
    created_at: datetime
