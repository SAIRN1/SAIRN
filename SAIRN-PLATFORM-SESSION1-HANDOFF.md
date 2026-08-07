# SAIRN — Platform Session 1 Handoff

Written at a natural stopping point (end of session), 2026-08-07.
Claims below are independently verified against the actual repo/live site,
not assumed from memory — same standard as prior sessions in this series.

**Naming note:** this is the first `SAIRN-PLATFORM-SESSION-N` file, using
the per-app-prefix convention resolved in the `sairn-session-handoff`
skill. This session's real work spanned SAIRNgrounds + SAIRNscape +
shared platform infra (`api/sd-data.js`) + local skill config, which is
exactly the "cross-cutting" case that convention calls for — not a
StoneDesk session, so not `SAIRN-SESSION-N`. The existing `SAIRN-SESSION63
-69` files are StoneDesk work in spirit; not renumbered, per the skill's
own instruction not to retroactively touch them.

## 1. Verified current state

- `origin/main` HEAD: `1f50c705f9430b26932f1fbde6bb5f85b83d350e` —
  confirmed via `git fetch origin main` + `git log origin/main -1` just
  before writing this, local HEAD matches exactly.
- All pushed commits below were byte-verified against GitHub's Contents
  API (not `raw.githubusercontent.com`, which caches stale) after each
  push, and the two `.html` deploys were byte-verified live against
  `sairn.vercel.app/sairngrounds` and `/sairnscape` after each Vercel
  deploy — not assumed from a clean `git push`/deploy exit code.

## 2. Commits this session, in order

1. `9c75038` — Item 3: photo-verified completion gate for SAIRNscape
   Scheduling (SAIRNgrounds already had it; this brought SAIRNscape to
   parity).
2. `8918e3c` — Item 10: self-service course-mapping foundation in the
   Golf Course Module (tee/pin/hazard GPS capture, reuses Design Walk's
   existing AR session rather than a second implementation). No paid
   course-data vendor — that decision (iGolf) was reversed by Michael the
   same night, before any build started on it.
3. `cd3464e` — progress_photos cross-device fix: real
   `grd_progress_photos`/`scp_progress_photos` routes+tables, client-side
   photo compression to fit the 64KB payload cap, honest "this device
   only" toast on sync failure. Also fixed a related bug found in the
   process: SAIRNgrounds' schedule writes were silently hitting
   SAIRNscape's `schedule` route and 400ing.
4. `f2b25f1` — DreamClose invoice/schedule writes never actually reached
   the server: real `grd_invoices`/`grd_dreamclose` routes+tables
   (`invoices` collided with SAIRNscape's route; `dreamclose` had no
   route at all), `dcCreateInvoiceAndSchedule()`/`saveInv()` now await
   and honestly report sync failures.
5. `68bd04a` — Full resource-name sweep, phase 2: real routes+tables for
   the remaining 26 SAIRNgrounds/SAIRNscape resources (Merchandise/Bar
   module, training academy, invasive species, ecosystem reports, BOQ
   rates, vendors, irrigation, water features, design walk) — same
   await+honest-toast+read-sync treatment as items 3-4 above.
6. `1f50c70` — Added `SAIRN-BACKLOG.md`, logging the graphify rebuild as
   a deferred item.

Not committed/pushed (deliberately): `.claude/settings.local.json`'s
4 skill toggles (see §4) — that file is gitignored by design.

## 3. What was CORRECTED, not just added

- **Branch**: the paste-workflow's standing deploy command named
  `master`. Independently re-verified `main` is the live branch
  (`master` is 60+ commits stale) before any deploy — corrected the
  command, didn't just follow it.
