# Cody, queue 13 — what landed, what was already landed, and what is blocked

**2026-10-05. HEAD at the start of this session: `6b30168c`.** Everything below
was re-derived against the repo today; no figure is quoted from an earlier
document without being re-run, and where a figure moved, both numbers are given.

---

## 1. The previous paste — status of every item

**THE PASTE ITSELF IS NOT IN THIS SESSION'S CONTEXT, and that is stated rather
than worked around.** What follows is reconstructed from three sources that
*are* current: this clone's status row (`cody.json`, which says *"queue done:
items 1,2,3,4,5,6,7,10,11 landed; 8 claim-refused (ledger held at the time) and
reported"*), the commits on `origin/main` authored on 2026-09-30, and
`docs/2026-09-30-tier-a-obligation-cody-queue.md`, which lists that queue's
artefacts in full. **Item numbers below are mapped from the artefacts, not read
off the paste**, so treat the mapping as the weakest part of this section.

| what landed | sha | state |
|---|---|---|
| `tools/bare_run_writers.py` — the 20 tools whose bare run is *meant* to write, each with its path and reason | `c86050b4` | **DONE** |
| `tools/bare_run_write_check.py` — reads that list, reports entries as INTENDED rather than omitting them, fails on an undeclared path | `c86050b4` | **DONE** |
| `tools/tool_owner_header_check.py` + probe + push-gate wiring — a newly ADDED `tools/*.py` must carry `# OWNER:` | `c86050b4` | **DONE** |
| `tools/condition_coverage.py` — mutates a detached worktree instead of `api/_lib/ledger.js` | `a468b4b8` | **DONE** |
| `tools/nhi_register.py` — bare run report-only, sibling scan bounded (was 1865 git launches) | `a468b4b8` | **DONE** |
| Citation-drift sweep: one write-site model covered 2 apps of 14, and the sweep said so instead of reporting no drift | `9e3caeef` | **DONE** |
| Three StoneDesk suites re-anchored on stale expectations — none of the three was an app defect | `d9083b93` | **DONE** |
| `tools/dead_rule_sweep.py` probe section A sabotaged the tracked tool it controls — the same defect one layer up | `07115616` | **DONE** |
| `tools/sairn_claim.py` — warn at claim time when a task string names a file that resolves to nothing | `c60825a1` | **DONE**, and it shipped a crash: `33474f39` fixed the unresolvable-name warning taking down every real claim, and the probe arm that should have caught it **only grepped** |
| Generated-document regeneration for the queue's new tools and probes | `4d2ef931` | **DONE** |
| The Tier A review obligation for the queue | `b1e618f0` → `docs/2026-09-30-tier-a-obligation-cody-queue.md` | **CLAIM-REFUSED, recorded as a document instead.** `docs/tier-a-reviews.json` was held by hank and the claim tool refused twice, forty minutes apart. The obligation was written to a doc so it exists somewhere a human can read, with that weakness stated in the file. **It has since been moved into the ledger** — `2d61bc91`, author cody, reviewer hank, resources `rf_cert_rules` / `rf_contingency_rules` / `stonedesk_quote_history`, still `open` today. |

**NOTHING FROM THAT QUEUE WAS REDONE TODAY.** Each row above was confirmed
present at HEAD before this session started work.

**AND ONE THING THE STATUS ROW DOES NOT ACCOUNT FOR:** it names items
1–7, 10, 11 as landed and 8 as refused, which is ten of eleven. **Item 9 is
named by neither list.** I cannot tell from the repo whether it landed, was
dropped, or never existed, and I am not going to infer it from the artefact
list — that is exactly the kind of gap-filling that produced the
"a handoff item may already be built" class. **If item 9 of that paste
mattered, it needs re-stating.**

---

## 2. Fixture sets for the never-claimed tools — 1 of 7 done, and the set is not 39

**THE NUMBER 39 DOES NOT RE-DERIVE, AND THE CORRECTION MATTERS MORE THAN THE
COUNT.** Measured today against `.claude/claims/*.json` and
`report_only_checks.REGISTRY`:

```
report-only registry tools                        71
...never named in ANY claim by any session        42      (not 39)
tools/*.py on disk                               286
...never named in any claim                      159
```

**But only 7 of the 42 need a fixture set at all**, and that is the real work
list. `tools/dead_rule_sweep.py` at HEAD separates them:

| # | tool | rules needing work | state today |
|---|---|---|---|
| 1 | `write_without_readback_check.py` | 7 (it had **no evidence of itself at all** — COULD NOT RUN) | **DONE — `77b5b536`.** 7 of 7 ablatable, 7 exercised, 0 dead |
| 2 | `accepted_risk_expiry_audit.py` | `ACCEPTED`, `CLOSED_STATUS` | not started |
| 3 | `dependency_graph.py` | `REQ`, `ENV`, `BASELINE_RE`, `BASELINE_DATE_RE`, `SCHED_HEAD_RE`, `SCHED_DATE_RE` | not started |
| 4 | `register_freshness_check.py` | `BARE_PATH`, `SHA`, `CELL_FILE`, `CELL_CALL`, `CELL_CAMEL` | not started |
| 5 | `advisory_lock_isolation_check.py` | `READ_RE`, `AGG_RE`, `DROP_RE` | not started |
| 6 | `service_role_tier_a_gate_check.py` | `TIER_A_ROW` | not started |
| 7 | `overrun_inversion_scan.py` | `DISPLAYISH` | not started |

