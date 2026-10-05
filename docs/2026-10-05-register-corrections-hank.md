# Register corrections — derived at HEAD, text only

**2026-10-05 (hank).** Items 5, 6 and 7. **Nothing here is applied.** Every line
number below was re-derived from the file at HEAD; **not one was taken from the
queue**, and where the queue's number disagrees with the file, the file wins and
the disagreement is recorded.

`docs/CRITICALITY-TIERS.md` is not under anyone's claim right now, but the brief
says text-only, so text it is. `docs/SAIRN-OPEN-WORK-INDEX.md` **is** cc's
(live), which is why §7 is paste-ready rather than applied.

---

## 0. Item 8 — the premise log, one line per item

| Item | Subject | Premise at HEAD |
|---|---|---|
| 1 | `rebase_state_guard` seq 452 | **HELD** — 15 of 34 forms bypassed `forbidden_forms()`; fixed, 34/34 |
| 2 | registry tail 44–72 | **PARTLY FALSE** — the sweep was already loud (names them, exit 1); the silence was `--list` |
| 3 | `push_retry` usage crash | **HELD** — exit 1, `UnicodeEncodeError`, 0 `reconfigure` |
| 4 | manifest drift, 6 tools | **HELD** — now 7; all 6 committed ones trace to real commits |
| 5a | #745 queue6, 5 repoints | **UNVERIFIABLE FROM THIS CLONE** — see §1 |
| 5b | #747 `dnt_providers` | **FALSE** — row 310 cites **nothing** |
| 5c | #760 `rf_buildings`, `rf_photos` | **FALSE** — rows 504 and 519 cite **nothing**; sairnroofing has 0 drifted |
| 5d | #764 four repoints, `sb_perf`, `sb_ap` | **MIXED** — the numbers are wrong, and the **real** drift is one the tool cannot see. §4 |
| 5e | #768 `sen_franchise_agreements` | **FALSE** — row 558 cites **nothing** |
| 5f | #777 `sc_encoder` −7/−7 | **FALSE** — both citations are **deliberate and correct** |
| 5g | #780 `leg_monuments` | **FALSE** — `:4085` is **sound**, 5 lines from the write |
| 5h | #782 `dnt_cred_rules` | **FALSE** — row 301 cites **nothing** |
| 6 | #772 `sdn_timeentries` + `sdn_vendors` PII | **SPLIT** — drift FALSE, **PII HOLDS and is 10 days old** |
| 7 | rows 82 / 845 | **HELD** — both stale; cc's file, so §7 is text |

**Eight of the thirteen register premises are FALSE at HEAD.** That is the
headline, and it is the same shape as last round: a routed finding that was true
when logged, overtaken, and never re-checked. The difference is that this time
**the routing itself carried numbers that never matched the file** — see §4.

---

## 1. Item 5a — #745 cannot be verified from here, and I will not guess

The queue names a *"queue6 package, 5 register repoints, still unapplied."* I
could not find it:

* no doc under `docs/` carries a queue6 repoint package
* `grep -rn "#745"` over `docs/` → nothing
* the only hit anywhere in this clone is
  `.claude/skills/sairn-hover-auditor/tools-hover2/hover_citation_linter.py`

**Hover log #745 lives in the auditor's own tamper-evident record, in
`Documents\SAIRN-hover`** — a clone a build agent must not reach into
(`docs/2026-09-15-hover-auditor-separation-enforcement.md`;
`tools/hover_auditor_scope_gate.py` enforces it).

**So five repoints are named and I cannot see which five.** I am not inferring
them from the other items: a guessed repoint applied to a register is worse than
an unapplied one, because it looks done. **Needs hover to route the package into
a doc in this repo, or a paste of the five rows.**

---

## 2. Items 5b, 5c, 5e, 5h — four rows cite nothing at all

Derived by reading each row and extracting every `` `:NNN` `` and
`` `file.html:NNN` `` from it:

| Item | Row | Resource | Citations found | Write sites in the app |
|---|---|---|---|---|
| 5b | `:310` | `dnt_providers` | **NONE** | none resolvable |
| 5h | `:301` | `dnt_cred_rules` | **NONE** | none resolvable |
| 5c | `:504` | `rf_buildings` | **NONE** | none resolvable |
| 5c | `:519` | `rf_photos` | **NONE** | none resolvable |
| 5e | `:558` | `sen_franchise_agreements` | **NONE** | `sairnsenior.html:4732` |

**A row with no citation cannot have a drifted one.** There is nothing to
repoint, and `citation_line_drift_check.py` agrees independently: sairndental
reports **0 DRIFTED**, sairnroofing **0 DRIFTED**, and neither
`sen_franchise_agreements` nor `dnt_cred_rules` appears in any drift list.

