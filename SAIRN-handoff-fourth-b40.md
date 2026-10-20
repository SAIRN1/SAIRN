# HANDOFF — fourth / ted, batch b40, 2026-10-20

**READ THIS FILE ONLY.** It is the whole state.

**Written at the automatic wrap point, with nothing half-finished.** All work
is on `origin/main`; the only uncommitted files are this handoff, the manifest,
the report and the digest.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**FOUR THINGS TO READ FIRST:**

1. **4 of 6 DONE. ITEMS 4 AND 5 WERE STOPPED BY THE STANDING 85% WRAP RULE —
   not skipped and not claim-blocked.** §7 has the measurement and §8 has what
   the next session inherits, which is a full specification in both cases.
2. **THE EUR-LEX ROUTE IS FIXED, and the AI Act turns out to have been in
   application since 2 August 2026** — eleven weeks before this batch. Three
   audits treated it as a future cliff. §4.
3. **MY FIRST DESIGN FOR THE CREDENTIALING FIX WAS WRONG AND A COUNTED
   ASSERTION CAUGHT IT.** The app already had the facility I was reinventing.
   §3.2.
4. **MY OWN b39 NEXT-STEP POINTED AT THE WRONG TWO PANELS.** §5.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\ea7d41f7-de8c-4e21-afd3-fc6d47e335b9.jsonl`
(same session as b37–b39 — a continuation)

**Working files:** `…\ea7d41f7-…\scratchpad\b40\` — `fix_cred_reasons.py` (the
abandoned first design), `fix_cred2.py` (the one that shipped), `eu_fetch.py`
(**the fixed EUR-Lex route, re-runnable**), `add_defect.py`, `fill40.py`,
`land.sh`, `httpd.log`, `aiact.txt` / `amlr.txt`.

**NO SQL THIS BATCH.** Nothing written to `sql/`.

---

## 1. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | **0 ahead, 0 behind** | `git rev-list --left-right --count origin/main...HEAD` |
| the b40 commits | **`cc919c30`** sairndental fix · **`953d70a3`** EU route + articles · **`ac3f5fc8`** sairncode addendum · **`a6be552b`** defect record | `git log --oneline -4` |
| confirmed on origin | **all four pass `merge-base --is-ancestor`** | per commit |
| **files touched** | **exactly 4** — `sairndental.html`, two docs, `docs/defect-density-register.json` | `git show --name-only --format=""` |
| **forbidden paths** | **0** — and the check includes **`docs/tier-a-reviews.json`** this batch, deliberately | same, piped to `grep -cE` |
| `sairncode.html`, `sairndesign.html`, `stonedesk.html`, `api/` | **NOT touched** | absent from the file list |
| `git stash` | **0** | `git stash list` |
| **force push** | **NONE** | — |
| **overrides** | **NONE, any form** | — |
| b40 manifest | **4 done, 2 blocked**, validates | `batch_manifest.py --check --agent fourth --batch b40` |

**`docs/tier-a-reviews.json` WAS DELIBERATELY NOT TOUCHED.** cc's b27 claim
says *"THE SIX TIER A VERDICTS ARE DEFERRED, NOT DROPPED — docs/tier-a-reviews.json
is held LIVE by fourth b39 and will be claimed separately when fourth
releases."* I released it at the end of b39, so it is cc's to take. It was
declared `NOT-` in my claim and touched **0** times.

---

## 2. CLAIMS HELD

**`fourth` holds ONE claim** over `sairndental.html`, `sairndesign.html`,
`docs/cloud-research/`, the b39 artefacts doc, the manifest and the three
deliverables, with six negatives declared: `NOT-docs-tier-a-reviews-json-CC-IS-WAITING-FOR-IT`,
`NOT-api-ANYTHING-codys`, `NOT-tools-shared-REPORT-ONLY`, `NOT-CLAUDE-md-ccs`,
`NOT-dot-claude-skills-ccs`, `NOT-sairncode-html-DOCS-ONLY`.

**RELEASED IN FULL AT THE END OF THIS BATCH.**

**THE CLAIM MATCHER BLOCKED THIS BATCH AND THE RESOLUTION IS RECORDED.** Three
sessions matched on the app name `sairndental` — cc, cody, hank — and **not one
of the three lists `sairndental.html`**. hank's claim explicitly declares
**`NOT-sairndental-html-fourths`**; cody's dental files are all `api/`
(`public-book.js`, `dental-photo-validation.js`) — the **server** half, to my
client half; cc's are `tools/`, `docs/fmea/`, `Agents.md`, `CLAUDE.md`. **Re-run
with a declared FILES list → CLEAR**, which is the tool's own sanctioned
resolution and the same route b38 and b39 took.

---

## 3. ITEM 1 — THE BOUNDARY, AND A DESIGN I THREW AWAY

### 3.1 `lateBy===0` needed no fix and is now proven

b39 shipped the GFE lateness fix **with this case undriven** and said so in the
Tier A entry it opened against itself. Driven now across **seven** trigger
dates, so a weekend shift in `gfeAddBusinessDays` cannot make the answer an
accident of one calendar position: `issued_at == dueDate` → `lateBy 0` →
**"in time"**, green `bg` badge. **7/7.**

**NEIGHBOUR CONTROL**, because 7/7 "in time" proves nothing if the branch fires
unconditionally. Same trigger, offsets on a due date of **2026-10-08**:

| offset | issued_at | rendered | badge |
|---|---|---|---|
| −1 | 2026-10-07 | issued … — **in time** | `bg` |
| **0** | **2026-10-08** | issued … — **in time** | `bg` |
| +1 | 2026-10-09 | issued … — **1 day LATE** | `br` |
| +14 | 2026-10-22 | issued … — **14 days LATE** | `br` |

Four distinct renderings, correct singular/plural, and the Issued sub-line went
*"All 7 issued in time"* → *"2 issued LATE"* in the danger colour.
**`CONTROL_PASS` true. NO CODE CHANGED** — the open question is answered, not
patched.

### 3.2 The four null conditions, and the design I abandoned

**I wrote a new `dntCredFailure` module variable. A COUNTED ASSERTION TRIPPED**
on `code:'NO_LICENCE'` appearing twice — and that is what found the real answer:

> **`dntLastErr` (`sairndental.html:1647`) ALREADY IS this facility**, read by
> `dntLastErrCode()`, `dntLastErrText()` and `dntWriteRefused()`, and its own
> comments carry the same reasoning I was reinventing — *"a stale server
> sentence reads as a real diagnosis and is worse than the generic fallback."*
>
> **`sdnEvaluateCredentials()` was simply a SECOND FETCH PATH THAT NEVER FED
> IT.** Not a missing reason — a missing wire.

It now writes `dntLastErr['dnt_credentials']` at every failure exit exactly as
`sdnData` does, **keeping the `status` convention**: present means a server
answered and its words may be shown, absent means the sentence is
browser-authored and `dntLastErrText()` must stay quiet.

**DRIVEN, awaiting the real promise rather than sleeping. Four codes, four
sentences, each naming whose problem it is:**

| code | sentence names | whose |
|---|---|---|
| `FORBIDDEN` (403) | *"not authorised … this panel is owner-only"* | **your sign-in** |
| `UPSTREAM` (500) | *"the server refused … run its schema first"* | **the server** |
| `NETWORK` | *"could not be reached … check the connection"* | **the connection** |
| `NO_LICENCE` | *"no licence key on this install"* | **this practice** |

A 200-with-`ok:false` is separated too (`REFUSED`, status 200). **NEGATIVE
CONTROL:** a successful board clears the record, restores `0 0 0 0` and
**hides** the badge.

**AND DRIVING IT FOUND A SECOND-ORDER DEFECT I THEN FIXED.** The first panel
drive snapshotted `NO_LICENCE` while a 403 was in flight, because
`nav('credentials')` paints `rCredentials(null)` **before** the evaluation
resolves. The key is now cleared **on entry**. **The flash is narrowed, not
eliminated, and the comment says so.**

---

## 4. ITEM 2 — THE EUR-LEX ROUTE, AND WHAT IT BOUGHT

**THE ROUTE.** Three batches lost their EU limb to an empty body from
`eur-lex.europa.eu` web pages. The fix is the **official machine interface**:

    GET http://publications.europa.eu/resource/celex/<CELEX>
    Accept: application/xhtml+xml

AI Act `32024R1689` → **HTTP 200, 1,257,134 bytes**. AMLR `32024R1624` →
**HTTP 200, 1,165,026 bytes**. Both 303 to a Cellar resource, which is the
documented behaviour. **No bot wall is involved and none is circumvented** —
the same rule b38/b39 applied to eCFR: *stop at the wall, find the published
machine interface.*

**THE HEADLINE: THE AI ACT IS NOT A FUTURE CLIFF.** Article 113 — applies from
**2 August 2026**; Chapters I–II from 2 February 2025; Ch. III §4, V, VII, XII
and Art. 78 from 2 August 2025; **Article 6(1) from 2 August 2027**. **Today is
2026-10-20, so the general date is eleven weeks past.**

**AND THE ANSWER FOR SAIRNCODE IS NEGATIVE, ON THE ACTOR TEST.** Annex III
**5(a)** is *"by public authorities or on behalf of public authorities"*;
**5(c)** is *"risk assessment and pricing … in the case of life and health
insurance"* — the **insurer's** side; **5(d)** is emergency triage; **6(1)**
needs an Annex I product under third-party conformity assessment. **So
SAIRNcode is NOT Annex III high-risk — stated as a BOUNDARY, not a clearance**:
a sale to a payer or public authority making eligibility or pricing
determinations engages 5(a) or 5(c) **with no code change at all**.

**AMLR Article 90 confirms b37's dates from source:** 10 July 2027, except
Article 3(3)(n) and (o) at 10 July 2029. **b37 was right from a snippet and
b38/b39 refused to cite it.**

**AND THE PRIVILEGE CARVE-OUT HAS A CLAUSE NO AUDIT HAD.** It covers
information received *"before, during or after"* proceedings — and the exception
ends: ***"Such knowledge and purpose can be inferred from objective factual
circumstances."*** **The carve-out is not self-certifying, and the record the
software keeps is part of those circumstances.** That makes b38's AML company
decision **harder to defer, not easier**.

---

## 5. ITEM 3 — MY OWN NEXT STEP POINTED AT THE WRONG PANELS

b39 said *"EXACT NEXT STEP: `hcc` and `drg` … the rows where the answer could be
yes."* **Wrong in both directions.**

* **`hcc`** — a 1,434-char shell; `renderHcc()` (`:4497`) reads
  `{cat, patient, value, status}`. **No 92.210 variable.** `drg` the same at
  1,391 chars.
* **`transport`** — `id="tr-age"`, *"Patient age (months)"* (`:1386`). **AGE,
  determinatively.**
* **`esrd`** — `id="esrd-age"`, *"Age at end of month"* (`:1690`), and the
  panel's own copy: *"The code is fixed by the age at the end of the month."*
* **`sex` and `gender`: ZERO anywhere in the file.**

**The use is lawful and that is not the point:** those codes are fixed by age
**by the rule being implemented**. But `92.210(b)` is a duty to **identify**,
and an inventory that misses the only two panels using a protected-class
variable has failed at its one job.

**`(B)(7)` also gets its first measured leaf, specified from a store that
already exists** — `rejected / (rejected + accepted)`, **decided items only in
the denominator**, because `needs_human_review` is an item nobody looked at and
`auto_assigned` is not an acceptance. **Not built:** `sairncode.html` is
DOCS-ONLY in this claim.

---

## 6. ITEM 6 — THE PUSH

**0 ahead / 0 behind, all four commits ancestors, clean tree, no force, no
override of any form.** 4 files, **0 forbidden paths**.

**ONE GATE REFUSAL, ANSWERED NOT SKIPPED.** `register_feed_gate` denied the fix
commit **eight times** for having no defect record. **This one IS a defect in
shipped behaviour**, so a record was filed: injection **`876bd84c`**, severity
**LOW** (nothing was mis-stated — the panel already said nothing had been
checked; what was missing was **which** failure), `rule: not-citable` **with a
note proposing the rule that would cover the class** — *a fetch path that can
fail must write the same per-resource error record every other fetch path in
the file writes* — **four factors, two of them about my own process**, and
**recurrence left open on three counts**.

---

## 7. WHY ITEMS 4 AND 5 DID NOT RUN

**The dispatch set an automatic wrap at 85% real context.** Measured with
`tools/context_verify.py --digest-line`:

| point | context |
|---|---|
| batch opened | **67.9%** |
| item 1 closed | 72.4% |
| item 2 closed | 73.8% |
| item 3 closed | **76.2%** |

**~9 points remained against wrap deliverables that have historically cost
6–7.** Item 4 is a **code change** to `sairndesign.html` which the methodology
requires be reproduced, fixed and driven — **starting it would have crossed the
trigger mid-edit, which is the one state the wrap rule exists to prevent.** Item
5 is a worldwide audit, which in this series costs **5–8 points on its own**.

**NEITHER IS CLAIM-BLOCKED.** The check was CLEAR on `sairnbiz`, and nobody
holds `sairndesign.html`. **This is the wrap rule working, not a refusal.**

---

## 8. WHAT IS OPEN — EXACT NEXT STEP PER ITEM

1. **Item 4 — sairndesign B1–B3. FULLY SPECIFIED, no re-derivation needed.**
   `docs/cloud-research/sairndesign-worldwide-competitive-gap-audit-2026-10-20.md`
   §4 has the field group, the applicability predicate from **16 CFR 1640.3(e)**
   and the **40 CFR 770.45** chain (producer name, lot number, EPA TSCA Title VI
   TPC number). The write site is **`sairndesign.html:2042`**, and `vendor` +
   `sku` are already on the row, **so the join is one field away.** Reproduce
   first: a spec item has no compliance field at all.
2. **Item 5 — sairnbiz worldwide audit.** **It will be the FIRST in the series
   that can cite EU law from source**, because item 2's route works. SAIRNbiz is
   payroll/HR/invoicing; its `employees` resource is Tier A/A with
   `hourly_rate` feeding StoneDesk's labour rate **across an app boundary**
   (b37/b38), so employment and payroll regulation is the lens. Write sites:
   `sairnbiz.html:2433` `saveEmp()` and `:5066` `syncEmps()`.
3. **cc: the six Tier A verdicts.** `docs/tier-a-reviews.json` is **released and
   untouched this batch** — it is yours to claim, as your b27 note said. **The
   `lateBy===0` question in the b39 obligation is now ANSWERED (§3.1), so start
   elsewhere in that entry's five attack points.**
4. **The EU instruments still unread:** Construction Products Regulation, GPSR,
   REACH — **one CELEX identifier each**, route in
   `scratchpad/b40/eu_fetch.py`. And **the AMLR privilege text is a RECITAL**;
   the operative article was not located and must be before any reporting flow.
5. **The credentialing first-paint flash** is narrowed, not closed — needs a
   pending state `rCredentials` does not have. Recorded as open recurrence.
6. **`hcc` and `drg` server-side** — could read age or sex and the client would
   look identical. `api/sd-data.js` is **cody's**.
7. **The `(B)(7)` rejection rate** — two `filter().length` calls, and it must
   ship with its denominator visible (`N of M decided`).
8. **Carried:** b37 items 1+2 (hank's); `mech_schedule`; the `rt_routes`
   handler; the dental clearinghouse decision; sairnmechanical and sairnroofing
   still have **zero** audits; `CLAUDE.md` and `sairn-session-handoff` still
   lack the four b38 standing rules — **cc's b27 claim now covers both.**

---

## 9. WHAT b40 PROVED vs LEFT UNPROVEN

**PROVED, driven or measured:**

* `lateBy===0` renders **in time** across 7 trigger dates, with a −1/0/+1/+14
  neighbour control giving four distinct renderings
* four distinct failure codes with four distinct sentences, driven by stubbing
  `fetch`, plus a negative control that clears and hides on success
* **the EUR-Lex route**: two instruments, HTTP 200, 1.26MB and 1.17MB, from the
  official CELEX content-negotiation endpoint
* Article 113, Article 6, Annex III point 5 and Article 90 **read from source**
* `hcc`/`drg` carry **no** 92.210 variable on the client; `transport`/`esrd`
  carry **age**; `sex`/`gender` are **zero** file-wide
* 4 files, 0 forbidden paths, no force, all four commits ancestors of origin

**LEFT UNPROVEN:**

* **Items 4 and 5 were not started** — §7.
* **The credentialing first-paint flash is narrowed, not eliminated.** A
  sub-second render of *"the reason was not recorded"* remains.
* **Nothing server-side was read** — `api/sd-data.js` is cody's, so no claim
  about the credential board itself, or about `hcc`/`drg`'s server computation.
* **The EU documents were read by TARGETED EXTRACTION**, not whole (585,353 and
  424,875 chars flattened). The surrounding obligations — AI Act Articles 8–15
  and Annex IV, the AMLR's CDD chapter — were **not read**.
* **The AMLR privilege text is a RECITAL, not an article**, and the operative
  provision was not located.
* **No consolidated-version check** on either EU instrument.
* **No legal review.** The Annex III conclusion is a text reading against a
  product description.
* **No screen-reader test.** **Nothing live** — unchanged from b34 onward.
