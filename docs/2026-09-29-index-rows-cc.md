# Index rows, ready to paste — CC, 2026-09-29/30

`docs/SAIRN-OPEN-WORK-INDEX.md` was in **hank's declared `FILES:` set** when this
work was done (claim `hank`, opened 2026-09-29T17:21:49Z, and its
`SUBJECT NAMED PER PR 4.3 FILES:` list names that path), so nothing here was
written into it. These are the rows, in the index's own seven-column format, for
whoever holds the file to paste.

**Read the status column before pasting.** Three of the five are **CLOSED** —
they were found and fixed in the same session, and a row that says OPEN for
something already fixed is worse than no row. Two are genuinely open and one of
those needs Michael, not a session.

---

## The rows

| App | Item | Status | Owner | Blocked by | Next action | Sz |
|---|---|---|---|---|---|---|
| **Process** | **&#9989; `api/alf-append-only-read-order.test.js` was RED on `main` and its subject had not changed** &mdash; the matcher required each trail read to sit inside ONE inline `rest('...')` literal, so the `alf_incidents` read being refactored into a query variable (`api/sd-data.js:10695`, with `&order=created_at.desc` present and correct) made the arm report zero reads and fail *"expected exactly 1 ... found 0"* | **FOUND AND FIXED 2026-09-29/30 (CC), commit `76885c1b`** | CC | &mdash; | **DONE.** The matcher resolves the variable to its definition, requires the identifier to reach `rest()`, and concatenates the literal fragments. **DECIDING TEST: `api/alf-append-only-read-order.test.js`, the arm named *"THE REFACTOR THIS ARM WENT RED ON"*, plus three known-bad arms** &mdash; a variable read with no order must FAIL, an order present only in a trailing `//` comment must FAIL, and a query variable never handed to `rest()` must not count. 15 assertions pass. Severity **MODERATE**: a red suite on `main` that reads as a regression is how a real one later gets waved through | S |
| **Process** | **&#128993; THREE MORE TESTS PIN THE SAME SPELLING AND ARE STILL LATENT** &mdash; each is GREEN today only because its target read is still inline, and each goes red the day that read is refactored | **REPORTED 2026-09-30 (CC), NOT FIXED** | unassigned | &mdash; | **`api/_lib/dental-gfe.test.js:186-187`** (`assert.match(block, /rest\('dnt_patients\?license_hash=eq\./)` and the same for `dnt_settings`); **`api/law-auth-custody-matter-attribution.test.js:66`** (pins the full concatenation, `/rest\('law_matters\?license_hash=eq\.' \+ enc\(licHash\)/`, the strongest form); **`tests/cron_schedules_do_not_collide.js:167`** (`REM.indexOf("rest('dnt_appointments?status=eq.Confirmed")`). All three targets confirmed inline today: `api/sairndental/public-book.js:136`, `api/law-auth.js:743`, `api/sairndental/send-reminder.js:144`. **DECIDING TEST for each: refactor its target read into a query variable in a throwaway worktree and require the arm to still pass.** Severity **LOW each, MODERATE as a class** &mdash; no product exposure, but a test that fails on a refactor trains people to ignore it | M |
| **SAIRNmechanical** | **&#9989; the CLIENT redactor was a day behind the SERVER and the parity arm could only see ONE of the four divergences** &mdash; `sairnmechanical.html:1754` still had `Suite\|Ste\|Unit\|Apt` inside the address alternation after `api/_lib/mech-redact.js:147` demoted them to an optional tail in `85ce0f01` (Ted, 2026-09-29 12:50), and had no labelled seven-digit local-number rule at all | **FOUND AND FIXED 2026-09-29/30 (CC), commit `4c918208`** | CC | &mdash; | **DONE.** Client brought into line verbatim, in the server's order (labelled-phone BEFORE address, because the digit run must be consumed first). **The four divergences, all client-wrong:** `Site: 1425 Lakeshore Blvd, Suite 200` left `, Suite 200` beside the token (LEAK); `Phone: 555-0142  Unit: RTU-4` gave `Phone: 555-[ADDRESS REDACTED]: RTU-4` (number half-leaked AND equipment label destroyed); `Qty 12  Unit: RTU-4` destroyed a non-address (DATA LOSS); `Tel: 555-0142 for the shop` left intact (LEAK). **DECIDING TEST: `tests/mech_docs_redaction_wiring_probe.py` arm 4, with the case list widened by five, plus arms 4b/4c** &mdash; the client labelled-phone rule is deleted in memory and the parity arm must report a disagreement, and 4b first asserts the planted line was really found. Severity **MODERATE, not high: the client is a convenience and never the boundary** &mdash; the handler redacts whatever arrives, so this leaked only into the device's own `localStorage` row | M |
| **Process** | **&#9989; arm 1 of the same probe was a STALE ANCHOR** &mdash; it required the literal `resource === 'mech_docs'`, and the handler deliberately moved to a `MECH_SCANNED_TEXT` map lookup on 2026-09-29 so a third and fourth table could join. The only surviving occurrence is inside the comment recording its own removal (`api/sd-data.js:14394`), and the probe strips comments, correctly | **FOUND AND FIXED 2026-09-30 (CC), commit `4c918208`** | CC | &mdash; | **DONE.** The anchor is now the MECHANISM: `mech_docs` must be a key of `MECH_SCANNED_TEXT`, the call must exist, and it must be guarded by `MECH_SCANNED_TEXT[resource]`. **DECIDING TEST: arm 1b, a known-bad control that removes `mech_docs` from the map and requires arm 1 to catch it** &mdash; without it, arm 1 could degrade into asserting the map merely exists. Severity **MODERATE**: the redaction worked the whole time; what was broken was the only thing watching it. **SECOND INSTANCE OF THIS CLASS IN ONE SESSION**, the other being the read-order matcher above | S |
| **SAIRNmechanical** | **&#128308; TWO ROWS ON `MECH-PINNACLE-2026` THAT ONLY SQL CAN REMOVE, created by CC's own live verification** &mdash; `mech_checks.check_id = 'GATE-LIVE-CHECK-DO-NOT-KEEP'` and `mech_takeoffs.takeoff_id = 'GATE-LIVE-CHECK-DO-NOT-KEEP'`. `MECH_RECORDS` has `read` and `write` and no `delete`, so no API path can undo it | **OPEN 2026-09-29 (CC). Re-read live 2026-09-30: still 1 row each, `mech_docs` and `mech_quotes` 0** | **Michael &mdash; nobody else can run it** | needs a SQL run | **The select/delete/confirm block is in `docs/2026-09-29-mech-docs-gate-live-verification.md`. THAT DOC'S FIRST VERSION NAMED `entry_id` AND WAS WRONG** &mdash; these four tables use `check_id`/`takeoff_id`/`doc_id`/`quote_id`, so that SQL would have matched nothing and reported a clean delete; corrected, and the hash is now DERIVED in SQL with `encode(digest('MECH-PINNACLE-2026','sha256'),'hex')` rather than pasted. Both rows are synthetic, both tables held exactly one row so no real demo content is near them, and `service_role` has no DELETE grant so this must run as the table owner. Severity **LOW for the data, MODERATE for the process** &mdash; see the row below | S |
| **Process** | **&#128993; a live-verification tool that WRITES has no obligation to record what it created** &mdash; CC's gate check wrote two rows and the only reason they are known is that CC happened to read them back | **OPEN 2026-09-30 (CC), PARTLY ADDRESSED** | CC for own tools; **fourth already owns the general form** | &mdash; | **Fourth's queue already carries *"the asserted-teardown obligation to `tools/live_probe_residue_audit.py` so a future writing probe with the same gap is caught by the convention that already invokes it"*.** Found the same day from the other direction; named here so the two meet rather than being solved twice. **DECIDING TEST: a live-verification tool that creates a row and does not write a dated residue record must FAIL its own control.** Severity **MODERATE** | M |
| **Platform** | **&#9989;/&#128993; THE `data` BLOB CANNOT BE NULL, AND THAT IS THE ANSWER TO THE WHOLE CLASS** &mdash; the `derive_charges` finding (a prior invoice whose `data` is null skipping the 2026-09-27 guard) was recorded at severity HIGH and is now **CORRECTED TO LOW**: every `data jsonb` column declared across `sql/` is `NOT NULL` &mdash; **353 of 353, zero nullable** | **SWEPT AND MEASURED 2026-09-30 (CC), commit `984f1f4` corrects the register record** | CC | &mdash; | **DRIVEN, NOT INFERRED: all 398 resources in `api/_resources/` were put through the REAL `api/sd-data.js` read with a stored row whose `data` is null. ZERO returned 500 and zero threw** &mdash; so the class is not a crash risk, measured rather than argued. 339 hand the client a null where a record belongs (310 as a bare `[null]` in the data array, 18 as a row object with a null `data` field, 11 elsewhere in the payload), 53 answer cleanly, 6 could not be reached and are named. **NOT FIXED IN 339 HANDLERS, DELIBERATELY: the database refuses the input, so 339 edits would be defensive code for a state that cannot occur.** Severity **LOW** | S |
| **Platform** | **&#128308; NOTHING IN THIS REPO KNOWS THE *DEPLOYED* NULLABILITY, so the row above rests on the DECLARED schema** | **OPEN 2026-09-30 (CC)** | **Michael &mdash; one line of SQL** | needs a read against Supabase | **`db/schema_snapshot.json` carries column NAMES only, and `sql/schema_snapshot_query.sql` selects `c.column_name` and never `c.is_nullable`.** So a table created before its constraint existed &mdash; every schema file uses `create table if not exists` &mdash; would keep the old shape and nothing here would know. **Next action: add `is_nullable` to the snapshot query's column aggregate and re-run it.** Until then the 339-handler verdict above is "unreachable per the declared schema", which is a weaker claim than "unreachable", and is written that way in the register record. Severity **MODERATE** &mdash; it decides whether the row above is closed or reopened | S |

