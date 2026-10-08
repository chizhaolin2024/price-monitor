import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    store TEXT NOT NULL,
    title TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    active INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price REAL,
    in_stock INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'ok',
    error TEXT NOT NULL DEFAULT '',
    checked_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_history_product ON price_history(product_id, id);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    old_price REAL NOT NULL,
    new_price REAL NOT NULL,
    currency TEXT NOT NULL,
    channels TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(SCHEMA)


def get_or_create_product(conn: sqlite3.Connection, url: str, store: str, title: str, currency: str) -> tuple[dict, bool]:
    existing = conn.execute("SELECT * FROM products WHERE url = ?", (url,)).fetchone()
    if existing:
        return dict(existing), False
    conn.execute(
        "INSERT INTO products (url, store, title, currency, active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
        (url, store, title, currency, time.time()),
    )
    row = conn.execute("SELECT * FROM products WHERE url = ?", (url,)).fetchone()
    return dict(row), True


def list_products(conn: sqlite3.Connection, active_only: bool = True) -> list[dict]:
    sql = "SELECT * FROM products"
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY id DESC"
    return [dict(r) for r in conn.execute(sql).fetchall()]


def add_history(conn: sqlite3.Connection, product_id: int, price: float | None, in_stock: bool, status: str, error: str = "") -> None:
    conn.execute(
        "INSERT INTO price_history (product_id, price, in_stock, status, error, checked_at) VALUES (?, ?, ?, ?, ?, ?)",
        (product_id, price, 1 if in_stock else 0, status, error, time.time()),
    )


def history_rows(conn: sqlite3.Connection, product_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT price, in_stock, status, checked_at FROM price_history WHERE product_id = ? ORDER BY id",
        (product_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def lowest_price_before(conn: sqlite3.Connection, product_id: int) -> float | None:
    row = conn.execute(
        "SELECT MIN(price) AS m FROM price_history WHERE product_id = ? AND status = 'ok' AND price IS NOT NULL",
        (product_id,),
    ).fetchone()
    return row["m"] if row and row["m"] is not None else None


def add_alert(conn: sqlite3.Connection, product_id: int, title: str, old_price: float, new_price: float,
              currency: str, channels: str, message: str) -> int:
    cur = conn.execute(
        "INSERT INTO alerts (product_id, title, old_price, new_price, currency, channels, message, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (product_id, title, old_price, new_price, currency, channels, message, time.time()),
    )
    return int(cur.lastrowid)


def list_alerts(conn: sqlite3.Connection, limit: int = 30) -> list[dict]:
    rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def delete_product(conn: sqlite3.Connection, product_id: int) -> None:
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
