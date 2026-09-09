# Playbook run against cartsvc — 2026-08-16

All 12 prompts from `backend-developer-prompt-playbook.md`, run against
this actual repository. Read-only prompts were executed for real (code
read, tests run, the fixture script run, two additional live
reproductions built) — nothing below is inferred without a citation.
Prompts that don't structurally apply to a first pass over this repo
(no PR diff exists yet, no live incident is happening, no dependency
upgrade was requested) are marked **N/A** with the reason, not forced.

---

## Prompt 1 — Understand an unfamiliar repository

**CONFIRMED**, `README.md` + direct read of every file under `src/cart/`:

- `src/cart/cart.py` — cart creation, item addition, checkout orchestration
- `src/cart/pricing.py` — subtotal/discount/tax/total, pure functions
- `src/cart/coupons.py` — coupon lookup, validation, redemption
- `src/cart/catalog.py` — product lookup and search
- `src/cart/risk.py` — fraud scoring (synthetic CPU-bound stand-in for a real risk service)
- `src/cart/db.py` — SQLite schema, connection-per-call, seed data

**Data model** (`db.py:12-53`): `products(sku, name, price, stock)`,
`carts(cart_id, user_id, status, created_at)`,
`cart_items(item_id, cart_id, sku, qty, unit_price)`,
`coupons(code, percent_off, max_uses, uses, expires_on)`,
`orders(order_id, cart_id, user_id, subtotal, discount, tax, total, created_at)`.
No foreign keys, no unique constraints beyond primary keys — **CONFIRMED**
by reading the `CREATE TABLE` statements directly.

**Every place a connection is opened**: `connect()` is called once per
function in `cart.py`, `coupons.py`, `catalog.py` — 8 separate call
sites (`cart.py:26,40,52,87,101`; `coupons.py:14,44`;
`catalog.py:12,44`). **No connection is ever shared across a check and
its corresponding write** — this is the mechanism behind findings 1 and
2 below, not incidental.

**Outbound calls and timeout behaviour**: none. This service makes no
network calls — `risk.py`'s docstring states the real version would call
a risk service, but this build computes the score locally.

**What the test suite asserts, and what it does not**: `tests/test_cart.py`
(20 tests, all passing — verified by running `pytest -q`) covers
catalogue lookups, pricing arithmetic, coupon validation, and
single-threaded checkout. **It does not assert anything about
concurrent checkouts, the interaction between discount and tax, or
untrusted input to `search()`** — confirmed by reading every test name;
none references threading, `%` characters, or comparing coupon vs.
no-coupon tax.

