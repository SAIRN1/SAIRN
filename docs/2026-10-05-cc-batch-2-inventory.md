# CC batch 2, 2026-10-05 — enforce mode is live, twelve suites are green, and two test suites were defending defects

**Every figure below was measured, driven or run at HEAD today. Where something
is quoted from an earlier document it says so and says it was not re-derived.**

Methodology, as the last batch: **every screen reports its blind-spot count on
its last line.** A verification with no stated blind spots is claiming
completeness it has not earned.

---

## 1. What landed, with shas

| sha | What |
|---|---|
| `ac9c21df` | `test-alf-mar.js` **0/20 → 21/21** and `sairnbuild_retainage_race.js` **1/2 → 3/3** |
| `98e17047` | Register record for the arm that asserted the absence of a controlled-substance witness control |
| `395f7f2a` | The other **ten** suites green; `alf-incidents` was hiding an untested self-scope |
| `8aa0c008` | Register record for the `alf_incidents` self-scope that had no arm |
| `723dfca7` | Re-seat the sha a rebase moved under the first register record |
| `60a19a43` | **PR #18 merged** — 12 external competitive-gap audits, the SOC 2 study, the Novaclad teardown |
| `1d46ab8d` | The two citations PR #18 landed drifted, repointed; both claims hold |
| `88ee8fe7` | **SAIRNlegacy competitive-gap audit, PART 1** — first of the three apps that had none |
| `6469d2eb` | `seam_cannot_tell_watch.py` + baseline + 19-arm probe, and **why the count grew** |

**BLIND SPOTS: 1.** Four of these shas were rewritten by `push_retry.py`'s rebase
during this session and are re-resolved here by commit subject, not carried
forward from my own earlier notes — which is the reason `723dfca7` exists at all.

---

## 2. `SAIRN_CLAUDE_AUTH_MODE=enforce` — LIVE, confirmed against the real endpoint. **ITEM CLOSED.**

### The env var exists now, where six days ago it did not

Read from the Vercel API: `SAIRN_CLAUDE_AUTH_MODE`, target **production**,
created `1791193015496`. **Its value is masked** (`sensitive`, `decrypted:false`)
so the API cannot tell me it says `enforce` — which is why this was settled
behaviourally instead.

### The discriminator, driven live, and it needed no revoked key

`api/claude.js:325` answers **401 `NO_LICENSE`** only when
`claudeAuthMode === 'enforce'`. In `observe` it does not exist as a code path.
So an unauthenticated call distinguishes the modes without a revoked licence:

```
POST /api/claude   no Authorization header      -> 401 NO_LICENSE
POST /api/claude   Bearer ZZ-NOT-A-REAL-KEY     -> 401 NO_LICENSE
```

**`NO_LICENSE` is mode-gated, so its presence IS the proof.** This is the arm
the test file calls E0 — *"an absent licence is 200 in observe and 401 in
enforce."*

### And the paired negative, which is what makes the above mean something

A **valid** licence must still get *past* the gate. Driven, and deliberately
chosen so it costs no Anthropic call:

```
Bearer SD-AUDIT-2026, no messages   -> 400 {"message":"messages array is required"}
Bearer SB-TEST-2026,  no messages   -> 400 {"message":"messages array is required"}
```

**400, not 401** — refused at the envelope, having cleared the licence gate. A
401 here would have meant enforce mode was locking out paying customers, and
that is the failure this pair exists to separate from success.

### The suite and the ablation, re-run at HEAD

`api/claude-licence-enforce.test.js`: **12 passed, 0 failed.** Both single-layer
ablations re-driven, each mutant confirmed to **parse** first:

| Layer removed | Arms red | Arms green |
|---|---|---|
| The refusal — `:352`, `enforce && inactive` → 403 | **A1, A2** | 10, including every control |
| The budget grouping — `\|\| authState === 'inactive'` restored at `:470` | **C1** | C2, C3, C4 |

`api/claude.js` restored byte-for-byte; `git diff` empty.

