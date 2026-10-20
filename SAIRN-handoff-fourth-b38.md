# HANDOFF — fourth / ted, batch b38, 2026-10-20

**READ THIS FILE ONLY.** It is the whole state.

**Written BEFORE the report, at a point where nothing is half-finished.** All
six items' work is on `origin/main`; the only uncommitted files right now are
this handoff, the batch manifest and the two remaining deliverables.

**THE BATCH SPANS A DATE BOUNDARY** — dispatched 2026-10-19, finished
2026-10-20. New docs are dated by the day they were **written**, because a
handoff is found by the date in its filename.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**FOUR THINGS TO READ FIRST:**

1. **6 of 6 DONE.** First full batch in several. b37's items 1 and 2 remain
   **hank's** and were not touched — `stonedesk.html` is in **0** of this
   batch's commits.
2. **THE REGISTER-FEED GATE DENIED THE FIRST PUSH AND IT WAS ANSWERED, NOT
   SKIPPED.** No override of any form was used. §3.
3. **AN ASSERTION STOPPED ME REWRITING FIVE TIER-REGISTER ROWS I HAD NOT
   READ.** The failure is the finding. §5.
4. **THE SAIRNCODE AUDIT INVERTS THE SERIES**: capability with no artefact,
   and the first audit whose main recommendations have no blocker. §6.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\ea7d41f7-de8c-4e21-afd3-fc6d47e335b9.jsonl`
(the same session as b37 — a continuation)

**Working files:**
`…\ea7d41f7-…\scratchpad\b38\` — `fix_constraint_citations.py` (§4),
`fix_tier_cells.py` (§5, with the pipe-count assertions),
`fill_manifest38.py`, `msg.txt` / `trailer.txt` / `newmsg.txt` (§3).

**SQL THIS BATCH: one file EDITED, none created.** `sql/rt_routes_schema.sql`.

---

## 1. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | **0 ahead, 0 behind** | `git rev-list --left-right --count origin/main...HEAD` |
| the b38 commits | **`cc95b740`**, **`232127e0`**, **`033dca64`** | `git log --oneline -3` |
| confirmed on origin | **all three pass `merge-base --is-ancestor`** | per commit |
| **files touched** | **exactly 8** — `sql/rt_routes_schema.sql`, `docs/CRITICALITY-TIERS.md`, `sairnlaw.html`, the two b37 deliverables, and three new docs | `git show --name-only --format=""` |
| **forbidden paths** | **0** — no `api/`, no `tools/`, no `.githooks`, no `settings.json`, **no `.claude/skills/`** | same, piped to `grep -cE` |
| **`sairndental.html`** | **NOT touched** — item 5 was an audit, by instruction | it is absent from the file list |
| uncommitted | this handoff, the manifest, the report, the digest | `git status --porcelain` |
| `git stash` | **0** | `git stash list` |
| **force push** | **NONE.** No `--force`, no `--force-with-lease` | — |
| **overrides** | **NONE, any form.** No `SAIRN_SKIP`, no `gate_skip.py` grant, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SEED_GATE` | — |
| auditor clones | **not entered**; `.claude/skills/` not edited | — |
| b38 manifest | **6 done, 0 blocked**, validates | `batch_manifest.py --check --agent fourth --batch b38` |

**The forbidden-path check is scoped to MY OWN three commits, not a range** —
b35's recorded reason.

---

## 2. CLAIMS HELD

**`fourth` holds ONE claim**, declaring `sql/rt_routes_schema.sql`,
`docs/CRITICALITY-TIERS.md`, `sairnlaw.html`, `sairndental.html`,
`docs/cloud-research/`, the notes docs, the manifest and the three
deliverables — with four negatives declared on purpose:

`NOT-stonedesk-html-hanks-b37-items-1-and-2` ·
`NOT-api-sd-data-js-codys` · `NOT-tools-shared-REPORT-ONLY` ·
`NOT-dot-claude-shared-REPORT-ONLY` · `NOT-docs-tier-a-reviews-json`

**RELEASED IN FULL AT THE END OF THIS BATCH.** Nothing is mid-edit.

**THE CLAIM CHECK BLOCKED AND IT WAS THE b37 SHAPE AGAIN.** `check` refused on
*"same app: sairndental, sairnlaw"* against hank's b23, whose FILES tokens are
literally **`NOT-sairndental-html-fourths`** and **`NOT-sairnlaw-html`** —
hank's own declarations that both files are mine. **Unlike b37, there is no
substantive overlap behind it:** hank's b23 is `api/law-*`,
`sql/sairnlaw_*` and `tools/*_live_probe.py`, and names no dental work at all.
**Re-run with a declared FILES list, the claim went through CLEAR** — which is
the tool's own advice when the file question is otherwise unanswerable.

