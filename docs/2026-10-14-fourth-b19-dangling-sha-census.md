# The 34 REVIEWED records whose sha no longer resolves — classified, every one

**fourth, batch b19, 2026-10-14.** Measured against `origin/main` at the time of
the run; **re-run before quoting any number here** (`--list` and
`--reseat-shas` are the commands, and the register moves hourly).

**WHY THIS EXISTS.** My b18 handoff recorded *"34 of 88 REVIEWED records carry a
sha that no longer resolves"* and said the tool's own words about it: *"RE-RUN
WITH `--include-reviewed` TO EXAMINE THEM. Until then this run says nothing
about them, which is not the same as saying they are fine."* **That sentence was
the whole content of the b18 claim. This document is the examination it
deferred** — all 34, each classified, with the tool work routed rather than
done, because `tools/` is cc's.

---

## 0. THE MEASUREMENT, AND THE b18 FIGURE IS CONFIRMED EXACTLY

```
CMD PYTHONIOENCODING=utf-8 python tools/tier_a_review_gate.py --reseat-shas --include-reviewed
    distinct file sets indexed : 1584
    population                 : open + reviewed (--include-reviewed)
    records examined           : 252
    reachable already          :  66   -- not touched
    reseatable                 :   1   (subject twin or exact file set)
    reseatable, WEAK           :  13   (file-set subset in a 6h window)
    REFUSED                    : 172   -- named below with the reason
```

| | count | derivation |
|---|---:|---|
| records in the register | **252** | 233 `reviewed` + 19 `open` |
| records carrying an `opened_at_sha` at all | **107** | all 19 open, plus **88** reviewed |
| **REVIEWED records carrying a sha that no longer resolves** | **34** | 88 − 54 reachable |
| open records with a dangling sha | **7** | 19 − 12 reachable |
| reachable, total | **66** | 54 reviewed + 12 open ✓ |

**34 of 88. The b18 figure reproduces exactly**, which is worth saying because
the b18 note was quoting the tool rather than deriving it, and a quoted figure
that survives an independent derivation is a different thing from one that has
only ever been repeated.

### THE BIGGER NUMBER b18 DID NOT MENTION, AND IT IS NOT A DANGLING SHA

```
  REFUSED: NO_SHA_AT_ALL   ->  145 records, every one `reviewed`
           oldest 2026-09-15 … newest (within the reviewed population)
```

**145 reviewed records have no `opened_at_sha` in the first place.** They
predate the sha stamp. **That is a different fact from "a sha that no longer
resolves" and must not be folded into it:** a record with no sha never claimed
one, and nothing about it is broken. A record **with** a sha that dangles made a
claim that is now unverifiable. **145 + 34 = 179 reviewed records whose subject
cannot be re-derived from the register alone** — and only 34 of those are a
defect. The rest are history.

**This is the finding of the census, and it is a framing finding rather than a
code one:** "34 dangling" sounds like the problem. **The problem is 179
unre-derivable reviews, of which 145 are simply old.** Any fix that targets only
the 34 leaves 80% of the unre-derivable population untouched, and any report
that says "34" without saying "of 179" overstates how much a re-seat would buy.

---

## 1. THE 34, CLASSIFIED

### By disposition

| classification | count | what it means | can it be fixed mechanically? |
|---|---:|---|---|
| **RESEATABLE-WEAK** | **10** | a commit within a 6h window whose file set is a **superset** of the record's | **Yes, with two flags** — `--write --write-weak-basis`. Containment is not equality and the tool splits them on purpose |
| **REFUSED: NO_OBJECT_IN_CLONE** | **7** | the sha is not in this clone's object store and **no commit anywhere carries that file set** | **No.** Reseatable by subject only from the clone whose rebase orphaned it |
| **REFUSED: AMBIGUOUS_EXACT_SET** | **6** | **several** commits match the file set exactly — so a re-seat would be a guess between them | **No, and refusing is right** |
| **REFUSED: NO_OBJECT_IN_CLONE + SUBSET_AMBIGUOUS** | **4** | absent **and** the subset candidates are ambiguous. The worst class | **No** |
| **REFUSED: EXACT_SET_OUT_OF_WINDOW** | **3** | an exact file-set match exists but **outside** the time window the tool trusts | **No by default** — and the window is the judgment call |
| **REFUSED: TWIN_SUBJECT_AMBIGUOUS** | **2** | two commits share the subject line | **No** |
| **REFUSED: SHA_WRONG_WHEN_WRITTEN** | **2** | **the sha was wrong at the moment it was written** — not orphaned afterwards | **No — and this is the only class that is a WRITE-TIME defect** |

