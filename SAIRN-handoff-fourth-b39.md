# HANDOFF — fourth / ted, batch b39, 2026-10-20

**READ THIS FILE ONLY.** It is the whole state.

**Written BEFORE the report, at a point where nothing is half-finished.** All
six items are on `origin/main`; the only uncommitted files now are this
handoff, the manifest, the report and the digest.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**FIVE THINGS TO READ FIRST:**

1. **6 of 6 DONE**, and **both fixes were reproduced in a browser before a line
   was changed** — the dispatch's methodology, and it paid for itself twice. §3.
2. **THE PUSH TOOK TWELVE ATTEMPTS AND THREE GATE REFUSALS, ALL ANSWERED, NONE
   SKIPPED — and one of them was MY OWN BUG, caught by the gate.** §7.
3. **I OVERTURNED ONE OF MY OWN b38 FINDINGS** rather than shipping it. §3.3.
4. **THE FUNERAL SENTENCE WAS RIGHT ON ONE ROW OF SIX AND WRONG IN THREE
   DIFFERENT WAYS** on the others. §4.
5. **READING THE REGULATION ITSELF NEARLY PRODUCED A WRONG ARTEFACT** — there
   is an *expired* criterion with the same heading. §5.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\ea7d41f7-de8c-4e21-afd3-fc6d47e335b9.jsonl`
(same session as b37 and b38 — a continuation)

**Working files:** `…\ea7d41f7-…\scratchpad\b39\` — `fix_b39.py` (the two
render fixes, counted assertions), `fix_leg_rows.py` (§4, pipe-count
assertions), `fetch_dsi.py` / `read_b11.py` (§5), `fetch_design.py` (§6),
`add_defects.sh`, `land3.sh` (§7), `fill39.py`, `httpd.log`.

**NO SQL THIS BATCH.** Nothing written to `sql/`.

---

## 1. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | **0 ahead, 0 behind** | `git rev-list --left-right --count origin/main...HEAD` |
| the b39 commits | **`21a4b3ce`** fixes · **`1355fade`** Tier A obligation · **`63ebc546`** leg rows · **`1d2a96c0`** sairncode artefacts · **`d9b2ec18`** sairndesign audit · **`8c858b7b`** defect records | `git log --oneline -6` |
| confirmed on origin | **all six pass `merge-base --is-ancestor`** | per commit |
| **files touched** | **exactly 6** — `sairndental.html`, `docs/CRITICALITY-TIERS.md`, `docs/tier-a-reviews.json`, `docs/defect-density-register.json`, and two new docs | `git show --name-only --format=""` |
| **forbidden paths** | **0** — no `api/`, no `tools/`, no `.githooks`, no `settings.json`, no `.claude/skills/` | same, piped to `grep -cE` |
| `sairncode.html`, `sairndesign.html`, `stonedesk.html` | **NOT touched** — items 4 and 5 are documents by instruction | absent from the file list |
| `git stash` | **0** | `git stash list` |
| **force push** | **NONE.** No `--force`, no `--force-with-lease` | — |
| **overrides** | **NONE, any form** | — |
| b39 manifest | **6 done, 0 blocked**, validates | `batch_manifest.py --check --agent fourth --batch b39` |

---

## 2. CLAIMS HELD

**`fourth` holds ONE claim**, declaring `sairndental.html`,
`docs/CRITICALITY-TIERS.md`, `docs/tier-a-reviews.json`,
`docs/cloud-research/`, the notes doc, the manifest and the three
deliverables, with five negatives declared on purpose:
`NOT-stonedesk-html-hanks` · `NOT-api-sd-data-js-codys` ·
`NOT-tools-shared-REPORT-ONLY` · `NOT-dot-claude-shared-REPORT-ONLY` ·
`NOT-sairncode-html-DOCS-ONLY-THIS-BATCH`.

**RELEASED IN FULL AT THE END OF THIS BATCH.** Nothing is mid-edit.

**`docs/defect-density-register.json` was NOT in the claim and was written
to** — §7 is why (the push gate required it). Disclosed rather than quietly
added.

---

## 3. ITEM 1 + 2 — THE TWO FIXES, REPRODUCED FIRST

### 3.1 The repros, which are the evidence

| | before the fix | after |
|---|---|---|
| **GFE** — requested 2026-09-01, due **2026-09-04** under `149.610(b)(1)(vi)(C)`, marked Issued **2026-10-20** = **46 days late** | Due tile **1 → 0**, nav badge **inline-block → none**, row badge **neutral**. `rec.issued_at` stored all along | row: *"issued 2026-10-20 — 46 days LATE"*; Issued tile sub-line *"1 issued LATE, 1 timing not on file"* in the danger colour |
| **CREDENTIALING** — licence key blanked, two credentials expired **21 and 28 months** (2025-01-31, 2024-06-30 vs 2026-10-20) | **Expired 0 / Expiring 0 / CE 0 / MATE 0**, nav badge hidden | all four **`--`** with a per-tile tooltip, nav badge **`?`**, and the empty table says *"could not be evaluated"* |

**THE EMPTY VARIANT IS WORSE THAN b38's AUDIT SAID, AND REPRODUCING IS WHAT
FOUND IT.** b38 reported the rows would read *"Not checked yet"* — true only
when local records exist. **With none, four zeros sat beside "No credential
records yet" and nothing anywhere said the board had never been evaluated.**
That correction came from driving it, not re-reading it.

### 3.2 Three outcomes, never two — all three driven

`issued LATE` with the day count · `issued in time` · **`issued, timing not on
file`** for records predating `issued_at`, which **must not** read as on time
because nothing established that.

**NEGATIVE CONTROL, and it found real work:** a *successful* board must **clear**
the `--` and the tooltips, or a tile that is now a real `0` keeps a tooltip
saying it was never checked — the same defect inverted. Driven: could-not-run
first (all four `--`), then a real board → all four `0`, `title` null, badge
title cleared. **PASS true.** Without that arm, `--` sticking forever would have
looked identical to the fix working.

### 3.3 I overturned one of my own b38 findings

**b38 called `due<=today` an off-by-one. It is not** — the tile is labelled
*"Due today or overdue"*, so the code matches its own label. **Left exactly as
it was, with the reason in a comment so the next reader does not re-raise it**,
and the Tier A entry asks the reviewer to re-decide rather than inherit it.

### 3.4 The Tier A obligation

`tier_a_review_gate.py --open --resources dnt_gfe,dnt_credentials` →
**recorded, ASSIGNED TO cc.** The entry names **five things to attack** (the
date arithmetic and whether `lateBy===0` reads as in-time, which I did *not*
drive; whether the third outcome can leak into the "All N issued in time"
branch; the negative control's limited scope; the `due<=today` decision; and
that nothing server-side was read) rather than asking for a re-read.

---

## 4. ITEM 3 — THE FIVE SIBLING `leg_*` ROWS

**b38 stopped here on purpose** and recorded that the five were unread. They
have now been read **at their write sites**. **1 of 5 correct, 4 wrong in
THREE different ways** — which is why any single fix would have been wrong.

| row | verdict |
|---|---|
| `leg_deathrecords` | **THE SENTENCE IS CORRECT** — the row it was written for. `decedent_full_name`, `date_of_death`, `place_of_death`, `county`, `attending_physician`, `cause_pending`, all on-row. **LEFT ALONE.** |
| `leg_certs` | **WRONG PERSON CLASS** — a **staff** certification; the government identifier belongs to a living employee and there is no decedent on it at all |
| `leg_custodylog` | **A-by-chain** through `case_id` — where a named decedent's body was, in whose hands, at a known time |
| `leg_invoices` | **A-by-chain**, and the old sentence never mentioned **`declined_items`**, the FTC Funeral Rule record of what a bereaved family declined |
| `leg_preneed` | **THE SUBJECT IS ALIVE**, and `linked_case_id` is **optional** |

**NO TIER MOVED, and `leg_preneed`'s is FLAGGED NOT DECIDED.** It reads closer
to **C-B** by this register's own comparables — `rf_claims` and `invoices` are
both C-B on *"sensitive to the customer, not an elevated class"* — and **a C-A
tier decides who must review a change to it**, so moving one on a single
session's reading is the blast radius this register exists to control. **The
cell asks somebody else to decide, with both comparables named.**

**A SIXTH FINDING, on the one row whose sentence was right:**
`leg_deathrecords`' **integrity** cell said *"or SSN fragment"* and **there is
no SSN anywhere in the app** — `grep -ic "ssn" sairnlegacy.html` is **0** and no
`sql/` file mentions one. Replaced with the real field list; tier unaffected.

**Mechanics:** unique substring in one named row, pipe count asserted per row,
file unchanged at **788 lines / 3241 pipes**, and a post-check requiring the
shared sentence to appear **exactly once** afterwards **and to be on
`leg_deathrecords`**. **Down from 6 to 1.** `PROBLEMS` 6, **0 new**.

---

## 5. ITEM 4 — THE DSI RECORD, AND THE EXPIRED CRITERION

`docs/2026-10-20-fourth-b39-sairncode-compliance-artefacts.md`

**Read from the regulation's own XML** (eCFR renderer API, 248,888 bytes),
because b38 built on a WebFetch *summary* and said so.

**AND IT NEARLY PRODUCED A WRONG ARTEFACT.** `§ 170.315(a)(9)(v)` **also**
carries a *"Source attributes"* heading, with only **FOUR** items, and its own
`(a)(9)(vi)` says that criterion *"expires on January 1, 2025."* **My first
extraction landed on the dead one** — a grep for the heading finds it first.

**REAL COUNTS from source:** `(iv)(A)` = **13** (confirming b38's figure);
`(iv)(B)` = **9 headings carrying 31 leaf items**, which b38 could only call
*"a longer list."*

**B1 is written for all 31 leaves and its value is that 15 say NOT
ESTABLISHED** — `(b)(11)(iv)` requires the attributes be *supported*, and an
aspirational entry converts a missing control into a false claim. External
validation: **nothing, all four**. Quantitative performance: **nothing, all
five** — recorded beside the history that this file once carried **fabricated
82%/71% confidence scores**, since removed, because an absent measure is the
correct state and a manufactured one was the previous state.

**Two entries are genuinely strong and measured:** there is no training set to
describe (the prompts require live search and a **character-for-character**
`source_snippet`, with `no_match:true` rather than a guess), and **use of the
`(A)(5)–(13)` protected-class variables as input features is NONE** —
`ethnic` 0, `sexual orientation` 0, `gender identity` 0, SDOH 0, health status
0, and **`race` returns 2 hits that are both the word "traceable."**

**B3** = the two `422.310(g)` dates as *computed* data plus a mode switch.
**B4** = the `92.210(b)` inventory, nine entries, **naming the panels it has
not assessed**, with **`hcc` and `drg`** flagged as the two most likely to be a
*yes*.

---

## 6. ITEM 5 — SAIRNDESIGN

`docs/cloud-research/sairndesign-worldwide-competitive-gap-audit-2026-10-20.md`

**Two instruments read in full text.** `16 CFR 1640` whole: effective
**25 June 2021**, labelling compulsory since **25 June 2022**, `§1640.5(a)`
makes **all** upholstered furniture comply with **California TB 117-2013**,
`§1640.4(b)` fixes the exact label string, `§1640.5(b)` **preempts** differing
state rules, and `§1640.3(e)`'s scope catches indoor seating, movable *or
stationary*, **able to be stuffed**, expressly **including furniture for a
child**. `40 CFR 770` targeted: `§770.10`'s four ppm limits, and `§770.45`'s
producer name / lot number / **TPC number** chain that *"must be made available
to potential customers upon request."*

**THE FINDING:** `sdn_specitems`' write (`sairndesign.html:2042`) stores
**thirteen fields and every one is commercial.** `TB 117` **0**,
`formaldehyde` **0**, `TSCA` **0**, `flame` **0**, `ASTM`/`E84` **0**,
`Prop 65` **0**, `accessib` **0** — and `ADA` returns **3, all three inside the
word "UNREADABLE"**, said out loud because an earlier 12-hit alternation count
looked like accessibility content and was exactly that mistake.

**B1–B3 have no blocker** and are one field group, one predicate and one portal
panel — the app already carries `vendor` and `sku`, so the join is one field
away.

**THE EU LIMB IS UNSOURCEABLE FOR THE THIRD BATCH RUNNING** — b37's AMLR,
b38's AI Act across three URL forms, and this one. **No EU instrument is cited
anywhere.** A worldwide audit that cannot read EU law is a US audit with a
wider title, **and fixing the route is worth more than the next audit.**

---

## 7. ITEM 6 — TWELVE PUSH ATTEMPTS, THREE REFUSALS, ALL ANSWERED

**No force, no override of any form.** The three refusals:

**(a) `register_feed_gate`** denied the sairndental fix for having no defect
record. **Unlike b38's schema reconciliation this one IS a defect in shipped
behaviour**, so **two real records** were filed — injection commits
**`a002b2dc`** (GFE panel, 2026-09-02) and **`876bd84c`** (credentialing,
2026-08-24), four factors each including a *latent condition* and a
*not-actionable detection* factor, `rule: not-citable` **with a note proposing
the rule that would cover the class**, and **recurrence left OPEN on both**.

**(b) `docs/tier-a-reviews.json` conflicted on a rebase** and was resolved with
**`tools/sairn_rebase_resolve.py`** — the sanctioned union-by-identity merger,
**272 ancestor + 1 upstream-only + 1 local-only = 274**, validated. **Never a
hand-resolve.**

**(c) MY OWN LANDING SCRIPT HAD A REAL BUG AND THE GATE CAUGHT IT.** Its fold
step staged `docs/defect-density-register.json` **without checking for conflict
markers**, so a conflicted copy was amended into a commit and became **broken
JSON**. The push gate refused with *"the defect register could not be read"* —
**the gate doing exactly its job.** The register was **restored from
`origin/main`** and the two records re-added cleanly; the script now **refuses**
to stage a file with conflict markers or invalid JSON rather than guessing.

**The `doc-sha-reseat` hook then correctly re-pointed both records from
`0b069085` to `21a4b3ce`** — verified: `21a4b3ce` **is** an ancestor of
`origin/main` and `0b069085` **is not**.

---

## 8. WHAT IS OPEN — EXACT NEXT STEP PER ITEM

1. **cc: discharge the Tier A obligation** on `dnt_gfe` + `dnt_credentials`.
   Five attack points are named in `docs/tier-a-reviews.json`. **Start with the
   date arithmetic and `lateBy===0`** — I did not drive the issued-exactly-on-
   the-due-date case.
2. **`leg_preneed`'s C tier (§4).** Flagged, not decided. Needs somebody other
   than me, with `rf_claims` and `invoices` as the comparables.
3. **SAIRNcode B1's remaining 15 NOT ESTABLISHED leaves (§5).** The cheapest
   real one: adopt *what fraction of suggestions are rejected for an
   unverifiable citation* as the monitored performance measure — already
   computable from the human-review queue.
4. **SAIRNcode B4: read `hcc` and `drg` for 92.210 variables.** Both are
   age/sex-weighted by construction; both could be a *yes*.
5. **SAIRNcode B3** — two dates and a mode switch, but the handler is in
   `api/sd-data.js`, which is **cody's**.
6. **SAIRNdesign B1–B3** — one field group, one predicate, one portal panel.
   Nobody holds `sairndesign.html`.
7. **THE EUR-LEX ROUTE (§6).** Three batches of EU findings lost. **Worth more
   than the next audit.**
8. **The credentialing fix does not yet distinguish its four null conditions** —
   a practice cannot tell a missing licence key from an unreachable server.
   Recorded as `planned` in the defect register.
9. **Still not mine:** `api/sd-data.js:1352`'s stale `:11690` citation, and
   `api/_lib/law-trust-reconcile.js`'s header describing a function that no
   longer exists.
10. **Carried:** b37 items 1+2 (hank's); `mech_schedule`; the `rt_routes`
    handler branch cody holds; the dental clearinghouse decision;
    sairnmechanical and sairnroofing still have **zero** audits; `CLAUDE.md`
    and `sairn-session-handoff` still lack the four b38 standing rules.

---

## 9. WHAT b39 PROVED vs LEFT UNPROVEN

**PROVED, driven or measured:**

* both failing states **reproduced in a browser** with dates and counts, then
  both fixes **re-verified on a cache-busted URL**, plus a negative control
  that found real work
* five `leg_*` write sites read; the shared sentence **6 → 1**, with 788
  lines / 3241 pipes unchanged and **0** new `criticality_tier_check` problems
* `(b)(11)` read from the regulation's XML: `(iv)(A)` **13**, `(iv)(B)`
  **9 headings / 31 leaves**, and the **expired `(a)(9)` predecessor** found
* `16 CFR 1640` read whole; `sdn_specitems`' thirteen fields and seven zero
  compliance counts measured, with the `ADA`-in-"UNREADABLE" false positive
  named
* 6 files, **0 forbidden paths**, no force, all six commits ancestors of origin

**LEFT UNPROVEN:**

* **`lateBy===0` — an estimate issued exactly ON its due date — was NOT
  driven.** I intend it to read *in time*. The reviewer is asked to check it.
* **The "All N issued in time" branch's unreachability while `unknownIssued>0`
  is believed, not proven.**
* **The negative control ran once**, not twice, and not across a panel revisit.
* **Nothing server-side was read** for either fix or for SAIRNcode —
  `api/sd-data.js` is cody's.
* **The five `leg_*` tiers were judged from the client write site only**; no
  SQL schema or server branch was read.
* **No EU instrument, no ADA Standard, no `40 CFR 770` testing subpart, no
  interior-design licensure** — all named unread in their documents.
* **No screen-reader test** — unchanged from b36 onward.
* **Nothing live.** No deployed URL driven, unchanged from b34 onward.