**Three files to read first, and why**: `cart.py` (the checkout
orchestration — every other module's bug surfaces here), `pricing.py`
(short, pure, and the tax/discount interaction is the site of finding
3), `catalog.py` (11 lines, but `search()`'s query construction is the
site of finding 4).

**What I did not open**: no config files, no deployment manifests, no
CI configuration exist in this repo — confirmed by `find . -type f`
returning only the files listed above. There is nothing else to open.

---

## Prompt 2 — Turn a vague bug report into a reproduction

Applied to escalation #1 (unfulfillable orders) and #2 (coupon overuse) —
`evidence/ops-escalations-2026-08-14.md` §1–2.

**Assumptions in the report not yet verified**: that the negative-stock
readings and the overuse are the same underlying mechanism; that "flash
sale window" is causally relevant versus just being when concurrent
traffic happens to occur.

**Conditions that must hold, from the code**: concurrency (multiple
checkouts for the same SKU or coupon overlapping in time), and — from
`cart.py:71-76` vs. `88-93` and `coupons.py:35-36` vs. `44-47` — the
stock/coupon check and the corresponding write happen in **separate
database connections and separate transactions**, with no lock held
between them.

**Reproduction — built and run, not just designed**:
`fixtures/concurrent_checkout.py` already exists in this repo for
exactly this purpose. Ran it:

```
$ python3 fixtures/concurrent_checkout.py 8

SCENARIO A - last units of one product
  stock at start      : 3
  concurrent shoppers : 8
  orders written      : 7
  stock at end        : -4
  FAIL - 7 orders against 3 units in stock

SCENARIO B - single-use coupon
  coupon              : WELCOME10
  uses allowed        : 1
  times redeemed      : 8
  FAIL - redeemed 8 times, limit is 1
```

**Is this the same failure the customer hit, or a different one that
looks the same?** The reproduction's stock arithmetic matches the
report's worst case exactly: report says `SKU-KURTA-01` had 3 units and
6 orders were confirmed; this run (8 concurrent shoppers) produced 7
orders against 3 units. Same SKU, same starting stock, same failure
shape (orders exceed stock, stock goes negative) — high confidence this
is the same mechanism, not a look-alike. **CONFIRMED**, not HYPOTHESIS,
because the reproduction was executed, not reasoned about.

---

## Prompt 3 — Find the root cause

### Finding 1: oversell / negative stock (escalation #1)

Trace, `checkout()` in `cart.py`:

| Step | File:line | Reads/writes | State at that moment |
|---|---|---|---|
| 1 | `cart.py:72` | reads `stock_for(sku)` via a fresh connection | stock as of *this* read |
| 2 | `cart.py:73-76` | compares in Python | no lock held on the row |
| 3 | `cart.py:87-93` | opens a **new** connection, decrements stock | any number of other threads may have passed step 1-2 with the same stale stock value in between |

**Could anything interleave here?** Yes — nothing in `stock_for` or the
decrement holds a row lock or uses a conditional update (`WHERE stock >=
?`). Two threads can both read `stock=3`, both pass the `available <
qty` check, and both proceed to decrement. **CONFIRMED** by the live
reproduction above (7 orders against 3 units).

**Root cause**: check-then-act across two separate, unlocked database
transactions — the same defect class RxFlow's `docs/known-defect-classes.md`
documents for its own duplicate-order bug, here on inventory instead of
idempotency keys.

### Finding 2: coupon overuse (escalation #2)

Identical shape, `coupons.py`: `validate()` (line 35, reads `uses` vs.
`max_uses`) and `redeem()` (line 44-47, increments `uses`) are two
separate connections with no lock or conditional update between them.
**CONFIRMED** by the live reproduction (8 redemptions against a limit of
1).

### Finding 3: tax on discounted orders (escalation #3)

`pricing.totals()` (`pricing.py:32-50`): `tax = tax_on(sub)` computes
GST on the **pre-discount** subtotal, then `total = sub - discount +
tax`. Verified live:

```
No coupon:   subtotal=1000.0 discount=0.0   tax=180.0 total=1180.0
With coupon: subtotal=1000.0 discount=200.0 tax=180.0 total=980.0
If tax were computed on the POST-discount amount: tax=144.0, total=944.0
```

**CONFIRMED as a code-level defect**: tax does not change when a
discount is applied, which is what "the tax looks too high for what I
paid" describes — a customer paying ₹800 net-of-discount is charged the
same ₹180 GST as someone paying ₹1000 with no discount, ₹36 more than
if GST applied to the discounted amount. **HYPOTHESIS, not CONFIRMED**,
on which treatment is *correct*: the escalation itself states Finance
has not yet confirmed the correct GST tax base for a promotional
discount — this is the "two causes, tell me what distinguishes them"
case from Module 3: the code bug is real and quantified, but whether
pre-discount or post-discount tax is the *legally correct* treatment is
a policy question this repository's evidence cannot answer.

### Finding 4: merchandising search anomaly (escalation #4)

`catalog.search()` (`catalog.py:39`) builds SQL via an f-string with
`term` interpolated directly into a `LIKE` clause — no parameterization.
**CONFIRMED live**: a search term of `x' OR '1'='1' -- ` returned all 4
catalogue rows regardless of the search text — this is SQL injection,
not a UI display bug, and it directly explains "typed a search
containing an apostrophe... saw the full catalogue."

**Not requested by the escalation, but found while tracing #4**: the
same `search()` function is the only place in the codebase vulnerable
to this — `catalog.get_product`, `coupons.get_coupon`, and every other
query in the repo use parameterized `?` placeholders correctly
(`catalog.py:14`, `coupons.py:16`, etc.). This is a single-function
regression, not a systemic pattern — worth stating precisely rather than
implying the whole codebase has this problem.

**Additional finding, outside the four escalations, surfaced by reading
`cart.py` for finding 1**: `cart.py:121-128` logs `email` and `address`
directly via `log.info(...)`. No escalation raised this, but it's a real
PII-in-logs defect, the same class RxFlow's `logging.py` redaction
processor exists to prevent — flagging it here since prompt 1 asked for
the three highest-risk files and this belongs in that answer.

---

## Prompt 4 — Implement the fix

**Not run.** The playbook's prompt 4 requires an *approved* fix scope —
this session only diagnosed; no fix has been authorized. Running prompt
4 now would mean choosing a fix for finding 3 (tax treatment) before
Finance has answered the policy question the escalation itself says is
open. Say the word and I'll run prompt 4 for findings 1, 2, and 4 (all
three have unambiguous, policy-independent fixes); finding 3 needs a
human decision first per its own evidence.

