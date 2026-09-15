# Item 20 — a defect budget the data can actually carry; and the entity-split sweep

**2026-09-14 (Hank).**

---

## Item 20 — budget by standing RULE, because per-app cannot work

The obvious entity for a defect budget is the app. **Item 51 measured that it
will not work:** 11 apps, exactly one with ≥10 records and it is `PLATFORM`, a
catch-all holding 65% of everything, and 9 of 11 with three or fewer. A budget
on n=1 is that single value wearing a decision.

**And a per-app budget would invert the incentive.** Discovery is not saturating
— six days, ~490 substantive commits, no downward trend — so the app somebody
audited hardest looks worst and the untouched app looks clean. **Budgeting on
that punishes looking**, which is the last behaviour this platform should tax.

**The standing rule is the entity the data supports.**

**THE RANKING IS NOT COPIED HERE ANY MORE, AND THAT IS THE CORRECTION.** This
section originally reproduced the table — 68 records, 1.1 at 16, 1.11 at 7, two
rules accounting for 30 bites. **Twenty-four hours later every one of those
figures was wrong**: 77 records, 1.1 at 17, 1.11 at **10**, and the
not-citable count up from 9 to 14. Nothing announced it, because a hand-typed
copy of a generated number has no way to. Re-reference against the source:

    python tools/defect_budget.py            # the ranking, as of now
    python tools/defect_budget.py --json     # same, machine-readable
    python tools/defect_budget.py --budget 3 # the threshold is an argument

The **dated snapshot of 2026-09-14** is kept below for the record, clearly as a
historical reading and not as current state, because the *decision* this
document records was made against those numbers:

> 68 records · **1.1** a check that stopped checking — 16 · **1.5** the
> confident line printed after the error — 14 · **1.11** a check that depends on
> another tool must fail CLOSED — 7 · **1.3** an anchor that still matches ≠
> points at the right thing — 6 · **1.2** grep cannot tell code from text that
> describes code — 6 · 1.7 — 3 · 1.6 — 2 · 2.3 · 3.4 · 1.10 · 1.9 · Part 5 — 1
> each. Two rules accounted for 30 of the bites.

**What is stable is the CONCLUSION, not the counts.** A rule crosses apps and
sessions, so it is far less a measure of where somebody happened to look than a
per-app count is — less distorted, not undistorted. 1.1 and 1.5 have held the
top two places across both readings.

`tools/defect_budget.py`, 16 probe arms in `tests/run_defect_budget_probe.py`.

**IT IS DELIBERATELY NOT WIRED, and "report-only" was the wrong word for that.**
This line previously read *"report-only"*, which on this platform names a
specific thing: an entry in `report_only_checks.REGISTRY` that runs on every
push. It has never been in that registry, so the document described a wiring
state the repo did not have. The decision is now recorded where it can be
queried by tool name — a `NOT_PROMOTED` entry in `tools/report_only_checks.py`
— and the reason is not merely that it would be noisy. **A number somebody is
pushed to drive down rewards not citing a rule**, and `--rule not-citable`
exists so a record can decline honestly. Run it when the register is reviewed,
or before choosing which control to build next.

**Over budget means: this failure mode has recurred often enough that the next
occurrence is predictable rather than incidental**, so the next control built
here should target the top of the list. It does **not** block anything and
should not — a gate on this number would reward not citing a rule, and
`--rule not-citable` exists so a record can decline honestly.

**The threshold is 5, it is a judgement, and its sensitivity is printed on every
run** — 6 rules at 3, 5 at 5, 3 at 7, 2 at 10. A threshold whose sensitivity is
hidden is one nobody can argue with when it is wrong.

**And the output refuses to be read as blame:** a high count is not a bad rule.
It is a rule this platform keeps breaking, which is the opposite — the rule is
right and the practice around it is not.

### What it cannot see

- The **`not-citable` records** are bites nobody could attribute. Counted in the
  denominator and named, never quietly dropped. It was 9 on 2026-09-14 and 14 on
  2026-09-15; the tool prints the current figure and this line no longer copies
  it, for the reason given above.
- **A rule you are looking for is a rule you find.**
- `arguable` citations count the same as `clean` ones; weighting them needs a
  confidence model nothing here has.

---

## The entity-split sweep — seven name-sets, zero splits

Follow-up to `SAIRNBIZ` / `sairnbiz` sitting in the register as two apps. The
same question, asked everywhere else a name is used as a **key**:

| Name-set | distinct | split |
|---|---|---|
| open-work index, App column | 21 | **0** |
| `CRITICALITY-TIERS.md`, resource column | 404 | **0** |
| `api/claude.js` `KNOWN_APP_IDS` | 20 | **0** |
| `api/_resources/` declared names | 23 | **0** |
| claim files, session + subject | 275 | **0** |
| defect register, `app` | 11 | **0** (guarded by `--check` since today) |
| defect register, `found_by_tool` | 18 | **0** |

**Total: 0 across 512 distinct names.**

### The zero is proven, not assumed

A clean sweep from a scan nobody has seen fire is worth nothing. Run against the
register **as it stood before normalisation**, the identical grouping reports:

```
pre-normalisation register: 11 distinct, 1 split
    sairnbiz ['SAIRNBIZ', 'sairnbiz']
CONTROL FIRES: True
```

So the scan detects the one real split this platform is known to have had, and
finds no others.

### What this sweep does NOT claim

- **Case and whitespace only.** `sd_invoices` versus `invoices`, or an id
  versus its display label, are real entity splits this cannot see — they need
  a human who knows the domain.
- **Seven name-sets, not all of them.** Storage keys, SQL table names and every
  `data` JSON field are outside it.
- **No tool was promoted.** The register's own `--check` guard is the durable
  part; this sweep is a one-off measurement, recorded here so the next person
  does not re-derive it, and re-runnable from the script in the scratchpad.
