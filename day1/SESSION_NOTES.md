# Session Notes — Python OOP Production Code (Order Processing)

Reference notes from this session: the deliverable, the environment work needed to
verify it, the prompt-engineering iteration, and the requirements checklist against
the final code.

## Deliverable

- **Code:** [`order_processing.py`](order_processing.py) — an e-commerce order
  processing module demonstrating SOLID principles and the Strategy, Factory, and
  Observer patterns.
- **Domain:** `Order` / `LineItem` entities, `OrderStatus` state machine
  (`PENDING → PAID → SHIPPED`, or `CANCELLED`), pluggable `PaymentProcessor`
  (credit card / PayPal), pluggable `DiscountStrategy`, and `OrderObserver` hooks
  for notifications (email, audit log).
- **Orchestrator:** `OrderService` — depends only on abstractions
  (`InventoryService`, `PaymentProcessor`), injected via its constructor.

## Environment work done to verify it

Python was not installed on this machine. To actually run (not just claim to run)
the code:

1. Confirmed no interpreter on PATH (`python`, `python3`, `py` all missing) and no
   package manager available (`winget`, `choco` both missing).
2. Asked for and got permission to download the official installer from
   python.org (`python-3.12.7-amd64.exe`, ~25.3 MB) and install it silently,
   all-users, with PATH prepended → `C:\Program Files\Python312\python.exe`.
3. Compiled (`python -m py_compile order_processing.py`) — clean.
4. Ran the demo scenario — surfaced a real `datetime.utcnow()` deprecation warning
   on Python 3.12.
5. Fixed it (swapped for `datetime.now(timezone.utc)` in three places) and
   re-verified: clean run, `PENDING → PAID → SHIPPED`.

## Diagrams published this session

- **Tool Call Trace** — timeline of all 18 tool calls used to detect the missing
  interpreter, install Python, and get the script compiling clean.
- **Plan vs Implementation Mode** — contrasts the (unused) plan-mode flow against
  the implementation-mode flow this session actually took.
- **Senior Dev Plan & Execution** — deeper version: the actual design-thinking
  stages (Discover → Design → De-risk) a senior engineer runs before writing OOP
  code, with a pattern-rationale table, mapped against execution steps completed
  vs. still outstanding (unit tests, static analysis).

*(These were published as private Claude Artifacts during the session — links are
in the chat transcript, not reproduced here since artifact URLs are session-specific.)*

## Prompt-engineering iteration

The original prompt was terse:

> Topic - oops, Lang - python, Role - senior software engineer, task - write a
> production code for python oops using design principles

That required inferring: which domain, which SOLID principles, which patterns,
what "production" means concretely, and whether the code needed to actually run.
Rewritten with that context made explicit:

### Human-readable version

- **Role:** senior Python engineer, code-review-ready deliverable.
- **Domain constraint:** pick a domain with 2–3 independently-varying axes (e.g.
  payment method, discount policy, notification channel) — no toy
  `Animal`/`Shape` hierarchy.
- **Design principles:** all five SOLID principles, each mapped to a specific
  class; at least two GoF patterns, each justified in one line; constructor-based
  dependency injection only.
- **Production requirements (non-negotiable):**
  - Type hints throughout; no bare `Any` without justification.
  - Custom exception hierarchy — no bare `Exception`.
  - Correct primitives (`Decimal` for money, timezone-aware `datetime`).
  - `logging`, not `print`.
  - Enum-backed state with validated transitions.
  - Rollback behavior defined for at least one multi-step operation.
  - External dependencies behind `ABC`/`Protocol` for network-free unit tests.
- **Deliverable format:** design rationale (5–10 lines) → complete runnable file →
  proof of execution (compiled + run, real output shown) → explicit
  out-of-scope list.
- **Explicitly out of scope unless asked:** database, web/API layer, auth,
  async/concurrency, multi-file package structure.

### Compact (YAML) version for direct agent parsing

```yaml
role: senior_python_engineer
deliverable: production_module
topic: oop_design_principles

domain:
  select: one_with_real_variability
  forbid: [toy_hierarchy]
  require_axes: 2-3

principles:
  solid: {S: srp_per_class, O: extend_dont_edit, L: interchangeable_subtypes,
          I: small_interfaces, D: constructor_injection_only}
  patterns:
    min_count: 2
    source: [Strategy, Factory, Observer, Adapter]
    rule: include_only_if_removal_makes_code_worse
    require: 1_line_rationale_per_pattern

production_constraints:
  typing: full_type_hints
  errors: custom_exception_hierarchy
  money: Decimal
  datetime: timezone_aware
  logging: stdlib_logging
  state: enum_backed_explicit_transitions
  failure_mode: define_rollback_for_1_multistep_op
  external_deps: behind_ABC_or_Protocol

output:
  1: design_rationale
  2: complete_runnable_py_file
  3: proof_of_execution
  4: explicit_out_of_scope_list

out_of_scope_default: [db, web_api, auth, async, multi_file_package]
```

## Requirements checklist vs. actual code

Verified line-by-line against `order_processing.py`:

| Requirement | Status | Where |
|---|---|---|
| Type hints throughout | ✅ | Every signature; `from __future__ import annotations` |
| No bare `Any` without justification | ✅ | `Any` not used anywhere |
| Custom exception hierarchy | ✅ | `OrderError` + 3 subclasses, lines 33–55 |
| `Decimal` for money | ✅ | `LineItem.unit_price`, `PaymentResult`, `charge()`, `apply()` |
| Timezone-aware `datetime` | ✅ | `datetime.now(timezone.utc)`, lines 95 & 273 |
| `logging`, not `print` | ⚠️ partial | `logger.info` throughout, but one `print()` remains at line 391 (`__main__` demo output) |
| Enum-backed state, validated transitions | ✅ | `OrderStatus` enum; every transition method checks state first |
| Rollback for a multi-step operation | ✅ | `place_order` releases only the inventory it reserved if payment/stock fails |
| External deps behind `ABC`/`Protocol` | ✅ | `PaymentGatewayClient`/`PayPalClient` as `Protocol`; `InventoryService`/`PaymentProcessor` as `ABC` |

**Known gaps, not yet addressed:**
- `print()` still used for final demo output at line 391 — should be `logger.info` for strict compliance.
- `PaymentProcessorFactory.register`'s `builder` param is loosely typed (informal string annotation).
- No `pytest` suite yet — the module is *designed* to be testable (Protocols, DI) but tests for the failure paths (insufficient stock, declined payment, illegal transition) haven't been written.
- No static analysis (`mypy`/`ruff`) run against it yet.

## Open follow-ups (not done yet)

- Fix the `print()` → `logger.info` and the factory's loose typing.
- Add a `pytest` suite covering the failure paths.
- Run `mypy`/`ruff` and address findings.