The queue describes 5h as *"two large evaluateBoard drifts."* There is **no
`:NNN` citation of any size on that row**, and `evaluateBoard` is not cited by
it. I cannot reconcile that description with the file and I am not inventing a
reading of it.

**What these four rows actually need is the opposite of a repoint — a FIRST
citation.** `sen_franchise_agreements` is the only one with a resolvable write
site (`sairnsenior.html:4732`), so it is the only one where adding a citation is
mechanical today. The other three have no resolvable write site at all, which is
a separate and larger question than citation accuracy.

---

## 3. Items 5f, 5g — three citations that are correct, and must not be touched

### 5f `sc_encoder`, row `:277` — the queue says “−7/−7”; both citations are deliberate

| Cited | What is actually there | Verdict |
|---|---|---|
| `:4681` | `var s = localStorage.getItem('sc_encoder')` | **SOUND** — and the row cites it *as a read*: *“`getEncoderCodes()` at `:4681` reads it”* |
| `:10427` | `// Tier 1 -- the practice's OWN connected reference data (sc_encoder,` | **CORRECT** — the row cites it *as a comment*: *“The comment at `:10427` names the order”* |
| `sairncode.html:4729` | `list.push({id:'ec'+Date.now(), code:code, type:type, desc:desc, bundling:bundling});` | **CORRECT** — matches the row's *“writes `{id, code, type, desc, bundling}`”* exactly |

**There is no −7 anywhere.** `citation_line_drift_check.py` does report
`sc_encoder :10427 -> :4690 offset -5737`, and **that is the false positive
class I fixed in that tool yesterday**: `:10427` is a comment the cell cites on
purpose, and repointing it to the `setItem` would make the cell's own sentence
false. The tool now prints the cited line's text next to the arrow precisely so
this is visible in one read.

### 5g `leg_monuments`, row `:478` — sound, 5 lines from the write

Cites `:4085` = `var rec={id:ceid||newId('MN'), case_id:caseId, vendor_name:…, monument_type:…` — the row construction. Write site is `:4090`. **Five lines apart; well inside the window.** Not drifted. sairnlegacy reports 27 sound, 3 drifted, and `leg_monuments` is not among the three.

---

## 4. Item 5d — the numbers are wrong, and the real drift is one no tool can see

### What the queue said, and what the file says

The queue: *“four drift repoints, largest `sb_perf` +1723/+429. One `sb_ap` citation is unrepointed: derive it, do not guess.”*

Derived at HEAD:

* **`sb_ap`, row `:189`, cites NOTHING.** There is no `sb_ap` citation to repoint, drifted or otherwise. Its write sites are `:2154`, `:3138`, `:3930`, `:4041`.
* **`sb_perf`, row `:198`, has no +1723 and no +429.** It carries three citations, and **two of them are wrong** — but not the one the tool flags.

### THE FINDING: 188 citations in 147 rows are invisible to the drift checker

`tools/citation_line_drift_check.py` extracts citations with `` `:(\d+)` `` — the **bare** form only. Measured over `docs/CRITICALITY-TIERS.md` at HEAD:

    bare  `:NNN`            285   <- the only form the tool reads
    named `file.html:NNN`   188   <- INVISIBLE to it
    rows carrying a named-form citation: 147

**So every verdict that tool has ever printed covers 285 of 473 citations — 60% — and it does not say so.** A run reporting “SOUND: 27, DRIFTED: 3” is reporting on a partial denominator presented as the answer. That is the coverage-disclosure class, and it is in the tool I corrected yesterday for a different defect in the same function.

**This is where `sb_perf`'s real drift was hiding.**

### `sb_perf` row `:198` — three citations, two wrong

| Cited | Row's claim about it | What is at that line | Verdict |
|---|---|---|---|
| `sairnbiz.html:448` | *“rows are `{emp, type, due, rev, score, raise, pip, status}`”* | `<button class="btn bo" onclick="closeHireModal()">Cancel</button>` | **WRONG** — a Cancel button in the hire modal |
| `:4714` | *“exported with those headers at `:4714`”* | `$('tr-cert').textContent=tr.length; … $('tr-bud').textContent=fmt(spend);` | **WRONG** — the training KPI tiles, no export, no `sb_perf` |
| — | — | — | — |

