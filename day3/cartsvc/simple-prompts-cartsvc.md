# Simple Prompts — CLAUDE.md, AGENTS.md, Sub-agent — for cartsvc

Run each inside the `cartsvc/` folder.

---

## 1. CLAUDE.md

```
Look at this repository and write a CLAUDE.md file.

Include only:
- what each file in src/cart/ is responsible for, one line each
- the real verified test command (run it first, don't guess)
- one workflow rule: pricing.py needs a test proving current
  behaviour before any change, because it has a bug that passes
  all existing tests silently
- one rule about what must never happen (no string-built SQL,
  no float in money calculations)

Keep it under 40 lines. Don't explain, just state the rules.
```

**What this produces:** a short file that loads automatically every
time a Claude session opens in this repo — so nobody has to be told
about the pricing bug twice.

---

## 2. AGENTS.md

```
This repo might be opened by different AI coding tools, not just you.

Write an AGENTS.md with only the facts that would be true no matter
which tool is reading it: the real test command, the folder layout,
and the one rule about pricing.py needing a test first.

Nothing Claude-specific — no report formats, no Claude Code workflow
instructions. Just facts and commands any tool would need.
```

**What this produces:** the same core facts as CLAUDE.md, but written
so a different tool (Codex, or anything else) gets the same
information without you maintaining two versions that could drift
apart.

**Only do this if you're actually using more than one tool on this
repo.** If it's Claude only, skip this file — CLAUDE.md alone is
enough.

---

## 3. Sub-agent instruction

Not a file — this is what you type when you want a one-off, disposable
search. Try it directly:

```
Use a sub-agent for this. Read-only.

Search every file in src/cart/ and tell me: which functions touch
money values (prices, totals, discounts) and use float instead of
a safer decimal type?

Return only a list: file, line, function name. Nothing else.
```

**What this produces:** the sub-agent opens all six files, does the
search, and hands back a short list. None of the file contents it
read stay in your conversation — only the list does.

---

## The one-line difference between all three

CLAUDE.md and AGENTS.md are things you write once and they stay,
loaded every session. The sub-agent prompt is something you type
fresh each time you want a disposable search — there's no file to
create for it.

---

*Coderrange · corporate training and engineering capability*
