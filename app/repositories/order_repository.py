import sqlite3
from datetime import datetime
from decimal import Decimal

from app.database.connection import Database
from app.models.order import Order, OrderItem, OrderStatus
from app.schemas.order import OrderItemInput


class OrderRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def create(
        self, user_id: int, items: list[OrderItemInput], total: Decimal
    ) -> Order:
        with self._database.transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO orders (user_id, status, total) VALUES (?, ?, ?)",
                (user_id, OrderStatus.PENDING.value, str(total)),
            )
            order_id = cursor.lastrowid
            connection.executemany(
                """
                INSERT INTO order_items (order_id, sku, quantity, unit_price)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (order_id, item.sku, item.quantity, str(item.unit_price))
                    for item in items
                ],
            )
            row = self._get_row(connection, order_id)
        return self._to_order(connection, row)

    def get_by_id(self, order_id: int) -> Order | None:
        with self._database.read() as connection:
            row = self._get_row(connection, order_id)
            return self._to_order(connection, row) if row is not None else None

    def list_for_user(self, user_id: int) -> list[Order]:
        with self._database.read() as connection:
            rows = connection.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC",
                (user_id,),
            ).fetchall()
            return [self._to_order(connection, row) for row in rows]

    def list_all(self) -> list[Order]:
        with self._database.read() as connection:
            rows = connection.execute(
                "SELECT * FROM orders ORDER BY id DESC"
            ).fetchall()
            return [self._to_order(connection, row) for row in rows]

    def update_status(self, order_id: int, status: OrderStatus) -> Order | None:
        with self._database.transaction() as connection:
            connection.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (status.value, order_id),
            )
            row = self._get_row(connection, order_id)
            return self._to_order(connection, row) if row is not None else None

    @staticmethod
    def _get_row(
        connection: sqlite3.Connection, order_id: int
    ) -> sqlite3.Row | None:
        return connection.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()

    @staticmethod
    def _to_order(connection: sqlite3.Connection, row: sqlite3.Row) -> Order:
        item_rows = connection.execute(
            "SELECT * FROM order_items WHERE order_id = ? ORDER BY id",
            (row["id"],),
        ).fetchall()
        return Order(
            id=row["id"],
            user_id=row["user_id"],
            status=OrderStatus(row["status"]),
            items=tuple(
                OrderItem(
                    sku=item["sku"],
                    quantity=item["quantity"],
                    unit_price=Decimal(item["unit_price"]),
                )
                for item in item_rows
            ),
            total=Decimal(row["total"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
