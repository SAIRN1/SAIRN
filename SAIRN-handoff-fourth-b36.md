# HANDOFF — fourth / ted, batch b36, 2026-10-19

**READ THIS FILE ONLY.** It is the whole state.

**Written BEFORE the report, at a point where nothing is half-finished.**

**b36 WAS WRAPPED UP ON INSTRUCTION, AND THE STOP COST NOTHING.** All six
items' work was already committed and landed on `origin/main` as `3c7f7efa`
before the instruction arrived. **Nothing was mid-edit, nothing was stashed,
nothing was reverted** — the only uncommitted files at the stop were this
handoff and the manifest row for item 6, both complete. §1.

**THE SCHEMA COLUMN CHECK WAS COMPLETED**, not abandoned: the full comparison
against the module and all four consumers is in §3, and the one defect it
found is reported there. The digest carries the file verbatim regardless, as
asked.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT. Re-derive anything you mean
to quote, including out of this file.**

**FOUR THINGS TO READ FIRST:**

1. **ITEM 2 IS A STOP-AND-REPORT, NOT A SKIP.** SAIRNmechanical has **no
   schedule data layer** — there is nothing to route. The app's own code says
   so twice. §4.
2. **TWO INSTRUCTIONS HAD PREMISES THAT DID NOT HOLD, AND BOTH ARE REPORTED
   RATHER THAN WORKED AROUND.** The redaction question (§5) and the audit
   target (§7).
3. **ONE REAL SCHEMA DEFECT FOUND AND DELIBERATELY NOT FIXED**, because it is
   a CHECK-constraint contradiction and the instruction scoped fixes to
   column-name and type mismatches. §3.
4. **SAIRNDENTAL HAS THE FIRST ACCESSIBILITY PASS ON ANY SAIRN APP**, and two
   things nearly shipped silently during it. §6.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\7114877e-14ff-4635-8129-799b043ea778.jsonl`
(same session as b33–b35 — a continuation)

**Working files:** `…\7114877e-…\scratchpad\b36\`
— `measure_redaction.js` (§5), `a11y_fix.py` (§6), `fix_memory_row.py`,
`httpd.log`.

---

## 1. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| `HEAD` vs `origin/main` | **0 ahead, 0 behind — PUSHED AND LANDED** | `git rev-list --left-right --count origin/main...HEAD` |
| the b36 commit | **`3c7f7efa`** | `git log --oneline origin/main` |
| confirmed on origin | passes `merge-base --is-ancestor` | — |
| **files it touches** | **exactly four** — `docs/CRITICALITY-TIERS.md`, the manifest, the new audit, `sairndental.html` | `git show --name-only --format="" 3c7f7efa` |
| **forbidden paths** | **0** — `api/sd-data.js`, `tools/`, `.githooks`, `settings.json` | same command `\| grep -cE …` |
| uncommitted | **none** | `git status --porcelain` |
| `git stash` | **0** | `git stash list` |
| force push | **none** | — |
| overrides | **none, any form** | — |
| auditor clones | **not entered** | — |
| b36 manifest | **5 done, 1 blocked** (item 2, with its reason) | `batch_manifest.py --check --agent fourth --batch b36` |
| tier checker | `RESOURCE_ROWS:400  TIER_A:283  PROBLEMS:14` — re-run **on the merge** | `criticality_tier_check.py` |

**The forbidden-path check is scoped to my own commit, not a range.** b35
recorded why: a range answers *"did anybody touch this in this window"*, which
is a different question and answered **1** for somebody else's commit.

---

## 2. CLAIMS HELD

**`fourth` holds one claim** declaring `docs/CRITICALITY-TIERS.md`,
`sairnmechanical.html`, `sairndental.html`, the audit, the notes doc, the
manifest and the three deliverables. **Released LAST, after the push.**

**`sairnmechanical.html` was claimed and NOT modified** — §4 is why.

**THE CLAIM IS RELEASED IN FULL AT THE END OF THIS BATCH. NOTHING IS KEPT
BACK**, because nothing is mid-edit: every file in the claim is either
committed and landed or was never modified. There is no file with unfinished
work holding a claim open.

**Other active claims:** cody on `platform` (`api/sd-data.js`), cc on `cc`
(`tools/defect_register.py`, `tools/sairn_push_gate_hook.py`), hank on `hank`
(`api/bridge.js`), hover2 on `hover2`. **None was touched.**

---

## 3. ITEM 1 — THE SCHEMA, AND ONE DEFECT LEFT IN PLACE ON PURPOSE

**Re-read against the module and all four consumers. NO column-name or type
mismatch**, so nothing was edited, exactly as instructed:

* all four consumers send `{job_ref, address, locked, status}`; `rt_stops`
  declares all four
* `status` enum `('pending','done','skipped')` matches what the consumers send
  and what `isPinned()` tests
* `source` enum matches `STORED_BASES` exactly
* route-level `app_id` / `assignee_id` / `route_date` all present

### The defect — reported, NOT fixed

```sql
constraint rtroutes_saved_sane
  check (saved_seconds is null or saved_seconds >= 0),