**SO BOTH HALVES ARE NOW LIVE.** The budget half was already live (it is
mode-independent). The refusal half **is no longer dormant** — a revoked licence
now gets 403 `LICENSE_INACTIVE` before the rate limiter and before Anthropic.

**BLIND SPOTS: 2.** (1) **No revoked licence key was driven against production.**
The `inactive` path specifically is proven by the suite and by the ablation, not
by a live call — what the live calls prove is that the `enforce` predicate those
two branches share is true in production. (2) Enforce mode also armed the
`absent`/`invalid` refusal at `:325`, which is the larger blast radius; the two
401s above are that change working as designed, and **no sweep was done for app
code that calls `/api/claude` without a licence key** and would now get 401
where it previously got 200.

---

## 3. The twelve red suites — all green, and two of them were defending defects

**200 assertions across thirteen files, 0 failed.** The population was measured,
not taken from the 2026-09-27 bisect note: **14 files** stub
`verifySessionToken` with an app-scope throw; **2** tolerated an absent
`expectedApp` and were green, **12** did not and were red.

### Cause 1 — the stub was stricter than the function it stands in for

`api/_lib/auth.js:604` is `if (expectedApp && payload.app !== expectedApp)
return null;` — the third argument is **optional**, and `api/sd-data.js:1387`'s
active-credential pre-gate omits it deliberately. Twelve stubs threw on
`undefined`, so **every arm answered 502 on the stub's own throw**. A suite
failing on its own mock is not evidence about its subject.

**The guard was kept, and ablated to prove it:** changing the `alf_mar` read
gate's scope to a wrong app still reddens **5** arms. A permissive stub that
could not fail would have been a worse outcome than the red.

### Cause 2 — `test-alf-mar.js` asserted the ABSENCE of a controlled-substance control

With cause 1 cleared, `alf-mar` went 0/20 → **18/20**, and the two survivors
were one defect. Found by **instrumenting and printing the refusal body** rather
than guessing which of the branch's four 403s had fired:

```
count (med_aide, own-assigned resident)  -> 403 WITNESS_REQUIRED
```

**The refusal is correct and the test was wrong.** `api/sairncare-witness.js`
(2026-09-30) requires a second person to have confirmed that exact record on the
server. The arm asserted **200** for a count carrying only a client-supplied
`witness_id` — a field the caller types, which the gate's own comment singles
out: *"`witness_id` IS DELIBERATELY NOT HERE. It names a SECOND person who is BY
CONSTRUCTION unverified."*

**Left alone, that arm would have pressured somebody into weakening a
controlled-substance control to make a suite green.** The fixture now satisfies
the lock instead, the way `api/sd-data-alf-mar-actor-identity.test.js` already
does, with `content_hash` computed by the module's **own** `contentHash`.

### Cause 3 — `test-alf-incidents.js` had NO arm on the self-scope at all, and could not have had one

Three arms asserted a flat **403** for care-role reads of the incident log,
which `api/sd-data.js:10739` deliberately stopped answering on 2026-09-27 — *"ending
write access is accountability; ending read access is just opacity."*

**And the suite's own fetch mock ignored the `&recorded_by=eq.` clause**, so it
returned every row to every caller. **The arm and the mock were wrong in the same
direction**, so the one control between a caregiver and the whole facility's
mandated-reporting log was untested in both halves while the suite read as
coverage.

Rewritten to the real contract — every row a care role sees was filed by that
caller, asserted over the **whole** result; a report filed by someone else is not
visible; **management does see that same row**, so it proves a scope and not an
empty fixture. **Ablated: removing the eq-clause now reddens three arms plus the
management count. Before this commit it would have reddened nothing.**

**One mistake of mine, kept in the file rather than quietly fixed:** my first
draft of that arm asserted an empty log and `med_aide` saw one row, because an
earlier arm has MA-1 file a report. A count is a fact about the fixture's
history; *"every row I can see is mine"* is the contract.