**SHA_WRONG_WHEN_WRITTEN is the one to read twice.** The other six classes are
all "the graph moved under a correct record". These two are "the record was
never right". **A rebase cannot cause this; only the stamping path can** — so it
is the only class that implies a defect in the tool rather than in the history.

### By author of the reviewed change

| author | count |
|---|---:|
| hank | **13** |
| fourth | **9** |
| cody | **7** |
| cc | **5** |

**Distributed roughly in proportion to who commits, which is the answer that
means "nobody's workflow is the cause".** It is not one session rebasing badly.

### Every one of the 34, in full

Format: `opened_at | author -> reviewer | recorded sha | classification | re-seat
target | resources (first 3) | file count`.

```
2026-09-25T15:08:08Z | cody   -> hank   | 51acc0ff6543 | RESEATABLE-WEAK | 47220a5d4c52 | invoices, sdn_clients                                  | 1
2026-09-26T00:13:53Z | hank   -> cc     | 7be498714a9c | RESEATABLE-WEAK | 72ba2261048b | mech_credentials, mech_site_assets                     | 2
2026-09-26T01:04:07Z | cc     -> fourth | 0800cd7d99be | RESEATABLE-WEAK | e683f59b52b8 | sdn_timeentries, sf_accounts, sf_members                | 2
2026-09-26T01:43:54Z | cc     -> hank   | 59e85d77fb37 | EXACT_SET_OUT_OF_WINDOW       | — | alf_clients, alf_incidents, alf_mar      | 2
2026-09-26T11:44:25Z | fourth -> cc     | 99ecd95a6dca | AMBIGUOUS_EXACT_SET           | — | exec_context, law_clecredits, rf_settings| 2
2026-09-26T12:36:06Z | hank   -> fourth | 82aaa2fd628d | RESEATABLE-WEAK | c0ae9a0a5354 | alf_mar, mech_credentials                              | 3
2026-09-26T13:38:34Z | cc     -> cody   | 1d8137609814 | RESEATABLE-WEAK | f3484b3c5889 | sv_audit_log                                           | 1
2026-09-26T17:36:42Z | hank   -> cody   | 0c53d58363a9 | NO_OBJECT_IN_CLONE            | — | alf_compliance_rules, sc_claims, sc_coded_items | 2
2026-09-26T17:39:03Z | fourth -> cc     | 11f5f4181e42 | RESEATABLE-WEAK | 1f9936429432 | invoices                                               | 2
2026-09-26T18:53:22Z | fourth -> cody   | 496ca6514724 | RESEATABLE-WEAK | 944a5faadae5 | rf_certifications, rf_claims, sd_quote_requests        | 4
2026-09-27T01:22:40Z | hank   -> cody   | e05276ed9549 | NO_OBJECT_IN_CLONE            | — | mech_insurance_policies, mech_site_assets, sc_anesthesia | 2
2026-09-27T02:06:03Z | cody   -> cc     | 0f9d1eb9f143 | NO_OBJECT_IN_CLONE            | — | mech_credentials, mech_site_assets, sc_claims | 3
2026-09-27T02:31:54Z | hank   -> cc     | b9b9525d17d7 | NO_OBJECT+SUBSET_AMBIGUOUS    | — | alf_compliance_rules, alf_staff, alf_staff_credentials | 4
2026-09-27T03:05:32Z | cody   -> fourth | 49b0d2ec8158 | AMBIGUOUS_EXACT_SET           | — | sb_ts                                     | 1
2026-09-27T03:24:52Z | cody   -> fourth | 5192346a1d24 | AMBIGUOUS_EXACT_SET           | — | sen_caregivers, sen_clients, sen_visits   | 1
2026-09-27T03:42:29Z | hank   -> fourth | 54e4835ac96e | NO_OBJECT_IN_CLONE            | — | alf_staff, sen_visits                     | 4
2026-09-27T12:34:26Z | hank   -> cc     | e7d5e05ae6a9 | NO_OBJECT_IN_CLONE            | — | alf_billing, sen_visits                   | 3
2026-09-27T23:49:53Z | cody   -> cc     | b55ff8c52cf7 | RESEATABLE-WEAK | 5c03c0ae7d58 | quotes                                                 | 1
2026-09-28T01:24:38Z | fourth -> cody   | d617d7fabc47 | AMBIGUOUS_EXACT_SET           | — | alf_activities, alf_billing, alf_claim_routes | 2
2026-09-28T19:34:37Z | fourth -> cc     | fff078df83e6 | NO_OBJECT+SUBSET_AMBIGUOUS    | — | quotes                                    | 1
2026-09-28T21:33:14Z | hank   -> cc     | 50c32b02a46d | RESEATABLE-WEAK | cc956d9ec115 | quotes                                                 | 1
2026-09-29T10:44:09Z | cc     -> cody   | 4cc70be89999 | AMBIGUOUS_EXACT_SET           | — | alf_billing, invoices                     | 1
2026-09-29T12:46:19Z | fourth -> cc     | 7d15d0a27af0 | TWIN_SUBJECT_AMBIGUOUS        | — | alf_family_contacts, alf_incidents, sen_visits | 3
2026-09-29T14:00:49Z | fourth -> cody   | e4b3f21a2ceb | TWIN_SUBJECT_AMBIGUOUS        | — | quotes, sf_trustee_audits, sf_vehicle_service | 3
2026-09-29T14:46:23Z | fourth -> cody   | c4dd292fd8a8 | SHA_WRONG_WHEN_WRITTEN        | — | mech_quotes, scp_quotes, sf_trustee_audits | 3
2026-09-30T11:08:08Z | fourth -> hank   | 00030f2d11b7 | SHA_WRONG_WHEN_WRITTEN        | — | bld_jobs, bld_photo_analyses, grd_progress_photos | 1
2026-09-30T15:15:56Z | cody   -> hank   | 2d61bc91eb85 | AMBIGUOUS_EXACT_SET           | — | rf_cert_rules, rf_contingency_rules, stonedesk_quote_history | 1
2026-10-05T09:25:27Z | cody   -> cc     | 6dd690d61081 | EXACT_SET_OUT_OF_WINDOW       | — | sd_crm                                    | 1
2026-10-05T12:35:55Z | hank   -> cody   | f9f6786cca15 | NO_OBJECT+SUBSET_AMBIGUOUS    | — | sb_perf                                   | 2
2026-10-05T21:33:08Z | hank   -> cody   | 4b1e81df2403 | EXACT_SET_OUT_OF_WINDOW       | — | sd_comms                                  | 1
2026-10-07T13:46:11Z | hank   -> cc     | f1d2fd198878 | NO_OBJECT_IN_CLONE            | — | alf_activities, alf_billing, alf_clients  | 5
2026-10-07T15:13:50Z | hank   -> cc     | 07b3fc837835 | NO_OBJECT+SUBSET_AMBIGUOUS    | — | alf_activities, alf_billing, alf_facility | 1
2026-10-12T11:35:03Z | cc     -> hank   | 518a0a902fd3 | RESEATABLE-WEAK | 86189e37d552 | bld_bids, bld_draws                                    | 2
2026-10-14T11:55:18Z | hank   -> fourth | 3a2fa87fde45 | NO_OBJECT_IN_CLONE            | — | bld_photo_analyses, grd_progress_photos, mech_checks | 5
```

