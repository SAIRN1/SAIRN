# SAIRNvet — Session 58 Handoff
Generated: July 8, 2026 | Verified via fresh GitHub blob fetch, not memory

## VERIFIED CURRENT STATE (re-verify this yourself before trusting it — see protocol below)
- Master commit: f861a61547b9dcbda065d97bcddd96c933b3a425
- sairnvet.html: 376,984 bytes
- VET_DRUGS: 485 entries (283 originally verified-confident + 202 added this session across sheep/goat/llama/emu, split roughly 60/40 confident vs needsReview)
- VET_DIAGNOSES: 465 entries
- 54 panels, nav confirmed working
- api/claude.js: 4,114 bytes — EXISTS NOW, was missing from both GitHub and Michael's local machine all along until this session
- Guardian v2 skill: 33 checks (was 25 at start of session)

## CRITICAL — READ THIS FIRST
**api/claude.js did not exist anywhere before this session** — not in the GitHub repo, not on Michael's local machine — despite every app (StoneDesk, SAIRNbiz, SAIRNcode, SAIRNvet) calling `https://sairn.vercel.app/api/claude` this whole time. It silently failed with an empty-catch swallow every time. Built and pushed this session. `ANTHROPIC_API_KEY` has been added to Vercel (Production + Preview) and Michael confirmed the dosing calculator's AI narrative is now genuinely working end to end.

**api/bridge.js likely has the same problem** — never verified to exist. Do NOT build the SAIRNbiz↔SAIRNvet payroll/HR bridge Michael wants until you've checked whether `api/bridge.js` exists the same way we had to check for `api/claude.js` (Vercel dashboard Functions tab, and `dir api` on the local machine). Treat it as probably-missing until proven otherwise.

## THIS SESSION'S WORK (chronological, all pushed and independently verified from GitHub after each push)

**1. Branch mismatch caught:** GitHub's default branch is `main` (stale, old broken skeleton at d5ce52a0). All real work is on `master`. A fresh Claude Code session defaulted to `main` and reported the wrong file. Fixed by explicit branch checkout; added as a permanent Guardian check (#26).

**2. VET_DRUGS schema migration:** 208 entries (multi-species rows, one dose applied across a species list) exploded into 466 per-species rows with real `doseMin`/`doseMax`/`doseUnit`/`needsReview` fields. ~40% flagged `needsReview:true` with null bounds rather than fabricated doses, by design.

**3. Safety architecture built into the dosing calculator and diagnosis generator:**
   - `RED_FLAG_MATRIX` — deterministic contraindication gate, runs before any AI call, blocks known-fatal combos (acetaminophen+cat, ivermectin+chelonian, permethrin+cat, amitraz+cat/rabbit, penicillin+rodent, monensin+horse, copper+sheep, carfentanil/etorphine human-lethality, etc.)
   - `findDrugEntries()` — grounds the AI in verified VET_DRUGS records instead of letting it guess
   - Deterministic dose math — weight × doseMin/doseMax computed in plain JS, never by the AI
   - Vet sign-off checkbox required before anything is "confirmed," audit log to `sv_audit_log`
   - Diagnosis generator now requires a ranked differential, never a single answer

