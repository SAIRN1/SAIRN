# Stored-data criticality — device-local keys that carry a tier and cannot have a register row

**The unit of this table is a `localStorage` KEY, and it is stated here rather than
left to be inferred because tiering the wrong unit is the mistake
`docs/CRITICALITY-TIERS.md` already made once.** That register tiered whole apps;
measuring the eight Tier B apps moved every one of them to A, 21 of 22 verticals
became Tier A, and the register had stopped discriminating. The measurement was
honest and the GRANULARITY was wrong. So a table that introduces a new unit says so
on its first screen, and `tools/stored_data_criticality_check.py` refuses a version
of this file that has dropped the sentence.

**This table is NOT an extension of the register and does not touch it.**
`docs/CRITICALITY-TIERS.md` tiers RESOURCES, and that is mechanical rather than a
preference: `tools/criticality_tier_check.py` enforces a bijection in both
directions against `api/_resources/*.js`, and its own refusal text reads
*"`The unit of this table is the registry.`"* Its bijection is deliberately left
exactly as it was. The boundary is enforced from THIS side instead — a row here
whose key is in some app's `resources` array is refused with `IS A RESOURCE`. The
two tables are disjoint by arm, not by good intentions.

---

## What this table is for, and the gap it closes

A device-local key cannot have a register row. Adding one makes
`criticality_tier_check.py` print `NOT A RESOURCE` and turns
`tests/run_criticality_tier_probe.py` RED on `main` — **the cost of the wrong row
is a red probe, which is checkable rather than arguable.**

The venue that already exists for these keys is an app's `notSynced` declaration
plus `tools/local_only_collection_check.py`. It records that a key is device-local
and **carries no tier**. So before this file the platform could say *"this lives on
one device"* and could not say *"and losing it loses a wage-determining record."*
That is the whole gap, and it is the narrower of the two honest ways to close it.

**The wider way was rejected for a stated reason, not skipped.** Extending the
register's unit to stored data changes the unit for all 391 rows — the same class
of change as the app→resource migration, with the same requirement that it be said
out loud, and it would put a transport buffer and a signed district report in one
table. A second table with its own unit, its own checker and its own probe costs
one more file and moves nothing that is already right.

---

## The two rows

| key | app source | integrity | confidentiality | worst case if it is wrong or lost | worst case if it is disclosed | declaration venue | evidence, re-derived at HEAD 2026-09-30 |
|---|---|---|---|---|---|---|---|
| `sen_evv_queue` | `sairnsenior.html` | **A** | **A** | **While a device is offline this is the ONLY copy of a payable visit.** A clock-in and clock-out taken offline are two entries for one visit; losing the store loses the visit entirely, and `sen_visits` — already A/A — never hears about it. Its two inputs are what a caregiver is PAID, hours × rate with FLSA weighted-average overtime on top, so a lost entry is simultaneously a mispriced invoice and an underpaid person, and an underpayment carries liquidated damages regardless of intent. **The cap bounds the loss and does not remove it:** at cap 200 `evvQueueAdd` returns false rather than dropping the oldest silently, and the panel says so | Each entry is `{queued_at, payload}` where the payload is a `sen_visits` write — so it carries `SEN_VISIT_EVV_FIELDS`, including `clock_in_lat` and `clock_in_lng`. **That is a NAMED CLIENT's HOME BY COORDINATE, sitting unencrypted in one browser's storage**, which is the same confidentiality class `sen_visits` is already A for. A device-local copy of PHI-adjacent location data is not a lesser exposure than the server row; it is the same data with fewer controls in front of it | **UNDECLARED** — `api/_resources/sairnsenior.js` has **no `notSynced` list at all**, so this key is in neither the `resources` array nor a declaration. *"A payable visit lives in one browser while offline"* is currently news rather than a decision | `SEN_EVV_QUEUE_KEY='sen_evv_queue'` at `sairnsenior.html:3015`; `SEN_EVV_QUEUE_MAX=200` at `:3019` with `evvQueueAdd` refusing at the cap (`:3026`) and storing at `:3027`; FIFO stop-on-first-failure flush `senFlushEvvQueue()` at `:3037`, which replays each entry into `sen_visits` at `:3047` and only then shifts and re-stores at `:3054`. The re-read after the await, before the shift, is deliberate and is why a concurrent append is not dropped |
| `law_strike_log` | `sairnlaw.html` | **A** | **A** | **This record is what a Batson challenge is answered from, and one cache clear removes it.** A peremptory strike is defended by the reason recorded contemporaneously at the time of the strike — a reason reconstructed later is worth materially less, and an absent reason is not an absence of evidence, it is an adverse one. There is no server copy and nothing notices the loss: the three consumers read an empty array exactly as they read a never-used one | The row is `{juror_id, reason, juror_statement, case_relevance, recorded_at, recorded_by}` — **a named juror's own statement joined to a lawyer's private assessment of why they were struck.** Disclosure is not embarrassing, it is the substance of the challenge itself, and `juror_statement` is a third party's words held about them without their knowledge. Litigation work product about an identified individual | **UNDECLARED** — not in `api/_resources/sairnlaw.js`'s `resources` array, and not in its `notSynced` list either, which holds only `law_billingcodes` (`api/_resources/sairnlaw.js:145`). So it is in neither of the two places every `sairnlaw` key is meant to be | `juryStrikeLog()` reads `localStorage.getItem('law_strike_log')` at `sairnlaw.html:7156` and `juryStrikeSave()` writes it at `:7157`; three consumers, the append path being the read at `:7176` and the save at `:7178`. Both functions swallow their exception and return `[]` / `false`, so a full quota is a silent empty log |

