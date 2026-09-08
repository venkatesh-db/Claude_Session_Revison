# Evidence of Fix — Duplicate Order on Retried Submit

| | |
|---|---|
| **Defect** | No idempotency enforcement on `POST /orders`; a retried slow submit creates a second order, stock reservation, and payment charge |
| **Root cause** | `app/services/order_service.py:19` (`create_order()`) unconditionally created a new `Order` on every call, with no field on `OrderCreate` to recognize a retry |
| **Fix verified on** | 2026-09-08 |
| **Status** | **Fixed and verified** — see test run and live repro below |

This document is evidence, not narrative: every code block below is either the
actual current file content or actual captured command output from this
machine, not illustrative text.

---

## 1. Files changed

| File | Change |
|---|---|
| `migrations/versions/0005_add_orders_idempotency_key.py` | **New.** Adds `orders.idempotency_key`, unique together with `customer_id`, via `batch_alter_table` (required for SQLite, which cannot `ALTER` in a constraint directly) |
| `app/models/order.py` | Declares `idempotency_key` column and `UniqueConstraint("customer_id", "idempotency_key")` |
| `app/schemas/order.py` | `OrderCreate.idempotency_key: str` — required field |
| `app/services/order_service.py` | `create_order()` looks up an existing order by `(customer_id, idempotency_key)` before creating one; added `IdempotencyKeyConflictError` and `_matches_existing()`; wrapped `db.flush()` in a `try/except IntegrityError` fallback for the concurrent-race case |
| `app/api/orders.py` | Passes `idempotency_key` through to `create_order()`; maps `IdempotencyKeyConflictError` to `HTTP 409` |
| `tests/integration/test_order_flow.py` | 5 pre-existing tests updated to carry the now-required `idempotency_key`; 8 new tests added (`test_t1_*` … `test_t11_*`) |
| `KT.md` | §4 and §9 updated to document the new lookup/constraint behavior |

---

## 2. Current state of the changed source (post-fix)

### `app/models/order.py`

```python
class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("customer_id", "idempotency_key", name="uq_orders_customer_idempotency_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    total_cents: Mapped[int] = mapped_column(Numeric(10, 0))
    shipping_address: Mapped[str] = mapped_column(String(500))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
```

### `app/schemas/order.py`

```python
class OrderCreate(BaseModel):
    items: list[OrderItemCreate]
    shipping_address: str
    card_number: str
    card_last4: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=128)
```

### `app/services/order_service.py`

```python
class IdempotencyKeyConflictError(Exception):
    """Raised when a key is replayed against a different cart/payload."""


def _matches_existing(existing: Order, items: list[dict], shipping_address: str) -> bool:
    if existing.shipping_address != shipping_address:
        return False
    existing_items = sorted(
        ((i.product_id, i.quantity) for i in existing.items), key=lambda pair: pair[0]
    )
    incoming_items = sorted(
        ((i["product_id"], i["quantity"]) for i in items), key=lambda pair: pair[0]
    )
    return existing_items == incoming_items


def create_order(
    db: Session,
    customer: Customer,
    items: list[dict],
    shipping_address: str,
    card_number: str,
    card_last4: str | None,
    idempotency_key: str,
) -> Order:
    existing = (
        db.query(Order)
        .filter(Order.customer_id == customer.id, Order.idempotency_key == idempotency_key)
        .first()
    )
    if existing is not None:
        if not _matches_existing(existing, items, shipping_address):
            raise IdempotencyKeyConflictError(
                f"idempotency_key {idempotency_key!r} was already used for a different order"
            )
        return existing

    if not items:
        raise OrderValidationError("order must contain at least one item")

    order = Order(
        customer_id=customer.id,
        status="pending",
        total_cents=0,
        shipping_address=shipping_address,
        idempotency_key=idempotency_key,
    )
    db.add(order)
    try:
        db.flush()  # assign order.id; also surfaces a concurrent duplicate key here
    except IntegrityError as exc:
        db.rollback()
        winner = (
            db.query(Order)
            .filter(Order.customer_id == customer.id, Order.idempotency_key == idempotency_key)
            .first()
        )
        if winner is not None:
            return winner
        raise OrderValidationError("could not create order") from exc

    # ... unchanged: reserve_stock per item, authorize_and_record_payment,
    #     commit, send_order_confirmation.delay(order.id) ...
```