```

**The module deliberately returns NEGATIVE savings un-clamped.** `routes.js`:
*"A NEGATIVE RESULT IS RETURNED AS-IS AND IS NOT CLAMPED… a caller that stores
a negative saving has learned something true."* A test arm asserts it is
negative, and **all four consumers render it** — *"this order is about N min
LONGER than the one you had."*

**If the handler branch ever stores a negative, Postgres rejects the entire
upsert** and the route write fails.

**NOT FIXED because it is a CHECK-constraint contradiction, not a column-name
or type mismatch**, and the instruction scoped edits to those two. **Next
step:** either drop `rtroutes_saved_sane`, or clamp in the module and lose the
distinction the module exists to preserve. **The first is correct**; the second
re-introduces the 2026-06-18 defect.

**Published verbatim to Drive as `SAIRN-sql-rt_routes_schema.sql`** —
8,777 bytes, sha256 `2c9488e38554e320`, unedited. Full text is in the digest
under `SQL`.

---

## 4. ITEM 2 — SAIRNMECHANICAL: STOPPED AND REPORTED

**Read the data model first, as instructed. There is nothing to route.**

Its **7 registered resources** are `mech_credentials`, `mech_site_assets`,
`mech_insurance_policies`, `mech_quotes`, `mech_checks`, `mech_docs`,
`mech_takeoffs`. **None is a schedule, an assignment, or a dated visit.**

`mech_site_assets` **does** carry `site_address` and `customer_name`, so
addresses exist — but it has **no assignee and no scheduled date**.
`recorded_by` is who entered the row; `installed_on` is an install date. **A
route needs stops + an assignee + a date. Two of the three do not exist.**

**The app says so itself, twice:**

* the Dispatch panel markup — *"This panel has no backend; building one is
  separate scoped work."*
* `aiDispatch()` — *"There is no data layer for this app yet, so the honest
  behaviour is to refuse. Do NOT restore a fixture prompt — wire it to real
  records."*

Wiring a card would mean **inventing that layer** (explicitly out of scope) or
**shipping a dead control over an empty state that can never populate** — a
Check 0d defect.

**THE MODULE IS UNCHANGED AND CORRECT.** This is not the "shape needs a module
change" case the instruction anticipated; it is stronger — the prerequisite
data does not exist.

**EXACT NEXT STEP:** build `mech_schedule` (a job/asset ref + an assignee + a
date) as its own scoped work. Once it exists the card is the same three edits
as SAIRNscape.

---

## 5. ITEM 3 — THE REDACTION RATE: **100%**, AND THE QUESTION'S PREMISE WAS WRONG

**Measured: `complete:false` on 193 of 193 samples. `complete === true`: 0.**

**Method, re-runnable** — `node scratchpad/b36/measure_redaction.js`: 185
paragraph-sized chunks harvested from six real repo files, plus 8 synthetic
documents built to the shapes `AI_SCANNED_TEXT` names and seeded with every
identifier class the rules target.

**And the structural reason beats the sampled one.** All three `complete:`
literals in `api/_lib/mech-redact.js` are `false`, and the source says why:

> *"NEVER TRUE. Stated as a constant rather than computed, because there is no
> input for which this pass is complete and a field that could be true invites
> a caller to branch on it."*

**So b35's premise — that the B "rests on `complete:true` not being
abnormal" — was false.** It is never true.

**The sharper result came from the residual check**, which deliberately used a
**different pattern set from the redactor's own rules** (checking a redactor
with its own regexes only proves self-consistency):

* `Customer: Diane Ferraro` **IS** redacted when the label starts a line —
  `LABELLED_NAME` is line-anchored
* **the same string SURVIVES mid-line**, and `Marcus Webb` in prose survives,
  which the shipped `NOT_REDACTED_NOTE` discloses

**Tier unchanged at B — on NEW grounds**, and the row now names a sharper next
test: *does a real `ai_memories` corpus contain prose personal names?* That
needs production rows this clone does not have, **recorded rather than
guessed**.

---

## 6. ITEM 4 — SAIRNDENTAL A11Y: FOUR FIXES, RE-RENDERED

**The first accessibility pass on any SAIRN app.** Each fix carries a counted
assertion in `scratchpad/b36/a11y_fix.py`.

| | fix | measured |
|---|---|---|
| A | `:focus-visible` outlines | visible ring across 5 panels **8/26 → 26/26** |
| B | 144 labels associated by `for`/`id` | unlabelled inputs **147 → 3** |
| C | `role="dialog"` + `aria-modal="true"` | **0 → 7 of 7** modals |
| D | Escape closes an open modal | **confirmed true** in the browser |

**On (A):** the global rule set `outline:none` on every input, select and
textarea, leaving only a 1px border-colour change. The `outline:none`
declarations are **left in place and overridden** — deleting them changes the
*resting* appearance of every control, where this changes only the focused
state.

`checkblocks` **5/0**; `wcag_contrast_check --gate` **0 findings**.

### Two things that nearly shipped silently

1. **An assertion refused the Escape listener.** `'</body>'` appears **twice**
   — the first inside a **JavaScript string at `:5750`** building a print
   document. A blind replace would have injected the listener into generated
   print markup and left the real page without it: working by appearance,
   broken in fact. Re-anchored on the last occurrence.
2. **The first verify run read from browser cache** and showed all four fixes
   absent. Without a cache-buster this would have been reported as a false
   failure.

### What remains, with line numbers

* **3 inputs still unlabelled** — `#gkey` (`:230`, licence gate),
  `#icap-file` (`:428`, a `display:none` file input), `#tp-item-planned`
  (`:981`, its label has no `id` to point at).