**ORDER.** "Claim-record order" has no content here — **none of the seven has
ever been claimed**, which is what puts them on the list. They are taken in the
order `dead_rule_sweep` reports them, which is report-only-registry order, and
`write_without_readback_check.py` was pulled to the front because it was the
only one in the COULD-NOT-RUN bucket without the "the tool writes when run"
excuse: a tool with **no** evidence is a worse state than a tool whose evidence
misses a rule.

**THE ONE THAT IS DONE PRODUCED TWO FINDINGS BEYOND THE MISSING FIXTURES,** and
they are the reason this is worth doing rather than box-ticking:

- **`WRITE_VAR_RE` had no consumer.** Compiled at module level, documented as
  the fix for the 2026-09-05 generic-write blind spot, and never read — SHAPE B
  of `resolve_generic_writes` re-spelled the identical pattern inline. Two
  copies, one dead. Item 43: a second copy is not a second opinion.
- **`WRAPPER_RE`'s only consumer was a field nobody printed.** `audit()`
  computed `wrappers` every run and `main()` never showed it. Not deleted —
  surfaced, because the tool's own first printed line is the SCANNED-BY-NAME
  caveat and naming the wrappers is what makes that caveat checkable. On the
  real run `stonedesk.html` matches **14** wrappers and `sairncare.html` **2**,
  which was invisible before.

**AND TWO OF MY OWN ARMS WERE WRONG ON THE FIRST DRAFT, CAUGHT BY ABLATION AND
NOT BY READING.** A shape-A fixture resolves its write set through a different
inline regex and never touches `WRITE_VAR_RE`; a generic read that *resolves*
never touches `READ_VAR_RE`, whose only consumer is the could-not-tell reason.
Both arms were green and both rules were still reported DEAD. That is the
twelfth discipline doing its job on the person applying it.

---

## 3. The expired/blocker-clause matcher defect — FIXED, `2f52470b`

Registered MODERATE at `d0bb0678`, filed by fourth 2026-09-29
(`docs/2026-09-29-claim-matcher-prose-collisions.md`), **owner UNASSIGNED** —
the doc says so in its own header and asks for an assignment before a fix.

**REPRODUCED AT HEAD BEFORE ANYTHING WAS CHANGED.** Three of the eight wordings
the finding named still produced a false hard block:

```
waiting for api/sd-data.js          -> same file or resource: api/sd-data.js
resume when api/sd-data.js frees    -> same file or resource: api/sd-data.js
skip api/sd-data.js this round      -> same file or resource: api/sd-data.js
```

…and the loose direction, which is the worse one and was not in the finding:

```
"rewrite the sd_crm branch in api/sd-data.js. api/sd-data.js is not touched
 by the hover half"   vs   "fix api/sd-data.js dispatch"      ->  None
```

Three changes, **each measured over all 532,512 cross-session pairs in the
1,178-claim record** rather than argued:

| change | BLOCK→CLEAR | CLEAR→BLOCK |
|---|---|---|
| only-inside (a path taken elsewhere is not disclosed) | 0 | 54 |
| front word-boundary markers (`blocked` was matching inside **UNBLOCKED**) | 0 | included above |
| seven new markers, each measured alone | **0 each** | — |

**A PURE TIGHTENING. It takes nothing away and restores 54 blocks the
disclosure rule had been giving away**, on `api/sd-data.js`,
`docs/tier-a-reviews.json` and `tools/report_only_checks.py` — the three
busiest shared files here.

**FOUR CANDIDATE MARKERS WERE MEASURED AND REJECTED:** `deferred` 73,
`holds` 61, `is <session>'s` 50, `conflict declared` 22. **Reading them is what
kills them, not the size** — `holds` loses to one line of ordinary English:
fourth's *"a soft-deleted record … never reaches a device that already HOLDS
it FILES: api/sd-data.js"*, where the word is about a **device**.

**SO TWO OF THE EIGHT WORDINGS ARE STILL OPEN ON PURPOSE** — `X is hank's` and
`X is another session's` — and arm E6 asserts they still block so closing them
is a deliberate act. **The cause is the CLAUSE SPLITTER, not the marker list:**
hank's real claim runs `…is not held by another session FILES: api/sd-data.js …`
with no `. `, `;` or ` -- ` between the disclaimer and the declared file list,
so a marker firing there exempts a file the session genuinely holds. Whether
`FILES:` should be a hard clause break is **unmeasured** and is the biggest
remaining question.

`tests/run_claim_matcher_probe.py` — 30 arms, 0 failed. Section D's fixture
prefix had to move: it was `FILES: api/sd-data.js. `, which **claims** the path,
so the old fixture asserted the contract this change deliberately reverses and
four arms went red on a fix rather than on a defect.

**NOT MINE, PRE-EXISTING, PROVEN BY STASHING:**
`tests/claims/run_fileset_matcher_probe.py` is red at HEAD with 3 failures
**without** this change. This change moves its PINNED figure **26 → 0** — the
file-set matcher now refuses nothing the lexical matcher misses, because the
lexical matcher stopped giving those catches away. **I did not re-pin it.**
Somebody has to decide whether that is a result or a regression in the argument
for keeping both checks.

---

## 4. The two item-4 subjects — one was already closed, one was a real hole

### 4a. The review-record usage line — **VERIFIED CLOSED AT HEAD, nothing to fix**