---

## The `NULL-STATE` population, by app

Printed because a total is not a location. These are resources whose read hands
the client a null where a record belongs, when driven with a null blob — **all of
them unreachable through the declared schema.** Counted, not fixed.

| App | resources | App | resources |
|---|---|---|---|
| `sairnvet` | 42 | `sairndesign` | 17 |
| `sairnlegacy` | 36 | `sairnroofing` | 16 |
| `sairnfreedom` | 36 | `sairnbiz` | 13 |
| `sairnbuild` | 31 | `sairnscape` | 12 |
| `sairngrounds` | 30 | `sairnmechanical` | 6 |
| `stonedesk` | 28 | `sairncare` | 2 |
| `sairncode` | 27 | `sairnsenior` | 1 |
| `sairndental` | 22 | | |
| `sairnlaw` | 20 | **total** | **339** |

**THE 6 NOT DRIVEN, NAMED RATHER THAN ROUNDED AWAY.** A resource this sweep
could not reach is a resource nobody checked, and folding it into the clean
column would be the exact defect this platform keeps paying for:

- `exec_context` (stonedesk) — HTTP 400 `UNKNOWN_ROLE`
- `mech_insurance_policies` (sairnmechanical) — HTTP 400 `NO_TODAY`
- `rf_claim_agreements`, `rf_claim_photos`, `rf_photos`, `rf_proposals`
  (sairnroofing) — HTTP 400, no code; the read needs a payload this sweep did
  not supply

