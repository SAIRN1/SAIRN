# SAIRN Open Work Index

**One place to see everything that is open across the whole platform.**
Last rebuilt: **2026-08-23**. Last updated: **2026-08-24** (handoff-reading pass + California service extensions).

Before this file existed, open work lived in `SAIRN-BACKLOG.md`, in
`SAIRN-ACTIVE-WORK.md`, in ~40 per-app handoffs, and in skill files — so real
items got missed and sessions sat idle while work existed. This is the index.
It does not replace those files; each row points back at the source of truth.

**Note, 2026-08-24:** `SAIRN-ACTIVE-WORK.md` was split per session to stop the
recurring merge conflicts. Its historical entries are still there (unchanged),
but new active-work entries go in `SAIRN-ACTIVE-WORK-hank.md`,
`SAIRN-ACTIVE-WORK-cc.md`, `SAIRN-ACTIVE-WORK-cody.md`, and
`SAIRN-ACTIVE-WORK-fourth.md` (one per clone). **The next rebuild of this index
must read all four, not just the shared file.**

---

## How to use this in 30 seconds

1. Filter by **Owner** — `unassigned` rows are the ones a free session can take.
2. Skip anything whose **Blocked by** is not empty unless you can clear the block.
3. Do what **Next action** says. If it says *verify*, the row's status is a claim
   that has not been re-checked; verify before building on it.

**Every row is a claim, not a fact.** Same standard as a handoff: re-verify
before you act on one. Rows marked ⚠️ are ones this rebuild could not confirm.

---

## Open items

Legend — **Sz**: S = under a session, M = one session, L = multi-session.

