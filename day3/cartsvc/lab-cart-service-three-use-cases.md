# Lab Pack: Three Use Cases on One Repository
## E-commerce cart and checkout service

**Repository:** `cartsvc/`
**Duration:** 3 hours, or three separate 60-minute sessions
**Language:** Python 3, standard library plus pytest. No other dependencies.

Three jobs an engineer does on unfamiliar code — **understand it**,
**trace a flow through it**, **review a change to it**. Same repo, same
model, three different prompts and three different deliverables.

---

## Setup and verification

```bash
tar -xzf cartsvc.tar.gz
cd cartsvc
python3 -m pytest -q                          # 20 passed
python3 fixtures/concurrent_checkout.py       # both scenarios FAIL
```

Expected output from the fixture:

```
SCENARIO A - last units of one product
  stock at start      : 3
  orders written      : 5
  FAIL - 5 orders against 3 units in stock

SCENARIO B - single-use coupon
  uses allowed        : 1
  times redeemed      : 5
  FAIL - redeemed 5 times, limit is 1
```

Run both on the projector before the lab starts. **Twenty passing tests
and two reproducible failures from the same codebase.** That contrast is
the hook for the whole session.

Counts vary between runs because thread scheduling varies — typically 4
to 6 orders against 3 units. Say so upfront so nobody thinks their setup
is broken.

---

## The system

Cart and checkout for a storefront. A checkout validates stock for every
line, applies a coupon, scores the order for fraud risk, commits stock,
and writes the order.

### What is seeded (do not tell participants)

| # | Defect | Where |
|---|---|---|
| 1 | Stock checked, then decremented later — not atomic | `cart.py` — check loop and the UPDATE are separated by coupon validation, pricing and the risk call |
| 2 | Coupon usage limit checked, then incremented later — not atomic | `coupons.py` `validate()` and `redeem()`, called at different points in `cart.py` |
| 3 | GST computed on the **pre-discount** subtotal | `pricing.py` `totals()` — `tax_on(sub)` before the discount is subtracted |
| 4 | Search query built with f-strings | `catalog.py` `search()` |
| 5 | Email and full address written to application logs | `cart.py` final `log.info` |
| 6 | Price snapshotted at add-to-cart, never revalidated at checkout | `cart.py` `add_item()` stores `unit_price`; `checkout()` never rechecks |

**Defect 3 is the interesting one.** Every pricing function is correct in
isolation, and every unit test of them passes. Only the composition is
wrong. `python3 -c` on `pricing.totals` with a ₹1,000 cart and a 20%
coupon gives tax of ₹180 on a discounted amount of ₹800 — the customer
is taxed ₹36 more than the goods they actually paid for.

---

# Use case 1 · Code understanding

**Question:** *I have never seen this repo. What is here?*
**Pattern:** plan-before-change
**Deliverable:** a map with an address for every claim

## The prompt

```
Read-only. Do not modify anything.

I have never seen this repository before. Give me a map I can act on.

Cover:
  - what each module is responsible for, one line each
  - the data model: tables, columns, and any constraints
  - every place a database connection is opened
  - what the test suite actually asserts, and what it does not
  - the three files I should read first, and why

Every claim needs a file and a line range. Mark each CONFIRMED
(you read it) or HYPOTHESIS (you inferred it).

End with two lists: what you did not open, and what you are
unsure about.
```

## Why each line is there

**"what the test suite does not assert"** — the highest-yield line in the
prompt. Twenty tests pass. None of them checks a total end-to-end, and
none runs anything concurrently. Asking what a thing *doesn't* do surfaces
more than asking what it does.

**"every place a database connection is opened"** — makes the transaction
boundary visible without naming it. Each function opens and closes its
own connection, so nothing spans a transaction. That single observation
explains defects 1 and 2 before either is investigated.

**"what you did not open"** — the sampling check. A model that read six of
thirteen files and says so is more trustworthy than one that answers
about all thirteen.

## Expected findings