- **A prior session's "PASS" on DreamClose's schedule write was real
  but narrower than it read.** The claim ("real schedule entry,
  correctly cross-linked by quote_id") was true about local data
  correctness. It was never actually a claim about server persistence —
  that code path was fire-and-forget from Item 7 onward and could not
  have caught the later-discovered `grd_schedule` collision either way.
  Traced this precisely rather than assuming either "the old PASS was
  fake" or "nothing's wrong" — see the conversation for the full
  reasoning; not re-derived here.
- **The graphify "explicitly declined ('No.') yet installed" premise
  did not hold up.** Investigated fresh (independently re-confirming a
  prior session's Aug 4 finding, not just trusting it): no decline is
  recorded anywhere in `.claude/history.jsonl`. What's actually there is
  a pasted instruction explicitly approving the install
  (`uv tool install graphifyy && graphify install`). `graphifyy` (double-
  y) is the real, legitimate PyPI package name, not a typosquat.
- **Graphify's installed graph was reported as possibly valuable; tested
  and found currently unusable.** 91% of its 191,739 nodes are unrelated
  `AppData\Microsoft\Edge`/`Office` noise from an unscoped directory
  walk; it contains zero nodes for the actual live `stonedesk.html`/
  `sairngrounds.html` files; built 84 commits stale. Not disabled
  outright — logged as a deferred backlog item per Michael's call, and
  `graphify` skill set to `"off"` in the meantime.
- **SQL file content pasted into chat came through visibly truncated**
  (missing semicolons, mid-word cuts) on relay to Michael. Re-verified
  the real files on disk directly (paren balance, statement-count vs.
  semicolon-count parity, no truncation-pattern matches) — all 4 files
  are complete and structurally valid; the truncation was a chat-relay
  artifact, not a file problem.
- **A credential got pasted into this chat three times** during a
  GitHub token rotation (session key expired mid-session). Flagged each
  time rather than acting on it silently; the working token ended up in
  `Documents\SAIRN\.env.local` (not the repo-root `.env.local`, which is
  a separate file — both exist, only one is what `tools/gh_push.py`
  actually reads).

## 4. Open items, prioritized

1. **SQL migrations — per Michael, all 4 confirmed run tonight**
   (`sairngrounds_data_schema.sql`, `sairnscape_data_schema.sql`,
   `sairngrounds_data_schema_phase2.sql`, `sairnscape_data_schema_phase2.sql`).
   This status is **as reported by Michael, not independently verified
   by Claude** — no Supabase credentials are available in this
   environment to confirm table existence directly. Whoever picks this
   up next with real Supabase access should do that direct check before
   trusting it further, same standard as everything else in this doc.
2. **Full cross-device round-trip verification is blocked**, expectedly:
   no license-key generation mechanism exists anywhere in this codebase
   (`api/_lib/license.js` only reads `license_keys`; it's owned by a
   separate, not-yet-built license-generation system tied to next week's
   Stripe integration). Not a gap to fix tonight — revisit once
   Stripe/licensing is live, then run a real write+read round-trip
   through two separate sessions for at least one `grd_*` and one
   `scp_*` resource before calling any of tonight's 30 fixed resources
   fully verified end-to-end.
3. **`SAIRN-BACKLOG.md`**: graphify rebuild (scoped to
   `C:\Users\marsh\Documents\SAIRN` only, current commit) — deferred,
   not urgent.
4. **4 skills disabled**, local-only by design (`.claude/settings.local.json`,
   gitignored, never pushed): `design-taste-frontend`, `differential-review`,
   `security-auditor`, `graphify`.
5. **Real, still-open, pre-existing gaps not touched this session**
   (carried forward, re-stated not re-verified): item 9's void/override
   RBAC is client-side-enforced only, no server-side re-check; StoneDesk's
   progress-photo QC has the same client-side-only limitation. Neither
   was in scope tonight.
6. **Minor residual note, not urgent**: `.claude/settings.local.json`'s
   accumulated `permissions.allow` history contains old, likely-rotated
   Vercel/GitHub token fragments from past sessions' commands. The file
   is correctly gitignored and was never pushed — flagging only because
   it's real and was seen directly while investigating tonight, not
   because it's an active exposure.

## 5. Standard verification reminder for whoever reads this next

Verify `origin/main` HEAD, verify which branch is actually live, and
independently re-check the SQL-migrations-run claim in §4.1 before
trusting it — including everything else in this document. A clean
`git push`/deploy exit code, or a verbal "confirmed," is not proof by
itself; that's the standard this whole session tried to hold to.
