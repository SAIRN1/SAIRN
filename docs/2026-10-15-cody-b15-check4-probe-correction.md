# `check4_probe.py` — "ARM 3 → 4" re-measured, and what it actually counts

**Written 2026-10-15 by cody, batch b15 item 2.** Corrects
`SAIRN-report-cody-b7.txt:337-338`. Found by **h1**, routed by **cc b13**:
*"the file defines only ARM 1 and ARM 2 in both revisions."*

**THE FINDING IS CONFIRMED, AND IT IS NARROWER AND MORE INTERESTING THAN
"DOES NOT REPRODUCE".** The *number* 3 → 4 reproduces exactly. The *thing it
counts* is not named arms. Both halves matter, so both are stated.

---

## What the b7 report said

> ...so its REAL mechanism was counted too: named **ARM labels 3 → 4**,
> `if not` conditions 3 → 5, outcome-flag assignments 1 → 2.

## What is actually true

| figure as published | re-measured | verdict |
|---|---|---|
| named ARM labels **3 → 4** | **distinct named arms: 2 → 2** | **WRONG AS DESCRIBED** |
| — | `"ARM <n>"` text mentions: **3 → 4** | this is what the number counts |
| `if not` conditions **3 → 5** | **3 → 5** | **REPRODUCES** |
| outcome-flag assignments **1 → 2** | **1 → 2** | **REPRODUCES** |
| assert **2 → 2** | **2 → 2** | REPRODUCES |
| raise **1 → 1** | **1 → 1** | REPRODUCES |
| `sys.exit` **7 → 7** | **7 → 7** | REPRODUCES |
| file **568 → 678** lines | **568 → 678** | REPRODUCES |
| `print()` **26 → 24** | **26 → 24** | REPRODUCES |

**`tests/push_gate/check4_probe.py` has had exactly TWO arms throughout** —
`ARM 1: CLEAN api change must be allowed by check 4` and `ARM 2: PLANTED seam
violation must block`. It never had three, and it did not gain a fourth.

### Where the four mentions are, so the number is checkable

Read out of git, never retyped. Every `ARM <n>` occurrence:

| revision | line | what it is |
|---|---|---|
| `c465743b~1` | `:397` | `# ---- ARM 1: CLEAN api change must be allowed by check 4 ----` |
| `c465743b~1` | `:453` | `# ---- ARM 2: PLANTED seam violation must block ----` |
| `c465743b~1` | `:564` | a **`print()`** — `'  ...WITH ARM 1 UNPROVEN: ...'` |
| `c465743b` | `:413` | `# ---- ARM 1: ... ----` |
| `c465743b` | `:463` | `# ── ARM 1 IS NOW ANSWERED FIRST-HAND INSTEAD OF REPORTED UNPROVEN` |
| `c465743b` | `:529` | `# ---- ARM 2: ... ----` |
| `c465743b` | `:637` | `# ── ARM 1'S VERDICT, FIRST-HAND, AND IT IS PART OF \`ok\`` |

**Three of the four in the new revision are section COMMENTS and the fourth is
a comment too; the old revision's third is a `print()`.** Not one of the added
mentions is an arm. `0` of them are string literals holding an arm's *name* —
measured: `re.findall(r"'(ARM [^']*)'")` returns **nothing** in either
revision, which is itself why an arm-name count had to be done some other way
and why the wrong way was reached for.

### Why the wrong description is worse than a wrong number

**An arm count rising 3 → 4 reads as evidence of ADDED COVERAGE.** That is the
one direction a weakening-flag resolution most wants to show, and it is the
claim a reviewer is least likely to re-derive, because it looks like a
mechanical count somebody already ran. The real mechanism of the change is in
the two figures beside it — `if not` 3 → 5 and the second `ok` assignment —
and those are the ones that hold.

---

## The commands, one per figure

```sh
git show c465743b~1:tests/push_gate/check4_probe.py > /tmp/old.py
git show c465743b:tests/push_gate/check4_probe.py   > /tmp/new.py

# distinct named arms -- 2 and 2
python -c "import re,io;print(len(set(re.findall(r'ARM (\d+)',io.open('/tmp/old.py',encoding='utf-8').read()))))"
python -c "import re,io;print(len(set(re.findall(r'ARM (\d+)',io.open('/tmp/new.py',encoding='utf-8').read()))))"

# "ARM <n>" mentions -- 3 and 4, the figure the report published
python -c "import re,io;print(len(re.findall(r'ARM \d+',io.open('/tmp/old.py',encoding='utf-8').read())))"
python -c "import re,io;print(len(re.findall(r'ARM \d+',io.open('/tmp/new.py',encoding='utf-8').read())))"

# `if not` conditions -- 3 and 5
python -c "import re,io;print(len(re.findall(r'\bif not ',io.open('/tmp/old.py',encoding='utf-8').read())))"

# assignments to the real outcome flag `ok` -- 1 and 2
python -c "import ast,io;t=ast.parse(io.open('/tmp/new.py',encoding='utf-8').read());print([n.lineno for n in ast.walk(t) if isinstance(n,ast.Assign) and any(getattr(x,'id',None)=='ok' for x in n.targets)])"
```

---

## A false alarm of my own, recorded rather than quietly dropped

The **first** re-measurement of *outcome-flag assignments* matched any
assignment whose target NAME CONTAINED `ok`/`pass`/`fail`/`verified`/`proven`/
`arm` and returned **1 → 9**, which would have made the report wrong a second
time. **The heuristic was wrong, not the report.** Restricted to the flag the
probe's own comment at `:637` names — `ok` — it is **1 → 2**, assigned at
`:553` in the old revision and `:629` and `:675` in the new.

**This is the eighth cross-domain convention arriving in my own work:** a
measurement whose criteria were not locked against the subject's own vocabulary
first. The probe says which flag it uses; I substituted a pattern for reading
it. Recorded so the next session does not "re-correct" a figure that is right.

---

## What is NOT changed

* **The weakening-flag verdict is NOT reopened.** The signal was and remains
  `print()`-only, 26 → 24, with zero assertions removed. Every figure
  supporting that still reproduces.
* **`docs/scrutiny-flags.json` is NOT edited** — it is cc's, and cc already
  recorded h1's finding in the ledger's `method` field in b13.
* **`SAIRN-report-cody-b7.txt` keeps its original sentence**, with a dated
  `>>> CORRECTION` block beneath it. A published report is not rewritten to
  look as though it never said the wrong thing; the wrong sentence is left
  where a reader lands and the correction travels with it.
* **`tests/push_gate/check4_probe.py` itself is untouched.** It has two arms,
  it is honest about what it cannot attribute, and nothing here is a finding
  against it. Its `docs/known-red-suites.json` row stays in `not_red` at exit
  3: the upstream blocker is a different push-gate check's blind lock, which is
  still not cody's.

**Owner of the remaining work: none — this item is closed by this document.**