**BLIND SPOTS: 3.** (1) Nothing counts **unscoped** `verifySessionToken` calls, so
a branch gate that dropped its app scope **entirely** — rather than setting a
wrong one — passes all 14 stubs, including the two reference-green ones. The
guard catches a WRONG app and is blind to a MISSING one. (2) Legacy
`alf_incidents` rows carry `recorded_by` NULL and are invisible to the
self-service tier by a recorded decision; no arm covers that state. (3) The
eleven mechanical fixes were verified by **running** each suite, not by reading
each diff — the script's exactly-once refusal is the control on that, and it is
weaker than a read.

---

## 4. PR #18 — merged, and NOT blindly

**`60a19a43`.** 14 markdown files, **+11,332 / −0**, no code. GitHub's own
verdict at merge time: `mergeable: true`, `mergeable_state: **clean**`.

### Why it is not a blind copy

Every claim the docs make about **our own** codebase was re-derived at HEAD
first. Ten code citations across three of the fourteen files; the other eleven
cite no internal code at all. **Eight land on live content. Two had drifted, and
both claims are still TRUE with only the line wrong** — re-derived from the
claimed *text* by a script that refuses unless it resolves to exactly one line:

| Cited | Actual at HEAD | Drift | What the old line is now |
|---|---|---|---|
| `stonedesk.html:12427` | **`:12470`** | **+43** | blank, inside a FABRICOR header |
| `sairncash.html:1154` | **`:1703`** | **+549** | an unrelated QBI-deduction comment |

Both carry real findings — the first is an **FTC 16 CFR 251 "free"** exposure:
`SD_BASE_PROMPT` says payroll, HR and accounting *"are handled by SAIRNbiz,
included free with this subscription"*, with no SAIRNbiz service agreement and no
pricing page in `docs/legal/`. Repointed in `1d46ab8d`, **old citation kept in
the note** so the drift stays auditable.

### One check failed and I merged anyway — said out loud, not glossed