| App | Item | Status | Owner | Blocked by | Next action | Sz |
|---|---|---|---|---|---|---|
| **SAIRNbuild** | Zero server-side backup for any real business data | Open | unassigned | — | Scope the resource set, then add to `api/sd-data.js` allowlist + schema. Largest single item in the backlog | L |
| **Platform** | No app clears local data on a license/device re-key; storage keys are not license-scoped | Open | unassigned | — | Decide scope (all 13 apps or lead app first), then namespace keys by license hash | L |
| **Platform** | No delete capability via `api/sd-data.js` **except** the 28-resource `SC_RESOURCES` (SAIRNcode) family | Open — **row corrected 2026-08-24** | unassigned | — | The old wording said "for any resource, any app", which is wrong: `delete` IS implemented and gated for `SC_RESOURCES`, so there is a working pattern to copy rather than a design to invent. Found while trying to clean up a verification probe from `dnt_appointments`. Decide soft- vs hard-delete, then widen the gate — note the gate and the handler branch are separate, and registering one without the other yields an unreachable 400 (`api/sd-data.js` says so in its own comment) | M |
| **SAIRNlaw** | AI Chain of Custody gap 2: `matter_id` is an unvalidated localStorage id | Open (gap 1 closed) | unassigned | `law_matters` must be server-backed first | Blocked — do the SAIRNlaw server-sync item first | M |
| **SAIRNlaw** | `law_check_and_insert_disbursement` can return a null row on a cross-client `trusttx_id` collision | Open ⚠️ | unassigned | — | The idempotency lookup keys on `(license_hash, trusttx_id)` and does **not** filter by client. Verify a cross-client collision reproduces, then add the client predicate | S |
| **SAIRNlaw** | `ai_list` derived-status window can go stale at high license-wide volume | Open (accepted nit) | unassigned | — | Per-license row-count or per-entry status query. Fails safe toward `Unreviewed`, never fabricates a status | S |
| **SAIRNlaw** | Illinois holiday list: statute (205 ILCS 630/17) vs court-observed (M.R. 5272) disagree both ways | Open — legal judgment | **Michael** | Needs a lawyer's read | Confirm the statutory list is the right basis for 5 ILCS 70/1.11. Encoded that way; changes real dates (Good Friday, Pulaski Day) | S |
| **SAIRNlaw** | Deadline engine coverage: 11 jurisdictions (federal + 10 states), 119 rules | **Batch 2 complete — awaiting Michael's direction** | **Michael** | — | **Batch 1: IL ✅ FL ✅ CA ✅. Batch 2: TX ✅ (`cc6899b`, 10), NY ✅ (`18e41a4`, 10), GA ✅ (`c656135`, 12).** Nothing is in flight. The next decision is Michael's: more states, a third domain (family/probate/criminal), or an Ohio-neighbour track. **Note the external-facing claim doc (`docs/sairnlaw-deadline-engine-external-claim.md`) is now four phases stale** — it still describes five jurisdictions and 64 rules. Re-run `sairn-decision-gate` and rewrite it before any coverage claim goes outside the team | L |
| **SAIRNlaw** | `later_of` multi-trigger cannot express "later of two COMPUTED PERIODS" — only "later of two supplied dates" | Open — **capability gap, one real rule already hit it** | unassigned | — | Found seeding Georgia 2026-08-24, by working the arithmetic by hand rather than by a test. `resolveTrigger()` picks between supplied trigger DATES and then applies ONE `count` to the winner. O.C.G.A. 9-11-36(a)(2) needs a **different count per limb** — 30 days after the request, 45 days after service of process, whichever is later. Encoded as a `later_of` row it returned **2026-07-20 where the statute requires 2026-08-04 — 15 days early, on a self-executing admission**, which forfeits the matter. Fixed for Georgia by decomposing into two rows (a 30-day deadline and a 45-day floor) that the engine computes separately and explicitly does not combine — the California Rule 8.104 treatment, inverted. **This is the same underlying gap already named for CPLR 5513(c), Tex. R. App. P. 26.1(d), Ohio App.R. 4(B)(1) and FRCP 15(a)(3)**, which are all currently refused rather than decomposed. Next action: decide whether to add a `resolve_periods` shape (each limb carrying its own count, engine takes the later/earlier) — that would close all five at once and convert four standing refusals into real dates. Until then, **audit any existing `later_of` row for whether its limbs share a count**; only the federal ones do | M |
| **SAIRNlaw** | Georgia holiday calendar is a FROZEN 2022 federal snapshot — must not be regenerated from a live federal list | Open (standing caution on the `ga` calendars) | unassigned | — | O.C.G.A. 1-4-1(a)(1) adopts "All days which have been designated **as of January 1, 2022**, as public and legal holidays by the federal government". It is a snapshot, not a live reference: a federal holiday created after that date does **not** reach Georgia through this subsection. The `ga` calendars are the eleven days in force on that date (Juneteenth included — designated June 2021). **Anyone regenerating them from a current federal list will silently add days Georgia has not adopted, pushing real deadlines LATER.** Disclosed in `sql/sairnlaw_deadline_calendars_georgia.json`. Related and not modelled: 1-4-1(a)(2) gubernatorial proclamations, which unlike the equivalent limbs in IL/IN/FL/CA/TX/NY are **guaranteed to exist every year** — the subsection requires the Governor to designate at least one of Jan 19, Apr 26 or Jun 3 or a date in lieu, so a Georgia date is correct only absent a proclamation and at least one such day always exists | S |
| **SAIRNlaw** | Service-extension SEQUENCING must be read per rule — two of three states checked did not follow the federal order | Open (pattern, watch on every new jurisdiction) | **Hank** | — | Found 2026-08-24 by a failing New York test, then fixed in Texas (`04455a5`) where it had already shipped wrong. **Georgia (`c656135`) confirmed the pattern a third time** — O.C.G.A. 9-11-6(e) also says "added to the prescribed period", and it was read up front rather than caught by a test. Final tally for the batch: **3 of 4 states lengthen the period; only Florida follows the FRCP after-expiry order.** FRCP 6(d) and Fla. 2.514(b) say days are added *"after the period would otherwise expire"* — roll, add, roll again. CPLR 2103(b)(2) and Tex. R. Civ. P. 21a(c) instead say the days are added *"to the prescribed period"* — one period, one rollover at its end. The difference was **3 days and always in the LATE direction**, which is the direction that misses a filing. Every standard now declares `sequence` explicitly and none is left on the default. **Next action is a habit, not a task:** when seeding any new jurisdiction, read the service-extension rule's own words for expiry-vs-period language before assuming the federal order — and re-read `ca_ccp_1013_1010_6`, which is declared `roll_then_add_then_roll` to preserve shipped behaviour but was **not** re-verified against CCP 1013's actual wording during the New York work | S |
| **SAIRNlaw** | Deadline engine cannot version a rule by the date the CASE WAS FILED, only by the date the period runs from | Open — **structural limit, disclosed not fixed** | unassigned | Needs a schema decision, not a patch | Found seeding Texas 2026-08-24. Tex. Sup. Ct. Misc. Docket No. 20-9153 amended TRCP 47, 99, 169, 190, 192–198 effective 2021-01-01 but keys applicability to filing: *"The amendments apply to cases filed on or after January 1, 2021 ... The rules amended by this Order continue to govern procedures and limitations in cases filed before January 1, 2021."* `computeDeadline()` selects a version with `effective_from <= <date the period runs from>`, and there is no `case_filed_on` input. **So a Texas case filed in late 2020 whose service or discovery happened in 2021 silently gets the post-2021 row — the wrong version, with no refusal.** Not Texas-specific: any jurisdiction whose amendment order keys to filing rather than to the trigger has the same hole, and none of the other 8 were checked for it. Next action: audit the other 8 jurisdictions' amendment orders for filing-date keying, then decide whether to add an optional `case_filed_on` that narrows rule selection and refuses when it is absent but a filing-keyed rule is in scope. Disclosed in `sql/sairnlaw_deadline_seed_texas.json` readme | M |
| **SAIRNlaw** | Deadline engine accepts a trigger date as given even where the law makes that date itself a COMPUTED one — no validation, no warning in the returned date | Open — **highest-consequence input gap in the engine** ⚠️ | unassigned | — | Found seeding New York 2026-08-24; flagged in the seed readmes but it is not a New York problem. `computeDeadline()` never validates what a trigger date means — it counts from whatever it is handed. **Sharpest instance: CPLR 308.** Both `ny-cplr-320a-appearance-30-service-complete` and `ny-cplr-3012c-answer-30-service-complete` run 30 days from when *"service is complete"*, and for CPLR 308(2) leave-and-mail and 308(4) affix-and-mail that is a computed date — a fixed number of days after proof of service is **filed**, often more than a week after delivery. CPLR 308 was deliberately not read verbatim for that seed, so no completion arithmetic is encoded and none is guessed. **A user supplying the delivery date gets a deadline that is too early; supplying the filing date gets one that is too early by a different amount. Neither draws a refusal.** The same class already spans the engine: Florida's `rendition` (a term of art, not the signature or mailing date), California's Rule 8.104 service-of-notice-of-entry limbs, Texas's `signing of the judgment`, New York's `service ... with written notice of its entry`. Four jurisdictions now start an appeal clock four different ways and nothing stops a caller conflating them. Next action: decide between (a) encoding CPLR 308's completion arithmetic as a real computation so the engine derives it, and (b) a `trigger_requires_derivation` flag on such rows that makes the endpoint surface a named warning alongside the date rather than returning a bare one. (b) is cheaper and covers all four jurisdictions; (a) only fixes New York. Do **not** close this by adding prose to the seed notes — those are already there and are invisible at the point the date is read | M |
| **SAIRNlaw** | Two deadline-rule authorities rest on secondary sources, recorded rather than silently trusted | Open (accepted, documented) | unassigned | — | Both found seeding Texas 2026-08-24 and both are **disclosed in the seed/calendar readmes**; neither is load-bearing, which is why they are accepted rather than blocking. **(1) Proctor v. Green, 673 S.W.2d 390 (Tex. App.—Houston [1st Dist.] 1984)** — CourtListener confirms case, court, docket `01-84-73-CV`, date and citation but serves no accessible full text, and Leagle/vLex refused automated access; the holding and its worked dates come from a legal database's rendering, not a primary source read this session. The rule row cites **Tex. R. Civ. P. 99(b)**, not the case, and the same result follows from the rule's own words, so nothing computes off it. **(2) Tex. R. Civ. P. 4 and Tex. R. App. P. 4.1 both say "legal holiday" without defining it and without citing Tex. Gov't Code 662.021** — the link to 662.021 (which is what the `tx` calendars encode) is the settled reading, not an express cross-reference, and was not found stated in either rule's text. Next action: if a lawyer's read is ever commissioned for the Illinois holiday row above, add both of these to the same question set | S |
| **SAIRNlaw** | Court e-filing: readiness check built, transmission not possible | Closed as scoped | — | EFSP certification is a contract, not code | Nothing to build. Revisit only if an EFSP relationship is pursued | — |
| **StoneDesk** | ~28 `sdDemoCleared() ? [] : SEED` fallback sites unaudited (Slabs fixed in `501d15b`) | Open ⚠️ | unassigned | — | Count is `grep -c` measured, not authoritative — Guardian's note says 29 constants / 56 sites. **Re-count precisely first**, then apply the two-part test per site | L |
| **StoneDesk** | Procedural stone texture likely inflates `canvas.toDataURL()` PNG snapshots against an existing quota risk | Open | unassigned | — | Measure a real textured snapshot's byte size before changing anything | M |
| **StoneDesk** | Saved-quote Load: overwrite confirm fires on a merely-opened Drawing Tool tab | Open | unassigned | — | Gate the confirm on actual unsaved drawing state | S |
| **StoneDesk** | `dcMode` doesn't reset to `preset` on a same-session Custom-Draw-then-preset quote Load | Open | unassigned | — | Reset `dcMode` in the Load path | S |
| **StoneDesk** | Stone-texture visualization — accepted cosmetic nits | Open (accepted) | unassigned | — | None unless a client raises one | S |
| **SAIRNbiz** | AP "Pay" button doesn't mark anything paid | Open | unassigned | — | Real status write + server sync | M |
| **SAIRNbiz** | No way to update a training cert's status at all | Open | unassigned | — | Add status transition + persistence | M |
| **SAIRNbiz** | Budget "actual" spend never syncs with recorded expenses | Open | unassigned | — | Derive actuals from the expense store rather than a separate field | M |
| **SAIRNbiz** | Payroll runs are never recorded anywhere | Open | unassigned | — | Persist a payroll-run record | M |
| **SAIRNbiz** | Benefits panel has no way to enroll anyone | Open | unassigned | — | Enrollment write path | M |
| **SAIRNdental** | Real-sync sweep can silently exhaust localStorage once photo-bearing bookings accumulate | Open | unassigned | — | Quota guard + honest failure. Silent-failure class — treat as higher priority than its size suggests | M |
| **SAIRNdental** | `public-book.js` returns a generic 502 on a real slot race instead of 409 `SLOT_TAKEN`, and orphans a patient record | Open | unassigned | — | Distinguish the race, return 409, clean up the orphan | M |
| **SAIRNdental** | Pediatric guardian fields: `onPtDobChange()` not called at page init | Open | unassigned | — | Call it on init | S |
| **SAIRNdental** | Per-patient photo history panel | Open (feature) | unassigned | — | Scope before building | M |
| **SAIRNdental** | Vendor/supply ordering — deferred whole-branch-review items | Open | unassigned | — | Re-read the review list, triage | M |
| **Tooling** | Rebuild graphify's knowledge graph, properly scoped | Open | unassigned | — | Decide scope first; the last attempt was unscoped | M |
| **Platform** | `C:\Users\marsh\` is itself a working-tree checkout of the repo, 33+ commits behind | Open | **Michael** | Needs repo/clone-setup owner | Retire it as a checkout. Complication: it is also the user-level skill store, so the store must move too | M |
| **Platform** | `api/sd-data.js` returns all 171 resource names to any caller with a junk bearer token | Open — minor disclosure, **deliberately not fixed** | unassigned | Needs an auth-ordering decision, not a patch | **Verified live 2026-08-24**, no credential used: `POST /api/sd-data` with `Authorization: Bearer not-a-real-key` and an unknown resource returns 400 listing every registered resource, because the resource gate (`sd-data.js:190`) runs *before* license validation (`:221`). Low severity — names only, no data, and every path past the gate still 401s. Moving license validation above the gate changes the first-failure response for **every app**, so it needs a deliberate call and the same baseline-replay proof as the verb-gate change, not a quick reorder. Note it also makes that baseline capturable without credentials, which is a real testing benefit to weigh against fixing it | M |
| **Platform** | `service_role` holds TRUNCATE/REFERENCES/TRIGGER/MAINTAIN (Postgres default ACL, confirmed live via `pg_default_acl`) on full-CRUD tables **beyond** the append-only-by-design set already fixed in `sql/append_only_grant_audit.sql` | **Diagnosed, draft fix written, not run** | unassigned | — | `sql/full_crud_truncate_sweep_2026-08-24.sql`: Section 1 is the real list-free discovery query (`information_schema`, not a hand-built table list); Section 2 is a DO-block draft fix that reads each table's own current SELECT/INSERT/UPDATE/DELETE grants and re-asserts exactly that set, so it cannot add or remove functional capability, only strip the unused TRUNCATE/REFERENCES/TRIGGER/MAINTAIN baseline. 151 of 158 granted tables (counted, not estimated) lack the sound `revoke all` pattern and are code-level candidates; Section 1 confirms which ones actually carry it live. StoneDesk slabs (`sd_slabs`/`sd_blocks`/`sd_bundles`/`sd_slab_history`) and sampled SAIRNgrounds/MSB tables checked directly in `api/sd-data.js`, not assumed from this row's own earlier wording: all genuinely use UPDATE (real `on_conflict` upserts), none ever get a DELETE (platform-wide, exactly one `method: 'DELETE'` call exists anywhere in that file, and it's the SC_RESOURCES/SAIRNcode branch). Separate finding, deliberately not bundled into the fix: most full-CRUD tables are granted DELETE at the DB level with no live code path that ever uses it — narrowing that would be a real functional-capability decision, not a strip-the-unused-default fix, and needs its own review | L |
| **SAIRNlaw** | `CANLII_API_KEY` | **Closed** | — | — | No longer a blocker — Canada is out of scope and the code is deleted | — |

### Added by the handoff-reading pass, 2026-08-24

Everything below came out of the ~40 per-app handoffs and was **re-verified
against current code before being listed** — several handoff claims turned out
to be stale, and those are in *Contradictions* rather than here.

| App | Item | Status | Owner | Blocked by | Next action | Sz |
|---|---|---|---|---|---|---|
| **SAIRNdental** | `dnt_appointments` still carries a DB-level 64 KB `CHECK` (`dntap_data_size`) while photo capture ships ~900 KB per booking | **Open — live risk** ⚠️ | unassigned | — | **Verified still present** at `sql/sairndental_data_schema.sql:80`, `octet_length(data::text) <= 65536`. SAIRN-PLATFORM-SESSION3 called this "the single most important thing to pick up next, before this reaches a real practice" and the migration was never written. Confirm empirically whether the constraint bites on the live table, then raise it — do not degrade photo quality to fit it | M |
| **SAIRNcare** | Resend sending domain `sairn.com` is not verified — alert emails are refused `403` | **Open — outage** | **Michael** | Needs DNS access at resend.com/domains | Verify `sairn.com`, or point `RESEND_FROM_EMAIL` at an already-verified sender. Affects **every** Resend sender on this project. Confirm via the hourly `/api/alf-alerts` log: the `403` line disappearing while the test facility still has a late dose. **Do not read a bare 200 as success** | S |
| **SAIRNcare** | PA ALR: "max 2 residents per living unit" and the cognitive pre-admission screening window unverified | Open | unassigned | Needs a primary Ch. 2800 source | Encode only from a positive source. **Do not carry the PCH equivalents across** — those are confirmed, ALR's are not, and substituting is the exact error the handoff flags | S |
| **SAIRNcare** | PCH "no RN or dietitian required" recorded as unverified, deliberately | Open (accepted) | unassigned | — | Asserting a negative from an absence in one chapter is a compliance claim. Needs a positive source or it stays unencoded | S |
| **SAIRNcare** | `ALF_PHARMACY_SECRET` is set and `api/alf-pharmacy.js` is live, but no real pharmacy is connected | Open | unassigned | Needs a pharmacy partner | Nothing to build until there is one to integrate with | M |
| **SAIRNvet** | 20 panels never audited | Open | unassigned | — | Panels confirmed to exist. Start with `panel-staff`. Money-touching panels are all done; these are clinical/operational, so watch for fake success toasts and non-functional buttons rather than dollar fabrication | L |
| **StoneDesk** | 163 missing DOM targets, never triaged | Open ⚠️ | unassigned | — | **Re-measured: 163 of 1,425 distinct targets, not the 184 the handoff recorded.** Pre-existing baseline, never individually traced. Triage by hand | L |
| **StoneDesk** | `panel-remnant` double-render: `sdRemnantRender()` and `remRender()` both live, two containers | Open | unassigned | — | **Verified still real.** Search/filter inputs call only `remRender()`, so typing updates the grid and leaves the table stale | M |
| **StoneDesk** | Two parallel template modules with different storage keys | Open | unassigned | — | **Verified still real** — `sd_templates` and `sd_template_records` both present. Check which one `panel-templates` actually renders from **before** merging; the wrong direction silently orphans real user data | M |
| **StoneDesk** | 2 `stonedesk-demo` license fallback sites, each its own expression | Open | unassigned | — | Was 3, now 2. Collapse into one shared helper so they cannot diverge from `sdData()`'s identity resolution | S |
| **StoneDesk** | Chamfer setback input does not live-refresh when a run is shrunk after typing | Open (display only) | unassigned | — | Pricing and the cut sheet read the live-clamped value, so this is staleness, not a money bug | S |
| **StoneDesk** | Three drawing-tool feature gaps: no 45° corner angle-snap; raised bar cannot combine with L/U-shape; canvas fixed at 480px | Open | unassigned | — | All three re-confirmed in Session 79 and untouched since. Missing precision features, not paths to a bad cut | M |
| **StoneDesk** | Worktree branch `worktree-stonedesk-chamfered-corners` is five features past its name | Open | unassigned | — | Carried unactioned from Sessions 81–84. Rename or retire | S |
| **StoneDesk** | Dormant `custAddNew()`/`custSave()` form missing the `rating` field | Open (quarantined) | unassigned | — | Quarantined by explicit direction 2026-07-28. If anyone wires a button to it, it creates records missing `rating` | S |
| **StoneDesk** | Four `safety*` render functions have no containers and no callers | Open (accepted gap) | unassigned | — | Real feature-completion work (3–4 UI sections + nav), not a mechanical fix. Accepted by explicit direction 2026-07-28 | M |
| **StoneDesk** | `#rm-causes` permanently empty since the old IIFE render was removed | Open (cosmetic) | unassigned | — | No crash, no data risk | S |
| **StoneDesk** | ~40 lower-frequency `sd_*`/`sh_*` storage keys never traced for the two-system collision pattern | Open | unassigned | — | The pattern was real for `sd_customers`, `sd_inventory`, `sd_remakes`. Trace the rest | L |
| **SAIRNbiz** | `syncEmps()` — payload reshaped (`16fbb31`), but blockers 2 and 3 not confirmed closed | Open ⚠️ | unassigned | Needs live Supabase | **Could not verify from code** — needs a real round-trip against the live project. Re-read SAIRNBIZ-SESSION1 §4 before assuming the fix landed | M |
| **SAIRNbuild** | AI Budget Early Warning: `f072765` fixed 5 review findings and was never independently re-reviewed | Open | unassigned | — | Self-review only. A genuinely separate pass before calling it done | S |
| **SAIRNbuild** | Never live-verified against `sairn.vercel.app/sairnbuild` | Open | unassigned | — | `git push` succeeded; no curl or browser check was ever run for that feature | S |
| **SAIRNdental** | Vendor ordering never live-browser verified | Open | unassigned | — | Every check was a hand-traced code walkthrough. The handoff calls a real browser session the single highest-value next step | M |
| **SAIRNdental** | SDD workspace and `worktree-sairndental-vendor-ordering` never cleaned up | Open | unassigned | — | Commits are already fast-forwarded onto `main`; only the branch and workspace remain | S |
| **StoneDesk** | Several SDD workspaces under `.superpowers/sdd/` never cleaned up | Open | unassigned | — | Carried across Sessions 80, 83, 84 | S |
| **Platform** | No redaction check before writing a handoff or any file | Open | unassigned | — | The `sairn-session-handoff` skill calls for one; no hook exists. A real GitHub PAT was involved in a prior session | S |
| **Platform** | `core.autocrlf` produces false-positive deploy-mismatch hook fires | Open | unassigned | — | Set `core.autocrlf=false` or `input` for this repo, so a real stuck-webhook incident is not misdiagnosed as line endings — or vice versa | S |
| **Platform** | `.agents/` untracked pile at repo root, never examined | Open | unassigned | — | Very likely tool/plugin cache, not SAIRN content. Confirm what wrote it before `.gitignore`-ing or deleting | S |
| **SAIRNcash** | Stripe not configured — `api/sairncash/checkout.js` returns `{"error":"Stripe not configured"}` | Open | **Michael** | Needs `STRIPE_SECRET_KEY` / `STRIPE_PRICE_ID` in Vercel | Expected, not a bug — Stripe setup was planned separately. Blocks the estimator panel's final live-subscriber regression test | S |

