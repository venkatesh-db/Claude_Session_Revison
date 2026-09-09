"""Order pricing: subtotal, coupon discount, tax and total."""

GST_RATE = 0.18


def subtotal(items):
    """Sum the line totals for every item in the cart.

    Args:
        items: rows from cart_items, each with qty and unit_price
    """
    return round(sum(i["qty"] * i["unit_price"] for i in items), 2)


def discount_for(amount, coupon):
    """Return the rupee discount a coupon gives on an amount.

    Args:
        amount: the amount the coupon applies to
        coupon: a coupon row, or None
    """
    if coupon is None:
        return 0.00
    return round(amount * (coupon["percent_off"] / 100.0), 2)


def tax_on(amount):
    """Return GST payable on an amount."""
    return round(amount * GST_RATE, 2)


def totals(items, coupon=None):
    """Price a whole cart.

    Returns:
        A dict with subtotal, discount, tax and total.
    """
    sub = subtotal(items)

    tax = tax_on(sub)
    discount = discount_for(sub, coupon)

    total = round(sub - discount + tax, 2)

    return {
        "subtotal": sub,
        "discount": discount,
        "tax": tax,
        "total": total,
    }