## Prompt 5 — Review someone else's PR

**N/A.** No PR/diff exists in this repository yet — there is nothing to
review. Applicable once a fix branch exists.

## Prompt 6 — Change legacy code with no tests

**Partially applicable, not run in full.** `pricing.py` has tests
(`test_totals_includes_every_component` etc.) but none pin the exact
current (buggy) tax-on-discounted-order behavior — if finding 3 is
fixed, a characterization test should exist first, pinning today's
₹980 total for the ₹1000/20%-coupon case, so the fix's effect is
provable as a diff against a known baseline rather than just "the new
number looks right." Not written yet — this is scoped work for when
prompt 4 runs against finding 3.

## Prompt 7 — Turn "it feels slow" into a number

**N/A.** No performance complaint exists in the escalations or anywhere
in this repo's evidence. Note in passing, found while reading
`risk.py:11-17`: `_fingerprint()` does a 300,000-iteration Python loop
per checkout — real CPU cost, but nobody has reported it as slow, and
inventing a performance investigation nobody asked for is exactly the
"fix any bugs you see" anti-pattern documented in
`rxflow/docs/labs/bad-claude-md-example.md`. Flagged, not investigated.

## Prompt 8 — Production incident

**N/A.** Nothing here is a live incident — these are historical
escalations with dates in the past, already contained (support has
already refunded the affected customers per escalation #1). The
distinction matters: prompt 8's "answer mitigation first" framing is for
an active, ongoing incident; this is retrospective root-cause work, which
is what prompts 2-3 above actually did.

## Prompt 9 — Design a new endpoint

**N/A.** No new endpoint was requested. Nothing in the escalations asks
for new functionality — all four are defects in existing behavior.

## Prompt 10 — Dependency or framework upgrade

**N/A.** `cartsvc` has no dependency manifest (no `requirements.txt`,
`pyproject.toml`) beyond the stdlib and `pytest` — confirmed by `find .
-name "*.toml" -o -name "requirements*.txt"` returning nothing. No
upgrade has been requested regardless.

## Prompt 11 — Read a log file

**N/A.** No log file exists in this repository — `log.info(...)` in
`cart.py` writes to Python's logging module with no configured handler
visible in this codebase, so there's no persisted log to read. Note:
this is itself worth flagging back to whoever owns deployment — a
service logging PII with no visible log-retention/access-control
configuration in the repo is a gap, not just an absence of a file to
analyze here.

## Prompt 12 — Close a session cleanly

**Applying it now, for real, since this session is ending its diagnostic pass:**

- **Established as fact, with file and line**: oversell (`cart.py:72`
  vs. `87-93`, reproduced live: 7 orders/3 units), coupon overuse
  (`coupons.py:35` vs. `44-47`, reproduced live: 8 redemptions/limit 1),
  tax computed pre-discount (`pricing.py:40`, quantified: ₹36 overcharge
  on a ₹1000/20% example), SQL injection in `search()` (`catalog.py:39`,
  reproduced live: apostrophe payload returned full catalogue), PII
  logged in `cart.py:121-128`.
- **Decided / rejected**: did not run prompt 4 (implement) on any
  finding — diagnosis only was requested. Did not investigate
  performance (`risk.py`'s loop) — nobody reported it as slow, and
  inventing work nobody asked for is the anti-pattern this playbook
  exists to prevent.
- **Still unverified**: whether pre- or post-discount is the *correct*
  GST tax base — a Finance policy question, not a code question.
- **Exact next step**: get explicit approval to run prompt 4 against
  findings 1, 2, and 4 (unambiguous fixes); get Finance's answer on tax
  treatment before touching finding 3.
