# Escalations to Engineering — Cart & Checkout
**Raised by:** Retail Operations · **Date:** 2026-08-14

Four separate issues, grouped because they all sit in checkout.
Operations has no code access; everything below comes from order
records, the warehouse system and customer contacts.

---

## 1 · Orders we cannot fulfil

**Nine occurrences since 28 July.**

Warehouse reports orders for items that were already out of stock.
Stock levels in the admin panel have shown negative values on four
occasions, always for items with low stock during a sale.

Worst case: `SKU-KURTA-01` had 3 units. Six orders were confirmed and
paid. Three customers were refunded and given vouchers.

Every occurrence was during a flash sale window. Support cannot
reproduce it by placing orders manually.

---

## 2 · Single-use coupons used many times

**Finance flagged this on 6 August.**

`WELCOME10` is configured for one use per code. The report shows it
redeemed 47 times in one hour on 5 August. Similar pattern on two
other single-use codes.

All redemptions cluster within a few seconds of each other.

---

## 3 · Customers disputing the tax on discounted orders

**Twelve tickets since 30 July.**

Customers using a discount code say the tax on their invoice looks too
high for what they paid. One customer sent a worked example: order of
₹1,000, 20% code applied, expected total ₹1,180 minus the discount
effect, got ₹1,180 all the same.

Finance has not yet confirmed which treatment is correct under GST for
a promotional discount. This may be a code issue, a policy issue, or
both.

---

## 4 · Merchandising dashboard behaving oddly

**Reported by the merchandising team, 12 August.**

The search filter on the internal dashboard sometimes returns products
that do not match what was typed — including products from categories
the user did not search. One analyst reported seeing the full
catalogue after typing a search containing an apostrophe.

Marked low priority by Operations. Included here for completeness.

---

## What Operations needs

1. Whether orders that cannot be fulfilled can be prevented at source
2. Whether coupon limits can be enforced properly
3. A definitive answer on the tax treatment, from Finance and Engineering together
4. Whatever item 4 turns out to be

Contact: #retail-ops-escalations