**THREE OBSERVATIONS THE TABLE MAKES AND A COUNT DOES NOT:**

1. **`2026-09-27T03:42:29Z` IS b18's OBLIGATION.** The 418-hour one I discharged
   last batch is in this list — `NO_OBJECT_IN_CLONE`, and it is why that verdict
   had to be a state review. **This census explains, mechanically, why that
   discharge was bounded the way it was.**
2. **The newest entry is three hours old** —
   `2026-10-14T11:55:18Z`, `hank -> fourth`, `NO_OBJECT_IN_CLONE`, five files
   including `api/_lib/ai-safeguards.js`. **This is not a historical backlog. It
   is happening today**, and that record was *reviewed* with an already-dangling
   sha.
3. **Six of the 34 name `docs/CRITICALITY-TIERS.md` as their only file.** Those
   are register-row reviews, and their file set is the single most-touched
   document on the platform — which is exactly why their exact-set matches come
   back AMBIGUOUS. **The tool is not failing on those; the file set is simply
   not discriminating.**

---

## 2. WHAT I DID NOT DO, AND WHY

**I ran the census read-only and wrote nothing to the register beyond my own two
discharges.**

* **I did not run `--reseat-shas --write`.** One record is strong-basis
  reseatable (`hank 2026-10-13T09:03:35Z`, EXACT FILE SET) and it is **open**,
  not one of the 34. The 10 weak ones need `--write --write-weak-basis`, and
  **the tool splits those across two flags deliberately: containment is a
  different claim from equality and must not ride along on one keystroke.**
  Re-seating 10 of somebody else's reviewed records from my clone, on a
  containment basis, is a register-wide write on a judgment I am not the owner
  of.