`github-advanced-security` is `failure` at step 19 *"Processing Request
(Linux)"*, with an **empty output body**, no annotation beyond *"exit code 1"*,
and **it cannot be re-run** (GitHub answers 403 *"this workflow run cannot be
retried"*). What is positively known:

* **0 open code-scanning alerts** on `refs/pull/18/head`
* CodeQL, Analyze (python), Analyze (javascript-typescript), hover-separation,
  GitGuardian, Vercel Preview Comments — **all success**; combined status success
* `mergeable_state: clean`, which GitHub does not report for a failing
  **required** check
* The repo's one open secret-scanning alert (**#1, Google API Key, 2026-05-14**)
  has three locations — `SAIRtype_Synced.html`, `index.html`,
  `index.html.html` — **none of which this PR touches**, and it predates the PR
  by four and a half months

**BLIND SPOTS: 3.** (1) I could not read the failing job's log — the API redirect
to the Azure blob returns 401 — so *"empty output, no alerts"* is what the API
reports about it, not a positive explanation of why it failed. (2) The
**competitor-facing half of all fourteen documents is unverified and not
claimed**: no vendor price, feature or roadmap claim was re-checked against any
source, and they should be read as of 2026-09-25 to -27. (3) Merging through the
API bypassed this repo's local push gate, so the 14 files were never seen by
`sairn_push_gate_hook.py`.

---

## 5. SAIRNlegacy — first of the three apps with no audit. **PART 1 ONLY, and the title says so.**

**`88ee8fe7`.** Picked on measurement: largest of the three (319,748 B vs
269,114 and 258,355), most panels (**27** vs 20 and 0), most register rows
(**36** vs 18 and 9), and **twice the Tier A data** of the next (**20** vs 10 and
1). And the reason that outranks those — **it is the only one of the three with a
federal rule that prescribes the product's own paperwork.** The FTC Funeral Rule
mandates specific disclosure documents, when they must be offered, and
itemisation, which turns *"is a competitor beating us"* into a checkable list.
`sairnscape`, with 1 Tier A row, has no comparable axis.

**F1, confirmed by reading code and not by counting words.** The General Price
List is a first-class object — `leg_gplservices`, seeded `:2028`, read `:2917`,
rates edited and server-written `:3301-3302`. **The Casket Price List and Outer
Burial Container Price List are not modelled as price lists at all**: caskets and
urns exist as *merchandise inventory* in `leg_merch_catalog`
(`category:'Casket'`, `category:'Urn'`), a different object from a mandated
disclosure document. `casket price list`, `CPL`, `OBCPL` — **zero occurrences
each.** It does not claim non-compliance; it claims the narrower checkable thing:
**the product does not model it, so it cannot help.**

**F2.** `declinable` / `non-declinable` — **zero**, and declining individual
items *is* the Rule's mechanic. Marked as a vocabulary measurement plus a
model-shape **inference**, not as driven.

**F3, the money surface.** `preneed` has a panel, a collection and 35 mentions;
`irrevocable`, `revocable` and `surety` are **zero** — and that distinction
decides whether funds can be withdrawn and whether they count against Medicaid
eligibility. Stated as a gap in the model, **not** as a defect: whether
SAIRNlegacy intends to administer preneed trusts or merely record that a contract
exists is a product decision I am not making, and it is the highest-value
question on the brief.

**Where we may be AHEAD, named so research starts there:** chain of custody. 23
mentions, `leg_custodylog` a real collection beside `leg_cremations` and
`leg_deathrecords`. **With its own history attached:** per the file's comment at
`:1528`, until 2026-09-21 **56 of 58 `sdnData()` call sites sent no session
token** and 36 `LEG_RESOURCES` tables — `leg_deathrecords` and `leg_custodylog`
among them — were authorised by the licence key alone.

**Checked and cleared rather than left looking wrong:** `sairnlegacy`'s transport
is named `sdnData`, the same name `sairndental`, `sairndesign` and `sairnlaw`
use. Each is its own local function sending its own app's licence key — a copied
naming convention, **not** a cross-app collision.

**BLIND SPOTS: 5**, on the document's own last line — external half absent;
vocabulary counting cannot see a capability under other words; the 27-panel
figure counts DIVs and no panel was checked for whether it works; cemetery,
livery and pet lines named and not examined; and the pick used size and Tier A
density as **proxies** for commercial importance.

---

## 6. The seam watch — wired to nothing, and the 19th seam is named

**`6469d2eb`.** `tools/seam_cannot_tell_watch.py`, a committed baseline, and a
**19-arm** probe.

**WHY THE COUNT GREW, answered rather than guessed.** All 19 COULD-NOT-TELL seams
share one cause — `roleSet()` into `api/_lib/auth.js`, one row per caller — so
the count moved because one more file started calling it. Bisected by when each
caller **first** gained that call: **eighteen landed together on 2026-09-24**,
and the nineteenth is **`api/sairncare-witness.js`, 2026-09-30 08:53** — the
controlled-substance witness lock, the same control that surfaced in §3. A new
unreadable seam on a two-person medication control, and nothing announced it.

**The names are the point, not the count.** A count-only watch is silent on one
seam becoming readable while another becomes unreadable — the total holds still
and the risk moves. Arm C drives exactly that: two in, two out, total unchanged,
**still exit 1**, both sides named.

**Fails closed five ways**, each exit **2 COULD NOT RUN** and never 0: dependency
missing (named, not skipped), dependency crashes, summary unparseable, baseline
missing — **and** it refuses when the parsed row count disagrees with the summary
count, because one of the two is then being read wrongly.

**It does not update its own baseline.** `--propose` prints; no flag writes. A
detector that re-baselines its own rise can never report one.

**BLIND SPOTS: 4.** (1) It cannot say whether a COULD-NOT-TELL seam is **broken** —
unreadable is not unsafe; a rise means a new seam needs a hand-written test.
(2) It inherits `sairn_seam_check.py`'s universe whole, which is why it prints
the clean/not-forwarded/could-not-tell triple as its denominator. (3) **UNWIRED** —
see §7 item 1. (4) All 19 seams share one cause, so the reason-text's role in
seam identity is untested outside the probe's synthetic rows.

---

## 7. Blocked

### 1. `report_only_checks_probe` arm **E2** — BLOCKED, and the diagnosis changed the finding

`tools/report_only_checks.py` is held under **hank's live claim** (claimed 0.2h
before I checked; `FILES:` names it). Not edited. **Diagnosed statically
instead, and the result is not what I recorded eight days ago:**