---

## Contradictions found by the handoff-reading pass

Flagged, **not silently resolved**, per instruction. Each was re-verified
against current code or git before being called stale.

| Claim | Where | What is actually true now |
|---|---|---|
| "`main` is 47 commits behind `master`" — carried as an unresolved gap across SAIRNvet Sessions 60, 61 and 62 | SAIRNVET-SESSION60/61/62 | **Inverted.** `origin/main` is **1,142 commits AHEAD** of `origin/master`; master is 1 ahead of main. `master` is the stale branch, which is what `CLAUDE.md` says. The handoff series repeated a wrong claim three times. Nothing to merge or re-point |
| "Guardian v2 skill file found at 25 checks despite being logged as 33" | SAIRNVET-SESSION59, carried to 60/61/62 | **Resolved.** The skill now declares 28 numbered checks and carries 34 numbered entries. Neither 25 nor 33 |
| "`div_balance_check.py`'s pre-existing `DIFF:-4` / line 5092 underflow on StoneDesk" | STONEDESK-SESSION78 | **Resolved.** `stonedesk.html` now measures 4,747 open / 4,747 close, `DIFF:0`, PASS |
| "184 missing DOM targets on StoneDesk" | STONEDESK-SESSION78 | **Still open but the number is wrong** — re-measured at **163** of 1,425 distinct targets |
| "3 `stonedesk-demo` fallback sites" | STONEDESK-SESSION77 §4.2 | **Still open, now 2.** Reduced but not eliminated |
| "Resend vars not reaching Production — Michael action item, not a code fix" | SAIRNCARE-SESSION2 §5.1 | **Diagnosis was wrong**, and the later SAIRNcare handoff says so itself: the real cause was a code-side name mismatch (`RESEND_FROM_ADDRESS` vs `RESEND_FROM_EMAIL`), now fixed for SAIRNcare. A *second*, separate problem — the unverified sending domain — is what remains, and that one genuinely is Michael-only |
| "Two colour collisions: SAIRNhr/SAIRNvet `#7C3AED`, SAIRNcare/SAIRNacc `#0D9488`" | SAIRN-SESSION68 §4.4 | **Moot.** Guardian's App File Map removed SAIRNhr and SAIRNacc on 2026-08-13 as speculative entries that were never real apps, which resolves both collisions by elimination |
| "No delete capability via `api/sd-data.js` for **any** resource, any app" | This index's own row, carried from `SAIRN-BACKLOG.md` | **Overstated.** `delete` is implemented and gated for the 28-resource `SC_RESOURCES` family (`sc_denial`, `sc_claims`, `sc_settings`, …). It is genuinely absent everywhere else — `dnt_appointments` included, which is how this surfaced. The row is corrected above rather than left to imply the work starts from nothing |

