# CLAUDE.md

## src/cart/ responsibilities

- `cart.py` — cart lifecycle and checkout orchestration
- `pricing.py` — subtotal, discount, tax, total
- `coupons.py` — coupon lookup, validation, redemption
- `catalog.py` — product lookup and search
- `risk.py` — fraud scoring
- `db.py` — schema, connections, seed data

## Test command

`python -m pytest -q` — 20 passed, verified.

## Workflow rule

Before changing `pricing.py`, write a test that pins its current
behaviour, including the tax-on-pre-discount-subtotal bug. Every
existing test passes with that bug in place, so no existing test
will catch a regression in it.

## Must never happen

- No SQL built by string formatting or concatenation. Every query
  uses parameter binding.
- No `float` for money. Currency values are integers (paise/cents)
  or `Decimal`, never `float`.