| | 2026-09-28 (my earlier note) | HEAD today |
|---|---|---|
| E2 failures | 4 | **5** |
| Which | `register_freshness_check`, `log_cluster`, `allan_deviation_check`, `response_shape_check` | `assertion_label_shape_check`, `entry_point_scope_check`, `parse_zero_third_state_check`, `fact_sheet_regenerates`, `verification_owed_report` |

**THE MEMBERSHIP ROTATED COMPLETELY WHILE THE ARM STAYED RED.** The four I named
got their `evidence` fields; **five newly promoted entries landed without one.**
So E2 is not a backlog of four strings to write — **it is a recurring intake
defect**, and the registry has been accepting entries without evidence
continuously while a report-only probe said so and nobody read it. Registry size
**73**; `verification_owed_report.py` lacks **both** `evidence` and `catches`.

**The durable fix is not five strings.** It is making the registry **refuse** an
entry with no `evidence` at import time — fail closed — so the next promotion
cannot do this. That is one change in hank's file.

### 2. The seam watch is UNWIRED

It is **not** in `report_only_checks.REGISTRY` for the same reason — that file is
hank's. So it runs only when somebody types it, which is the engine-with-no-caller
shape this repo keeps finding. **Stated in the module header, in its PURPOSES
entry, and here**, rather than left to be discovered. Wiring it is one REGISTRY
line. It was deliberately **not** given both a PURPOSES entry and a REGISTRY
entry: two descriptions of one tool are two sources that can disagree, which the
inventory gate already refused once.

**BLIND SPOTS: 1.** Both blockers rest on a claim record that is only as fresh as
the last push to it; hank may have finished and not released.

---

## 8. Inventory — ranked twice, and the two orderings still disagree

### By platform severity

