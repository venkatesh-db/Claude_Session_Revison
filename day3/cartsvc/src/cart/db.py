"""SQLite access for the cart service.

Each request opens its own connection, matching how the service runs
behind the worker pool in production.
"""

import os
import sqlite3

DB_PATH = os.environ.get("CART_DB", "cart.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    sku    TEXT PRIMARY KEY,
    name   TEXT NOT NULL,
    price  REAL NOT NULL,
    stock  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS carts (
    cart_id     TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cart_items (
    item_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_id     TEXT NOT NULL,
    sku         TEXT NOT NULL,
    qty         INTEGER NOT NULL,
    unit_price  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS coupons (
    code         TEXT PRIMARY KEY,
    percent_off  REAL NOT NULL,
    max_uses     INTEGER NOT NULL,
    uses         INTEGER NOT NULL DEFAULT 0,
    expires_on   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id    TEXT PRIMARY KEY,
    cart_id     TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    subtotal    REAL NOT NULL,
    discount    REAL NOT NULL,
    tax         REAL NOT NULL,
    total       REAL NOT NULL,
    created_at  TEXT NOT NULL
);
"""

SEED_PRODUCTS = [
    ("SKU-KURTA-01", "Cotton kurta, indigo", 1299.00, 3),
    ("SKU-JEANS-04", "Slim fit jeans", 2499.00, 40),
    ("SKU-TSHIRT-09", "Graphic tee", 699.00, 120),
    ("SKU-SAREE-02", "Handloom saree", 4850.00, 6),
]

SEED_COUPONS = [
    ("FESTIVE20", 20.0, 100, 0, "2026-12-31"),
    ("WELCOME10", 10.0, 1, 0, "2026-09-30"),
    ("EXPIRED5", 5.0, 500, 0, "2026-01-31"),
]


def connect():
    """Open a connection for one request."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path=None):
    """Create the schema and load seed data."""
    global DB_PATH
    if path:
        DB_PATH = path

    conn = connect()
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?)", SEED_PRODUCTS
    )
    conn.executemany(
        "INSERT OR REPLACE INTO coupons VALUES (?, ?, ?, ?, ?)", SEED_COUPONS
    )
    conn.commit()
    conn.close()


def reset():
    """Clear carts and orders, restore seed stock and coupon counters."""
    conn = connect()
    conn.execute("DELETE FROM cart_items")
    conn.execute("DELETE FROM carts")
    conn.execute("DELETE FROM orders")
    conn.executemany(
        "INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?)", SEED_PRODUCTS
    )
    conn.executemany(
        "INSERT OR REPLACE INTO coupons VALUES (?, ?, ?, ?, ?)", SEED_COUPONS
    )
    conn.commit()
    conn.close()