The defect (registered 2026-09-24, moderate) was the `--discharge` usage line
reading `<author> "<verdict>"` while the parser wants `opened_at` **second**, so
a real call of `--discharge cc 2026-09-26T13:13:44Z --help` wrote `--help` as
the verdict of a 70-hour obligation and printed DISCHARGED. Four things were
checked today, all at HEAD:

1. The usage line at the top of `tools/tier_a_review_gate.py` names the verdict
   **last** and carries the correction inline — fixed.
2. Both impossible shapes are refused at **write** time (`_v.startswith('--')`,
   `len(_v) < MIN_VERDICT_CHARS`, which is 40) — fixed.
3. **The damaged RECORD was repaired.** Across all 221 records: records whose
   verdict looks like a flag = **0**; verdicts under 25 characters = **0**;
   shortest verdict in the file = **1012** characters. The specific obligation
   (`cc`, `2026-09-26T13:13:44Z`) now carries a real multi-paragraph verdict.
4. The merge validator is `--validate`, not `--list` — changed 2026-09-23 and
   the `merge_policy.note` records why, so the related defect is closed too.

**"Verify each still open at HEAD, then fix" — this one is not still open.** No
change was made and none was needed.

### 4b. The literal-backspace push-gate hole — **FIXED, `d3d2db42`, severity HIGH**

**IT IS NOT WHERE THE PHRASE POINTS, AND THE SEARCH FOR IT IS WORTH RECORDING.**
I first looked for a raw `0x08` that reached `origin/main` and **there is
none** — every one of the 5 committed versions of
`tools/assertion_label_shape_check.py` is clean, so the 2026-09-29 backspace was
fixed in-session and check 11 never had a chance at it. Check 11 is working:
it caught the 2026-09-22 and 2026-09-29 instances, both recorded. **The hole is
structural, not a missed byte:**

> **Check 11 — the one gate whose entire subject is a byte in a committed blob —
> derived its file list from the OUTGOING COMMIT RANGE and then handed the
> checker WORKING-TREE PATHS.** It answered about bytes that are not the bytes
> being pushed.

**REPRODUCED IN A THROWAWAY REPO BEFORE ANYTHING WAS WRITTEN:**

```
1. commit a file containing  PAT = r'grant[^;]*<BS>delete<BS>'
2. repair the WORKING TREE only, do not commit
3. control_char_check.py <path>   -> "CLEAN -- no raw control bytes", exit 0
4. git show HEAD:guard.py         -> two raw 0x08, still outgoing
```

So the push that shipped the defect would have passed a clean gate. Four fixes:

1. **`--rev REV`** reads each named path as that revision holds it. The gate
   passes `--rev tip`, and a checker whose output carries no `source` line
   under that flag is **refused** — it ignored the flag and read the tree.
2. **A named file that cannot be read is exit 2 and is NAMED.** It was
   `if not os.path.exists(...): continue`, *silently*, while `files scanned`
   still counted it — a printed number that was a claim about bytes nobody
   opened, which the gate's own count guard then compared against and agreed
   with.
3. **`git ls-files` QUOTES A PATH IT CANNOT PRINT PLAINLY, AND THAT HID A
   TRACKED FILE FOR 25 DAYS.** Found by fix 2 on its first run. This repo
   tracks `archive/.../SAIRNlaw \342\200\224 A Partnership Proposal … .pdf`,
   which plain `ls-files` prints wrapped in double quotes with C escapes, so
   every sweep since 2026-09-10 looked for a filename starting with a quote
   character, failed, and skipped it **in silence while counting it as
   scanned**. It is a PDF and would have been skipped as binary anyway — the
   defect is that the skip was invisible, so the next such path (a `.js` with an
   em-dash) would have been unscanned and reported as scanned. Fixed with `-z`,
   **not with an unquoter**: writing the unquoter is how this class recurs.
   Measured after: 2973 given, 2969 scanned, 4 binary, exit 0.
4. **Check 11 denies on exit 2.** The block handled 1 and the scoping mismatch
   and nothing else, so a COULD NOT RUN fell through as a pass. Latent until
   fix 1 made exit 2 reachable. PR §1.11.

`tests/push_gate/check11_probe.py` sections H and J — 9 new arms, 29 total, 0
failed. **NEGATIVE CONTROL RUN:** with both tools stashed back to HEAD, **6 of
the 9 FAIL** and the probe exits 1. The arms bite.

**NOT CLOSED, AND NAMED IN THE REGISTER RATHER THAN QUIETLY LEFT:** checks 2,
3, 4, 5, 6, 7, 12 and 12b build the same working-tree paths from the same
`changed` list and were **not swept**. Whether a working-tree read is wrong for
each of them is a per-check judgement, not one edit.

---

## 5. The gap-ledger pilot — `tools/gap_ledger.py` DOES NOT EXIST

**Status: NOT BUILT. Not started, not stubbed, no design document.** `ls` on the
path fails and the string `gap_ledger` appears nowhere in `tools/`.

**The inputs are ready and were prepared for it by somebody else.**
`docs/2026-09-29-competitive-gap-doc-inventory.md` opens *"For the gap ledger
Cody is building"* and is the per-app source table. What it establishes:

- **Three apps have NO competitive-gap doc of any kind** — `sairndesign`,
  `sairnlegacy`, `sairnscape`. Not thin coverage, nothing at all. Those are the
  rows the ledger opens empty.