---

## What a Tier A here obliges, and what it does not

**It does not oblige a server table.** Both keys are device-local for reasons that
are correct: an offline outbox that synced would not be an outbox, and a strike log
is written in a courtroom. A tier is a statement of consequence, not a demand for
a particular remedy.

**What it obliges is that the consequence is written down where somebody looking
for it will find it**, and that the `UNDECLARED` column stops being true. The
deciding test for each is the same one `tools/local_only_collection_check.py`
already reads: add the key to its app's `notSynced` list with its reason, and that
tool goes from silent to accounted-for on the key. For `sairnsenior` that means
creating the list, which does not exist.

**Both of those are edits to files this table's author does not hold a claim on,
and they are not made here.** A tier and the remediation it implies are two
decisions with two owners; a table that quietly performed the second would be a
detector blessing its own fix, which is the eleventh cross-domain discipline one
step later.

---

## What this table and its checker cannot see

**It is not a completeness check, and the checker prints that sentence on every
run** rather than leaving it in a docstring. Nothing here enumerates every
`localStorage` key on the platform and asks which ones lack a row — that set is
unbounded and most of it is UI state. So a clean run says *the rows present are
well-formed, none of them belongs in the resource register, and each Tier A cites
something.* It says nothing whatsoever about rows that should exist and do not.

**It cannot say a tier is right.** Nothing mechanical can. That is what the
evidence column is for, and every citation in it is re-derivable — which is the
other half of the reason the app-source column exists.

**The citations carry a re-derivation obligation, not a guarantee.** Discipline 8:
nothing announces the day a bare line number stops pointing at what it named.
`sairnsenior.html` and `sairnlaw.html` are both actively edited; the five-reference
`sd_owner_pin` finding drifted 46 lines inside 24 hours. The checker verifies the
KEY still exists in the named source, which is the part that can be mechanised; it
does not verify that `:3047` is still the flush. Re-derive on the same cadence the
register uses.

---

## Provenance

Two independent reads found these two keys within the same hour on 2026-09-29 —
hover log #718 (cold, code only) and `docs/2026-09-29-register-cells-hank.md`
item 2b (write-shape extraction), neither having read the other. **They agreed on
every fact and disagreed on the VENUE:** hover proposed register rows; this session
declined on the ground that the register states its own unit and neither name is in
a `resources` array. Recorded in `docs/SAIRN-OPEN-WORK-INDEX.md` as a scope
decision, ruled 2026-09-30: **the register tiers resources, these two get no row
there, and the gap gets a table of its own.** Both positions were right about
different things and hover's substance is the stronger half — it is reproduced
above rather than paraphrased.

**Checker:** `tools/stored_data_criticality_check.py`
**Control:** `tests/run_stored_data_criticality_probe.py` — written before the
checker and the table, and RED on its first run with `MISSING` on both paths.
