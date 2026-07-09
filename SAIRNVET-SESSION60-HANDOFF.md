# SAIRNvet — Session 60 Handoff

## Verified current state (confirmed independently via GitHub API, not trusted from prior notes)
- Branch: **master** (main is stale/broken — hard Guardian check)
- `sairnvet.html`: **524,283 bytes**, blob sha `84a0f79b115019feb06428748b9e0ae54883598a`
- Master HEAD commit: `1c9214cfde83613d3258d4f6d65cc4dbc6657532`
- `api/claude.js`: 4,114 bytes, sha `d6ac41172afb37c91c89a5d754b0d99a9e404c24` — unchanged this session, still proxy-only, still works
- `api/bridge.js`: **confirmed still absent from the repo tree.** Do not build the SAIRNbiz↔SAIRNvet bridge until this is deliberately started.
- Panels: **54 total** — nav↔panel reconciliation (54 `svNav()` targets vs 54 real panel divs, zero broken links, zero orphans) re-confirmed independently after every single push this session.

## ⚠️ Gap — main/master divergence (worse than last handoff, still unresolved)
`main` is now **40 commits behind master** (was 35 at the start of this session) and keeps diverging with every push. Not touched this session — no approval given to merge or repoint anything. If Vercel's GitHub integration auto-deploys from the default branch (`main`), it has not seen any work from Session 59 or this session. Production has only been current via the manual local sequence (`git fetch origin && git reset --hard origin/master` then `npx vercel --prod --force`). Needs a decision: fast-forward `main` to `master`, or repoint Vercel's git integration to `master`.

## ⚠️ Gap carried forward — Guardian v2 skill file (from Session 59, not re-checked this session)
Session 59 found the on-disk Guardian v2 skill file still at 25 checks despite being logged as upgraded to 33. Not re-verified this session — carry forward, check before trusting any "33-check" claim.

## Workflow change this session
Per explicit instruction, Claude Chat did all panel fixes directly this session — no Claude Code handoff. Same standard workflow, same Iron Laws, same push/verify discipline as Session 59. All 5 fixes independently re-verified byte-for-byte straight from GitHub after each push.

## Panels fixed this session (5) — all pushed to master, all independently re-verified byte-for-byte after push

1. **panel-wildliferehab** — commit `4f310378`. Was fully static (KPIs 17/89/71%/24 with only 2 hardcoded rows, zero JS backing at all — not even started, despite Session 59 believing extraction was in progress). Now real ids, live KPIs (Active Cases/Released YTD/Release Rate/Species Diversity), Days in Care computed live from intake→today or intake→release. `sv_wildliferehab`.
2. **panel-speciesref** — commit `3df88a29`. Fabricated KPIs (140+ profiles, 12 body systems, 800+ ranges, static "Updated" date) replaced with real counts. The existing "Ask Claude About a Species" AI feature was already genuinely wired to the proxy — left alone, just added an honest AI-lookup counter to it. `sv_speciesref`.
3. **panel-conservation** — commit `66bec478`. Had an invented **"Genetic Diversity Index: 0.89"** — a pseudo-scientific figure with nothing behind it, impossible to honestly compute from a studbook status table. Dropped; replaced with Species Tracked/Breeding Pairs Logged/Active Recommendations/Programs, all real. `sv_conservation`.
4. **panel-compliance** — commit `05bcb4bc`. Status is no longer manually typed — computed deterministically from due date (Overdue / Due Soon ≤60 days / Current), same "computed not claimed" pattern as the Surgery consent gate and Coggins certificate gate. `sv_compliance`.
5. **panel-clients** — commit `1c9214cf`. **Largest fabrication found this session** — claimed 1,204 total clients / 28 new this month / $2,140 avg lifetime value / 91% retention against 2 actual rows. LTV and retention rate were dropped (not honestly computable from a 2-column snapshot table); replaced with Total Clients/Active Clients/New This Month/Total Outstanding Balance, all real. `sv_clients`.

## Remaining panels not yet audited (25)
panel-invoicing (do this one first — see note below), billing, panel-financials, reports, panel-analytics, panel-staff, panel-multisite, panel-documents, panel-referrals, panel-petinsurance, panel-portal, panel-boarding, panel-wellness, panel-mobilevet, panel-communications, panel-reminders, settings, companion-patients, equine-patients, large-patients, exotic-patients, avian-patients, reptile-patients, aquatic-patients, zoo-patients

**Note: panel-invoicing, billing, panel-financials, and reports/panel-analytics remain flagged extra-high-risk for fabricated dollar figures.** Confirmed pattern twice now — panel-farmcalls' fake $41,200 "Revenue MTD" (Session 59) and panel-clients' fake $2,140 "Avg Lifetime Value" (this session). Also worth a second look when reached: `runMissedChargeScan()` (likely in panel-financials or billing) sends a hardcoded fabricated practice snapshot ("62 new patients/month, wellness compliance 94%, avg invoice $287") into an AI prompt as if it were real data — spotted in passing this session, not yet fixed.

## Standard workflow for continuing (proven across 20 panels now — Session 59 + this session)
1. Confirm master HEAD unchanged since last known commit (`git/refs/heads/master`) before touching anything.
2. Fetch `sairnvet.html` fresh via GitHub raw content API — don't trust local cache from a prior turn.
3. Extract the target panel's HTML block by finding `<div id="X"` through the next `<div id="`.
4. Audit for: fabricated/mismatched KPIs, missing ids, fake success toasts, non-functional buttons, claims in the description that aren't actually implemented.
5. Design a real data model: `sv_<n>`-prefixed localStorage, click-to-edit pattern (row onclick → edit card with Save/Cancel/Remove), add-record form, KPIs computed live from the actual list — never re-fabricate a number; if something can't be honestly computed, drop it or make it an optional logged field that starts at "—"/0 until entered.
6. Add safety gates where the panel implies a real requirement the old version ignored (mirrors Surgery consent gate, Coggins certificate gate, Compliance computed-status pattern).
7. Check for id/function-name collisions against the live file before writing (`grep -c` for each new id/function name — must be 0).
8. Run scoped Guardian-equivalent checks (JS syntax via `node --check`, no Unicode box chars, no `alert()`, no `console.log`, no duplicate ids, div-tag balance, single `<script>` block, `escHtml` used in every new render function).
9. Reconcile nav↔panel counts (must stay 54/54) before pushing.
10. Push via GitHub REST API blob→tree→commit→ref (never `git push` directly).
11. Independently re-fetch from GitHub after push and diff against the local pushed copy — must be byte-identical.
12. Hook the new `render<n>()` call into **both** init blocks (PIN-login success path and restored-session path) — there are always exactly two matching call sequences.
13. Reuse existing helpers where they already exist and are generic (e.g. `svDaysBetween`) instead of duplicating logic.

## Iron Laws — unchanged, all followed this session
GitHub REST API only (blob→tree→commit→ref, never `git push` directly) · no Unicode box-drawing chars in JS · no dark backgrounds · no `alert()` (showToast only) · all new localStorage keys `sv_`-prefixed · Claude calls through proxy only · Guardian-equivalent scan before every push · Chat stops rather than compacts — produce handoff instead.

## Deploy
Local machine: `C:\Users\marsh\Documents\SAIRN`, plain CMD (never PowerShell):
```
git fetch origin
git reset --hard origin/master
npx vercel --prod --force
```
