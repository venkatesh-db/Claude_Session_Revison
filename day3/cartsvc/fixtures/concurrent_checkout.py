"""Reproduce the two concurrency problems reported by operations.

Scenario A: many shoppers buy the last units of one product
Scenario B: many shoppers redeem a single-use coupon

Usage:
    python3 fixtures/concurrent_checkout.py
    python3 fixtures/concurrent_checkout.py 8
"""

import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cart.cart import (  # noqa: E402
    OutOfStock,
    RiskBlocked,
    add_item,
    checkout,
    create_cart,
)
from src.cart.catalog import stock_for  # noqa: E402
from src.cart.coupons import CouponInvalid, get_coupon  # noqa: E402
from src.cart.db import connect, init_db, reset  # noqa: E402

SKU = "SKU-KURTA-01"        # seeded with stock = 3
BULK_COUPON = "FESTIVE20"   # max_uses = 100
SINGLE_COUPON = "WELCOME10"  # max_uses = 1


def run_concurrently(shoppers, coupon_code):
    """Give every shopper one unit of SKU and check them all out at once."""
    carts = []
    for i in range(shoppers):
        cart_id = create_cart(f"user-{i}")
        add_item(cart_id, SKU, 1)
        carts.append((cart_id, f"user-{i}"))

    accepted = []
    lock = threading.Lock()

    def buy(cart_id, user_id):
        try:
            order = checkout(
                cart_id,
                user_id,
                f"{user_id}@example.com",
                "12 MG Road, Bengaluru 560001",
                coupon_code,
            )
            with lock:
                accepted.append(order)
        except (OutOfStock, CouponInvalid, RiskBlocked):
            pass

    threads = [threading.Thread(target=buy, args=c) for c in carts]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return accepted


def order_count():
    conn = connect()
    n = conn.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"]
    conn.close()
    return n


def scenario_a(shoppers):
    print("SCENARIO A - last units of one product")
    print("-" * 52)
    reset()

    starting = stock_for(SKU)
    run_concurrently(shoppers, BULK_COUPON)
    ending = stock_for(SKU)
    orders = order_count()

    print(f"  stock at start      : {starting}")
    print(f"  concurrent shoppers : {shoppers}")
    print(f"  orders written      : {orders}")
    print(f"  stock at end        : {ending}")
    print()

    if ending < 0 or orders > starting:
        print(f"  FAIL - {orders} orders against {starting} units in stock")
    else:
        print("  PASS - no oversell")
    print()


def scenario_b(shoppers):
    print("SCENARIO B - single-use coupon")
    print("-" * 52)
    reset()

    run_concurrently(shoppers, SINGLE_COUPON)
    coupon = get_coupon(SINGLE_COUPON)

    print(f"  coupon              : {SINGLE_COUPON}")
    print(f"  uses allowed        : {coupon['max_uses']}")
    print(f"  times redeemed      : {coupon['uses']}")
    print()

    if coupon["uses"] > coupon["max_uses"]:
        print(f"  FAIL - redeemed {coupon['uses']} times, limit is "
              f"{coupon['max_uses']}")
    else:
        print("  PASS - coupon limit held")
    print()


def main():
    shoppers = int(sys.argv[1]) if len(sys.argv) > 1 else 8

    init_db()
    scenario_a(shoppers)
    scenario_b(shoppers)


if __name__ == "__main__":
    main()