* **NO FOCUS TRAP** on any of the 7 modals. Deliberately not half-built: a
  trap needs per-modal first/last bookkeeping and a return-focus target, and
  half of one reads as done.
* **No panel-change announcement.** `nav()` toggles `.on` with no `aria-live`
  region, so a screen-reader user gets no notice that the panel changed.
  2 `aria-live` attributes exist in the file, neither on the switcher.
* **NO ACTUAL SCREEN-READER TEST WAS RUN.** This was a mechanical audit
  (roles, labels, focus, keys) driven through the DOM. NVDA/JAWS/VoiceOver
  were not used, and that is a different and stronger check.

---

## 7. ITEM 5 — THE AUDIT TARGET'S PREMISE DID NOT HOLD

**All four named verticals already have a current audit:**

| vertical | audits | newest |
|---|---|---|
| sairnlaw | 2 | 2026-09-26 |
| sairncode | 2 | 2026-09-26 |
| sairnbiz | 1 | 2026-09-26 |
| sairndesign | 1 | **2026-10-05** |

None older than four weeks. **Three apps have ZERO:** `sairndental`,
`sairnmechanical`, `sairnroofing`. **Took sairndental** — no audit at all, and
already open for §6 so the code recon is first-hand.

**THE RESULT INVERTS THE SERIES.** The previous four audits each found a market
gap SAIRN had no capability to fill. **This one found the gap the 2026 dental
market most loudly names — eligibility + denials + credentialing in one tool —
already three-quarters built here**: `dnt_denial`, `dnt_credentials` /
`dnt_cred_rules`, `dnt_coverage_rules`, plus `dnt_gfe`, which incumbents mostly
lack.