| Finding | Level |
|---|---|
| Six modules, each with a single responsibility | CONFIRMED |
| No foreign keys and no unique constraints anywhere in the schema | CONFIRMED |
| Every function opens its own connection; nothing spans a transaction | CONFIRMED |
| `cart_items.unit_price` stores a price snapshot | CONFIRMED |
| No test asserts a full checkout total; pricing is only tested per-function | CONFIRMED |
| No test runs anything concurrently | CONFIRMED |
| The price snapshot may go stale before checkout | HYPOTHESIS — correct, and a strong unprompted find |

## Rubric

| Level | Looks like |
|---|---|
| Weak | Module summaries with no line references. Describes what the tests cover, not what they miss. |
| Adequate | Accurate map with addresses. Notes the per-function connections. Marks claims CONFIRMED or HYPOTHESIS. |
| Strong | Also notices the missing constraints, that no test asserts an end-to-end total, that nothing is concurrent, and raises the price snapshot as a risk without being asked. |

---

# Use case 2 · Code flow

**Question:** *What actually happens on one checkout?*
**Pattern:** incident diagnosis — structure before speed
**Deliverable:** an ordered trace with state at each step

## The prompt

```
Read-only.

Trace one call to:

  checkout(cart_id, "user-1", "a@example.com", "12 MG Road",
           coupon_code="WELCOME10")

from the first line to the return value.

For each step give:
  - file and line
  - what it reads from or writes to the database
  - the database state at that moment
  - whether a second concurrent checkout could interleave here

Present it as an ordered list, not prose.

Then answer these three questions separately:

  1. Between the stock check and the stock decrement, how many
     other operations run? Name them.
  2. Between the coupon check and the coupon increment, how many
     other operations run? Name them.
  3. The item price used at checkout — when was it decided, and
     could it have changed since?

Do not propose fixes. Do not write code.
```

## Why each line is there

**"the database state at that moment"** — turns a call list into a timeline.
"Stock is still 3 here" is a fact a second thread can contradict; "calls
`stock_for`" is not.

**Questions 1 and 2 are the exercise.** They convert "there's a race" into a
*measurable width*. The answer to 1 is: coupon validation, a full pricing
calculation, and a fraud risk score — that is a large window, and it is
why the fixture reproduces so easily.

**Question 3 finds defect 6 without naming it.** The price was decided at
`add_item()`. Nothing rechecks it at checkout. A cart sitting open for two
days bills yesterday's price — a revenue defect nobody escalated because
no customer complains about being undercharged.

## Expected findings

| Finding | Level |
|---|---|
| Stock read in a loop, then decremented much later in a separate connection | CONFIRMED |
| Between them: `coupons.validate`, `pricing.totals`, `risk.is_blocked` | CONFIRMED |
| `risk.is_blocked` is the expensive one and widens the window most | CONFIRMED |
| `validate()` reads `uses`; `redeem()` increments it after the order is written | CONFIRMED |
| Two checkouts can both pass validation before either redeems | CONFIRMED |
| `unit_price` fixed at add-to-cart, never revalidated | CONFIRMED |
| The coupon window is wider than the stock window — redemption happens even later | HYPOTHESIS from the trace, and correct |

## Rubric

| Level | Looks like |
|---|---|
| Weak | Lists functions in order. No state, no interleaving analysis. |
| Adequate | Ordered trace with line numbers, correctly identifies both non-atomic windows. |
| Strong | Also names the three operations sitting inside the stock window, identifies the risk score as the dominant cost, and answers question 3 by connecting `add_item` to `checkout` across two functions. |

---

# Use case 3 · Code review

**Question:** *Should this merge?*
**Pattern:** adversarial review, security lens
**Deliverable:** findings by severity and a merge decision

**Run this in a fresh session.** A model that just traced the flow has its
own reasoning in context and will agree with itself.

## Setting up the change to review

Have a participant (or you, beforehand) make a plausible partial fix:

```bash
git checkout -b fix/oversell
# in cart.py, move the stock decrement immediately after the check,
# before the coupon and risk calls
git commit -am "narrow the oversell window"
```

This is the patch a hurried engineer writes. It genuinely helps. It is
also not a fix.

## The prompt

