# SAIRN latest — cody

**b12, 2026-10-14. `origin/main` `37c649fc`, 0 ahead / 0 behind, 8 commits all ancestors. Pushed without `--force`. Nothing overridden — no `SAIRN_SEED_GATE`, no `SAIRN_GATE_EXEMPT`, no hook, no `settings.json`, no `api/` `sql/` `tools/` or `CLAUDE.md` edit.** Claim `tests` released after these four artefacts.

**All six items done. Not one of the six suites I was sent at had a defect in its subject** — five carried stale anchors or stale expectations in `tests/`, one needed a finding written down rather than fixed. **And three of my own new or tightened arms went red first with the ARM's defect, not the subject's:** a comment matched as code, a range *string* read as a revision walk, a LOCAL sha treated as needing a remote-existence guard, and a `file:line` computed against a comment-stripped copy.

Measured: tripwires DERIVED (0 today, printed) with replacement coverage asserted · blob universe **179 files, 0 outside** — 129 was the OLD GAP, not the new universe · blob ratchet **64 → 58** by the tool · decode sites **56 → 0** across 33 `tests/` files · register `entries` 69 → **64**, `recovered` 31 → **37** · **four** stale `EXPECTED RED` footers where two were named, three fixed.

## Open — mine
- **The retired counterfactual's replacement.** Do *not* replay the suite: apply the OLD predicate to the mutant's own refusal (`!== 401` accepts a 500, `=== 403 && FORBIDDEN` refuses it). No historical copy, no world-state.
- **`tests/run_two_axis_tier_parser_probe.py`** — RED, one arm, **pre-existing** (confirmed by stashing before my change). Check its register row against that arm. Not diagnosed in b12.
- **58 unconverted blob sites** in `docs/blob-conversion-coverage.json`. A ratchet, not a target.

## Routed — exact next step
**HANK, `api/`. Four findings, each with a RED arm in `tests/run_b12_routed_findings_probe.py` that goes green on its own when fixed; `--ablate` shows which fix each one measures.**
- **T16** `api/sd-data.js:7179` — a SECOND `sen_visits` write carrying `clock_in_at` **replaces the caregiver's recorded time with no trail**; a PAST time is explicitly allowed and stored. The append-only correction route exists beside it, so this is an asymmetry.
- **T17** `api/sen-auth.js:263` — `setup` upserts with `merge-duplicates`, so an owner can **demote the last owner** and provisioning becomes unrecoverable from inside the app. `set_active` in the same file *does* carry the guard.
- **T18** `api/_lib/compliance-rules.js` — `applies_to_positions` contents are never checked against `STAFF_POSITIONS`, while the next leg of the same expression checks `audience`. An unmatchable list is counted MAPPED and then **decides "does not apply"** for everybody.
- **N4** `api/sd-data-cross-tenant-dispatchers.test.js:577` cites `api/sd-data-grd-session-gate.test.js`; the real path is `tests/sd_data_grd_session_gate.js`. **One-line comment correction.**

**FOURTH** — the Tier A review obligation in `docs/tier-a-reviews.json`, assigned by the gate on `grd_boq_rates` / `grd_rounds`. 48h before `--takeover`.
**CC (`tools/`)** — `MIN_TEST_FILES` 370 against 796 discovered; `sairn_push_gate_hook.py:988-991` says "THE BLANKET FORM STILL WORKS" while `:1377-1392` refuses it.
**`CLAUDE.md` owner** — it still says "`SAIRN_SEED_GATE=off` still works"; the code contradicts it.
**A routing question, not a code change** — `tests/run_scope_gate_unfetched_base_probe.py` carries `# OWNER: cc` while living in `tests/`, which the register's path rule makes cody's.

## Unverified
T16/T17 are read from source structure, not driven through the handler (T18 *is* driven). `tools/red_suite_register_check.py` was not run. No deployed-URL check applies — no `api/`, `sql/` or app file changed. Arm 6 is textual order in one function, not dataflow. N4 is phrase-gated; its population (314) is printed so the narrowness is visible.

**CONTEXT 64% used of 1,000,000 (Opus 5 1M)** — measured from this session's own transcript usage records (644,254 input tokens on the last recorded request), not from `tools/sairn_status_line.py`, which answers `ctx ??%` from inside a turn.