---

## Recently closed (kept briefly so nobody re-opens them)

| App | Item | Closed | Evidence |
|---|---|---|---|
| SAIRNlaw | Trust disbursement cross-device atomic check | 2026-08-17/18 | `law_check_and_insert_disbursement` live in `api/sd-data.js` + `sql/sairnlaw_trust_disbursement_atomic_check.sql`; 4 `law_` resources in the allowlist. **`SAIRN-BACKLOG.md` still lists this as open — that entry is stale.** |
| SAIRNlaw | Void-of-deposit could retroactively negative a client balance | 2026-08-17/18 | `law_check_and_void_deposit`, browser-verified |
| SAIRNlaw | CanLII / Canada coverage | 2026-08-23 | `b747ecb` — deleted, live-verified |
| SAIRNlaw | Orphaned `public.canlii_rate_limit_log` table | 2026-08-24 | Dropped by Michael. Was flagged for the schema owner because dropping a table on a shared DB is not a session's call — that routing worked as intended |
| SAIRNlaw | Deadline engine: Florida | 2026-08-23 | `78af333` — 47/47 isolation + live-loaded. Needed a real engine change (`shifted_start`), contrary to the plan |
| SAIRNlaw | Deadline engine: California | 2026-08-24 | 52/52 isolation + live-loaded. Two computation standards, statutory vs rules-of-court |
| SAIRNlaw | California service extensions (CCP 1013, 1010.6) | 2026-08-24 | Read verbatim and encoded. Per-method amounts: 5/10/12/20 calendar days for mail by location, 2 **court** days for overnight, fax and electronic. Appellate rows carry none — both sections exclude a notice of appeal in terms. 84/84 |
| Index | Handoff-reading pass over all 46 handoff files | 2026-08-24 | 28 new rows added, 7 stale claims caught and listed under Contradictions |
| SAIRNdental | `send-reminder.js` read the non-existent `RESEND_FROM_ADDRESS` | 2026-08-24 | **Fixed by another session after this index flagged it** — now reads `RESEND_FROM_EMAIL` at lines 46 and 98, with a regression test asserting the name. The index row saying "verified still broken at lines 37 and 75" was true when written and went stale within hours. Guardian Check 30 now catches this class mechanically |
| SAIRNlaw | Court e-filing (Ohio-first) | 2026-08-23 | `a183a07` — readiness check; transmission scoped out with reasons |
| SAIRNlaw | Deadline engine: Illinois | 2026-08-23 | `b8250a2`, 39/39 isolation + live-loaded |
| SAIRNdesign | Invoicing server-side uniqueness constraint | 2026-08-10 | Backlog marked resolved |
| SAIRNlegacy | Merchandise reservation server-side lock | 2026-08-10 | Backlog marked resolved |
| StoneDesk | Saved quote history didn't capture drawing-tool state | 2026-08-13 | Backlog marked resolved |
| StoneDesk | `SD-AUDIT-2026` credential blocker | 2026-08-23 | CC — fixed and verified |
| Guardian | `vercel_config_check` false 404s, `nav_panel_check` conventions, dead Check 23 | 2026-08-23 | `158999f` — 12/12 apps pass |

