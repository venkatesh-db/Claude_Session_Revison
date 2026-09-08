# cart-service

Cart and checkout for the storefront.

## What it does

Holds open carts, prices them, and converts them into orders. A
checkout validates stock for every line, applies a coupon if one was
supplied, scores the order for fraud risk, commits stock and writes the
order row.

Runs behind the worker pool. Each request opens its own database
connection.

## Layout

```
src/cart/cart.py       cart operations and checkout
src/cart/pricing.py    subtotal, discount, tax, total
src/cart/coupons.py    coupon lookup, validation, redemption
src/cart/catalog.py    product lookup and search
src/cart/risk.py       fraud scoring
src/cart/db.py         schema, connections, seed data
tests/test_cart.py     unit tests
fixtures/              concurrency reproduction
evidence/              operations escalations
```

## Running

```bash
python3 -m pytest -q
python3 fixtures/concurrent_checkout.py
```

## Seed data

Four products, three coupons. `SKU-KURTA-01` is seeded with low stock
(3 units) because it is used by the concurrency fixture.
`WELCOME10` is a single-use coupon.

## Open escalations

Operations has raised four issues in checkout — unfulfillable orders,
coupon overuse, tax disputes on discounted orders, and odd behaviour in
the merchandising search filter.

See `evidence/ops-escalations-2026-08-14.md`.

## Contacts

Owner: Commerce Engineering
Escalation: #retail-ops-escalations