**AND THE HARNESS'S OWN FIRST RUN REPORTED 64 CRASHES THAT WERE ALL ITS OWN.**
It minted every session token with role `owner`, and `sairncode` and
`sairnfreedom` have no `owner` role, so `signSessionToken` threw and the harness
scored that as the handler crashing. Recorded because a sweep that blames its
subject for a defect in itself is how a false finding gets 64 rows, and because
the fix is the same one this repo keeps writing down: take the vocabulary from
the module's own export, not from a copy.

---

## Item 8's sweep — mutation/sabotage/ablation runners and their baseline precondition

**ONE FIX COVERED 68 OF THEM.** `tests/sabotage_harness.py` already refused to
plant anything on a red baseline and already printed the right sentence; it
returned **1**, which is its own code for *"a planted defect was NOT refused"*.
So a run that verified nothing and a run that found a real hole answered the same
number. Fixed in `a1247a2e`, driven by
`tests/run_sabotage_harness_baseline_probe.py` (8 arms, landed red at 2).

| population | count | baseline precondition |
|---|---|---|
| use the shared `sabotage_harness` | **68** | **yes — and now exits 2, not 1** |
| hand-rolled, baseline language present | 41 | **not read one by one — see the blind spot below** |
| hand-rolled, **no baseline language at all** | **35** | **NO** |