### `app/api/orders.py` — `place_order()`

```python
    try:
        order = create_order(
            db,
            customer=current_customer,
            items=[item.model_dump() for item in payload.items],
            shipping_address=payload.shipping_address,
            card_number=payload.card_number,
            card_last4=payload.card_last4,
            idempotency_key=payload.idempotency_key,
        )
    except OrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IdempotencyKeyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return order
```

### `migrations/versions/0005_add_orders_idempotency_key.py` (new file, full content)

```python
"""add orders.idempotency_key with a per-customer unique constraint

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-08 00:00:00

"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch_op.create_unique_constraint(
            "uq_orders_customer_idempotency_key",
            ["customer_id", "idempotency_key"],
        )


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("uq_orders_customer_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_key")
```

---

## 3. Evidence: migration applies cleanly (captured output)

```
$ DATABASE_URL="sqlite:///./evidence_scratch.db" python -m alembic upgrade head
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, initial schema
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, add webhook_events table
INFO  [alembic.runtime.migration] Running upgrade 0002 -> 0003, add reorder_threshold to inventory
INFO  [alembic.runtime.migration] Running upgrade 0003 -> 0004, add index on orders.status
INFO  [alembic.runtime.migration] Running upgrade 0004 -> 0005, add orders.idempotency_key with a per-customer unique constraint
```

Resulting schema, read directly from `sqlite_master` (proves the constraint
actually landed, not just that the migration ran without error):

```
CREATE TABLE "orders" (
	id INTEGER NOT NULL,
	customer_id INTEGER NOT NULL,
	status VARCHAR(32) DEFAULT 'pending' NOT NULL,
	total_cents NUMERIC(10, 0) NOT NULL,
	shipping_address VARCHAR(500) NOT NULL,
	created_at DATETIME NOT NULL,
	idempotency_key VARCHAR(128),
	PRIMARY KEY (id),
	CONSTRAINT uq_orders_customer_idempotency_key UNIQUE (customer_id, idempotency_key),
	FOREIGN KEY(customer_id) REFERENCES customers (id)
)
```

Downgrade was also exercised and completes cleanly:

```
$ python -m alembic downgrade -1
INFO  [alembic.runtime.migration] Running downgrade 0005 -> 0004, add orders.idempotency_key with a per-customer unique constraint
```

**Note on this evidence:** the first attempt at this migration used
`op.create_unique_constraint()` directly and failed against SQLite with
`NotImplementedError: No support for ALTER of constraints in SQLite dialect`.
It was corrected to use `op.batch_alter_table(...)` before being accepted as
fixed — this file reflects the corrected, working migration.

---

## 4. Evidence: full test suite (captured output)