| # | Finding | Sev | Logged? |
|---|---|---|---|
| 1 | **SAIRNbiz finding 13** — a record entered while the backup latch was armed is stranded on that device forever. `sbSyncCollection` diffs against the value immediately before that save | **HIGH** | **YES**, register `1977d133`, index `0929a535`. **Still open, still unfixed** |
| 2 | **Nothing counts UNSCOPED `verifySessionToken` calls.** A branch gate that dropped its app scope entirely passes all 14 stubs, including the two reference-green ones. The guard catches a WRONG app and is blind to a MISSING one | **HIGH** | **NEW — logging now.** Carried in both register records' recurrence notes |
| 3 | **`report_only_checks.REGISTRY` accepts entries with no `evidence`, continuously.** E2's membership rotated 4 → a different 5 while red throughout | **MODERATE** | **NEW — logging now.** Blocked on hank's file; the fix is refuse-at-import, not five strings |
| 4 | **FTC 16 CFR 251 exposure**: `SD_BASE_PROMPT` claims SAIRNbiz is *"included free with this subscription"* with no service agreement and no pricing page behind it | **MODERATE** | **Already in the merged audit**, citation now repointed. **Nobody owns the remediation** |
| 5 | **SAIRNlegacy models the GPL and not the CPL or OBCPL** — two of the Funeral Rule's three mandated price lists are merchandise rows, not disclosure documents | **MODERATE** | **NEW — in `88ee8fe7`; logging an index row** |
| 6 | **Nothing reports an app's red set on a cadence.** Twelve suites, 172+ assertions, red for 8 days; the `alf_incidents` gap survived *inside* that redness | **MODERATE** | **YES** — now in **three** register records' recurrence notes (2026-09-18 StoneDesk, and both of today's). Third instance, still unactioned |
| 7 | **A control landing on an already-red suite is invisible.** The witness lock landed 2026-09-30 into a red `alf-mar`, so the arm contradicting it produced no signal | **MODERATE** | **NEW — logging now.** Second instance alongside item 6 |
| 8 | ~~`tools/md_table_check.py` exits **2** while reporting 0 malformed over 820 rows,~~ **&#10060; THIS CLAIM IS FALSE AND IS WITHDRAWN (2026-10-05, same day, by me). `md_table_check.py` EXITS 0, and `main()` has no path that returns 2 at all (`return 1 if (total or unseen) else 0`). I read the 2 off a COMPOUND Bash command, where the status belongs to the pipeline's last element rather than to the tool. Full withdrawal in `docs/SAIRN-OPEN-WORK-INDEX.md` row 73 and in commit `7ca1c7b9`; the half that WAS true -- a three-file default list -- is fixed and the list now covers six files.** Originally: and reads **three** files not including `CRITICALITY-TIERS.md` | **LOW-MOD** | **YES**, logged last batch. Unchanged |
| 9 | The seam watch is unwired | **LOW** | **This document, §7.2** |

### By competitive exposure — and it is still nearly the inverse

| # | Finding | Is a competitor actually beating us? |
|---|---|---|
| 1 | **Two apps still have no competitive-gap doc: `sairndesign`, `sairnscape`** (down from three) | **UNKNOWN, and that is the point.** For two shipping products we cannot answer the question. Unknown exposure cannot be priced |
| 2 | **SAIRNlegacy cannot produce two of three mandated Funeral Rule price lists** | **Probably yes, and it is disqualifying rather than a to-do.** Every established death-care vendor sells Funeral-Rule paperwork as a headline feature, because it is what the director is personally liable for. **Unverified** — §6 of that audit is a brief, not a finding |
| 3 | **SAIRNbiz finding 13** | **Yes, and directly.** "Data you typed lives on one device forever" is the one finding here a prospect discovers themselves in a trial |
| 4 | **The "free" claim with no agreement behind it** | **Not a competitor problem — a regulator and customer problem.** Different axis, same urgency |
| 5 | The red-suite class, the registry intake defect, the unscoped-call blind spot | **No.** Internal verification surface. Real severity, zero competitive visibility — which is exactly why they survive |

**THE DISAGREEMENT IS STILL THE FINDING, and one line of it moved today:** nine of
fourteen apps' audits were branch-only this morning and are on `main` tonight, so
that item is **closed**. What remains is that **nothing on this platform ranks
commercial exposure in the same table as engineering work** — which is why two
apps with no audit at all have never competed with a red suite for attention.

### Deliberately left, per the instruction

Items 8 and 9 of the severity list are logged and not chased. Item 2 is logged
and **not** fixed because changing the stub shape is a decision about 14 files,
including the two reference-green ones. Item 3 is blocked, not deferred.

**BLIND SPOTS: 4.** (1) The competitive ordering is a judgement, mine, with no
market evidence in this document. (2) The severity list covers what this session
touched or tripped over; it is not a sweep. (3) The twelve-suites figure is now
*measured* (14 stub files, 12 red, 2 green) but the **172 assertions** figure is
still quoted from the 2026-09-27 bisect and was not re-derived. (4) §8 item 4's
"nobody owns the remediation" is an absence of evidence in the index, not a
verified absence of an owner.

---

## 9. What this batch did NOT do

* **No revoked licence key driven against production** (§2).
* **No sweep for callers of `/api/claude` without a licence key**, which enforce
  mode now 401s (§2).
* **No competitor research** — the SAIRNlegacy audit is half a document and says
  so; the twelve merged audits' competitor halves are unverified.
* **No fix to `report_only_checks.py`** — blocked.
* **No `sairndesign` or `sairnscape` audit started.**
* **No SAIRNbiz click-through**, and finding 13 is still open.

**BLIND SPOTS: 1.** This is what I know I did not do; it cannot cover what I did
not think to check, which is what the per-section counts above exist to narrow
and do not eliminate.
