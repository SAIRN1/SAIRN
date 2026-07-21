# SAIRN — Session 64 Handoff

This session moves to **Claude Code** for continuation. Read this whole doc before touching anything — it covers what was fixed, what was verified clean, what's still broken, and the exact restraints needed to avoid the mistakes made *during* this session (documented honestly below, since they nearly shipped).

## Verified current state (confirmed independently via GitHub API, not trusted from prior notes)
- Repo: `SAIRN1/SAIRN`, branch **master** (main is stale — do not use)
- Master HEAD commit: `2cf6499f9612882ac386b1ebe3e18172bf3bb792`
- All commits this session listed below with SHAs for traceability

## ⚠️ Headline finding — SAIRNbiz was non-functional in production
Before any KPI work, `node --check` on SAIRNbiz's inline script failed: missing string-concatenation operators around a handful of `onclick="...('...)"` handlers built inside single-quoted JS strings caused a hard parse error. **This meant the entire app's JavaScript failed to load — nothing in SAIRNbiz worked at all**, independent of the fabricated-KPI issue. This was pre-existing (confirmed against the pristine pre-session fetch), not introduced this session. Fixed as the first commit.

**Takeaway for Claude Code:** before starting *any* audit/fix pass on *any* SAIRN app, run `node --check` on the extracted inline `<script>` block first. Do this even for apps marked "complete" in a prior handoff — SAIRNbiz's fabricated-KPI audit had never included a basic syntax check, and it should have been step zero.

## ⚠️ Mistakes made *this session* that Claude Code must not repeat
Documented honestly so the same errors aren't repeated:
1. **Twice deleted an adjacent line when inserting new functions.** Pattern: replacing `old_str` that included a stable anchor line (e.g. `var soapPendingNote = null;`) plus surrounding text, but the `new_str` accidentally omitted that anchor line, silently deleting it. Caught both times only by re-grepping for the declaration immediately after. **Fix going forward: anchor insertions on a line that is never itself the target of a future edit** — e.g. `function getCogginsTests(){` (appears exactly once, never modified) — and always re-grep for any global `var` declarations you moved past, immediately after any insert, before running Guardian checks.
2. **Introduced the same unescaped-quote bug I was fixing**, twice, in newly-written code (rHire and rPerf dead-button strings in SAIRNbiz) by copy-adapting the buggy original pattern instead of the corrected one. Caught by `node --check` each time — which is exactly why that check has to run after *every* edit, not just once at the end.
3. **Misread "SAIRNcode" as unrelated during a voice-transcribed instruction** ("Claude code coming back faulty") mid-session and nearly started an unplanned audit of the wrong app. No changes were made or pushed to `sairncode.html` as a result — confirmed via diff before abandoning that thread — but it cost a chunk of the session. **Takeaway: if a spoken instruction names something ambiguous between an app and a tool, pause and ask in one line rather than guessing and burning turns.**

## Workstream 1 — SAIRNbiz (Session 64: full first-pass audit + fix, single commit)
Commit `8748b14246c4239dba3b517a33fc78faae6a297e`.

Never audited before this session despite the same fabricated-KPI pattern already being fixed in SAIRNvet/SAIRNcode. Fixed in one consolidated push (not panel-by-panel commits, given the scope):
- The syntax bug above (headline finding)
- Dashboard: removed a hardcoded `+28000` flat addition to "live" revenue, a fully fabricated 6-month revenue chart, and hardcoded fake activity/action feeds — all now computed from real invoice/expense/AP/training/perf records
- P&L (inside Payroll panel): removed hardcoded $498K revenue/$199K COGS/fabricated category breakdowns/fabricated 6-month chart — now computed from real invoice/expense data; relabeled overclaiming "YTD" text to "Recorded" since only partial-period data exists
- Invoices: real avg-days-to-pay from actual paid dates (added `paidDate` field to seed data)
- Expenses: removed a fake ×6 "YTD" extrapolation multiplier
- A/R: real aging buckets and collection rate from actual due dates (was hardcoded $6,750/97%/fake "43 days")
- Tax: rebuilt from real payroll/revenue × published tax rates instead of a fully invented table with fabricated dollar figures
- Benefits: real per-employee enrollment flags instead of an assumed 75% enrollment / flat $520 cost
- Hiring, Training, Performance: replaced hardcoded 16-day time-to-hire / 284 training hours / 2 raises approved / etc. with values computed live from actual records

Guardian clean: `node --check` pass, 0 duplicate ids, div balance 713/713, 20/20 nav↔panel reconciliation. Byte-verified against GitHub after push.

## Workstream 2 — SAIRNvet (continued from Session 63's 12/30 panels done)

Session 63 handoff undercounted the scope: on inspection, **14 of the ~18 "remaining" panels turned out to be fully static hardcoded HTML with zero backing JavaScript at all** (worse than a computed-but-fabricated KPI — there was no computation happening, ever). The other panels in that remaining set already had real render functions.

**Fixed this session (8 panels, one commit each):**
| Panel | Commit | What was wrong |
|---|---|---|
| patients | `3bd05904105dd80de02b5ee02fc1b95cb881f88b` | Fully static ("1,847 active/62 new/2.4 visits/97%" baked into markup), only 6 demo rows, dead Add button |
| soap | `a3ad20f2829084e334840b5cc6b4229d8e6da7f5` | Fully static KPIs disconnected from the real `generateSOAP()` AI feature; now logs and times real notes |
| boarding | `4a887ba84ceb0aa7057b1d721ff69c40ad36e8e4` | Fully static, no add form existed at all |
| communications | `42955d87e71aaec3a3a7de2ce674fe302c8318b8` | Fully static; also dropped an unfounded "SMS Enabled: Yes" — no SMS integration exists anywhere in the app |
| documents | `f465bd2d19ca690e7662b9aa6e1b09617871ad05` | Fully static; dropped unfounded "E-Signature Enabled"/"Storage Used: 2.1 GB" — neither integration exists |
| mobilevet | `d456ea22778f28c3ff64fc6ae8426c56d9473b19` | Fully static; dropped a fabricated live-GPS/ETA claim — no real-time tracking system exists |
| petinsurance | `dd722156f27b8a0316233931ef0fdbf22c946476` | Fully static claims table |
| portal | `2cf6499f9612882ac386b1ebe3e18172bf3bb792` | Fully static; dropped unfounded "Portal Users: 892"/"Adoption Rate: 74%" — no client user-account system exists |

