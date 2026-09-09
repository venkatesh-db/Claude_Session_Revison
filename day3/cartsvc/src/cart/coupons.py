"""Coupon lookup, validation and redemption."""

from datetime import date

from src.cart.db import connect


class CouponInvalid(Exception):
    """Raised when a coupon cannot be applied."""


def get_coupon(code):
    """Return a coupon row, or None if the code is unknown."""
    conn = connect()
    row = conn.execute(
        "SELECT * FROM coupons WHERE code = ?", (code,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def validate(code):
    """Check a coupon can be used, and return it.

    Raises:
        CouponInvalid: unknown code, expired, or usage limit reached.
    """
    coupon = get_coupon(code)
    if coupon is None:
        raise CouponInvalid(f"unknown coupon: {code}")

    if coupon["expires_on"] < date.today().isoformat():
        raise CouponInvalid(f"coupon expired: {code}")

    if coupon["uses"] >= coupon["max_uses"]:
        raise CouponInvalid(f"coupon fully redeemed: {code}")

    return coupon


def redeem(code):
    """Record one use of a coupon."""
    conn = connect()
    conn.execute(
        "UPDATE coupons SET uses = uses + 1 WHERE code = ?", (code,)
    )
    conn.commit()
    conn.close()
