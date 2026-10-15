# SAIRN latest — cody

**b13, 2026-10-14. CHAIN TIP `0c7d4ac8` — `origin/main` identical, 0 ahead / 0 behind, ancestry verified. Pushed without `--force`, first attempt, no gate refusal.** Nothing overridden — no `SAIRN_SEED_GATE`, no `SAIRN_GATE_EXEMPT`, no hook, no `settings.json`, no `api/` `sql/` `tools/` or `CLAUDE.md` edit. Claim `tests` released after these four artefacts.

**STOPPED EARLY ON INSTRUCTION AT 71% CONTEXT. Item 1 done and landed; items 2, 3, 4 and 5 NOT REACHED and NOT STARTED; item 6 done. Nothing is half-finished** — no arm added and left failing, no register row edited in anticipation, `docs/blob-conversion-coverage.json` untouched at `unconverted: 58`. One file changed: `tests/app_session_isolation_probe.py`.

## Done — item 1, the replacement for the retired replay
`old_predicate_is_blind()` applies the OLD predicate to the mutant's own refusal shape. **It replays nothing** — the property is ONE EXPRESSION (`out.code !== 401` vs `out.code === 403 && … FORBIDDEN`), not a suite, so no worktree, no historical copy, no world-state. Every input DERIVED: new predicates from the suite's own `ok(` expressions (gate **403 FORBIDDEN**, oracle **400**), the old predicate from HISTORY at `798543873912^` (**`!== 401`**, one expression read, never run), each mutant code from the mutation table. Underivable → **exit 3 UNPROVEN**, never a pass.
**Measured:** exit 0, ALL 13 ARMS PASS (8 mutations), **2 same-reason mutations INVISIBLE to the pre-repair predicate and REFUSED by the current one**. `--ablate` **4 of 4**.
**And the ablation found two defects in its own controls:** CONTROL A could not fail (shape and predicate shared one name — split into `GATE_SHAPE_ERR`/`GATE_OK_ERR`); CONTROL B was tautological (it asked whether the predicate refuses `OLD_BLIND_TO`, true by construction — now `DERIVED_OLD`). **An arm whose failure path has never been run is an assertion, not a check.**

## Open — mine, with the next step
- **Item 2.** `tests/run_two_axis_tier_parser_probe.py` RED on one arm, **PRE-EXISTING** (confirmed by stashing in b12). Read its `known-red-suites` row FIRST, then fix the arm AT CAUSE or correct the row. No silent skip; do not edit the arm to go green.
- **Item 3.** `tests/run_scope_gate_unfetched_base_probe.py` line 2 still says `# OWNER: cc`. Change to cody, verify green (13/13 in b12) and verify it is WIRED.
- **Item 4, three arms, none written.** `leg_aftercare` key-collision failing-first — `('CS-7','1 Week')` and `('CS-7-1','Week')` must not derive the same `AC-CS-7-1-WEEK`; the function-name anchor arm must degrade to **UNPROVEN at exit 3**; and the `leg_clergybookings` arm at `tests/sairnlegacy_reservation_lock.js:330` **or** 35/36 accepted explicitly in the register **with the reason** — 35/36 with no recorded reason is the one unacceptable outcome.
- **Item 5, and a question blocks it.** Convert ten of the 58, ratchet the pin **with the tool**, record the failing-first command per conversion. **The sites are in `api/`, which is hank's, and b13's claim declared `api/` read-only.** Either hold an `api/` claim or route the ten to hank. Settle that first.

## Routed
- **HANK** (from b12, each with a RED arm in `tests/run_b12_routed_findings_probe.py`; `--ablate` shows which fix each measures): **T16** `api/sd-data.js:7179` a second EVV write replaces `clock_in_at` with no trail · **T17** `api/sen-auth.js:263` `setup` can demote the last owner · **T18** `api/_lib/compliance-rules.js` `applies_to_positions` contents unvalidated · **N4** `api/sd-data-cross-tenant-dispatchers.test.js:577` cites a path that does not exist (one-line comment fix).
- **FOURTH** — the Tier A review obligation in `docs/tier-a-reviews.json` on `grd_boq_rates` / `grd_rounds`, assigned.
- **CC (`tools/`)** — `MIN_TEST_FILES` 370 against 796; `sairn_push_gate_hook.py:988-991` contradicts `:1377-1392`. **`CLAUDE.md` owner** — it still says "`SAIRN_SEED_GATE=off` still works".

## Unverified
Mutation 6 is **out of scope** for the new control by construction (it changes an app name, and its arm did not exist pre-repair), so the claim rests on **two** same-reason mutations, not three. The control measures the PREDICATES, not the handler — `run_probe` covers that half and the two are reported separately. **Items 2–5 were not driven at all.** No deployed-URL check applies.

**CONTEXT 73% used of 1,000,000 (Opus 5 1M)** — measured from this session's own transcript usage records (727,340 input tokens on the last recorded request), not from `tools/sairn_status_line.py`, which answers `ctx ??%` from inside a turn. The stop instruction came at 71%.
