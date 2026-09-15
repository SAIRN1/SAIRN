# Hand-written lists that were supposed to match a pinned register — the sweep

**2026-09-15 (CC).** Michael's direction, after the same defect shape was found
twice by hand in two days. This is the deliberate sweep for the rest of it.

---

## 1. The shape, and why it is worth a tool

A literal list of resource names in one file, corresponding to a population
defined in another file, with **nothing anywhere comparing them**.

| Found | What | Consequence |
|---|---|---|
| 2026-09-14 | `SC_TIER_A_WRITE_GATED` was a hand-written list of **six** while `docs/CRITICALITY-TIERS.md` said **seven** `sc_*` resources are Tier A | `sc_denial_events` — *"the event history an appeal is argued from"* — accepted a write from the **licence key alone**. Measured live: the other six answered 401 `NO_SESSION`, it answered **200** |
| 2026-09-15 | `api/_resources/sairncode.js` granted a destroying `delete` to all 28 names in one `reduce()` | The seven Tier A records inherited a destroy verb nobody chose for them — item 97 |

**In both cases every individual piece was correct.** The register was right.
The list was right when it was written. The code did exactly what it said. The
failure was that no third thing ever asked whether the two agreed — and that is
a failure nothing catches by reading either file.

## 2. The sweep

`tools/pinned_list_drift_check.py`, report-only, held by
`tests/run_pinned_list_drift_probe.py`.

It finds literal arrays of registered resource names and says, for each, how
the list compares to two pinned populations: the owning app's **registry**, and
that app's **Tier A set**. A list that is **derived** produces no row at all —
that is the fix both real cases got, and a derived list has nothing to drift.

**Run it rather than quoting the counts below.** They are dated; the Tier A set
moved from 80 to 81 during the hour this was written.

## 3. THE RESULT: twelve candidates, ONE real, and it was mine

    literal lists found : 29
    PARTIAL-TIER-A      : 12   ← the shape that bit twice

**Every one of the twelve was read by hand.** Eleven are partial *on purpose*
and the reason is written beside each of them. One was real.

### The real one — and it was inside the probe built to catch this

`tools/sc_tier_a_write_gate_live_probe.py` carried its **own** hand-written list
of six. The handler was fixed on 2026-09-15; the probe's copy survived it by a
day.

**Its consequence was worse than the handler's.** The live verification said
*"all six refuse"*, and that was **TRUE** — over six of seven. A green run was
evidence about a population nobody had checked was the right one.

> A verification tool reporting clean over the wrong denominator is the one
> failure mode it must not have.

Derived from the registry now. **It was the first row the sweep ever printed.**

### The eleven that are correct, each checked rather than waved through

| Row | Why it is partial on purpose |
|---|---|
| `sairnbuild.html` `BLD_SYNCED` — no `bld_bids` | `bld_bids` has its own **privacy-gated** branch (`api/sd-data.js:3957`, `:3976`). Folding it into the generic loop would route bids past that gate |
| `stonedesk.html` `SD_SYNCED` — no `sd_hr_employees`, `sd_hr_certs`, `sd_quote_requests` | All three have bespoke branches with their own session gates (`api/sd-data.js:2088-2089`, and the `sd_quote_requests` block). Same reasoning as `sb_emps` in SAIRNbiz |
| `sairncare.html` `ALF_SCOPED_CACHES` | **Already pinned — to a better population.** Its own comment says it is checked against the real `ld('alf_*')`/`st('alf_*')` set, and `tests/phi_cache_scoped_to_user.js:105` does exactly that. The right question for a cache-purge list is *"which keys does this client cache"*, not *"which resources are Tier A"* |
| `api/sd-data-dental-financial-tier.test.js` `FINANCIAL` | Deliberately narrowed 2026-08-27 with the reason in place: `dnt_patients` and `dnt_referrals` **moved out** when provider-scoped patient read shipped, and are covered by `sd-data-dental-provider-scope.test.js` instead |
| `api/alf-append-only-fail-closed.test.js` `TABLES`, `OVERWRITES`, and one unnamed | Append-only tables and overwrite-refusal subjects — a different population that happens to overlap Tier A |
| `api/sd-data-sairnlaw-resources.test.js` `BESPOKE` ×2, `tests/app_session_isolation.js` `PHASE_1_UNGATED` | The four **bespoke** SAIRNlaw resources; the three missing are generic-branch ones and are named as such |
| `tests/dnt_vendor_backup_probe.py` `FOUR` | The four vendor resources, which is what that probe is about |

**An 11-of-12 false-positive rate is the correct result for this tool, not a
weakness.** It narrows 393 resources and 29 literal lists to twelve rows a
person can read in ten minutes, and the one that mattered was at the top.

## 4. What it cannot see, named rather than implied

- **Whether a partial list is wrong.** Most are partial deliberately. It cannot
  read the reason beside them and does not try.
- **Whether something already pins the list.** `ALF_SCOPED_CACHES` has a test
  doing exactly that and looks identical to a list with nothing. This is why it
  is a **read-list, not a score** — the same treatment
  `accepted_risk_scan.py` gets, and why its correct output length is not zero.
- **Lists built at runtime** — concatenations, spreads, values from a config
  object.
- **THE OTHER PINNED POPULATIONS, AND THIS IS THE REAL HOLE.** Roles, SQL table
  names, verbs and file paths have the identical failure shape and are **not
  covered**. `ROLES_BY_APP` in `api/_lib/auth.js` is the sharpest of them:
  CLAUDE.md already records a live case — *"SAIRNcode's `PROVISIONING_ROLES` is
  `admin`, not `owner`, and a guard hardcoding the other list passes clean
  forever while checking nothing"* — which is this exact defect against the role
  vocabulary rather than the resource register. **Recorded as a known hole, not
  left as an apparent absence of findings.**

## 5. The standing rule this leaves

**Two lists that must agree, and no third thing comparing them, is a defect
waiting for a tier change.** Derive one from the other where you can; where you
cannot, pin them with a test that fails in **both** directions. The tool finds
the ones nobody did either to — and it found one inside itself first.
