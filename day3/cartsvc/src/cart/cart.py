"""Cart operations and checkout."""

import logging
import uuid
from datetime import datetime

from src.cart import coupons, pricing, risk
from src.cart.catalog import current_price, stock_for
from src.cart.db import connect

log = logging.getLogger("cart.checkout")


class OutOfStock(Exception):
    """Raised when a cart line cannot be fulfilled."""


class RiskBlocked(Exception):
    """Raised when the risk service holds a checkout for review."""


def create_cart(user_id):
    """Open a new cart for a user."""
    cart_id = "CT" + uuid.uuid4().hex[:10].upper()

    conn = connect()
    conn.execute(
        "INSERT INTO carts VALUES (?, ?, 'open', ?)",
        (cart_id, user_id, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    return cart_id


def add_item(cart_id, sku, qty):
    """Add a line to the cart at the price showing right now."""
    price = current_price(sku)

    conn = connect()
    conn.execute(
        "INSERT INTO cart_items (cart_id, sku, qty, unit_price) "
        "VALUES (?, ?, ?, ?)",
        (cart_id, sku, qty, price),
    )
    conn.commit()
    conn.close()


def items_in(cart_id):
    """Return every line in a cart."""
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM cart_items WHERE cart_id = ? ORDER BY item_id",
        (cart_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def checkout(cart_id, user_id, email, address, coupon_code=None):
    """Convert a cart into an order.

    Checks stock for every line, applies a coupon if one was given,
    prices the cart, decrements stock and writes the order row.
    """
    items = items_in(cart_id)
    if not items:
        raise ValueError("cart is empty")

    for item in items:
        available = stock_for(item["sku"])
        if available < item["qty"]:
            raise OutOfStock(
                f"{item['sku']}: wanted {item['qty']}, have {available}"
            )

    coupon = None
    if coupon_code:
        coupon = coupons.validate(coupon_code)

    priced = pricing.totals(items, coupon)

    if risk.is_blocked(user_id, priced["total"]):
        raise RiskBlocked(f"checkout held for review: {user_id}")

    conn = connect()
    for item in items:
        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE sku = ?",
            (item["qty"], item["sku"]),
        )
    conn.commit()
    conn.close()

    if coupon_code:
        coupons.redeem(coupon_code)

    order_id = "OR" + uuid.uuid4().hex[:10].upper()

    conn = connect()
    conn.execute(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            order_id,
            cart_id,
            user_id,
            priced["subtotal"],
            priced["discount"],
            priced["tax"],
            priced["total"],
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.execute(
        "UPDATE carts SET status = 'ordered' WHERE cart_id = ?", (cart_id,)
    )
    conn.commit()
    conn.close()

    log.info(
        "order placed order_id=%s user=%s email=%s address=%s total=%.2f",
        order_id,
        user_id,
        email,
        address,
        priced["total"],
    )

    return {"order_id": order_id, **priced}
