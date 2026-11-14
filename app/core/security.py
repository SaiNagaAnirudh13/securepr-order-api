from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import threading
import time

from app.core.errors import AuthenticationError

_HASH_SCHEME = "pbkdf2_sha256"
_HASH_ITERATIONS = 210_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _HASH_ITERATIONS
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"{_HASH_SCHEME}${_HASH_ITERATIONS}${salt_text}${digest_text}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        scheme, iterations_text, salt_text, expected_text = encoded_hash.split("$")
        if scheme != _HASH_SCHEME:
            return False
        iterations = int(iterations_text)
        if iterations < 1:
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(expected_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


class SessionManager:
    def __init__(self, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("Session lifetime must be positive")
        self._ttl_seconds = ttl_seconds
        self._sessions: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def create(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        with self._lock:
            self._sessions[token_hash] = (user_id, time.monotonic() + self._ttl_seconds)
        return token

    def resolve(self, token: str) -> int | None:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = time.monotonic()
        with self._lock:
            session = self._sessions.get(token_hash)
            if session is None:
                return None
            user_id, expires_at = session
            if expires_at <= now:
                del self._sessions[token_hash]
                return None
            return user_id

    def revoke(self, token: str) -> None:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self._lock:
            self._sessions.pop(token_hash, None)


def require_valid_login(stored_hash: str | None, password: str) -> None:
    if stored_hash is None or not verify_password(password, stored_hash):
        raise AuthenticationError("Email or password is incorrect")