### The 35 with no baseline precondition, for registering by owner

`tests/cross_tenant_scope_grader_review_probe.py`,
`tests/dnt_vendor_write_confirmation_probe.py`,
`tests/faults/run_fault_suite_probe.py`,
`tests/functional_core_is_pure.js`,
`tests/law_phase2_control_review_probe.py`,
`tests/ld_reports_unreadable.js`,
`tests/license_trial_gate_probe.py`,
`tests/mech_docs_redaction_wiring_probe.py`,
`tests/push_gate/check4_probe.py`,
`tests/python_escape_hygiene_scope_review_probe.py`,
`tests/run_advisory_lock_isolation_probe.py`,
`tests/run_ai_prompt_refusal_probe.py`,
`tests/run_check_precedence_probe.py`,
`tests/run_compliance_loader_probe.py`,
`tests/run_concurrency_retry_probe.py`,
`tests/run_copy_exactly_gate_probe.py`,
`tests/run_cron_liveness_probe.py`,
`tests/run_dispatch_state_probe.py`,
`tests/run_eaten_substitution_probe.py`,
`tests/run_financial_invariant_probe.py`,
`tests/run_hover_separation_probe.py`,
`tests/run_invisible_in_pattern_probe.py`,
`tests/run_literal_drift_determinism_probe.py`,
`tests/run_mutation_anchor_probe.py`,
`tests/run_register_feed_gate_probe.py`,
`tests/run_register_freshness_probe.py`,
`tests/run_sabotage_control_probe.py`,
`tests/run_service_role_gate_probe.py`,
`tests/run_temporary_state_probe.py`,
`tests/run_three_way_match_probe.py`,
`tests/sairnbiz_fault_probe.py`,
`tests/sairncash_entitlement_fault_probe.py`,
`tests/stale_row_sweep_control.py`,
`tools/master_plan.py`,
`tools/nhi_register.py`

**`tests/mech_docs_redaction_wiring_probe.py` is MINE and is on that list.** Its
arms 8, 9 and 10 plant mutations and require refusals, and nothing asserts the
unmutated baseline first. It is not fixed in this session and it is named here
rather than quietly excluded from a list I produced.

**`tools/master_plan.py` and `tools/nhi_register.py` are almost certainly false
positives** — they are generators, and the detector matched a `.replace()` on
source text plus the word "refused" in their prose. Named as probable
false positives rather than dropped, because a sweep that silently discards its
own uncertain hits is reporting a rate over the subset it liked.

### WHAT THIS SWEEP CANNOT SEE — its own blind population, counted

- **41 hand-rolled runners have baseline LANGUAGE and were not read one by one.**
  The word "baseline" appearing in a file is not the same fact as a precondition
  that gates the arms below it. That is 41 unverified, not 41 clean.
- **The detector requires all three of: a subprocess run, a textual mutation of
  source, and a caught/missed verdict.** A runner that mutates through a helper,
  mutates a data file rather than source, or words its verdict differently is
  invisible to it. No count is available for how many that is.
- **A red baseline exiting 2 is not the same as a runner ASSERTING its baseline.**
  The 68 get the gate; they do not each carry an arm that proves the gate bit.
  One control now proves it for the shared harness, which is one control for 68
  callers and is weaker than 68 controls.