```
Read-only. You did not write this change. Review it for merge.

Diff: git diff main..fix/oversell

Review in this order:
  1. Correctness — does it actually prevent overselling? Name the
     interleaving it still allows, if any.
  2. Coverage — is there a test that fails without this change?
  3. Security — anything in the touched files or their immediate
     callers involving SQL, logging, or personal data?
  4. Blast radius — what else calls the changed functions?
  5. Data — what happens to orders already placed that could not
     be fulfilled?

For each finding: file, line, severity (blocker / should-fix / nit),
and what you would need to confirm it.

End with one line: merge, or do not merge, and why.

Do not fix anything. Do not soften findings.
```

## Why each line is there

**"You did not write this change"** — sets an adversarial stance. Reviewing
in the same thread that produced the patch produces agreement, not review.

**"Name the interleaving it still allows"** — the patch narrows the window
but does not close it. Check-then-write is still check-then-write, however
close together. A reviewer who accepts "the window is smaller now" has
accepted a probability reduction as a correctness fix.

**Item 3 is deliberately worded as "the touched files or their immediate
callers"** rather than "the whole repo". This is what makes defects 4 and 5
findable in a review context — the f-string SQL in `catalog.py` and the
email and address in the checkout log line.

**Item 5 is the one engineers forget.** The patch prevents new bad orders.
It says nothing about orders already placed for stock that does not exist.
That is a refund and customer-contact decision, not a code change.

## Expected findings

| Finding | Severity |
|---|---|
| Check-then-write remains non-atomic; narrower is not safe | blocker |
| No test fails without this change — nothing is proven | blocker |
| Coupon redemption still non-atomic, untouched by this patch | blocker |
| `catalog.search()` builds SQL with f-strings | blocker |
| Email and full address written to application logs | should-fix |
| No unique or check constraints in the schema to catch this at the data layer | should-fix |
| Existing unfulfillable orders not addressed | should-fix, and not an engineering decision alone |
| Price snapshot staleness, unrelated to this diff | nit, log separately |

**Correct verdict: do not merge.** Not because the change is wrong — it
improves things — but because it ships without a test and leaves the same
class of defect in two other places.

## Rubric

| Level | Looks like |
|---|---|
| Weak | "Looks good, nice improvement." Or lists findings with no severity and no line numbers. |
| Adequate | Identifies that narrowing is not fixing. Notes the missing test. Correct merge decision. |
| Strong | Also finds the SQL injection and the PII logging while reviewing an unrelated diff, flags the untouched coupon race, and separates the existing-orders question as a business decision. |

---

## Closing discussion (15 minutes)

**"Twenty tests passed. What were they worth?"**

They were worth something — they caught nothing because they asserted
nothing about composition or concurrency. `test_tax_is_eighteen_percent`
is correct. `test_discount_is_the_coupon_percentage` is correct. The
function that combines them overcharges every discounted order. Unit
tests verify units; nobody wrote the test that verifies the whole.

**"Which of these three jobs could run unattended?"**

Understanding and flow tracing — both read-only, both produce artefacts a
human reads. Review can run unattended too, but the *decision* cannot: the
tax treatment needs Finance, and the existing unfulfillable orders need
someone who can authorise refunds.

That split — investigation automatable, decision not — is the same line
that appears in the MCP governance module, and it is worth naming
explicitly here because participants have just walked into it three times.

---

## Instructor notes

**Do not run the use cases in a single session.** Each needs a fresh
context, particularly the review. Running all three in one thread means
use case 3 inherits the answers from 1 and 2, and stops being a review.

**Defect 3 (tax) is the one that impresses senior people.** Every part is
correct, the whole is wrong, and the test suite is green. If you only have
time to demonstrate one thing, demonstrate that.

**Expect participants to find defect 4 (SQL injection) during use case 1**,
because it is visible in a file scan. That is fine. Ask them to log it and
carry on — noticing something and staying on task is itself a discipline.

**The fixture is non-deterministic by design.** Concurrency defects behave
this way in production too. If a run happens to pass, run it again with a
higher shopper count.

---

*Coderrange · corporate training and engineering capability*