- **Nine of the fourteen covered apps have their newest audit ONLY on a cloud
  branch**, eight of them on `claude/wizardly-ride-wtun13` (PR #18) alone.

**FOR THE PILOT PAIR SPECIFICALLY, both have a source document on `main`:**

| pilot app | doc on main | newer doc, branch-only |
|---|---|---|
| SAIRNcode | `docs/competitive-gap-audit-sairncode.md` | `docs/cloud-research/sairncode-external-competitive-gap-audit-2026-09-26.md` on PR #18 |
| SAIRNlaw | `docs/cloud-research/SAIRNlaw-external-competitive-gap-audit-2026-09-25.md` | `…sairnlaw-external-competitive-gap-audit-2026-09-26.md` on PR #18 |

**SO THE PILOT CAN RUN ON MAIN, AND IT WOULD BE BUILT ON THE OLDER AUDIT OF THE
TWO IN BOTH CASES.** That is the decision to take before building, not after: a
ledger whose SAIRNlaw row cites the 09-25 doc while the 09-26 doc sits on PR #18
is a ledger that will disagree with the next person who reads the branch. The
honest options are (a) merge PR #18 first, (b) cite the main doc and record the
branch-only successor on the row, or (c) build the ledger with an explicit
"as-of ref" column. **I did not pick one — it is a scope call.**

Not built, and the reason is budget rather than a blocker: items 3, 4 and 2's
first tool took the session.

---

## 6. Gate 1 — live migration, every app with a demo key. ONE SQL action for Michael

**DRIVEN LIVE TODAY, 113 (app, schema file) pairs across 16 apps**, using
`tools/schema_provisioning_check.py --app X --schema Y --key Z --json` with the
licence keys from `docs/2026-09-03-demo-credentials.md`. Read-only: every
request is `action:'read'` and nothing was written.

```
declared tables across all 113 pairs       402
PROVISIONED -- confirmed present, live     148   (37%)
MISSING     -- confirmed absent              2
REFUSED     -- session-gated, unanswerable 216
UNREACHABLE -- declared in SQL, not registered in api/_resources
                                            26
```

### THE HEADLINE IS NOT THE MISSING TABLE, IT IS THAT GATE 1 IS 37% ANSWERABLE

**216 of 402 declared tables cannot be answered with a licence key**, because
the resource is behind the employee session gate and this check only presents a
key. Per app: `sairnvet` 42, `sairnlegacy` 36, `sairnroofing` 25,
`sairndental` 24, `sairnlaw` 19, `sairnfreedom` 17, `sairnsenior` 15,
`sairncare` 14, `sairnbiz` 13, `sairndesign` 10, `stonedesk` 5,
`sairnmechanical` 3, `sairnscape` 2, `sairnbuild` 1.

**THE FIX IS SMALL AND IS NOT BUILT:** the PINs are in the same credentials
document the keys came from, so the check could sign in at `/api/<x>-auth`,
carry the session token, and convert most of those 216 refusals into real
answers. `schema_provisioning_check.py` takes `--key` and has no `--pin`.
**Until it does, "Gate 1 is clean" cannot be said about any session-gated
resource on this platform, and the gate's own MASTER-PLAN section says the list
grows only when somebody confirms a migration.**

### THE SQL ACTION — MICHAEL

**SAIRNgrounds: `grd_rounds` and `grd_cart_orders` DO NOT EXIST.** Confirmed
live on `GRD-DEMO-2026` (exit 1, both named under `missing`). The file has never
been run; the other two SAIRNgrounds schemas are fully provisioned, which is why
this is one unrun migration rather than a broken app.

> **Run `sql/sairngrounds_caddie_schema.sql` whole in the Supabase SQL editor.**
> It is `create table if not exists` throughout and is safe to re-run. **Do not
> retype it and do not run it in pieces** — paste the file.

**THEN RUN THE CONFIRM QUERY, because a multi-statement paste can half-apply
and report success:**

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('grd_rounds', 'grd_cart_orders')
order by table_name;
```

**Two rows is the pass. One row or zero means the paste truncated** — re-paste
and re-run the confirm, do not assume. After that,
`python tools/schema_provisioning_check.py --app sairngrounds --schema sql/sairngrounds_caddie_schema.sql --key GRD-DEMO-2026`
should exit 0 with `MISSING: 0`.

**DO NOT ADD A `delete` GRANT when fixing anything in that file.** The file says
so itself and `sql/unused_delete_grant_revoke_2026-08-24.sql` revoked it
platform-wide across 134 tables.

### 26 UNREACHABLE — a different problem with the same symptom

Declared in a `sql/` file and **not registered** in `api/_resources`, so the
check cannot route to them at all and neither can the app. Several are
deliberate (auth tables, rate-limit tables, witness-token tables are reached by
bespoke endpoints, not by the generic dispatcher). **`sairnlaw` has 10**, which
is the one worth a read: `cl_case_cache`, `cl_citing_treatments`,
`cl_court_cache`, `cl_coverage`, `cl_feedback_log`, `cl_rate_limit_log`,
`fcl_rate_limit_log`, `law_deadline_rules`, `law_holidays` and one more. **Not
investigated — named, not diagnosed.**

---

## 7. The register cells — FOUR OF FIVE WERE ALREADY LANDED, and one is a new finding

**Verified cell by cell in `docs/CRITICALITY-TIERS.md` at HEAD before touching
anything. Nothing was re-done.**

| sub-item | state at HEAD |
|---|---|
| `sf_vendors` cell | **ALREADY LANDED 2026-09-29.** The cell carries *"RE-ANCHORED 2026-09-29: this cell cited `:4514`, which is now the `PRODUCT_CATEGORIES` table"* and cites `sfAddVendor()` by name with the line as a "currently near". Tier unchanged at B/B, correctly — `licensed` is a flag nothing gates on and the prices live on `sf_vendor_prices`, already A |
| `sd_inventory` register note | **ALREADY LANDED 2026-09-29.** Cell carries `AUDITOR NOTE, 2026-09-29, NOT A TIER CLAIM: cost x qty FEEDS A VALUE FIGURE`, verified in `stonedesk.html` |
| `supplier_lead_times` register note | **ALREADY LANDED 2026-09-29**, and it is the stronger version: `AUDITOR NOTE … AND THE APP SIDE IS EMPTIER THAN THE NOTE SAYS` |
| SAIRNscape `customers` "no PII" basis | **ALREADY CORRECTED.** The cell now reads *"A CUSTOMER's NAME, PHONE, EMAIL AND STREET ADDRESS"* — the false no-PII sentence is gone |
| **citation drift** (`supplier_lead_times` cites `api/_lib/job-risk.js:218`; `'at_risk'` is at `:222`) | **OPEN, AND HANK IS WORKING IT RIGHT NOW.** hank's live claim reads *"sairngrounds grd citation line verdicts and the drift tool render-site false positive; open-work index row 73 job-risk citation closure"*. Not touched — that is a real overlap, not a matcher artefact |

### THE SAIRNscape LICENCE-KEY-ALONE ROW — NEW, AND IT NEEDS AN INDEX ROW

**Found by the Gate 1 sweep above and then confirmed by direct read, not
inferred.** SAIRNscape's `customers` resource — which the register now correctly
describes as carrying **a customer's name, phone, email and street address** —
is **reachable on the licence key alone, for READ and for WRITE**:

- `SD_GATE_APP` gates exactly **two** SAIRNscape resources: `scp_invoices` and
  `scp_quotes`. `customers` is in neither it nor `SD_SESSION_GATED`.
- The write branch is `api/sd-data.js:4768`, upserting to
  `scp_customers?on_conflict=license_hash,customer_id`.
- The live sweep reached `scp_customers` with a key and no session token and got
  `provisioned`, while `scp_invoices` and `scp_quotes` were refused — so the
  gating asymmetry is confirmed from both ends.

**THIS IS THE SAME SHAPE AS THE `mech_docs` ROW** (open-work row 98, severity
high, third holder in two days, still UNOWNED): PII writable on a licence key
with no employee session. **It is not written to the open-work index**, because
**cc holds `docs/SAIRN-OPEN-WORK-INDEX.md`** under a live claim. fourth hit the
same wall an hour ago and declared it in its own claim rather than rewording.
**The row belongs to cc or to the next session holding the index**, and the
three facts above are everything needed to write it.

---

## 8. SAIRNcode autonomous-coding scope — ALREADY WRITTEN, scoping only, nothing built

`docs/2026-09-29-sairncode-autonomy-scope-cody.md`, 151 lines, header:
*"SCOPING AND A CORRECTION. Nothing here is built."* **No new work was done and
none is needed unless the scope has moved.**

Its substance, re-read today because a scope document that was wrong once is the
kind that gets quoted:

- **It opens by correcting its predecessor**,
  `docs/2026-09-28-sairncode-autonomous-coding-scope.md`, whose central
  measurement was wrong: that document says `routing` appears **0 times** in
  `sairncode.html`; re-measured it is **20**. `autonomous` (0) and `audit trail`
  (0) were correct.
- **The predecessor's substantive claim was false when written.** *"There is a
  review queue and there is a derived confidence and nothing connects them"* —
  the connection is three lines inside the confidence function
  (`review_status`, `escalation_reason`), consumed by `scRouteCodedItems()`,
  which splits the queue so auto-assigned items stop consuming a coder's
  attention. **Both landed in `f9a3b381` on 2026-08-20** — five and a half weeks
  before the document that called the feature missing.

**If a build is wanted, that is a different instruction than this one.** This
item said scoping only.

---

## 9. Inventory — what landed, in flight, blocked, stale, and found-but-unlogged

### Landed this session, with shas

| sha | what |
|---|---|
| `2f52470b` | claim matcher: only-inside disclosure + front word-boundary markers + 7 new markers. 0 loosening, 54 false CLEARs closed |
| `d3d2db42` | check 11: `--rev`, could-not-read disclosure, `ls-files -z`, deny on exit 2 |
| `77b5b536` | `write_without_readback_check.py` fixture lock, 7/7 rules exercised; `WRITE_VAR_RE` given a consumer; `WRAPPER_RE` surfaced |
| `27636931` | the Tier A obligation for the matcher change (assigned to cc) |
| `abe2ce17`, and two reseat commits | the two defect-register records |

### In flight / not finished

- **Item 2: 6 of 7 fixture sets not started.** Named by tool and by rule in §2.
- **Item 5: `tools/gap_ledger.py` not built.** Inputs ready, one scope decision
  outstanding (§5).
- **Item 6's real fix — `--pin` on `schema_provisioning_check.py`** — not built.
  It is what moves Gate 1 from 37% answered to most of the way.

### Blocked, with the reason

| blocked | on what |
|---|---|
| Writing any open-work index row — including the SAIRNscape finding and the §4b residual sweep | **cc holds `docs/SAIRN-OPEN-WORK-INDEX.md`** under a live claim. Declared here rather than reworded past the matcher (PR §4.3) |
| The `supplier_lead_times` citation-drift closure | **hank is actively working it** (row 73). Real overlap |
| Re-pinning `tests/claims/run_fileset_matcher_probe.py`'s 26→0 figure | Needs a decision about whether the file-set matcher still earns its place, which is not mine to make alone |

### Stale documents and tool headers

1. **`docs/MASTER-PLAN.md`'s Gate 1 section lists 5 attested migrations and says
   "every app not named in either list" is unverified.** That is still literally
   true and is now also *understated*: 148 tables are confirmed present live as
   of today and none of that is in the attested table, because the table only
   takes human attestations. **The gate's design makes a mechanical confirmation
   invisible to it.** Worth a decision: either the table gains a
   "mechanically confirmed, read-only" column or the 148 stay unrecorded.
2. **`docs/2026-09-29-dead-rules-cody.md` publishes `29 DEAD / 65 checked / 156
   rules / 91 could-not-tell`. Re-run today: `26 DEAD / 136 checked / 160 rules
   / 24 could-not-run`.** The document's own last line says *"Re-run it rather
   than quoting these figures"*, which is why it is not wrong — but every figure
   in it has moved and anybody quoting it would be six days stale.
3. **`docs/2026-09-29-competitive-gap-doc-inventory.md` is as-of 2026-09-29 for
   its per-app table** and says so in an addendum. One of its ten refs no longer
   exists. Not stale in a way that misleads, because the addendum is there.
4. **`docs/2026-09-03-demo-credentials.md` tested ONE PIN PER KEY**, so a dead
   PIN and a dead key are indistinguishable in its table — the document says
   this about itself now, after `SB-PINNACLE-2026` was read for six days as an
   unusable licence when only the PIN had died. **`SV-PINNACLE-2026`'s PIN is
   still dead and SAIRNvet still has 42 session-gated resources nobody can
   reach**, which is the largest single block of Gate 1's 216.

### Found and never logged

| finding | severity | logged? |
|---|---|---|
| SAIRNscape `customers` — name, phone, email, street address, writable on a licence key alone | **high**, same shape as `mech_docs` | **NO — index is held by cc.** Facts in §7 |
| A tracked file was never scanned by check 11 for 25 days because `git ls-files` quoted its name | high | **YES**, in the `d3d2db42` register record |
| Checks 2/3/4/5/6/7/12/12b have the same working-tree-vs-commit shape as check 11 | unknown until read | **YES**, as `recurrence_open` on the same record |
| `tests/claims/run_fileset_matcher_probe.py` red at HEAD, 3 failures, pre-existing | moderate | **partly** — open-work row 160 covers a *different* red in the same family; this one has no row |
| `tools/schema_provisioning_check.py` has no `--pin`, so 216 of 402 tables are permanently COULD-NOT-TELL | **high for the gate, not for the product** | **NO.** This document is the only record |
| 11 Tier A obligations authored by cody are OPEN, oldest `2026-09-27T02:06:03Z` (8 days) | process | **NO.** Reviewers are cc (4), fourth (3), hank (2), cloud (1) |

### Ranked by severity, and by whether a competitor is actually beating us

**The honest answer to the competitor half is that NONE of this session's
findings is a competitive gap, and saying otherwise would be inventing one.**
Every item above is an internal-correctness or coordination defect. The
competitive question lives in the gap-ledger work (§5), which is **not built**,
and in the three apps with **no competitive-gap doc of any kind** —
`sairndesign`, `sairnlegacy`, `sairnscape`. **Those three are where a competitor
could be beating us and we would not know**, and that is a measured absence
rather than a judgement.

Ranked:

1. **SAIRNscape `customers` writable on a licence key alone** — real PII, real
   write path, confirmed from both ends. Needs an index row and an owner.
2. **Gate 1 is 37% answerable** — a gate that cannot answer is not a gate that
   passed. One small tool change fixes most of it.
3. **`grd_rounds` / `grd_cart_orders` missing** — Michael SQL action, §6.
4. **The working-tree-vs-commit shape in eight other push-gate checks** — one of
   them may matter as much as check 11 did.
5. **Six fixture sets not started** — each is a rule that can be deleted,
   mistyped, or shipped with a literal backspace while every light stays green.
6. **Three apps with no competitive-gap doc** — the only genuinely
   outward-facing item on the list.

**Logged where I could; the low ones are left as they are**, per the
instruction.

---

## 10. Dead-rule sweep — what has not fired, and dead versus quiet

**Re-run at HEAD today. Do not quote these figures either — run
`python tools/dead_rule_sweep.py`.**

```
71 tools from the report-only registry, 160 module-level compiled rules

CHECKED / UNIVERSE   136 of 160 could be ablated against SOME evidence
  against evidence the tool SHIPS      68 ->  42 exercised,  26 DEAD
  against the REAL RUN only            68 ->  38 move the output,
                                              30 do not move a byte
COULD NOT RUN                           24  -- 22 of them because the tool
                                              WRITES when run, so the real run
                                              is not safe evidence
FINDINGS                                56
```

**THE TWO QUESTIONS ARE DIFFERENT AND THE ANSWER DEPENDS ON WHICH ONE IS
ASKED.** "Has it fired in 30 days" is about the **corpus**; "is it dead" is
about the **evidence**. A rule can be silent because the defect it hunts does
not currently exist — that is **QUIET and correct** — or silent because nothing
would notice it vanishing, which is **DEAD**.

### DEAD — nothing the tool ships as proof of itself depends on the rule (26)

Six tools, all **never claimed by any session**, plus three that are claimed:

| tool | rules | claimed? |
|---|---|---|
| `dependency_graph.py` | `REQ`, `ENV`, `BASELINE_RE`, `BASELINE_DATE_RE`, `SCHED_HEAD_RE`, `SCHED_DATE_RE` | never |
| `register_freshness_check.py` | `BARE_PATH`, `SHA`, `CELL_FILE`, `CELL_CALL`, `CELL_CAMEL` | never |
| `advisory_lock_isolation_check.py` | `READ_RE`, `AGG_RE`, `DROP_RE` | never |
| `accepted_risk_expiry_audit.py` | `ACCEPTED`, `CLOSED_STATUS` | never |
| `service_role_tier_a_gate_check.py` | `TIER_A_ROW` | never |
| `overrun_inversion_scan.py` | `DISPLAYISH` | never |
| `metamorphic_check.py` | `_LINE_NO`, `_LEAD_NO`, `_LINES_LIST`, `_BYTES`, `_ENTITY_TOKEN`, `_FULL_LINE_COMMENT` | cody, 2026-09-25 |
| `register_feed_gate.py` | `TIER_A_ROW`, `REST_PATH` | fourth |

**`metamorphic_check.py`'s six remain the ones to read first.** Its
`blind_lock()` is among the best fixture locks here — two hand-built fixtures,
one sensitive and one robust, refusing the measurement when unlocked — **and
six of its own normalisation rules are invisible to it.** A strong lock over one
half of a tool says nothing about the other half.

### QUIET — exercised by evidence, but produces no finding on today's corpus (30)

These **have** fired in the sense that they are held by a fixture or a control;
they have **not** fired on real data, and for most of them that is the right
answer because the defect class is currently absent:

| tool | rules | reading |
|---|---|---|
| `sairn_dead_button_audit.py` | 6 | **QUIET.** No dead buttons on the corpus today |
| `sairn_strict_args_check.py` | 6 | **QUIET** |
| `temporary_state_check.py` | 3 (`PY_WRITE` twice, `JS_WRITE`) | **QUIET — and `PY_WRITE` is listed TWICE**, which is a duplicate rule name in one module and worth a look on its own |
| `md_table_check.py` | 2 | **QUIET.** No malformed tables in what it reads today |
| `discarded_verdict_crossfile.py` | 2 | **QUIET** |
| `literal_drift_check.py` | 2 | **QUIET** |
| `removal_path_check.py` | 2 | **QUIET** |
| `panel_nesting_check.py` | 1 | **QUIET** |
| `fail_open_check.py` | 1 | **QUIET** |
| `discarded_verdict_check.py` | 1 | **QUIET** |
| `truthy_sum_check.py` | 1 (`COERCED_RE`) | **QUIET, and this one is not reassuring.** It is the rule that recognises an ALREADY-COERCED fold — the thing that keeps the tool from re-flagging a fix. The grandfathered-entry history on this tool (48 → 46, which immediately exposed a third tax surface) says its blind spots have been load-bearing before |
| `eaten_substitution_check.py` | 1 (`LIST_ITEM`) | **QUIET, and it should have fired on me today.** I wrote a register field through bash backticks in a double-quoted `printf`, the shell ate the subject of the sentence, and this tool's subject is commit MESSAGES, not JSON fields. A real near-miss for its scope rather than its rules |
| `write_without_readback_check.py` | 2 | **NO LONGER QUIET — fixed today**, `77b5b536` |

### COULD NOT RUN — 24, and this is not a pass

**22 of the 24 belong to a tool that WRITES when run**, so the real run cannot
be used as evidence without mutating the repo — `traceability_matrix.py` (3),
`criticality_tier_check.py` (5), `hover_separation_audit.py` (8),
`master_plan.py` (2), `tooling_inventory.py` (2), `defect_register.py` (2). The
first attempt at that tier left three generated documents modified in the
working tree, which is why the sweep now refuses it. **The remaining 2 were
`write_without_readback_check.py`'s and are closed.**

**So the burn-down has a shape:** 2 of 24 closed today, 22 blocked behind a
different problem — those six tools need a `--check`-style read-only mode before
their rules can be ablated at all.

---

## ADDENDUM, same session, later — three of the sections above are now out of date

**Written as an addendum rather than folded into the sections, because the
sequence is part of the evidence: §2, §6 and §10 were true when written and the
work continued afterwards.**

### §2 — ITEM 2 IS CLOSED. 7 of 7 tools, not 1 of 7

| tool | result | sha |
|---|---|---|
| `write_without_readback_check.py` | 7/7 rules exercised, was COULD-NOT-RUN | `77b5b536` |
| `accepted_risk_expiry_audit.py` | 4/4, was 2 dead | `1eb6da5c` |
| `dependency_graph.py` | 6/6, was 6 dead | `1eb6da5c` |
| `register_freshness_check.py` | 8/8, was 5 dead | `e1192ce5` |
| `advisory_lock_isolation_check.py` | 9/9, was 3 dead | `e1192ce5` |
| `service_role_tier_a_gate_check.py` | was 1 dead | `e1192ce5` |
| `overrun_inversion_scan.py` | was 1 dead | `e1192ce5` |

**IN FOUR OF THE SEVEN THE RULE WAS NOT WEAK — IT WAS REACHED BY A SECOND
ROUTE THAT MADE THE EXISTING ARM PASS WITHOUT IT**, and that is the finding
worth more than the fixtures:

- **`READ_RE` / `AGG_RE`** (advisory locks) — every vulnerable fixture says
  `select count(*) into v`, which matches BOTH, so neutralising either left the
  other matching. **Two rules covering one fixture is one rule's worth of
  evidence.**
- **`DISPLAYISH`** (overrun inversion) — the arm `a progress BAR width ranks
  LOW, not HIGH` drives `done/total*100`, which matches neither `ESTIMATE` nor
  `PROGRESSY`, so with the rule neutralised it falls through `rank()`'s final
  `return 'LOW'` and the arm **gets the same answer by a different route**.
- **`TIER_A_ROW`** (service-role gate) — `self_check` replaces `TIER_A` with a
  hardcoded set so the fixtures do not depend on the live register. Correct —
  and it is exactly why the rule that builds that set was dead: **the isolation
  that makes every other arm trustworthy bypasses it.**
- **`WRITE_VAR_RE`** (write-without-readback) — **no consumer at all.**
  Compiled, documented, never read; SHAPE B re-spelled the identical pattern
  inline.

### §10 — the platform figure moved, and here is the before and after

Both numbers from `python tools/dead_rule_sweep.py`, same day, same criteria
version, before and after the seven tools:

| | before | after |
|---|---|---|
| tools in the registry | 71 | 73 |
| module-level rules | 160 | 162 |
| ablatable against some evidence | 136 | 140 |
| against SHIPPED evidence | 68 → 42 exercised / **26 DEAD** | 75 → 67 exercised / **8 DEAD** |
| against the real run only | 68 → 38 move / 30 do not | 65 → 37 move / 28 do not |
| **COULD NOT RUN** | **24** | **22** |
| **FINDINGS** | **56** | **36** |

**The 8 that remain are `metamorphic_check.py` (6) and `register_feed_gate.py`
(2) — both CLAIMED tools, cody and fourth respectively, and therefore outside
item 2's never-claimed scope by definition.** All 22 remaining COULD-NOT-RUN
belong to a tool that writes when run; none is a never-claimed tool with no
evidence. **Item 2's scope is empty.**

### §6 — GATE 1 IS NOW 77% ANSWERABLE, AND THERE ARE 24 MISSING TABLES, NOT 2

**`tools/schema_provisioning_check.py` gained `--pin` / `--auth` (`36d58d34`)
and the answer changed.** Full account and the eighteen SQL actions:
**`docs/2026-10-05-gate1-live-migration-signed-in.md`**.

| | licence key only | signed in |
|---|---|---|
| PROVISIONED | 148 | **289** |
| **MISSING** | **2** | **24** |
| REFUSED | 216 | 64 |
| answerable | 150/402 = **37%** | 313/402 = **77%** |

**TWENTY-TWO MISSING TABLES WERE INVISIBLE AND THE THING HIDING THEM WAS A
SECURITY CONTROL WORKING CORRECTLY.** The session gate answered 403, the sweep
recorded REFUSED — honestly — and REFUSED is indistinguishable in a summary
from a table nobody asked about. Eighteen schema files across five apps have
never been run: StoneDesk (1), SAIRNgrounds (1), SAIRNdental (3), SAIRNmechanical
(1), SAIRNsenior (7), SAIRNroofing (5).

**AND MY OWN IDEMPOTENCY CHECK WAS WRONG FIRST TIME.** A `create table` count
flagged five of the eighteen as not fully idempotent; re-read directly, **all
eighteen are** — each contains a comment with the words `create table if not` /
`exists` split across two lines, which the count read as a second statement. Had
I reported it, Michael would have been told to hand-edit five files that are
already safe to re-run.

**TWO APPS STILL CANNOT BE CHECKED AT ALL, 59 of the remaining 64 refusals:**
SAIRNvet (42 resources, PIN dead 2026-09-25, `bootstrap` permanently closed —
needs a decision, not a SQL file) and SAIRNfreedom (17 resources, including a
felony flag on a named volunteer and minors' names, because
`sql/sairnfreedom_employee_auth_schema.sql` has never been run — **that one IS a
SQL action**).

### What the addendum does NOT change

**§7's blocked items are still blocked** — cc still holds the open-work index,
hank still holds the citation-drift row — so the SAIRNscape licence-key-alone
finding, the 24 missing tables and the two blocked apps **still have no index
row.** Three documents now hold findings that belong in the index.

---

## What is NOT in this document

- **Any claim that an app is correct.** Gate 1 answers whether a TABLE EXISTS.
  It says nothing about whether a write succeeds, whether the id column matches
  what the client sends, or whether a row comes back.
- **A re-derivation of item 9 of the previous paste.** It is named by neither
  the landed list nor the refused list and I did not guess at it.
- **The 54 new blocks in §3 read one by one.** I read six. If one is a false
  positive it is in the other 48.
