# AGENTS.md

## Test command

`python -m pytest -q` — 20 passed, verified.

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

## Rule

Before changing `pricing.py`, write a test that pins its current
behaviour. All existing tests pass even with a known pricing bug in
place, so passing tests alone do not prove a change is safe.
