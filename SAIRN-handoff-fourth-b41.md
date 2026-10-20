# HANDOFF — fourth / ted, batch b41, 2026-10-20

**READ THIS FILE ONLY.** It is the whole state. **6 of 6 DONE**, all on
`origin/main`, no force, no override of any form. Wrapped at **~36% real
context** (`tools/context_verify.py --digest-line`), well inside the 85% rule.

**EVERY FIGURE NAMES THE COMMAND OR FILE THAT PRODUCED IT. Re-derive anything
you mean to quote, including out of this file.**

**FOUR THINGS TO READ FIRST:**

1. **The audit's own B1 named the wrong label.** sairndesign's composite-wood
   block records the **§ 770.45(c)(2) finished-good label** (fabricator,
   month/year, "TSCA Title VI compliant"), not the § 770.45(a) panel fields
   b39 specified. Re-read from the CFR text. §3.
2. **b40's credential-board mitigation never reached first paint, and b40's
   comment said it did.** On a revisit the panel showed the PREVIOUS attempt's
   FORBIDDEN "sign in again" while a request that would succeed was in
   flight. Closed with a pending state. §4.
3. **B1's own (B)(2)(iv) was false**: "every suggestion enters a human-review
   queue" — cleared items are `auto_assigned` and reach no coder. Corrected in
   place; it is the AI Act Art. 14(4)(b) automation-bias case. §6.
4. **SAIRNbiz invoice and employee ids are the last 4 digits of
   `Date.now()`** — neither sequential (VAT Art. 226(2)) nor unique, and the
   invoice id is the GL `source_id`. A defect regardless of jurisdiction,
   **not fixed** (audit-only). §7.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016.jsonl`
(a fresh session, not a continuation of b37–b40's `ea7d41f7-…`)

**Working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016\scratchpad\b41\`
— `drive_design.py` / `drive_dental.py` / `drive_code.py` (**the three drives,
re-runnable**; `live_*.py` are the same against `https://sairn.vercel.app/`),
`fix_design.py` / `fix_dental.py` / `fix_code.py` (count-asserted patches),
`eu_fetch.py` (**CELEX route, 11 instruments**), `rd.py` / `art.py` (article
readers), `add_defect.py`, `nodecheck.py` (Check 0a), and the fetched `*.txt`.

**NO SQL THIS BATCH.** The sairndesign `cert` record rides in the existing
`sdn_specitems.data` jsonb column.

---

## 1. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | **0 ahead, 0 behind** | `git rev-list --left-right --count origin/main...HEAD` |
| b41 commits | `078f3cf3` sairndesign · `2eb738de` sairndental · `6407cc4d` sairncode · `7951d9aa` review advisories · `f7b6845e` register record · `0cb4538e` AMLR + AI Act docs · `8e4cb106` sairnbiz audit | `git log --oneline --author=fx` |
| on origin | **all ancestors** | `git merge-base --is-ancestor <sha> origin/main`, per sha |
| live | **all three pages carry the change** and **the three drives pass against the live origin**: 66/66, 37/37, 27/27 | `tools/sairn_http.py` fetch; `scratchpad/b41/live_*.py` |
| force push / overrides | **NONE** | — |
| manifest | **6 done**, validates | `python tools/batch_manifest.py --check --agent fourth --batch b41` |
| Guardian v2 | **31 checks, no FAIL**, two advisories applied in `7951d9aa`, one left (§9) | subagent run over `078f3cf3` + `2eb738de` |