**`docs/CRITICALITY-TIERS.md` was checked against every claim file before item
2 began, as the dispatch required: cc does NOT hold it.**

---

## 3. THE PUSH — ONE GATE DENIED, AND IT WAS ANSWERED

**`register_feed_gate` blocked the first push:** *"this push closes a defect
and does not feed the register"*, naming the `fix(schema+tiers)` commit.

**I did not add a register record, and the reason is a judgment worth
reviewing rather than inheriting.** Nothing in that commit is a defect in
shipped behaviour:

* **`rtroutes_saved_sane` WAS NEVER RUN.** b36's review found the contradiction
  *before* Michael executed the file and he removed it before executing. **No
  database ever carried it; no write ever failed.** A record would put a fix
  with **no injection commit, no in-service detection and no affected
  behaviour** into a register whose numbers are used to reason about real
  defect density — the dilution its own `not-citable` rule exists to stop.
* The other two changes are **wrong sentences in a standing document** and a
  **stale line number in a comment**. Real, and documentation rather than
  behaviour.

**So the sanctioned `no-defect-record:` trailer was used, with the full
reasoning in the commit's own message.** That required amending a commit two
deep, which meant a history rewrite of **three UNPUSHED commits** via
`git checkout <sha>` → `--amend` → `git rebase --onto`. **Nothing published was
rewritten**, and `git branch -f b38-save` held the originals until it was done.

**A later push was denied by the same gate for a different reason it diagnosed
itself** — 3 ahead / 8 behind, so git would have refused anyway and **no ref
lines reached the hook**; the gate said *"This is NOT a finding about your
commits"* and named the fix. Resolved with `git pull --rebase`.

---

## 4. ITEM 1 — THE SCHEMA NOW MATCHES THE DATABASE

`constraint rtroutes_saved_sane` is gone, replaced by a comment on
`saved_seconds` saying **why there is no non-negative check and not to re-add
one**. Verified structurally rather than by eye: comments stripped, then
**parens 41/41 balanced, 14 statements, 0 `,,`, 0 `,)`**, and the constraint
name **absent from the code while still present in a comment** — a correction
that deletes the history is not a correction.

**THE HEADER NOW RECORDS THAT THE FILE HAS RUN, AND THAT CHANGES WHAT EDITING
IT MEANS.** `create table if not exists` makes a re-run a no-op, so a further
change to a column or key in that file **changes nothing in the database** —
only what a reader believes. Anything else needs an `ALTER` in its own `sql/`
file.

**CONSEQUENCE, REPORTED NOT RE-SCOPED:** that makes cc's composite-foreign-key
recommendation on `rt_stops.license_hash` (`docs/SAIRN-OPEN-WORK-INDEX.md`
line 454) **a migration rather than an edit**. The schema is mine and the
handler is cody's, so it is named here and not changed.

**Scope rule for the citations, stated rather than implied.** Eight files name
the constraint. The **two b37 files were corrected** — they are the current
handoff and digest and both said the SQL was unrun. The **four b36
deliverables and the b36 manifest were left alone** as point-in-time records of
a closed batch. `.claude/claims/fourth.json` is never edited.

---

## 5. ITEM 2 — THREE TIER-REGISTER CORRECTIONS, AND THE ASSERTION THAT EARNED ITS KEEP

Each edit is a unique-substring replace **inside one named row**, with the
pipe count asserted identical before and after. File-wide: **788 lines, 3241
pipes, both unchanged.** `|` was used read-only to identify which line is which
resource — never to rebuild a row.

| row | correction |
|---|---|
| `leg_cremations` | confidentiality grounds rewritten as the **traced chain** they are — the old sentence named a decedent identity, a cause and government identifiers, and **none of the 13 fields at `sairnlegacy.html:3190` carries any of them** |
| `employees` | stopped quoting `saveEmp()`'s **localStorage** shape as *"the stored data blob"*. What ships is `syncEmps()` at `sairnbiz.html:5069-5072` — **nine** fields — so `ec`, `notes` and `pay_freq` were cited as grounds and are not on the row |
| `rf_jobs` | write citation **`:5254` → `:5477`** |

**NEITHER TIER CHANGED.** Both cells were wrong in the direction of
over-claiming, which does not move a tier.

### THE FIRST RUN FAILED AND THAT IS THE FINDING

The `leg_cremations` sentence is **not unique**. The **same sentence sits on
six rows** — `leg_certs`, `leg_cremations`, `leg_custodylog`,
`leg_deathrecords`, `leg_invoices`, `leg_preneed`. **A file-wide replace would
have rewritten five rows whose write sites I have not read**, and
`leg_deathrecords` is precisely the one for which the old sentence is probably
*correct*.