---

## What this index does NOT cover, stated so the gap is known

- **Per-app handoffs were not read line by line.** Rows come from
  `SAIRN-BACKLOG.md` (section-by-section), `SAIRN-ACTIVE-WORK.md`, and work
  done in-session on 2026-08-23. There are ~40 handoff files; an item that
  exists **only** inside one and never reached the backlog is not here yet.
  That is the first thing to improve on the next rebuild.
- **Sizing is judgment, not estimation.** S/M/L is a rough shape, not a
  commitment.
- **Owners are observed, not assigned.** `unassigned` means no session has
  claimed it in the active-work log (`SAIRN-ACTIVE-WORK.md` at rebuild time;
  now the three per-session files) — not that it is unimportant. Rows
  owned by **Michael** need a decision or an access level a session does not
  have.
- **⚠️ rows carry a number or claim this rebuild could not confirm.** They say
  so in Next action.

---

## Keeping it alive

This file rots the moment it stops being updated, and a stale index is worse
than none — it makes work look handled when it is not.

1. **When you close something, move the row** to *Recently closed* with the
   commit SHA. Do not delete it silently.
2. **When you find something new, add a row** in the same action as logging it
   in `SAIRN-BACKLOG.md`. Two places, one action, or they diverge.
3. **Re-derive, don't trust.** Before a planning decision, spot-check the rows
   you are about to rely on. This rebuild found one stale backlog entry
   (SAIRNlaw trust disbursement, listed open, actually shipped) out of 26 —
   assume a similar rate next time.
4. **Do not renumber or restructure the backlog to match this file.** The
   backlog is the detailed record; this is the index over it.