**ONE EXISTING REGISTER PROBLEM, NOT MINE:** `python tools/defect_register.py
--check` exits 1 on **`ce15ddaa6a3c`** (*"b27(cody): the rt_routes primitive
made reachable…"*) — *neither the commit nor its subject is in this repo*.
**cody's record.** Not touched.

---

## 2. CLAIMS HELD

`fourth` held one claim over `sairndesign.html`, `sairndental.html`,
`sairncode.html`, the four docs, the manifest and the deliverables, negatives
declared for `tier-a-reviews.json` (cc), `api/` (cody), shared `tools/`,
`CLAUDE.md`, `.claude/skills/`, and **`sairnbiz.html` AUDIT-ONLY**.

**`docs/defect-density-register.json` was added mid-batch, and only after it
was free.** At start it was declared by **cc b27**, so it was left out (the
matcher blocked on it). By the time item 2 needed a record, cc had released
and re-claimed for b28 **without** the register; the check came back CLEAR and
the claim was re-issued with it. **Not routed around — waited for.**

**RELEASED IN FULL AT THE END OF THIS BATCH.**

---

## 3. ITEM 1 — sairndesign B1–B3, and CPR / GPSR / REACH

**REPRODUCED:** a seeded spec item had 14 keys and none for compliance; modal
11 inputs; portal 4 cards; `sdnCertState` undefined.

**BUILT** (`saveSpec()` writes `cert`, `sairndesign.html:2062`):

* **B2 predicate** — `sdnUflScope` (§ 1640.3(e)(1)–(3) + § 1640.2(a)'s 25 Jun
  2021 date, reupholstery included) and `sdnCwScope` (§ 770.3 + **§
  770.2(e)(4)**: composite wood made before 1 Jun 2018 is out — the app sells
  vintage). **Unanswered → NOT ESTABLISHED, never n/a, never compliant.**
* **B1 record** — per regime a label state (*not checked / sighted / absent*)
  plus evidence; *sighted* without evidence (or without fabricator / month) is
  **not established** and the reason names what is missing.
* **The vendor + SKU join** copies **product facts only**; label sightings,
  dates and evidence belong to the unit and **never join**.
* **B3** — a Client Portal card quoting the § 1640.4(b) statement or the §
  770.45(c)(2) line, **denominator on screen**, evidence notes not shown.

**DRIVEN 66/66** local and live; **mutation control** (undetermined → n/a)
trips. The proposal-approval reservation path mutates spec items in place and
**keeps `cert`** — driven.

**EU limb, from source** — CPR `32024R3110` (applies **8 Jan 2026**, Art. 96),
GPSR `32023R0988` (**13 Dec 2024**, Art. 52), REACH `32006R1907` (**PDF only**;
1 June 2007). **REACH Art. 33(2) is the EU twin of § 770.45's "upon request"**
— a *supplier of an article* (Art. 3(33), distributors included) must give a
consumer SVHC information **within 45 days, free**. GPSR Art. 13(2)–(3):
**substantial modification makes you the manufacturer** — reupholstery. GPSR
Art. 2(2)(i) excludes **antiques**; *vintage is not antique*. CPR Art. 25(3):
display required information **before the contract** — the proposal.
**B6–B8 specified, not built** (audit §6.3).

## 4. ITEM 2 — the credential board's first paint

**REPRODUCED with a delayed stubbed fetch:** first visit painted could-not-run
with `NO_REASON`; **a revisit painted the previous attempt's FORBIDDEN "your
session is not authorised … sign in again" while a request that would SUCCEED
was in flight.** b40's clear-on-entry runs **after** `nav()` painted, so it
never reached this; its comment is corrected in place.

**FIXED:** in flight is a fourth state. `refreshCredentialBoard(paintPending)`
increments a **count** before painting; `rCredentials(null)` renders
*"Checking the credential board…"* with `…` tiles and badge while it is
non-zero. Only `nav()` passes `paintPending`; the background sync refresh
leaves a real board up. Paint and evaluation are both inside `try`, so a throw
cannot leave it stuck.

**DRIVEN 37/37** local and live: ok / 403 / 500 / network each
pending-then-outcome, no-licence, overlap, background, throw. **Mutation
control** (pending branch disabled in a routed copy) trips. **Register record
filed** (`f7b6845e`), severity LOW, method fault-injection, injection
`876bd84c`, `rule: not-citable` with the proposed rule.

## 5. ITEM 3 — sairncode (B)(7), the first measured leaf

**"Citation-rejection rate" was ambiguous between b40 §A2's two figures, so
both are built, side by side** (`scCitationMeasures()` `sairncode.html:7432`,
rendered at `#coded-items-perf` `:880`):

* **coder rejection** = rejected / **decided** — `needs_human_review` and
  `auto_assigned` are in neither side;
* **citation held** = items whose citation is missing or unconfirmed / every
  coded item — **this is the exact property B1 (B)(9) recommended monitoring.**

**One predicate, `scCitationState()` (`:7115`), now feeds the routing and the
measure**, so they cannot drift. `N of M` always; percentage only beside it;
**nothing over zero**. **DRIVEN 27/27** local and live, incl. the live Reject
button; **mutation control** trips. Attached to B1 at (B)(7), detail §A3.

## 6. ITEM 4 — AMLR operative text; AI Act Arts 8–15 + Annex IV

**AMLR — three operative carve-outs, not one, and they differ** (EU doc §6):
**Art. 70(2)** (FIU reporting, has *"before, during or after"*), **Art. 24(4)**
(BO-register discrepancies, same wording, different re-application limit),
**Art. 21(2)** (terminate-or-refrain, **lacks** "before, during or after").
The *"inferred from objective factual circumstances"* clause b40 found in
recital (143) **is operative at 70(2)(c) and 21(2)(c)**. **Art. 70(3) lets
Member States narrow the exemption per transaction type.**

**AI Act — gap map against B1** (artefacts doc §A4). Not binding today (b40's
actor test stands); a map for the payer/public-authority boundary. Headlines:
**Art. 10(6)** — no training data still leaves **testing** data duties; **Art.
14(4)(b)** — the auto-assigned list is the automation-bias case, and **B1's
(B)(2)(iv) was wrong about it** (corrected); Annex IV has **no version, no
model identity, no architecture, no cybersecurity, no signed tests** in B1.

## 7. ITEM 5 — sairnbiz worldwide audit

`docs/cloud-research/sairnbiz-worldwide-competitive-gap-audit-2026-10-20.md`.
**Six instruments + one judgment, all from source:** Pay Transparency
Directive `32023L0970` (**transposition passed 7 June 2026**; **Art. 7 has no
size threshold**), WTD `32003L0088` (PDF) + CJEU **C-55/18**, TPWC
`32019L1152`, VAT Directive `32006L0112` Art. 226, GDPR Arts 9/88.

* **Pay:** no sex field, no equal-value category → Art. 7 cannot be answered.
* **Hours:** six daily totals, **Mon–Sat, no day seven**, no start/end → WTD
  Arts 3/5/6 cannot be evaluated; C-55/18 makes the *recording* the duty.
* **Invoices:** ids are `Date.now()` last-4 → Art. 226(2) and a collision
  defect (1 in 10,000 per pair).
* **OSHA log** is Art. 9 health data; lawful basis is national.

**Z1 (sequential/unique ids) is a defect fix with no blocker — do first.**

## 8. ITEM 6 — the push

Two land loops, **no force**. A register rebase conflict was resolved by
taking upstream's register, skipping my record commit and **re-adding the
record with the tool** — never by staging a conflicted file. The pre-push
reseat rewrote the record's SHA once and was amended in. Then fetched the
three live pages and re-ran all three drives against them.

---

## 9. WHAT IS OPEN — EXACT NEXT STEP PER ITEM

1. **sairnbiz Z1 — invoice/employee ids.** `saveInv()` `sairnbiz.html:2634`
   and `saveEmp()` `:2433`. Reproduce two invoices 10 000 ms apart → same id;
   then a per-series counter for invoices, a collision-checked id for
   employees. **Needs a claim on `sairnbiz.html`** (audit-only this batch).
2. **sairnbiz Z2 — the timesheet's missing seventh day**, then start/end
   times. `saveTimesheet()` `:3427`, modal `:576`. Read 29 CFR Part 778's
   workweek rule first for the US half.
3. **sairncode — the queue line counts `reviewed_rejected` as "cleared every
   check"** (`scRouteCodedItems()` `:7402`, line rendered in
   `renderCodedItems()`). Found while reproducing item 3; not fixed. A
   separate `fix(` with its own record.