The assertion refused. The edit is row-scoped, a post-check requires the
sibling sentence to still appear **exactly 5 times**, and the corrected cell
**says the five were not re-read and makes no claim about them**. That is
**discipline 7 — byte-identical is not safe-in-context — occurring inside the
register itself.**

**Third part:** the stale `api/sd-data.js:12439` citation at
`sairnlaw.html:3339` is fixed by **replacing the line number with the grep-able
branch predicate**, not with `:18747` — a line number is the thing that went
stale and a second one would go stale the same way. `checkblocks` **4/0**.

**`criticality_tier_check` PROBLEMS 14 → 6** across the batch, **0 new from my
edits**. The drop independently confirms b37's measurement: cc's `shared.js`
fix landed (`APPS_WITH_REGISTRIES` 18 → 19) and **14 − 8 = 6**.

---

## 6. ITEM 3 — SAIRNCODE, AND THE SERIES INVERTS

`docs/cloud-research/sairncode-worldwide-competitive-gap-audit-2026-10-20.md`

**Five primary sources READ IN FULL** — 45 CFR 170.315(b)(11), 42 CFR 422.310,
31 U.S.C. 3729, 45 CFR 92.210, WHO ICD-11. **Two could not be read and are not
paraphrased from memory.**

**THE FINDING IS THE OPPOSITE OF EVERY PRIOR AUDIT: capability with no
artefact.** `sairncode.html:842` already requires every suggested code to
**cite the exact phrase in the note** and **independently verifies that phrase
is present**, flagging any suggestion whose citation cannot be verified —
**stronger than `(b)(11)(iv)(A)` asks for** — with stored citation and
reasoning per coded item, a human-review queue, and a **derived** confidence
after fabricated 82%/71% scores were removed.

**And `grep -ci` over the file:** `RADV` **0** · `False Claims`/`upcod` **0** ·
`Section 1557` **0** · `170.315`/`source attribute` **0** · `first Friday`
**0** · `ICD-11` **0** · `effective date` **0**. **38 panels including `hcc`
and `rac`, and not one of the five rules named.**

**The sharpest single sentence read:** 31 U.S.C. 3729(b)(1) — *"knowing"*
covers **reckless disregard** and **requires no proof of specific intent to
defraud**. That is why the record a coding tool keeps is load-bearing.

**Second sharpest:** 42 CFR 422.310(g) — after the final deadline an
organisation **may only correct overpayments, not submit new diagnoses**. An
HCC tool that surfaces found-gaps and found-errors as the same kind of finding
is wrong about the only direction that still matters.

**FIRST AUDIT IN THE SERIES WHOSE MAIN RECOMMENDATIONS HAVE NO BLOCKER.** B1
and B4 are documents; B3 is two dates. B2 is a **licensing** question (CPT is
AMA-copyrighted) and is flagged as one. B5 (ICD-11) is a **timing judgment** —
WHO reports 132 Member States implementing but only **14** collecting or
reporting.

### What could not be read — §6 of the audit carries the full list

* **Regulation (EU) 2024/1689 (AI Act) — THREE attempts, THREE URL forms, all
  empty bodies.** b37 hit the identical EUR-Lex failure, so this is now
  **characterised and repeated**, and the EU limb of this series is currently
  unsourceable by that route. **No AI Act article, annex point or date is
  asserted anywhere.**
* **The eCFR *web* pages 302 to `unblock.federalregister.gov`, a bot wall.
  NOT routed around** — the documented eCFR **API** is the sanctioned machine
  interface, it answered, and it is what §1 of the audit reads.
* **The 92.210 compliance date** is in neither 92.210 nor 92.10 (which turns
  out to be the *notice* section). **No date is stated.**
* **The current adjusted FCA penalties** live in 28 CFR 85.5, unfetched — only
  the statutory base is given.

---

## 7. ITEMS 4 AND 5 — THE TWO FINDINGS MOST LIKELY TO BE ACTED ON

### 7.1 Currency sweep — four of six rules are not written down

`docs/2026-10-20-fourth-b38-currency-sweep.md`

**Unwritten anywhere a fresh session reads:** the **80% wrap-up threshold**,
the **30-line digest cap**, **SQL-in-files**, and the **done-line format**.
Searched with the patterns across `CLAUDE.md`,
`docs/SAIRN-PROCESS-RULES.md`, `docs/2026-09-13-cross-domain-disciplines.md`
and all 34 skills.

**`sairn-session-handoff` — the one skill whose job this is — has 17 headings
and no section on the digest at all**, and its *"When to write one"* says
*"before capacity runs low"* **with no number**. The 80% figure exists in
writing **on the auditors' side only**.

