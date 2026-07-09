# SAIRNvet — Session 62 Handoff

## Verified current state (confirmed independently via GitHub API, not trusted from prior notes)
- Branch: **master** (main is stale/broken — hard Guardian check)
- `sairnvet.html`: **553,330 bytes**, blob sha `5edad9ad6d52178d05737383cb15be56e0cf9a7b`
- Master HEAD commit: `e3c32b8276ae625be05cd7da9c47c6f552ea950c`
- `api/claude.js`: 4,114 bytes, sha `d6ac41172afb37c91c89a5d754b0d99a9e404c24` — unchanged, still proxy-only, still works
- `api/bridge.js`: still absent from the repo tree. Do not build the SAIRNbiz↔SAIRNvet bridge until deliberately started.
- Panels: **54 total** — nav↔panel reconciliation (54 `svNav()` targets vs 54 real panel divs, zero broken links, zero orphans) re-confirmed after every push this session.

## ⚠️ Gap — main/master divergence (still growing, still unresolved)
`main` is now **47 commits behind master**. Not touched — no approval given to merge or repoint anything. If Vercel's GitHub integration deploys from the default branch (`main`), it has not seen any of this session's work. Production is only current via the manual local sequence (`git fetch origin && git reset --hard origin/master` then `npx vercel --prod --force`). Still needs a decision.

## ⚠️ Gap carried forward — Guardian v2 skill file (from Session 59)
On-disk Guardian v2 skill file was found at 25 checks despite being logged as upgraded to 33. Not re-checked this session — carry forward.

## ✅ Resolved this session — the `runMissedChargeScan()` watch item
Flagged in Sessions 60/61 as sending a hardcoded fake practice profile into an AI prompt. Fixed as part of panel-analytics (see below) — now grounded in real Clients/Invoicing/Billing data.

## Panels fixed this session (10) — all pushed to master, all independently re-verified byte-for-byte after push

1. **panel-wildliferehab** — commit `4f310378`. Was fully static, zero JS backing at all. `sv_wildliferehab`.
2. **panel-speciesref** — commit `3df88a29`. Dropped fabricated KPIs (140+ profiles, 12 body systems, 800+ ranges). Added honest AI-lookup counter to the already-genuine "Ask Claude About a Species" feature. `sv_speciesref`.
3. **panel-conservation** — commit `66bec478`. Dropped an invented "Genetic Diversity Index: 0.89." `sv_conservation`.
4. **panel-compliance** — commit `05bcb4bc`. Status now computed deterministically from due date instead of manually typed. `sv_compliance`.
5. **panel-clients** — commit `1c9214cf`. Claimed 1,204 clients / fake $2,140 LTV / fake 91% retention against 2 real rows. LTV and retention dropped; replaced with real counts. `sv_clients`.
6. **panel-invoicing** — commit `01d4933e`. Fabricated financials ($4,820/$12,340/96%) matched nothing in the table. Replaced with real dollar-computed KPIs. `sv_invoicing`.
7. **billing** — commit `a7d7a7a6`. Same fabricated $4,820 figure reused here, plus fake plan/decline counts. Replaced with real KPIs. `sv_billing`.
8. **panel-financials** — commit `688e355f`. Biggest fabrication yet — invented $187,400 Revenue MTD / $102,300 Expenses MTD / 45% margin / +18% YoY growth. Reframed as an honest budget-vs-actual tracker with live-computed variance; also corrected an overselling panel description. `sv_financials`.
9. **reports** — commit `51f62b5f`. Dropped fabricated "32 reports available / 5 scheduled / static last-export date." Real counts from the actual report registry. `sv_reports`.
10. **panel-analytics** — commit `e3c32b82`. Dropped fabricated $3,420 missed-charges and 94% forecast-accuracy figures. KPIs and the insights table now compute live from real Clients + Invoicing + Billing data (avg invoice value, clients with no visit in 12+ months, declined transactions). `runMissedChargeScan()` now feeds the AI a real practice snapshot instead of a hardcoded fake one, with an honest instruction to flag small sample sizes. No CRUD here — this panel is a derived/computed view over other panels' real data, by design.

## Remaining panels not yet audited (20)
panel-staff (do this one next), panel-multisite, panel-documents, panel-referrals, panel-petinsurance, panel-portal, panel-boarding, panel-wellness, panel-mobilevet, panel-communications, panel-reminders, settings, companion-patients, equine-patients, large-patients, exotic-patients, avian-patients, reptile-patients, aquatic-patients, zoo-patients

No specific high-risk flags on these yet beyond the general pattern — audit each fresh per the standard workflow. Financial fabrication has now been found and fixed in every money-touching panel reached so far (farmcalls, clients, invoicing, billing, financials, reports, analytics) — the remaining panels are mostly clinical/operational, so watch for the same pattern (fake success toasts, non-functional buttons, claims not backed by data) rather than assuming dollar-figure fabrication specifically.

## Standard workflow for continuing (proven across 25 panels now — Session 59 + this session)
1. Confirm master HEAD unchanged since last known commit before touching anything.
2. Fetch `sairnvet.html` fresh via GitHub raw content API — don't trust local cache from a prior turn.
3. Extract the target panel's HTML block by finding `<div id="X"` through the next `<div id="`.
4. Audit for: fabricated/mismatched KPIs, missing ids, fake success toasts, non-functional buttons, claims that aren't actually implemented.
5. Design a real data model: `sv_<n>`-prefixed localStorage, click-to-edit pattern (row onclick → edit card with Save/Cancel/Remove), add-record form, KPIs computed live from the actual list — never re-fabricate a number; drop it or make it an optional field starting at "—"/0 if it can't be honestly computed. If the panel is a derived/analytics view over other panels' real data rather than its own entity, it doesn't need its own CRUD (see panel-analytics).
6. Add safety gates where the panel implies a real requirement the old version ignored.
7. Check for id/function-name collisions against the live file before writing (`grep -c` for each new id/function name — must be 0).
8. Run scoped Guardian-equivalent checks (`node --check` on extracted script, no Unicode box chars, no `alert()`, no `console.log`, no duplicate ids, div-tag balance, single `<script>` block, `escHtml` used in every new render function).
9. Reconcile nav↔panel counts (must stay 54/54) before pushing.
10. Push via GitHub REST API blob→tree→commit→ref (never `git push` directly).
11. Independently re-fetch from GitHub after push and diff against the local pushed copy — must be byte-identical.
12. Hook the new `render<n>()` call into **both** init blocks.
13. Reuse existing generic helpers where they already exist (e.g. `svDaysBetween`) instead of duplicating logic. Cross-panel reads (e.g. `getClients()`, `getInvoices()`) are fine to reuse from an analytics/derived panel — just don't write back to another panel's data store.

## Iron Laws — unchanged, all followed this session
GitHub REST API only (blob→tree→commit→ref, never `git push` directly) · no Unicode box-drawing chars in JS · no dark backgrounds · no `alert()` (showToast only) · all new localStorage keys `sv_`-prefixed · Claude calls through proxy only · Guardian-equivalent scan before every push · Chat stops rather than compacts — produce handoff instead.

## Deploy
Local machine: `C:\Users\marsh\Documents\SAIRN`, plain CMD (never PowerShell):
```
git fetch origin
git reset --hard origin/master
npx vercel --prod --force
```