Both derived replacements, found by searching for the claim rather than by offsetting the old number:

    rows are {emp,type,due,rev,score,raise,pip,status}
        LIVE WRITE  sairnbiz.html:2480
          p.push({emp:emp,type:$('rvtype').value,due:$('rvdue').value,
                  rev:$('rvrev').value.trim()||'Owner',score:…
        SEED        sairnbiz.html:2171-2175   identical shape, inside st('sb_perf',[ at :2170

    exported with those headers
        sairnbiz.html:5143
          else if(type==='performance'){rows=[['Employee','Type','Due',
            'Reviewer','Score','Raise','PIP','Status']];ld('sb_perf',[])…

`:5143` is an exact match for the row's sentence — the header list is literally `Employee, Type, Due, Reviewer, Score, Raise, PIP, Status`, and it reads `sb_perf`. The claim was true; only the number had moved.

### Paste-ready, for `docs/CRITICALITY-TIERS.md:198`

Replace, inside the evidence cell:

> `sairnbiz.html:448`  →  `sairnbiz.html:2480`
>
> `exported with those headers at `:4714``  →  `exported with those headers at `:5143``

and append:

> **CITATIONS RE-DERIVED 2026-10-05 (hank).** Both line numbers in this cell had
> drifted and **neither was visible to `citation_line_drift_check.py`**, which
> reads only the bare `` `:NNN` `` form: `:448` was the hire modal's Cancel
> button and `:4714` was the training KPI tiles. The row's two CLAIMS were both
> true and only the numbers had moved — the shape is written at `:2480` (live)
> and seeded identically at `:2171-2175`, and the export carrying
> `Employee, Type, Due, Reviewer, Score, Raise, PIP, Status` is at `:5143`.
> **The tier is untouched:** A on confidentiality for the `pip` flag, exactly as
> re-tiered 2026-09-25.

### The other four SAIRNbiz drifts, NOT recommended for repointing

`citation_line_drift_check.py` also reports `sb_exps :4005/:3702`, `sb_hire :1993`, `sb_train :4507`, `sb_vends :3745` and `sb_perf :4714 -> :2481`. **I did not read those five rows' prose**, and after `sb_perf` and `sc_encoder` the base rate on this document says roughly half of them will be deliberate render or read citations. **Each needs its own prose read before anything is repointed** — which is the whole finding from yesterday, and I am not about to repeat it in the other direction.

---

## 5. Item 6 — `sdn_timeentries` is sound; `sdn_vendors` contradicts the code, and has for 10 days

### `sdn_timeentries`, row `:342` — premise FALSE

Cites `:3136` and `:3140`; write sites `:1623` and `:3167`. Both citations are within 31 and 27 lines of `:3167` respectively — inside the window, **sound**. `sairndesign` reports 7 drifted and `sdn_timeentries` is not among them.

### `sdn_vendors`, row `:343` — premise HOLDS, and it is a flat contradiction

The cell asserts, absolutely:

> *“No elevated confidentiality class — **no PII**, PHI, privileged communication, or financial-account detail on this row. Classified by the stated B rule rather than individually read.”*

The code writes, at `sairndesign.html:2613-2614`:

```js
var rec={id:veid||newId('VN'),name:name,category:$('vcat').value,contact_name:$('vcontact').value.trim(),
  phone:$('vphone').value.trim(),email:$('vemail').value.trim(),lead_time_typical_weeks:…
```

**`contact_name` + `phone` + `email` is a named individual's direct contact detail.** The seed at `:1607-1611` makes it unmistakable: `contact_name:'Jamie Rourke', phone:'(800) 555-0100', email:'trade@rh.example.com'`.

**AND THE REGISTER WAS TOLD. `10855b55` (2026-09-25) says, in its own commit body:** *“sdn_vendors, one of the nine still ungated, is the row that actually carries named individuals' phone and …”*. **Ten days; the cell still says “no PII”.**

Note the cell's internal contradiction, which is the same shape as `mech_docs` last round: an **absolute** claim and an admission that it was **never individually read**, in one sentence.

### THE REASONING FIX, AND THE TIER DOES NOT MOVE

Asked for as a reasoning fix first, then the citation. The reasoning:

**The no-PII clause is false and must go. B is still correct, on established precedent rather than on a fresh call.** The register already answers this exact question for business-contact data: `properties` (SAIRNgrounds, row `:418`) carries *“a client's contact name, phone, email and address”* and is **B** — *“The `sd_customers` class — commercially sensitive, not an elevated one.”* A trade vendor's sales contact is that same class: a work phone and a work email for a person acting in a business capacity, not a special category and not a regulated record.

**So the correction removes a false clause and leaves the tier, which is the honest outcome — not a re-tier.** Bending the tier to match a corrected clause would be the wrong direction, exactly as with `mech_insurance_policies` on 2026-09-26.

### Paste-ready, for `docs/CRITICALITY-TIERS.md:343`

Replace the confidentiality cell:

> A trade vendor's record **including a named individual's direct work contact
> detail** — `contact_name`, `phone`, `email`. The `sd_customers` /
> `properties` class: commercially sensitive, not an elevated one

Replace the evidence cell:

> **INDIVIDUALLY READ 2026-10-05 (hank), CORRECTING A CLAUSE THAT WAS FALSE
> WHEN WRITTEN AND WAS CONTRADICTED IN WRITING TEN DAYS AGO.** The cell said
> *“no PII … classified by the stated B rule rather than individually read”* —
> an absolute claim and an admission it was never checked, in one sentence.
> READ OUT OF THE APP: `saveVendor()` at `sairndesign.html:2613-2614` writes
> `{name, category, contact_name, phone, email, lead_time_typical_weeks,
> rating, notes, created_at}`, and the seed at `:1607-1611` carries five real
> examples (`contact_name:'Jamie Rourke', phone:'(800) 555-0100',
> email:'trade@rh.example.com'`). **`10855b55` (2026-09-25) already said so**:
> *“sdn_vendors … is the row that actually carries named individuals' phone
> and …”*. **TIER UNCHANGED AT B, and that is the finding rather than a
> formality:** this is a work phone and a work email for a person acting in a
> business capacity — the `properties` / `sd_customers` class, already settled
> at B on commercial sensitivity. The false clause is removed; the tier it was
> attached to was right for a different reason than the one given.

---

## 6. Item 7 — rows 82 and 845, paste-ready. **cc's file; not edited.**

`docs/SAIRN-OPEN-WORK-INDEX.md` is in cc's live claim. Flagged to cc in the
shared status registry as well as here.

### Row 82 — MINE, and it is wrong. Replace with:

> | **Process** | **&#9989; RETRACTED: `tools/tier_a_review_gate.py` DOES have `--reseat-shas`, and it did before this row was written** <!-- QUEUE26-INVENTORY-HANK-2026-10-04 --> | **RETRACTED 2026-10-05 (hank), BY THE SESSION THAT WROTE IT.** The row claimed there was *“no `--reseat` for a record whose FILE SET matches no single commit”* and *“no path to repair them at all”*. Both false. | hank | &mdash; | **DECIDING TEST, RUN AT HEAD:** `python tools/tier_a_review_gate.py --reseat-shas` &rarr; `open records: 40 / reachable already: 23 / reseatable: 1 / reseatable WEAK: 6 / REFUSED: 10`, each refusal named. The capability is at `:15-17` (usage), `:2634` (dispatch), `:2751` (`_reseat_base()`), and the **file-set-subset logic this row called missing is at `:2960-2971`** — it admits containment only when exactly one commit contains the set, no commit matches exactly, and it lands inside `WEAK_BASIS_WINDOW_HOURS`, then stamps `opened_at_sha_reseat_basis: 'file-set-subset'` so the weaker basis is never indistinguishable from the stronger. **It landed `b66b1ac9` on 2026-09-29 — the same day as the inventory that first claimed it was missing.** I carried that claim through two inventories and into this row **without once running the tool**. | S |

### Row 845 — not mine, and also stale. Replace with:

> | **Tooling** | **&#9989; `assertion_label_shape_check.py` IS in the report-only registry** | **CLOSED 2026-10-05 (hank), found while checking my own rows for duplicates.** | &mdash; | &mdash; | **DECIDING TEST:** `python tools/report_only_checks.py --list` &rarr; the tool appears. The row asserts it is absent; it is present. **Recorded as a class rather than as one session's slip:** this is the second index row found in one afternoon asserting a gap that had already closed, the other being row 82 above, and ~900 rows are unchecked by anybody. See `docs/2026-10-05-inventory-hank.md`. | S |

---

## 7. What I will not claim

* **I did not apply any register edit.** Text only, as instructed.
* **I did not fix the citation-coverage hole I found.** `citation_line_drift_check.py` reads 285 of 473 citations and does not disclose it. That is a criteria change to a checker, needs its own claim and its own known-bad control, and I already hold one change to that file this week — a second, unrequested, in the same batch is scope growth. **Logged; the measurement is in §4 so it need not be re-derived.**
* **I did not read the prose of `sb_exps`, `sb_hire`, `sb_train`, `sb_vends`,** or of the 7 `sen_`, 7 `sdn_`, 14 `sc_` and 3 `leg_` rows the tool flags. I read exactly the rows I was sent at, plus `sb_perf`.
* **I cannot see hover log #745** and did not infer its five repoints.
* **I did not verify `sen_franchise_agreements`' write site is the right citation** to add — only that `:4732` exists and is the sole `st()` for it.
* **The `sdn_vendors` tier call is mine and is arguable.** I rested it on the `properties` precedent. A reader who thinks a named individual's phone and email is an elevated class regardless of business capacity would re-tier it A, and that argument is not silly — it is just not the one this register has been applying.