**My own breaches, measured:** b36 wrapped at **83.5%**; **all 8** of my
digests exceed 30 lines (b36 at **319**); b36's digest **embedded the schema
verbatim**. **Fixed for b38 by construction.** Everything shared is reported
with pasteable text and **not edited**.

### 7.2 SAIRNdental — two compliance panels that cannot tell *clean* from *unchecked*

`docs/2026-10-20-fourth-b38-sairndental-correctness-audit.md`

**The criterion for each panel was written down before its code was read.**

* **GFE** — `issueGfe()` stores `rec.issued_at` and **nothing ever compares it
  to the due date**. Marking an estimate Issued **erases the evidence it was
  late**: a practice three weeks late on every one shows a clean panel and a
  zero tile. Smaller: `due<=today` treats an estimate due *today* as overdue.
* **Credentialing** — four KPI tiles hardcoded `0`, and `rCredentials(null)`
  returns before touching them, so **four zeros render above a table reading
  "Not checked yet"** — permanently, whenever `sdnEvaluateCredentials()`
  returns `null`, which it does on **four silent conditions**.
* **Denials — CLEAN, and it is the control** that makes the other two findings
  real rather than a style preference. Same file, same week, and it keeps all
  three states apart deliberately.

**Neither finding would be caught by a fabrication check** — every figure
traces to a real function. **NOT FIXED: the dispatch said audit.** Both fixes
are a render change with no schema work, and both carry pasteable code.

---

## 8. WHAT IS OPEN — EXACT NEXT STEP PER ITEM

1. **SAIRNdental GFE + credentialing (§7.2).** Apply the two pasteable render
   fixes. **Opens a Tier A review obligation** — record it before pushing.
   Nobody holds `sairndental.html`; hank's b23 declares it mine.
2. **`CLAUDE.md` needs the deliverables section (§7.1).** Pasteable text is in
   the sweep, §5.1. Shared file — somebody has to decide to own it.
3. **`sairn-session-handoff` needs its digest half (§7.1).** Shared skill.
4. **A `--max-lines 30` arm on `tools/drive_upload_verify.py` (§7.1).** The
   cheapest fix for the whole digest class, and it lives in `tools/`.
5. **`rt_stops.license_hash` composite FK (§4)** — now a **migration**, not an
   edit. cc recommended it; cody holds the handler.
6. **SAIRNcode B1 + B3 + B4 (§6).** B1 is a document describing behaviour that
   already ships; B3 is two dates. **Read `170.315(b)(11)` itself before
   building B1** — a field list built from a summary of a field list is the
   staleness class this platform keeps paying for.
7. **Still not mine, still open:** `api/sd-data.js:1352`'s stale `:11690`
   citation (cody's file) and `api/_lib/law-trust-reconcile.js`'s header
   describing `reconcileTrust()` in the present tense when that function no
   longer exists.
8. **b37's items 1 and 2 — hank's**, untouched, fully specified in
   `SAIRN-report-fourth-b37.txt` §1.
9. **Carried:** `mech_schedule`; the `rt_routes` handler branch cody holds,
   which leaves all four wired consumers unreachable at runtime; the dental
   clearinghouse decision; sairnmechanical and sairnroofing still have **zero**
   competitive-gap audits.

---

## 9. WHAT b38 PROVED vs LEFT UNPROVEN

**PROVED, measured or driven:**

* the schema file matches what ran, checked structurally (41/41 parens, 14
  statements, constraint absent from code and present in comment)
* three register cells corrected with pipe counts unchanged file-wide, **0 new
  `criticality_tier_check` problems**, and the 14 → 6 drop reconciling exactly
  with cc's landed fix
* **five primary instruments read in full text**, and two named as unread
* four of six standing rules absent from every document a fresh session reads,
  by pattern search across 3 docs and 34 skills
* three SAIRNdental findings traced to specific lines, with the data that would
  fix them shown to already exist on the record
* 8 files, **0 forbidden paths**, no force, no override, all three commits
  ancestors of `origin/main`

**LEFT UNPROVEN:**

* **Nothing was driven in a browser this batch.** The SAIRNdental findings are
  source reads — **the credentialing one would be settled in a minute by
  blanking the licence key and opening the panel**, and that was not done.
* **No screen-reader test** — unchanged from b36/b37.
* **The five sibling `leg_*` rows were not re-read** (§5) and no claim is made
  about them.
* **The server half of SAIRNcode and of SAIRNdental credentialing was not
  audited** — both live in `api/sd-data.js`, which is cody's.
* **The sairncode audit drove no competitor product and quotes no market
  size**, so it cannot say whether anyone else already ships B1–B5.
* **The 13 attributes of `(b)(11)(iv)(A)` were summarised by the fetch, not
  enumerated** — read the criterion before building from it.
* **Nothing live.** No deployed URL was driven — unchanged from b34 onward.
