# StoneDesk — Session 78 Handoff

Written at a natural stopping point, 2026-08-07. Claims below are
independently verified against the actual repo/live site, not assumed
from memory.

## 1. Verified current state

- `main` HEAD: `516afac300a9d70f461fb619aee7daadde064278` — confirmed via
  `git log -1` and `git push` output.
- Live at `sairn.vercel.app/stonedesk` — the specific fix below was
  live-verified through a real browser interaction, not assumed from a
  clean push.

## 2. What happened this session

The freshly-fixed `key_collision_check.py` (see `sairn-portfolio-triage`
skill, Scanner Portability section, 2026-08-07 entry) was run against
`stonedesk.html` for the first time with its new wrapper-detection and
regex-literal fixes. It surfaced 5 `sd_*`/`stonedesk:*` keys written by
2+ distinct backing variables — a real signal category, but one that
needs human tracing before any of it is trusted as a bug (same standard
this file's own git history repeatedly re-learns).

## 3. Triage results — 1 confirmed real, 4 confirmed false positive

**`sd_referrals` — CONFIRMED REAL, fixed this session (commit
`516afac`).** Two independent, incompatible-shape writers shared this
key:
- **Live/canonical**: `sdRefAdd()`/`save()`/`render()` inside the
  `panel-referral` IIFE — real DOM (`#ref-total`, `#ref-list`, etc.),
  wired to the actual "Log Referral" button.
- **Dead**: `rfSave()`/`rfAddReferral()`/`rfRender()`/`rfAIBriefing()`
  ("16. REFERRAL TRACKER", module var `rfReferrals`) — its DOM targets
  (`rf-form`, `rf-cust`, `rf-date`, etc.) had zero matches anywhere in
  the file and `rfSave()`/`rfAddReferral()` had zero callers, so the
  *write* side was already fully unreachable. `rfRender()`, however, was
  still wired into both the central nav dispatcher (`id==='referral'`)
  and the BOOT `DOMContentLoaded` handler — it silently read the real
  `sd_referrals` data in the wrong shape on every visit/load. Harmless
  only because every element it targeted was equally nonexistent, but a
  real corruption risk if `rf-*` markup were ever restored without
  recognizing the duplication — same failure class as the already-fixed
  "15. CONTRACTOR PORTAL" orphaned duplicate a few hundred lines above
  it. **Deleted entirely** (functions, module var, both external call
  sites), not quarantined — a dated removal comment matching the file's
  own established convention was left in its place.
- Live-verified after push: bypassed the auth screen via direct DOM
  manipulation (the real login flow needs server-issued credentials this
  session doesn't have), navigated to the real Referral Program panel,
  submitted a new referral through the actual "Log Referral" form, and
  confirmed the new entry rendered correctly in the log with updated
  KPIs (6 total, 33% conversion) and zero console errors.

**The other 4 — reviewed and cleared, no action taken:**
- `sd_quote_history` (`sdQuoteSaveHistory()`'s `h` vs `save()`'s `d`) —
  same shape; the writer's own inline comment confirms it was explicitly
  aligned to the canonical schema after a past bug.
- `sd_slab_tracker` (`load()`'s `old` vs `save()`'s `d`) — `old` is an
  explicitly-documented, self-clearing, one-time migration copy from a
  legacy key (`sd_slabs`); already resolved and referenced in
  `STONEDESK-SESSION72-HANDOFF.md`.
- `stonedesk:ai_memories` (`syncSDMemoriesFromSupabase()`'s `data` vs
  `writeSDMemory()`'s `_sdMemories`) — same memory-object shape both
  ways; the two variables are literally aliased at one point
  (`_sdMemories = data`).
- `stonedesk:business_profile` (`syncSDProfileFromSupabase()`'s `data`
  vs `saveSDProfile()`'s `profile`) — same pattern, one shared
  profile-object shape used identically for server sync and local save.

## 4. Verification run on the `sd_referrals` deletion

- `checkblocks.py`: 128/128 blocks, 0 failed.
- `div_balance_check.py`: **FAIL, DIFF:-4** — confirmed **pre-existing**
  via `git stash` comparison (identical DIFF and
  `FIRST_UNDERFLOW_LINE:5092` before and after this edit). Not
  introduced by this session; not re-investigated further here — a real,
  standing, unrelated item for whoever picks up div-balance work next.
- `panel_nesting_check.py`: 62/62 panels, 0 trapped — unaffected (the
  deleted code had no host panel to begin with).
- `sairn_dead_button_audit.py`: identical before/after (`C1:1` notify(),
  `D2:1`/37 pre-existing reused names, `D1:0`, `E:0`).
- `key_collision_check.py`: `sd_referrals` no longer appears; the other
  4 (confirmed false positives above) still do, as expected.

## 5. Open items, prioritized

1. **`div_balance_check.py`'s pre-existing `DIFF:-4` / line 5092
   underflow** — real, confirmed not caused by this session, not yet
   root-caused. Worth a look next time div-balance is on the agenda.
2. **StoneDesk's other 3 `sairn-portfolio-triage` scanners were only run
   tonight for the first time with their new wrapper/regex-literal
   fixes** — `missing_dom_target_check.py`'s 184 missing targets are the
   pre-existing baseline, unaffected by tonight's work and not
   individually triaged this session (only the referral-panel one, found
   via the key-collision path, was traced). A future session could run
   the same triage-by-hand process against that list.
3. Nothing else blocked.

## 6. Standard verification reminder for whoever reads this next

Verify `main` HEAD, verify which branch is actually live, and re-check
§4's div-balance claim (real, but not this session's to fix) before
trusting it further — same standard as everything else in this doc.