* **I did not re-open any of the 34 reviews.** A dangling sha does not make a
  verdict wrong; it makes the verdict's *subject* unre-derivable from the
  register. **Those are different harms and only the second is present.**
* **I did not build the tool work.** `tools/` is cc's. Routed below by
  `file:line`.

---

## 3. ROUTED TO cc — four asks, by `file:line`

All four are in `tools/tier_a_review_gate.py`. Line numbers re-derived at HEAD
immediately before writing this, **and anchored on quoted text so they survive
the next rebase**:

| # | ask | anchor |
|---|---|---|
| **1** | **Separate NO_SHA_AT_ALL from the dangling population in every output.** The `--include-reviewed` summary currently reports `REFUSED: 172` as one number, 145 of which are records that never had a sha. **A reader cannot tell a defect from a date.** Print them as two populations with two counts. | the refusal classifier that emits `NO_SHA_AT_ALL`; the summary block that prints `REFUSED             : %d -- named below with the reason, never silently skipped` |
| **2** | **`SHA_WRONG_WHEN_WRITTEN` deserves its own exit path.** It is the only class that implies the stamping path was wrong rather than the graph having moved, and it is currently one refusal reason among seven. **Two records carry it. Either the stamp had a bug on 2026-09-29/09-30 or those two records were hand-edited — both answers matter and neither is visible.** | the branch that sets `SHA_WRONG_WHEN_WRITTEN` |
| **3** | **Make the `EXACT_SET_OUT_OF_WINDOW` window a stated, overridable number rather than a silent constant.** Three records have an exact file-set match that the window rejects. **An exact file-set match outside a 6h window is better evidence than a subset match inside it**, and today the first is refused while the second is offered as WEAK. That ordering is backwards and it is a one-constant decision, not a rewrite. | the window constant used by the subset/exact comparison, and the `6h window` wording in the WEAK-basis message |
| **4** | **Stamp at open time from `git rev-parse HEAD` in the SAME commit that writes the record**, if it does not already. Observation 2 above — a three-hour-old record whose sha was already absent — means either the stamp is taken before the commit that carries it, or the opening session rebased between stamping and pushing. **`--reseat-shas` is a repair for a defect that should be preventable**, and the repair is the thing that keeps being asked for. | the `--open` path's sha stamp |

**Ask 4 is the one that stops this document needing to be written again.** The
other three make the census legible; only 4 reduces the population.

**PRIORITY, stated so it is not read as four equal asks:** 1 first (it is a
print change and it stops a 172 being read as 172 defects), then 4 (it is the
only preventive one), then 2, then 3.

---

## 4. UNVERIFIED

* **Whether any of the 10 weak re-seats is CORRECT.** The tool says "file-set
  subset within 6h". I did not open the 10 candidate commits and compare. **A
  plausible candidate is not a verified one**, and that is precisely why the
  second flag exists.
* **Whether the 2 `SHA_WRONG_WHEN_WRITTEN` records were mis-stamped by the tool
  or hand-edited afterwards.** Both were authored by `fourth` — me — which is
  the one detail that makes it worth saying out loud rather than routing
  quietly. Deciding it needs the stamping path's history read against those two
  commits, and I did not do it.
* **Whether any of the 145 NO_SHA_AT_ALL records could be reconstructed at all.**
  `--backfill-shas` exists and I did not run it, even dry. **It is named here as
  the obvious next measurement, not as a recommendation** — a backfilled sha and
  a stamped one must not become indistinguishable, and the tool already says it
  marks the difference.
