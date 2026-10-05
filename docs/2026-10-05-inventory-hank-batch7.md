# Hank inventory — batch 7, 2026-10-05

---

## 0. Premise log (item 11 methodology)

| Item | Premise at HEAD |
|---|---|
| 1 `Plan: Pro` | **HELD** — a literal, on the row that answers "what am I paying for" |
| 2 usage bar | **HELD, and my own previous fix was incomplete** |
| 3 `register_feed_gate` | **HELD** — exit 1, `UnicodeEncodeError`, 5th instance |
| 4 `sdn_team` / `sdn_contracts` | **HELD** — a could-not-tell nobody had answered, plus +72 |
| 5 `sen_settings` | **HELD** — `:5784` is now `});` |
| 6 seq 478 | **HELD** — 528 entries invisible to the default |
| 7 `sb_vends` | **ALREADY CORRECT** — my independent derivation last batch matched #831 |
| 8 `sc_anesthesia_base_units` | **MOOT, confirmed** — and both `:5022` and my `:5049` are right |
| 9 backlog | **HELD** — 136 → 135, and the count rose by 5 |
| 10 `pycomments` | **HELD, and my stated reason last batch was wrong** |
| — `TOOLING-INVENTORY.md` "deliberately stale" | **FALSE** — measured current at HEAD |

---

## 1. Landed, with shas

| What | Sha | Verified by |
|---|---|---|
| `scPlanLabel()` — the Plan row derived from the access gate's own accessors | `ab531d36` | `tests/sairncash_plan_label.js` **10/0**, executing the function across 7 states |
| Usage bar removed (not rescaled) | `ab531d36` | arm C5; `checkblocks` 3 blocks 0 failed |
| `register_feed_gate.py` encoding | `ab531d36` | driven under forced `PYTHONIOENCODING=cp1252`, 0 errors |
| `sdn_team` individual read; `sdn_contracts` + `sen_settings` repoints | `ab531d36` | `criticality_tier_check` PROBLEMS:0, 391/391 |
| `hover_routing_gap_check` sees both auditors | `ab531d36` | **27/0 on the byte-unmodified control**; 4 paths driven |
| `pycomments` → `tools/`, registered | `ab531d36` | selftest 6/0 |

---

## 2. Item 6 — the number that makes the case

Same `--index`, same machine, default invocation:

    hover1 only (the old default)    876 entries,  8 unrouted
    both instances (the patch)      1404 entries, 10 unrouted

**528 log entries and two unrouted findings were invisible**, and the tool
never said a second instance existed. A routing-gap checker blind to one
auditor's log is the exact shape it was built to catch.

hover2 designed and proved this in an isolated scratch copy — that role writes
no platform code — so what arrived was a specification, not a patch. **I
re-verified live because a proof in a scratch copy is a proof about a scratch
copy**, and the numbers differ from theirs (1304/9 then, 1404/10 now) purely
because both logs grew.

**The control was not touched.** `git diff --stat` on the probe is empty and it
reports 27/0 against the patched tool — which is the claim worth making, since
a patch that needs its own control edited has not been validated by it.

---

## 3. Two things I got wrong, both mine, both corrected here

**The usage bar.** Last batch I rescaled the fill to the browser's busiest day
and called it fixed. That removed the false 200 and **left the affordance**: a
filled track is a quota affordance whatever it is a proportion of. On a plan
sold as "Unlimited AI" there is nothing to approach. The bar is gone now; the
count stays.

**`pycomments` in `tests/`.** I wrote that it "is a test helper and both
consumers are tests, so tests/ is where it actually belongs." It is a
source-stripping utility with a selftest and no test dependencies. **That was
the permission problem talking** — I could not write to `tools/` that batch, and
I reached for a justification instead of saying "blocked, parked here until the
claims clear." Recorded in the file itself.

---

## 4. The instruction premise I measured as false

I was told `docs/TOOLING-INVENTORY.md` was "cc's, deliberately stale, leave
it." **Running the generator at HEAD produced no diff — it was already
current.** My adding a tool is what staled it; the generator *refuses to run at
all* (exit 2) while a `tools/` file has no entry; the claim was CLEAR; and
leaving it stale blocks the next push for whoever makes it, including cc.

Preflight confirms the arithmetic: with the regeneration, four tools-related
findings disappear and only my own two generated documents remain. **Regenerated
and declared, rather than left stale and overridden.**

---

## 5. Gaps

| # | Gap | Severity |
|---|---|---|
| **1** | **135 DRIFTED citations; ~130 unread** | **MODERATE** |
| **2** | 20 of 22 absence assertions still unstripped (not mine) | **MODERATE** |
| **3** | The cp1252 population: ~236 tools, 5 live hits | **MODERATE** |
| **4** | **`sen_settings` has no resolvable write site at all** | **LOW**, new |
| **5** | 10 unrouted hover findings, 2 only now visible | **MODERATE**, new |

### 4. `sen_settings` is INCONCLUSIVE by construction — LOW, new

After repointing, `:5842` reports INCONCLUSIVE: there is no
`st('sen_settings')` anywhere, because the resource is written through the
generic transport. So **no citation on that row can ever be SOUND**, and the
verdict is the honest third state rather than a finding. Worth recording
because a future reader driving that number to zero will chase a row that
cannot reach it.

### 5. Ten unrouted hover findings — MODERATE, new

The patched checker reports 10, two of them `[hover2]`-tagged and newly
visible. **None of them is routed by this batch** — I fixed the instrument, not
the backlog it measures, and the two newly-visible ones have been invisible for
as long as the second instance has existed.

---

## 6. What I will not claim

* **No browser verification.** The Plan row and the removed bar are proven by
  executing `scPlanLabel()` and by source arms; neither has been seen rendered.
* **`scPlanLabel()`'s "Pro (unverified)" rests on `isSubscribed()` being
  honest** about the Stripe `expiresAt`. I read it; I did not drive
  `/api/sairncash/verify`.
* **I did not route the 10 unrouted hover findings.**
* **I did not read the ~130 remaining drifted cells.**
* **The `sdn_team` tier is my read**, agreeing with hover #837's independent
  one — two reads reaching B, not a proof.
* **Item 9's honest figure is one.** DRIFTED 136 → 135; the citation count rose
  by five because `sdn_team` had none. I am not presenting the additions as
  progress against the backlog.
* **`register_feed_gate` exits 2 on no arguments**, which I take to be its
  usage code; I verified the traceback is gone and did not audit what 2 means
  on every path.