```
$ python -m pytest -v
tests/integration/test_migrations_apply_live_db.py::test_alembic_upgrade_head_against_live_postgres SKIPPED
tests/integration/test_order_flow.py::test_place_order_end_to_end PASSED
tests/integration/test_order_flow.py::test_place_order_without_items_fails PASSED
tests/integration/test_order_flow.py::test_place_order_insufficient_stock_fails PASSED
tests/integration/test_order_flow.py::test_customer_can_fetch_another_customers_order_by_id PASSED
tests/integration/test_order_flow.py::test_list_orders_returns_only_own_orders PASSED
tests/integration/test_order_flow.py::test_t1_single_submit_creates_one_order PASSED
tests/integration/test_order_flow.py::test_t2_retry_with_same_key_returns_original_order_not_a_new_one PASSED
tests/integration/test_order_flow.py::test_t3_concurrent_duplicate_insert_resolves_to_one_order PASSED
tests/integration/test_order_flow.py::test_t4_same_key_different_cart_is_rejected PASSED
tests/integration/test_order_flow.py::test_t7_same_key_across_different_customers_does_not_collide PASSED
tests/integration/test_order_flow.py::test_t8_missing_idempotency_key_is_rejected PASSED
tests/integration/test_order_flow.py::test_t10_retry_does_not_call_payment_gateway_twice PASSED
tests/integration/test_order_flow.py::test_t11_retry_does_not_enqueue_confirmation_task_twice PASSED
tests/integration/test_product_stock.py::test_staff_can_update_product_stock PASSED
tests/integration/test_product_stock.py::test_non_staff_customer_cannot_update_stock PASSED
tests/integration/test_product_stock.py::test_update_stock_for_unknown_product_returns_404 PASSED
tests/integration/test_product_stock.py::test_update_stock_rejects_negative_quantity PASSED
tests/unit/test_inventory_service.py::test_reserve_stock_succeeds_when_available PASSED
tests/unit/test_inventory_service.py::test_reserve_stock_raises_when_insufficient PASSED
tests/unit/test_payment_gateway_client.py::test_authorize_payment_returns_mocked_success PASSED
tests/unit/test_security.py::test_hash_and_verify_password_roundtrip PASSED
tests/unit/test_security.py::test_create_access_token_contains_expected_claims PASSED
tests/unit/test_tax_client.py::test_calculate_tax_applies_flat_rate PASSED

23 passed, 1 skipped, 120 warnings in 21.25s
```

Baseline before this fix (per `KT.md` §12, unchanged file at the time): **10
passed / 1 skipped**. The 13 new passes are the 8 new idempotency tests plus
5 pre-existing order tests re-verified after being updated for the new
required field — none were dropped or weakened.

`ruff check app tests` after the change: same 9 pre-existing findings as the
documented baseline (all in `tests/`, import-order/E402), zero new findings
introduced by this change.

---

## 5. Evidence: live before/after behavior

### Before the fix (captured during defect analysis, same cart, two submits)

```
Attempt A -> [0.32s] 201 {'id': 1, 'status': 'confirmed', 'total_cents': 7000, ...}
Attempt B -> [0.26s] 201 {'id': 2, 'status': 'confirmed', 'total_cents': 7000, ...}

orders in DB: 2
  order id=1 status=confirmed total_cents=7000
  order id=2 status=confirmed total_cents=7000
inventory reserved=4   <- expected 2
TOTAL CHARGED: 14000 cents across 2 separate payment authorizations
```

### After the fix (captured just now, fresh run, same scenario plus an idempotency key)

```
Attempt A -> [0.28s] 201 {'id': 1, 'status': 'confirmed', 'total_cents': 7000, 'shipping_address': 'Evidence Ave, Suite 1', 'items': [{'product_id': 1, 'quantity': 2, 'unit_price_cents': 3500}]}
Attempt B (retry, same idempotency_key) -> [0.02s] 201 {'id': 1, 'status': 'confirmed', 'total_cents': 7000, 'shipping_address': 'Evidence Ave, Suite 1', 'items': [{'product_id': 1, 'quantity': 2, 'unit_price_cents': 3500}]}

orders in DB: 1
  id=1 status=confirmed total_cents=7000 key=evidence-run-key-01
inventory reserved=2 (expected 2)
```

Both HTTP calls return `id=1` — the retry did not create a second order, did
not reserve stock twice, and (per §4, `test_t10_*`) did not call the payment
gateway a second time.

---

## 6. Sign-off checklist

- [x] Root cause identified and cited to a line number (`order_service.py:19`, pre-fix)
- [x] Fix implemented at the source of the gap (service layer), not papered over at the API layer alone
- [x] DB-level constraint added, not just an application-level check — closes the concurrent-request race, not only the sequential-retry case
- [x] Migration verified to apply and to roll back cleanly against the dev/test database engine (SQLite)
- [x] New tests cover the reported defect (T2) plus 7 adjacent scenarios a narrower fix could have missed (T1, T3, T4, T7, T8, T10, T11)
- [x] Full existing test suite re-run and green; no regressions
- [x] Live repro of the original defect re-run against the fixed code with matching before/after output
- [x] Knowledge-transfer doc (`KT.md`) updated to reflect the new behavior
