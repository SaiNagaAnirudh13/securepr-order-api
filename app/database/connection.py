import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        self._connection: sqlite3.Connection | None = None
        self._lock = threading.RLock()

    def initialize(self) -> None:
        with self._lock:
            if self._connection is not None:
                return
            self._connection = sqlite3.connect(
                self._path, check_same_thread=False, timeout=5.0
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            schema_path = (
                Path(__file__).resolve().parents[2]
                / "migrations"
                / "initial_schema.sql"
            )
            self._connection.executescript(schema_path.read_text(encoding="utf-8"))
            self._connection.commit()

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            yield self._get_connection()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            connection = self._get_connection()
            try:
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("Database is not initialized")
        return self._connection
