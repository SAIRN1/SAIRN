---
name: sairn-minimalism
description: The laziest solution that actually works — and the review pass that finds what to delete. One skill, both directions: use it BEFORE writing code (does this need to exist, what is the smallest thing that solves the stated problem) and AFTER (what in this diff is speculative, reinvented, or dead flexibility). Trigger on any coding task, on "simplify", "over-engineered", "what can we delete", "YAGNI", "do less", or whenever a solution starts growing options nobody asked for. Every example is a real SAIRN case where the smaller answer was also the more correct one.
allowed-tools: Read Grep Glob Bash
---

# SAIRN Minimalism

Merged deliberately from two skills that were always one idea. Writing minimal
code and reviewing for over-engineering are the same judgment applied at
different times, and splitting them meant the review half never ran.

The claim this skill makes is not that small is elegant. It is that **on this
platform the smaller solution has repeatedly turned out to be the more
CORRECT one**, because the extra machinery encoded an assumption nobody had
checked.

---

# Part 1 — Before writing

## 1. Does this need to exist at all?

**Incident:** a `bridge_pushes` table and its migration were fully designed and
built for `api/bridge.js` before anyone checked whether existing infrastructure
already covered the need. It did — `bridge_data`, already provisioned. It was
found only by accident, from a PostgREST error hint that happened to name it:
*"Perhaps you meant the table 'public.bridge_data'"*.

Before any `CREATE TABLE` or new handler: grep `sql/`, grep `api/`, grep the app
HTML for the literal name. Only proceed when that search comes back genuinely
empty. See Guardian Check 0e.

**Incident, the other direction:** `sc_anesthesia_base_units` was recorded as
*"the right table shape and NO SEED FILE anywhere"* — a source-of-truth gap, and
a proposed task to write one. It was wrong in both halves. The table is
**customer-owned and empty by design** (a coder enters base units with their own
citation; an unmatched code says "not in your reference table yet" rather than
inventing a number), and its migration was queued and unrun. Authoring the seed
would have pushed unverified content into a compliance surface. **The task was
resolved by not doing it.**

## 2. Fix by substitution, not by allowlist

**Incident:** `tools/sairn_dead_button_audit.py` was flagging `List()` as an
undefined function. The source was `askAI('...General Price List (GPL)...')` — a
word followed by `(` inside a string literal. The available fix was to add
`List` to a `DOM_BUILTINS` allowlist. The correct fix was to **blank string
literals before scanning at all**, which also killed 16 `rgba` captures nobody
had explained yet.

> An allowlist chases one word at a time, and the next one is whatever prose
> someone types into the next AI prompt.

When a fix has an "add this name to the list" shape, ask what CLASS the name
belongs to and address the class.

## 3. Model the distinction, don't enumerate the cases

**Incident:** the first draft of `api/_lib/roofing-agreements.js` computed
"business days" as Monday-to-Friday. Ohio R.C. 1345.21 defines a business day
for the Home Solicitation Sales Act as *any calendar day except Sunday* plus
eleven named holidays — **Saturday is a business day in Ohio.** On a Thursday
signing that is Monday, not Tuesday.

The fix was not a special case for Ohio. It made the basis a **property of the
rule** (`oh_hssa` vs `mon_fri`) rather than of the code — so a `mon_fri` result
still states on its face that no holiday calendar was applied.

## 4. Prefer the thing that cannot go stale

**Incident:** two load-state gates were built the same night by two sessions. A
generated SQL gate, and a licence-key tool that reads the seeds at run time. The
SQL one was deleted despite being good work, for one reason among three: **a
generated gate must be regenerated after every seed edit, and a forgotten
regeneration is silently the same failure class the gate exists to catch.**

A derived artifact that must be manually refreshed is a landmine wearing a
safety vest.

## 5. Standard library, native platform, then dependency — in that order

No SAIRN app has a build step. The apps are single-file HTML with vanilla JS,
and that constraint has held through 13 apps. A dependency added to solve one
formatting problem is a permanent tax on a 2 MB file with a size ceiling.

---

# Part 2 — Reviewing for what to delete

One line per finding: **location, what to cut, what replaces it.** No essays.

## 6. Speculative flexibility — the option nobody asked for

Look for: a config value with one caller and one possible value; a strategy
parameter with one strategy; an abstraction with one implementation; a
`switch` with one arm plus a default.

**Counter-example that is NOT this** — know the difference: SAIRNroofing's
`business_day_basis` column has two values today and looks speculative. It is
not: it exists because two states genuinely disagree, and the alternative was a
wrong date. **Flexibility earned by a real, verified difference is not
speculation.** Flexibility earned by "we might need it" is.

## 7. Reinvented standard library

`Array.prototype` methods hand-rolled; date arithmetic that `Date` does;
deep-clone helpers where `structuredClone` or `JSON.parse(JSON.stringify())`
would do; a bespoke debounce.

## 8. Dead code with zero callers

**Incident:** `api/bridge.js`'s `pull` action had **zero callers across all 13
app files**, so `bridge_data` was written and never read — while the UI claimed
a completed sync. Two of its three StoneDesk push callers were also dead and
were deleted.

Zero-caller code is not free. It is file-size against a ceiling, and — per
Guardian 0d — a fabricated KPI inside an unreachable panel goes live the moment
someone adds a nav entry, with nobody re-checking it.

## 9. Two things that do one job

**Incident:** two load-state gates (above). **Incident:** `ponytail` and
`ponytail-review` as separate skills, which is why this file merged them.
**Incident:** a single shared `SAIRN-ACTIVE-WORK.md` split into four per-clone
files after repeated merge conflicts in one night — the opposite move, and
correct for the same reason: *one job, one place, and the place must fit how the
work actually happens.*

When a second copy of something is discovered, **that discovery is the finding.**
Resolve which is authoritative the same day.

## 10. Guard clauses that a real control already covers — and the ones that don't

Delete a client-side check that exists only to be polite when the server already
refuses.

**Do not delete the server-side one because the client has it.** A role check
and a value check are different controls and neither replaces the other —
SAIRNcode's retention floor guard sits alongside its admin role gate on purpose,
because *"by the time anything acts on it, nobody will remember who typed it."*

---

## The honest limit of this skill

Minimalism is not the only virtue and it loses to correctness, to auditability,
and to honest disclosure. The verbose comment explaining *why* a check exists is
not over-engineering — on this platform it is the thing that stopped the same
bug being reintroduced. **Cut code, not reasoning.**
