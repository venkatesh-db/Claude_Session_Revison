# Sub-agent instruction, rewritten with a real workflow

## The problem with the original

```
Use a sub-agent for this. Read-only.
Search every file in src/cart/ and tell me: which functions touch
money values (prices, totals, discounts) and use float instead of
a safer decimal type?
Return only a list: file, line, function name. Nothing else.
```

This is a single flat command. The sub-agent has no staged process —
it can pattern-match "float" and "money" and hand back a list that
looks right without ever confirming each line is actually a money
calculation and not, say, a float used for something unrelated. No
CONFIRMED/HYPOTHESIS discipline, no stage where it double-checks
itself before answering.

---

## The rewritten version

```
Use a sub-agent for this. Read-only. Follow these stages in order —
do not skip to the answer.

STAGE 1 — LOCATE
Search every file in src/cart/ for any use of float in a context
that could be money: prices, totals, discounts, tax. List every
candidate line, even ones you're not fully sure about yet.

STAGE 2 — VERIFY EACH CANDIDATE
For each line found in stage 1, confirm it is genuinely a money
calculation, not a float used for something else (a percentage
multiplier that isn't itself a currency amount, a loop counter, a
coincidental variable name). Drop anything that doesn't hold up.

STAGE 3 — CHECK FOR THE SAME BUG HIDING NEARBY
For each confirmed function, check whether it also rounds twice, or
whether it calls another function that already does the money
calculation correctly — sometimes the real risk is TWO functions
individually fine but wrong when combined, not the float itself.

STAGE 4 — RETURN ONLY WHAT SURVIVED VERIFICATION
Return a list: file, line, function name, and CONFIRMED or
HYPOTHESIS for each. If a stage-1 candidate got dropped in stage 2,
don't mention it — only report what actually survived the check.
Nothing else in the response.
```

---

## Why this is a real workflow now, not just a longer instruction

**Stage 1 is deliberately over-inclusive.** Cast a wide net first —
this stage is allowed to have false positives, because stage 2 exists
specifically to remove them. A sub-agent told to be precise on the
first pass tends to under-search instead.

**Stage 2 is the verification step the original prompt was missing
entirely.** Without it, the sub-agent's confidence and its accuracy
are two unrelated things — it will state a plausible-sounding line
number with the same tone whether it actually checked or not. This
stage forces it to look again before trusting its own first pass.

**Stage 3 is specific to this codebase's actual bug shape.** The real
defect in cartsvc's pricing isn't a single float — it's tax computed
correctly and discount computed correctly, wrong only in combination.
A search that stops at "found a float" would miss that entirely. This
stage exists because a flat search genuinely cannot find a composition
bug; only a staged one that checks neighboring functions can.

**Stage 4 keeps the discipline visible in the output**, not just in
the process. CONFIRMED vs HYPOTHESIS on each line means you, reading
the result, know which findings to trust outright and which to spot-
check yourself before acting on them.

---

## The one-line lesson

A sub-agent instruction that's just "go find X" is a search. A sub-
agent instruction with stages — locate, verify, check what a flat
search would miss, report only what survived — is a workflow. The
difference is exactly the same one from the CLAUDE.md fact-versus-
rule distinction earlier: a fact tells it what to look for, a
workflow tells it what order to check things in before it's allowed
to answer.

---

*Coderrange · corporate training and engineering capability*