4. **sairndental — two edges left open in the record:** `addCredential()`
   calls `rCredentials()` after a local add and replaces a real board with the
   not-checked view; and two overlapping evaluations render in **settle**
   order, so an older answer can overwrite a newer one. **Guardian's A3** too:
   during overlap `rCredRules(null)` / `rEnrollmentRisk(null,0)` still paint
   could-not-run beside a pending table.
5. **sairndesign B6–B8** (REACH Art. 33(2) SVHC + 45-day log; GPSR
   manufacturer identity / antique / modified-by-us; CPR DoPC on the
   proposal) — specified in the audit §6.3. **Also:** the spec CSV export
   (`sairndesign.html:1685`) has no Compliance column (Guardian, out of scope).
6. **One real write of `cert` to the real endpoint, read back** — every drive
   stubbed the server; no licence key was available to this session.
7. **cody: register record `ce15ddaa6a3c`** fails `--check`.
8. **Carried, unchanged:** `hcc`/`drg` server-side (`api/sd-data.js`, cody's);
   b37 items 1+2 (hank's); `mech_schedule`; `rt_routes`; the dental
   clearinghouse decision; sairnmechanical and sairnroofing have **zero**
   audits; the AMLR Member-State 70(3) decisions; consolidated-version checks
   on every EU instrument read.

## 10. PROVED vs LEFT UNPROVEN

**PROVED, driven or measured:** the three code changes, each reproduced
first, each driven with a mutation control that trips, each re-driven against
the live origin; 10 EU instruments and one CJEU judgment fetched by CELEX (REACH and WTD as PDF); the
quoted articles read in full; 0 ahead / 0 behind, all ancestors, no force.

**LEFT UNPROVEN:** no server-side read or write (stubbed throughout); **no
consolidated EU text** (REACH, VAT and WTD are original OJ text); **no national
transposition** of any Directive; no US source read this batch; no legal
review; no screen-reader test.