**THE BLOCKER IS FLAGGED AS A COMPANY DECISION.** Real-time eligibility is an
X12 270/271 transaction requiring a **commercial clearinghouse contract**
(DentalXChange, Vyne et al) — reported at **$40–60K integration, $20–40K/year,
$0.15–0.51 per transaction**. Same class as trucking's administered-service
blocker, narrower in scope. **Four of five series blockers are now company
decisions.**

**Sourcing is weaker than pest-control's and trucking's and the audit says
so:** no primary regulatory citation was pulled, and several sources sell into
this exact gap.

---

## 8. WHAT IS OPEN — EXACT NEXT STEP PER ITEM

1. **`rtroutes_saved_sane` vs negative savings (§3).** Drop the constraint —
   do **not** clamp the module. Needs whoever next holds `sql/`.
2. **`mech_schedule` (§4)** — scoped work, then the card is three edits.
3. **`api/sd-data.js`'s `rt_routes` handler branch — STILL unapplied.** cody
   holds it. Pasteable in `docs/2026-10-19-fourth-b34-routing-phase1.md` §3.
   **All four wired consumers remain unreachable at runtime.**
4. **`sql/rt_routes_schema.sql` — still never run.** Michael's.
5. **cc:** the `shared.js` skip fix (b35, measured to clear 8 findings), and
   the b34 Tier A review obligation on `rt_routes`/`rt_stops`.
6. **sairndental a11y remainder (§6):** focus trap, panel-change announcement,
   3 labelled inputs, and a real screen-reader test.
7. **Dental audit §6.1:** the clearinghouse decision. Michael's.
8. **sairnmechanical and sairnroofing still have zero audits.**

---

## 8b. EACH b36 ITEM: DONE / PARTLY DONE / NOT STARTED

| # | item | state | exact next step |
|---|---|---|---|
| 1 | publish + re-check `rt_routes_schema.sql` | **DONE** — column check **completed**, file published unedited | drop `rtroutes_saved_sane` (§3) |
| 2 | SAIRNmechanical as fifth consumer | **NOT STARTED — STOPPED AND REPORTED** (correct outcome, not a skip) | build `mech_schedule`, then 3 edits (§4) |
| 3 | measure `complete:false` rate | **DONE** — 100%, 193 samples, row corrected | optional: prose-name check on a real corpus |
| 4 | sairndental a11y | **PARTLY DONE** — 4 fixes landed and re-rendered; focus trap, panel announcement, 3 labels and a real SR test remain | §6 "What remains", with line numbers |
| 5 | competitive-gap audit | **DONE** — target premise corrected, sairndental audited | §6.1 of the audit: the clearinghouse decision |
| 6 | push, confirm landed | **DONE** — `3c7f7efa`, 0/0, 0 forbidden paths | — |

**Item 2 is the only NOT STARTED, and it is deliberate.** The data layer it
needs does not exist and the app's own code twice says building it is separate
scoped work.

---

## 9. WHAT b36 PROVED vs LEFT UNPROVEN

**PROVED, measured or driven:**

* the schema matches the module and all four consumers on names and types; one
  CHECK contradiction found and located
* `complete:false` on 193/193, and `complete` is a hard-coded constant
* sairndental: focus 8/26 → 26/26, labels 147 → 3, modals 0 → 7, Escape works
  — all re-rendered after a cache-buster
* `checkblocks` 5/0, wcag gate 0 findings, routes suite 56/56
* my commit touches four files and **0** forbidden paths

**LEFT UNPROVEN:**

* **No screen-reader test was run** — §6 was a mechanical DOM audit.
* **The negative-saving defect is reasoned, not reproduced** — the table does
  not exist, so no insert was attempted.
* **Nothing live.** Unchanged from b34/b35 and for the same measured reason.
* **The dental audit drove no competitor product and interviewed nobody**, and
  pulled no primary regulation.
* **SAIRNdental's GFE/denials/credentialing panels were read from the registry,
  not audited for correctness.** Existing and being right are different claims.
* **`memory`'s prose-name exposure in a real corpus** — needs production rows.
