"""Product catalogue lookups."""

from src.cart.db import connect


class ProductNotFound(Exception):
    """Raised when a SKU is not in the catalogue."""


def get_product(sku):
    """Return one product row by SKU."""
    conn = connect()
    row = conn.execute(
        "SELECT * FROM products WHERE sku = ?", (sku,)
    ).fetchone()
    conn.close()

    if row is None:
        raise ProductNotFound(sku)
    return dict(row)


def current_price(sku):
    """Return the catalogue price for a SKU right now."""
    return get_product(sku)["price"]


def stock_for(sku):
    """Return the units currently in stock for a SKU."""
    return get_product(sku)["stock"]


def search(term, max_price=None):
    """Search the catalogue by name.

    Used by the storefront search box and by the merchandising
    dashboard's ad-hoc filters.
    """
    query = f"SELECT * FROM products WHERE name LIKE '%{term}%'"
    if max_price is not None:
        query += f" AND price <= {max_price}"
    query += " ORDER BY price"

    conn = connect()
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]
