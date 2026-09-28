# Five reported results, re-derived from current source and live evidence

**2026-09-29 (Fourth).** The window changed to **Opus 5 at high effort**, and the
first thing a changed window should do is check the previous one's output rather
than assume it. Five results were re-derived against current `main` and against
the deployed endpoint. **Four held exactly. One diverged, and the divergence was
a defect in my own scanner.**

Each row says what was reported, what re-derivation produced, and the command,
so a third reader can repeat it without trusting either number.

---

## Summary

| # | Result | Reported | Re-derived | Verdict |
|---|---|---|---|---|
| A | `alf_incidents` columns-win + `recorded_by` stripped | both halves in place | both present, 1 occurrence each | **holds** |
| B | git-hook fail-opens | 5 → 0 | **0 in hooks** — but the *dependency total* was wrong | **DIVERGED** |
| C | auth-header sweep | 0 mismatched, 70/70 non-exempt | 0 mismatched, 70/70 | **holds** |
| D | blob-overrides-column | 4 exploitable, 0 identity | 4 exploitable, 0 identity | **holds** |
| E | care-role live self-scope | caregiver reads only its own | re-confirmed, plus teardown proven | **holds, strengthened** |

---

## A — the attribution fix (holds)

```
grep -c "storedBlob(payload, ['id', 'resident_id', 'created_at', 'reported_by', 'recorded_by'])" api/sd-data.js   -> 1
grep -c "Object.assign({}, r.data, {" api/sd-data.js                                                              -> 1
```

Both halves present, one occurrence each. No divergence.

## B — the fail-open sweep: **DIVERGED, and the fixture is the tool itself**

**Reported:** dependency-shaped fail-opens `21 → 16`, hooks `5 → 0`.

**The hook figure is correct and re-derives at 0.** The *dependency total* was
wrong in both directions, because the scanner **matched its own prose**.

### The fixture

`tools/fail_open_scan.py` documents the shapes it hunts. It quoted them. It
then counted its own documentation:

```
tools/fail_open_scan.py :13   exit-0-on-failure    ROOT=$(git rev-parse --show-toplevel) || exit 0
tools/fail_open_scan.py :28   exit-0-on-failure    `|| exit 0` is not the defect. The question is…
tools/fail_open_scan.py :45   exit-0-on-failure      exit-0-on-failure   `... || exit 0`, `|| true`…
tools/fail_open_scan.py :48   bare-except-pass      bare-except-pass    Python `except: pass`…
tools/fail_open_scan.py :193  exit-0-on-failure    print('A LIST TO READ. `|| exit 0` is not…
tools/tooling_inventory.py :78,79  exit-0-on-failure   (the PURPOSES entry describing this tool)
```

Every one is a **docstring, a comment or a print string**. **Eight of eighteen
reported sites were prose.** The published `21 → 16` were both inflated by a
scanner reading its own description of the thing it looks for.

**This is the third instance in one session** of the class
`tools/text_gate_literal_sweep.py` exists to measure — committed by the scanner
written *after* it.

### Two fixes, and the second exists because the first broke something

1. **Mask before matching.** `.py` via `tokenize` (a regex for Python strings
   must model triple quotes, raw/f prefixes, escapes and nesting; the tokenizer
   already does); `.sh` and hooks via a single left-to-right pass, because a `#`
   inside a quoted string is not a comment. A file that will not tokenise is
   **COULD NOT TELL**, never a raw-text fallback.

2. **Shape from code, subject from the literal.** Masking alone made
   SCOPE-shaped guards drop from 2 to **0**, and reclassified
   `.githooks/pre-commit`'s hover-auditor marker test as a **hook fail-open** —
   which, acted on, would have demanded every commit in four build clones be
   refused. The reason is that what makes a guard a *scope* test is **the name
   it tests for** (`$GITDIR/sairn-hover-auditor-clone`), and that name lives in
   a string literal the mask blanks. Shape is now matched on the masked line;
   subject on the raw line.

### The corrected figures

| | before mask | after mask |
|---|---|---|
| dependency-shaped | 18 (8 of them prose) | **30** |
| of those, in hooks | 0 | **0** |
| scope-shaped | 2 | **1** |

**The real number is higher than anything I published.** 30 `bare-except-pass`
sites in `tools/`, none in hooks. They are unfixed and are the queue's item 2.

## C — auth-header sweep (holds)

```
expected header, DERIVED from api/_lib/auth.js tokenFromRequest(): 'x-sd-auth'
CHECKED / UNIVERSE: 70 of 70 NON-EXEMPT session-sending files carry the derived name
OK -- no worse than pinned (0 mismatched).
```

## D — blob-overrides-column (holds)

```
mappers spreading the blob LAST  : 54
mappers spreading the blob FIRST : 38
of the LAST group, EXPLOITABLE   : 4
*** of those, IDENTITY keys      : 0
```

## E — the care-role live claim (holds, and now stronger)

Re-driven against the deployed endpoint on `ALF-AUDIT-2026`:

```
caregiver login after deactivation -> 401 INVALID_CREDENTIALS
owner read -> 200 rows=2 ids=['ZZ-AUDIT-INC-CAREGIVER','ZZ-AUDIT-INC-NURSING']
recorded_by per row: {'ZZ-AUDIT-INC-NURSING': 'zz-audit-nursing',
                      'ZZ-AUDIT-INC-CAREGIVER': 'zz-audit-caregiver'}
```

Each row carries the employee who actually filed it — and **the caregiver
credential is genuinely dead**, which the original run asserted but never read
back. The re-derivation is stronger than the claim it checked: it proves the
**teardown**, not only the behaviour.

---

## What this exercise says about the rest

Four of five held. The one that did not was **not a stale result** — it was a
**measurement that was never right**, published twice with a number attached.
Nothing about re-running it would have caught that; only masking prose and
re-counting did.

So the honest generalisation is not "re-derive after a window change". It is
that **a scanner whose subject is a source pattern will match its own
documentation unless something stops it**, and on this platform that has now
happened three times in one session — in the SQL preflight, in the text-gate
sweep itself, and here.