**4. VET_DIAGNOSES rebalanced and expanded:** 346 → 451 → 465. Was 60% dog/cat, now ~46%. Added real depth to reptile, avian, exotic mammal, zoo/wildlife (informed by this session's Columbus Zoo research — Great Ape Heart Project cardiac monitoring, Manatee Rescue rehab criteria).

**5. Guardian v2 expanded 25 → 33 checks** (`/mnt/skills/user/sairn-guardian-v2/SKILL.md`) — added Repo Integrity (branch verification, hollow-rewrite size check), AI Content Integrity (confidence field required, duplicated-flag-text check, deterministic cross-category danger checks), UI Completeness (visually-actionable-must-be-functional, stale hardcoded counts, new data must propagate to dropdowns). Three of these are now hard-blocks.

**6. Withdrawal time schema:** `withdrawalMeat`/`withdrawalMilk`/`withdrawalStatus` added to all 60 food-animal drug rows. No specific withdrawal times fabricated (formulation/brand-specific) — deterministic orange banner fires in the calculator whenever species is food-producing, independent of drug match confidence.

**7. Drug interaction checker:** curated 15-pair deterministic `INTERACTION_MATRIX` (NSAID-pair, NSAID+steroid, ACE+NSAID, digoxin+furosemide, alpha-2 stacking, MDR1 ivermectin+loperamide, etc.), explicitly labeled non-exhaustive.

**8. Persistent UI:** clinical-decision-support-only disclaimer banner on every panel (print-excluded). Zoo/Wildlife moved to its own "Specialty" sidebar section — data untouched, just deprioritized per the go-to-market scope discussion (focus: companion + equine + farm/food animal + small exotics common in Ohio; zoo/wildlife stays built but dormant).

**9. Ohio small-farm species added** (were completely or almost completely absent): Sheep 4→9 drugs, Goat 0→6, Llama/Alpaca 0→5 (includes meningeal worm prevention — real, serious, deer-borne risk in Ohio), Emu/Ratite 0→3 (heavily flagged, genuinely less-standardized territory). +15 diagnoses across these four. Species dropdowns updated in all 3 places (calculator, diagnosis search, drug database). Copper+sheep added to RED_FLAG_MATRIX (sheep are copper-sensitive; goats need MORE copper than sheep — mixing mineral mixes across species in a mixed operation is a real, common, dangerous mistake).

**10. Dashboard Quick Start links fixed** — were static non-clickable text styled to look like links.

**11. api/claude.js built and deployed** (see Critical section above). Demo-limit checking in it is in-memory/best-effort only — flagged as needing a persistent store (Vercel KV or the Supabase project already used elsewhere in SAIRN) before real customer traffic.

**12. Three ambiguous numeric placeholders fixed** (calc-weight, dx-weight, zoo-weight) — placeholder text "25" was visually indistinguishable from an actual entered value, causing a false "fill in fields" error during live testing. Changed to "e.g., 25" pattern.

**13. Whiteboard panel made fully interactive** — was 3 hardcoded static rows with zero interactivity. Now: click any patient row to edit location/status/doctor/notes inline, discharge/remove, add new patients. Persists to `sv_whiteboard`. KPIs compute live from actual data.

**14. SOAP Notes fixed** — added ranked-differential requirement, explicit draft-only framing, vet sign-off checkbox, audit log. Matches the dosing-calculator safety pattern.

**15. Controlled Substances panel — was completely fake.** The "Log Entry" form's inputs had **no id attributes at all**; the button's onclick just called `showToast('Logged...','success')` directly with no logic behind it — didn't read any value, didn't touch the table, didn't update any balance. Now real: data-driven (`sv_controlled`), actual running-balance subtraction on logging, Schedule II entries **blocked** without a witness name (real DEA co-sign requirement), negative-balance discrepancy flagging, live KPIs.

## PANEL AUDIT STATUS — this is a one-at-a-time, ongoing process (Michael's explicit preference given session-limit pressure)
**Audited and fixed this session:** dashboard, panel-diagnoses, panel-drugdb, panel-pharmacy, panel-patients (spot-checked, was already fine), panel-whiteboard, panel-soap, panel-controlled

**NOT yet audited — assume nothing about these until checked the same way:** panel-ai (AI Assistant — do this one next, it's the first Core sidebar item after Dashboard, most likely to get clicked early in a demo), panel-scheduling, panel-vitals, panel-lab, panel-imaging, panel-surgery, panel-dental, panel-examrooms, panel-teleconsult, panel-lameness, panel-farmcalls, panel-reproduction, panel-equinedental, panel-prepurchase, panel-coggins, panel-herdhealth, panel-wildliferehab, panel-speciesref, panel-conservation, panel-compliance, panel-clients, panel-invoicing, billing, panel-financials, reports, panel-analytics, panel-staff, panel-multisite, panel-documents, panel-referrals, panel-petinsurance, panel-portal, panel-boarding, panel-wellness, panel-mobilevet, panel-communications, panel-reminders, settings, companion-patients, equine-patients, large-patients, exotic-patients, avian-patients, reptile-patients, aquatic-patients, zoo-patients

The pattern to check for in each: (a) do buttons/forms have real ids and real logic, or fake success toasts like Controlled Substances had, (b) is any AI-calling function grounded/safety-gated like the dosing calculator, or raw like SOAP notes was, (c) are KPIs/counts live or hardcoded-stale, (d) do all interactive-looking elements actually do something.

## UNRESOLVED FROM THIS SESSION (Michael's side, not yet acted on)
- **SAIRNbiz↔SAIRNvet payroll/HR bridge** — Michael wants every app bridged to SAIRNbiz so one subscription covers HR/payroll everywhere. Blocked on verifying `api/bridge.js` actually exists (see Critical section). Do not build against an assumption.
- **"Media design" skill** — Michael asked for a new skill, ruled out three offered interpretations (client handouts, marketing collateral, social content) with "this is limited" and did not clarify further. Needs a real conversation about actual scope before building anything, to avoid overlapping `sairn-pitch-deck-builder` / `social-gtm-creator` / `canvas-design`.
- **Custom app pricing** — researched market data (small custom apps $50K-$100K+, AI-specific builds commonly $50K-$125K for small/mid scope). Discussed value-based vs. speed-based positioning given Michael's reusable-architecture advantage. No final pricing decision made — informational only.

## IRON LAWS (unchanged)
- GitHub REST API only — blob→tree→commit→ref, never git push directly
- Always fetch current SHA immediately before any write
- No Unicode box chars in JS, no dark backgrounds, no alert() (showToast() only)
- localStorage keys prefixed sv_
- All Claude calls through proxy only (sairn.vercel.app/api/claude), never api.anthropic.com directly
- Guardian scan (33 checks now) before every push, zero tolerance on the 8 hard-blocks
- Verify every claim via git tree/blob API — never trust /contents cache, never trust a prior handoff or this one at face value
- Deploy sequence unchanged: `git fetch origin && git reset --hard origin/master` then `npx vercel --prod --force`, always from CMD, never PowerShell

## NEXT SESSION START PROTOCOL
1. New PAT: SAIRN-Session59 | Fine-grained | SAIRN1/SAIRN | Contents R/W
2. Fetch sairnvet.html via git tree/blob (commit f861a61547b9dcbda065d97bcddd96c933b3a425), confirm 376,984 bytes / 485 drugs / 465 diagnoses / 54 panels before believing anything else in this handoff
3. Confirm master branch, not main — check this explicitly every time now, it's Guardian check #26
4. Continue the panel-by-panel audit starting with panel-ai, one panel per checkpoint, Guardian scan + push + independent GitHub re-verify after each — this pacing is deliberate, not a shortcut being skipped
5. Before touching the SAIRNbiz bridge: check Vercel dashboard Functions tab and local `dir api` for whether `api/bridge.js` exists anywhere
