# SAIRNvet — Session 61 Handoff

## Verified current state (confirmed independently via GitHub API, not trusted from prior notes)
- Branch: **master** (main is stale/broken — hard Guardian check)
- `sairnvet.html`: **531,316 bytes**, blob sha `f88c75df019571ed7264aea078b15562ed75a8bd`
- Master HEAD commit: `01d4933e3857d59f4aa0c2153818419142b7d68a`
- `api/claude.js`: 4,114 bytes, sha `d6ac41172afb37c91c89a5d754b0d99a9e404c24` — unchanged, still proxy-only, still works
- `api/bridge.js`: still absent from the repo tree. Do not build the SAIRNbiz↔SAIRNvet bridge until deliberately started.
- Panels: **54 total** — nav↔panel reconciliation (54 `svNav()` targets vs 54 real panel divs, zero broken links, zero orphans) re-confirmed after every push this session.

## ⚠️ Gap — main/master divergence (still growing, still unresolved)
`main` is now **42 commits behind master**. Not touched — no approval given to merge or repoint anything. If Vercel's GitHub integration deploys from the default branch (`main`), it has not seen any of this session's work. Production is only current via the manual local sequence (`git fetch origin && git reset --hard origin/master` then `npx vercel --prod --force`). Still needs a decision.

## ⚠️ Gap carried forward — Guardian v2 skill file (from Session 59)
On-disk Guardian v2 skill file was found at 25 checks despite being logged as upgraded to 33. Not re-checked this session — carry forward.

## ⚠️ Watch item — hardcoded fake data inside an AI prompt
`runMissedChargeScan()` (likely in panel-financials or billing, not yet reached) sends a hardcoded fabricated practice snapshot ("62 new patients/month, wellness compliance 94%, avg invoice $287") into an AI prompt as if it were real. Spotted in passing, not yet fixed. Flag when that panel is reached.

## Panels fixed this session (6) — all pushed to master, all independently re-verified byte-for-byte after push

1. **panel-wildliferehab** — commit `4f310378`. Was fully static, zero JS backing at all. Now real ids, live KPIs (Active Cases/Released YTD/Release Rate/Species Diversity), Days in Care computed live. `sv_wildliferehab`.
2. **panel-speciesref** — commit `3df88a29`. Fabricated KPIs (140+ profiles, 12 body systems, 800+ ranges) replaced with real counts. Existing AI lookup feature was already genuine — added an honest usage counter to it. `sv_speciesref`.
3. **panel-conservation** — commit `66bec478`. Dropped an invented "Genetic Diversity Index: 0.89" (impossible to honestly compute from this data). Replaced with Species Tracked/Breeding Pairs Logged/Active Recommendations/Programs. `sv_conservation`.
4. **panel-compliance** — commit `05bcb4bc`. Status now computed deterministically from due date (Overdue/Due Soon ≤60 days/Current) instead of manually typed. `sv_compliance`.
5. **panel-clients** — commit `1c9214cf`. Claimed 1,204 clients / fake $2,140 LTV / fake 91% retention against 2 real rows. LTV and retention dropped (not honestly computable from this data); replaced with Total Clients/Active Clients/New This Month/Total Outstanding Balance. `sv_clients`.
6. **panel-invoicing** — commit `01d4933e`. Fully fabricated financials — "$4,820 invoiced today," "$12,340 outstanding," "96% collection rate" matched nothing in the 2-row table. Replaced with the same 4 KPIs computed for real by dollar amount from actual invoices. `sv_invoicing`.

## Remaining panels not yet audited (24)
billing (do this one first — high financial-fabrication risk), panel-financials, reports, panel-analytics, panel-staff, panel-multisite, panel-documents, panel-referrals, panel-petinsurance, panel-portal, panel-boarding, panel-wellness, panel-mobilevet, panel-communications, panel-reminders, settings, companion-patients, equine-patients, large-patients, exotic-patients, avian-patients, reptile-patients, aquatic-patients, zoo-patients

**Note: billing, panel-financials, and reports/panel-analytics remain flagged extra-high-risk for fabricated dollar figures.** Confirmed pattern three times now (panel-farmcalls, panel-clients, panel-invoicing). Also see the `runMissedChargeScan()` watch item above.

## Standard workflow for continuing (proven across 21 panels now — Session 59 + this session)
1. Confirm master HEAD unchanged since last known commit before touching anything.
2. Fetch `sairnvet.html` fresh via GitHub raw content API — don't trust local cache from a prior turn.
3. Extract the target panel's HTML block by finding `<div id="X"` through the next `<div id="`.
4. Audit for: fabricated/mismatched KPIs, missing ids, fake success toasts, non-functional buttons, claims that aren't actually implemented.
5. Design a real data model: `sv_<n>`-prefixed localStorage, click-to-edit pattern (row onclick → edit card with Save/Cancel/Remove), add-record form, KPIs computed live from the actual list — never re-fabricate a number; drop it or make it an optional field starting at "—"/0 if it can't be honestly computed.
6. Add safety gates where the panel implies a real requirement the old version ignored (mirrors Surgery consent gate, Coggins certificate gate, Compliance computed-status pattern).
7. Check for id/function-name collisions against the live file before writing (`grep -c` for each new id/function name — must be 0).
8. Run scoped Guardian-equivalent checks (`node --check` on extracted script, no Unicode box chars, no `alert()`, no `console.log`, no duplicate ids, div-tag balance, single `<script>` block, `escHtml` used in every new render function).
9. Reconcile nav↔panel counts (must stay 54/54) before pushing.
10. Push via GitHub REST API blob→tree→commit→ref (never `git push` directly).
11. Independently re-fetch from GitHub after push and diff against the local pushed copy — must be byte-identical.
12. Hook the new `render<n>()` call into **both** init blocks (PIN-login success path and restored-session path).
13. Reuse existing generic helpers where they already exist (e.g. `svDaysBetween`) instead of duplicating logic.

## Iron Laws — unchanged, all followed this session
GitHub REST API only (blob→tree→commit→ref, never `git push` directly) · no Unicode box-drawing chars in JS · no dark backgrounds · no `alert()` (showToast only) · all new localStorage keys `sv_`-prefixed · Claude calls through proxy only · Guardian-equivalent scan before every push · Chat stops rather than compacts — produce handoff instead.

## Deploy
Local machine: `C:\Users\marsh\Documents\SAIRN`, plain CMD (never PowerShell):
```
git fetch origin
git reset --hard origin/master
npx vercel --prod --force
```