**Audited and found genuinely clean (no fix needed, no commit):**
- `diagnoses` — real 465-entry `VET_DIAGNOSES` database, live search, count matches the claimed 465 exactly
- `drugdb` — real 485-entry `VET_DRUGS` database, count matches claimed 485 exactly, careful species-specific safety flags (e.g. explicitly refuses to show a calculated numeric dose for carfentanil/etorphine rather than guessing)

**Still remaining — same static-HTML treatment needed:** `prepurchase`, `referrals`, `reminders`, `reproduction`, `wellness` (5 panels). Not yet inspected in detail this session, but given the pattern found in the other 14, assume they are fully static with hardcoded KPIs until checked.

Guardian clean throughout every commit above: `node --check` pass, 0 duplicate ids, div balance verified (grew from 1169/1169 to 1185/1185 as panels gained real content), 54/54 nav↔panel reconciliation maintained at every step. Every commit independently byte-verified against GitHub after push.

## Standard workflow (proven across this session and prior ones — follow exactly)
1. Confirm master HEAD unchanged since last known commit before touching anything (`GET /git/refs/heads/master`).
2. Fetch the target file fresh via GitHub raw content API — never trust local cache from a prior turn.
3. **Run `node --check` on the extracted inline `<script>` block FIRST, before any KPI/content audit** — added this session after the SAIRNbiz finding above.
4. Locate the target panel's HTML block and its backing render function (if any — check for a `render<Name>()` or `get<Name>()` function; its absence means the panel is fully static and needs a data model built from scratch, not just a KPI fix).
5. Audit for: fabricated/mismatched KPIs, dead buttons calling nonexistent targets, unfounded capability claims (SMS/e-signature/GPS/storage/user-accounts — check whether the claimed integration actually exists anywhere in the codebase before trusting a KPI that implies it), missing ids, fake success toasts.
6. Design a real data model: app-prefixed localStorage (`sv_` for SAIRNvet, `sb_` for SAIRNbiz), get/save/render/add/edit/remove functions matching the existing convention in that file, KPIs computed live from the actual list — never re-fabricate a number; drop it or show `--`/0 if it can't be honestly computed from data that exists.
7. Check for id/function-name collisions against the live file before writing (`grep -c` for each new id/function name — must return 0 for anything new).
8. **After every single edit** (not just at the end): re-run `node --check`. This is non-negotiable given mistake #2 above.
9. Run the rest of the Guardian-equivalent checks: no Unicode box chars, no `alert()`, no duplicate ids, div-tag balance, single `<script>` block.
10. Reconcile nav↔panel counts before pushing.
11. Push via GitHub REST API blob→tree→commit→ref (never `git push` directly).
12. Independently re-fetch from GitHub after push and diff against the local pushed copy — must be byte-identical.
13. Hook new `render<n>()` calls into **every** init/load path that exists in that specific app. SAIRNvet has two PIN-gated init blocks (search for `renderCoggins();` as a landmark — it appears in both). SAIRNbiz has one `function init(){...}`.
14. When inserting new top-level functions, anchor the edit on a stable line that is never itself modified later (e.g. `function getCogginsTests(){` in SAIRNvet) — never anchor on a `var` declaration or other line that might be adjacent to content you're also changing.

## Iron Laws — unchanged
GitHub REST API only (blob→tree→commit→ref, never `git push` directly) · no Unicode box-drawing chars in JS · no dark backgrounds · no `alert()` (showToast only) · all new localStorage keys app-prefixed · Claude calls through proxy only · Guardian-equivalent scan **after every edit**, not just before push · Chat/session stops rather than compacts — produce a handoff instead.

## What's next, in priority order
1. Finish SAIRNvet: `prepurchase`, `referrals`, `reminders`, `reproduction`, `wellness` — assume fully static until checked, same treatment as the 8 fixed this session.
2. Michael has explicitly said the goal is **every SAIRN app**, one at a time, brought to "100% complete, could be put on someone's computer" standard before moving to the next app. Do not move to another app until SAIRNvet's full panel list is clean AND the whole file has had a `node --check` pass confirming no hidden syntax bugs anywhere (not just in the panels touched this session).
3. After SAIRNvet: re-verify SAIRNcode with the same `node --check`-first rigor — it was marked "fully completed, 20/20 panels" in Session 63, but SAIRNbiz was *also* assumed fine until it wasn't. A basic syntax check on SAIRNcode has not yet been done with this level of scrutiny this session (the check was started, found clean — `node --check` passed, 0 dup ids, div balance 492/492, 20/20 nav-panel reconciliation on `showPanel()` targets — but a full fabricated-KPI re-audit was not completed before the session pivoted to this handoff).
4. Then the remaining platform apps in whatever order Michael prioritizes.

## Deploy
Local machine: `C:\Users\marsh` (repo root is the home directory itself), plain CMD (never PowerShell):
```
git fetch origin
git reset --hard origin/master
npx vercel --prod --force
```
Answer "yes" to the "deploying your home directory" prompt.
