# HANDOFF — fourth / ted, batch b18, 2026-10-14

**Written BEFORE the report**, at a point where nothing is half-finished: items
1–6 are committed and pushed, `HEAD == origin/main`, the working tree is clean,
no rebase or stash in progress, and the b18 claim is still held on purpose.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT.**

**The two things worth reading first:** (1) **the 418-hour Tier A obligation is
discharged**, and the one attack point of hank's six that had *never been
reviewed* is the one carrying a finding — a census SQL that reports a
structural zero in the direction that destroys a key; (2) **my own b15 §7.5
ruling is now corrected inline in the spec itself**, so a session reading §7.5
without the b17 review beside it can no longer act on it.

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\b0f8683c-3365-4d5b-82ea-094a13bdff7e\scratchpad\`
Logs this batch: `tier_a_list_b18.log`, `verdict_b18.txt`,
`tier_a_discharge_b18.log`, `reseat_b18.log`, `pull_b18.log`, `pull2_b18.log`,
`push_b18.log`, `push_b18b.log`, `incoming_files.log`,
`statusline_payload.json`.

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `b5ea4d3b` | `git -C <repo> rev-parse HEAD` |
| `origin/main` | `b5ea4d3b` | `git -C <repo> rev-parse origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | clean | `git status --porcelain` (empty) |
| the b18 work commits | **two**: `2050b423` (items 1–5) and `b5ea4d3b` (the citation re-derivation) | `git log origin/main --oneline -3` |
| push forced? | **NO** | `0c25a770..b5ea4d3b`; one `! [remote rejected]` on the first attempt, resolved by `git pull --rebase` and **not** by `--force` |
| `SAIRN_SEED_GATE=off` | **not used**, any form | — |
| `.claude/settings.json` | **not edited, not committed** | not in either commit's file list |
| hooks | **untouched this batch** — I neither added, removed nor restored any | by instruction |
| files written outside `docs/` | **0** (plus my three root deliverables) | by instruction |
| all six deliverable files present on `origin/main` | **6 of 6** | `git cat-file -e origin/main:<path>` per file |
| b18 manifest | **6 of 6 `done`**, close pending the three uploads | `batch_manifest.py --check --agent fourth --batch b18` |

**`b5ea4d3b` IS THE STATE AT FINALISATION OF THIS HANDOFF** — the report, the
digest, the b18 close and the claim release all land after it. **Re-derive
HEAD; do not quote this line.**

---

## 1. ITEM BY ITEM

| # | item | state | exact next step |
|---|---|---|---|
| 1 | manifest first, closed with the env var | **DONE** (close is the last action of the batch) | **cc fixes `tools/batch_manifest.py:386`** — still needed, `PYTHONIOENCODING=utf-8` was required on every call again |
| 2 | the 417h/418h Tier A obligation: discharge or hand back | **DONE — DISCHARGED, exit 0, as the assigned owner** | **hank: five findings. cody: four failing-first arms. cc: one runbook omission.** (§3.1) |
| 3 | §7.5 correction inline; spec the photoAnalyze write side and fqSaveQuote | **DONE — correction inline, §7.6 added, T17 and T18 spec'd** | **hank implements; cody writes T17/T18 FAILING FIRST** (§3.2) |
| 4 | one home-care practitioner question | **DONE — H8** | **a home-care agency owner or coordinator answers it**; then hank edits one constant (§3.3) |
| 5 | triage the 19 open obligations; request the cc tool | **DONE — 18 triaged with a disposition each, tool spec'd with 6 arms** | **cc builds the session-start surface; somebody takes over the four `cloud` rows** (§3.4) |
| 6 | push without force | **DONE — `0c25a770..b5ea4d3b`, 0/0** | nothing |
| — | this handoff, before the report | **DONE** | — |

---

## 2. CLAIMS, LOCKS AND HOLDS

| hold | count | detail | command |
|---|---:|---|---|
| repo claims held | **1** | b18, published on `origin/main`; release after the report and digest are up | `sairn_claim.py list` |
| **Tier A obligations assigned to me** | **3 open, 2 of them overdue** | **(a) 397h** `cody` 2026-09-28T03:34:57Z `dnt_ar, dnt_revenue`; **(b) 338h** `hover2` 2026-09-30T13:59:56Z `leg_insurance, mech_checks`; **(c) 3h** `hank` 2026-10-14T13:50:42Z `leg_*` — **inside the 24h deadline, not overdue** | `--list` |
| session locks held | **1 of 14 on disk** | `fourth.lock` still carries `claude_pid 53204` from `2026-10-13T05:36:03` — **re-read this batch, not quoted**; seven batches old | `cat ~/SAIRN-SESSION-LOCKS/fourth.lock` |
| locks removed by me | **0** | `rm` is denied and I did **not** route around it | — |
| `git stash` | **0** | | `git stash list` |
| worktrees besides main | **4** | **none mine** — all four are other sessions' temp gate trees under `AppData\Local\Temp` | `git worktree list` |
| status registry row | `working` | set at start; set to `idle` at release | `sairn_status.py set` |

**THE 418-HOUR OBLIGATION THAT HEADED THIS SECTION LAST BATCH IS GONE —
DISCHARGED, NOT MOVED.** What replaces it as my biggest open item is **two
more**, both mine, both overdue, and **b19's items 1 and 2 in age order** —
the same rule that produced this batch's item 2:

* **b19 item 1 — the 397h `dnt_ar`/`dnt_revenue` obligation.** Five specific
  claims cody asked to be tested, one file
  (`tests/reachability/resource_demand_probe.py`). **Its sha
  `f88105a88287` is `REFUSED [NO_OBJECT_IN_CLONE]`**, so it can only receive a
  state review — say so in the verdict, as this batch did.
* **b19 item 2 — the 338h `leg_insurance`/`mech_checks` obligation.**
  Retrospective, opened by hank on hover2's behalf. **Its verdict is
  PRE-REFUSED unless it names what it opened and what it looked for**, so it
  needs a real drive of `hover_citation_linter.py` — **read-only, against this
  clone's mirror of `.claude/skills/sairn-hover-auditor/`, and NEVER by
  entering `Documents\SAIRN-hover`.**

**I did not start either in b18 and that was a decision, not an oversight:**
one Tier A discharge cost ~9,000 words of verification this batch, and three in
one batch produces three thin verdicts. **A thin verdict is worse than a late
one** — it shortens the queue and gives the next session no reason to look.

---

## 3. WHAT IS OPEN, AND WHY

### 3.1 THE DISCHARGE — and the finding is on the point nobody had reviewed

`docs/2026-10-14-fourth-b18-tier-a-queue14-discharge.md`.

**Four of hank's six attack points survive re-verification at HEAD**, and one
of them is better than it was: the 2026-09-29 ROLE-not-IDENTITY finding on
`propose_clock_correction` **has been implemented** —
`api/sd-data.js:7076-7081` now sets `self_correction` on the entry and
`has_self_correction` on the row, flag-not-refusal, with the lockout argument
in the comment. **That is a closed loop and worth saying out loud.**

**ATTACK POINT (f) HAD NEVER BEEN REVIEWED** — absent from the 2026-09-29
document's summary table, body *and* exclusions, with no line saying it was
left out. **It is the one with the defect:**

```
CMD sed -n '73,81p' sql/legacy_ciphertext_census.sql
    count(*) filter (where data->>'enc' is not null
                       and data->>'enc' not like 'v2.%')   as legacy_rows,

CMD api/sc-credentials.js:205   next[service] = nextEntry;     (ALLOWED_SERVICES = { stedi: true })
CMD api/sc-eligibility.js:180   const rec = stored.stedi;
```

**The real path is `data->'stedi'->>'enc'`. `data->>'enc'` is NULL on that
shape, so the surface reports `legacy_rows = 0` for every possible database
state** — and that count is step **4a**, the precondition for clearing
`SD_AUTH_SECRET_PREVIOUS` (`api/_lib/auth.js:442-445`). **A structural false
zero in the destructive direction.** Severity is bounded and I said so: the
Stedi key is re-enterable and an undecryptable row answers 503. **A gate that
cannot fail is still the defect.** The same wrong path propagated to
`sql/sd_encryption_key_revoke_2026-09-24.sql:113`.

**FOUR MORE FINDINGS AT HEAD, and N1 is the one to act on first:**

* **N1 — the correction trail has a door beside it.** `api/sd-data.js:7179` is
  an **unconditional** copy of the EVV fields, so a caregiver can replace an
  already-set `clock_in_at` with **no `clock_corrections` entry and no
  `self_correction` flag**. The only guard is render-time
  (`sairnsenior.html:2975`). **The branch (b) blocked is audited; the branch it
  did not is not.**
* **N2 — `api/sen-auth.js:263-288` `setup` can demote the last owner.** No
  self-target check, no remaining-owner count; one request leaves
  `PROVISIONING_ROLES` empty with no in-app route back. **`set_active` already
  does this check** — the same reasoning was never applied to a role change.
* **N3 — a position excluded by a NON-EMPTY `applies_to_positions` list is
  dropped silently.** An `activities` person at a PA ALR reads `meets: true`
  against 2 hours when 36 may be owed. **Masked today only because `hire_date`
  is never written** — so it must be fixed *before* that field starts being
  written, not after.
* **N4 — three comments in `api/_lib/compliance-rules.js` claim driven
  coverage** for the anniversary, leap-day and day-zero cases that **no
  committed arm exercises.** Stated fairly: "driven" most likely means driven
  by hand, and the defect is that a hand-drive leaves no artefact.

**ROUTING: five to hank, four failing-first arms to cody, one to cc** — the
four-step rotation is published to an operator in `docs/NHI-REGISTER.md:69` and
`tools/secrets_inventory.py:74` **with step 4a missing entirely**, and the
generator is cc's.

### 3.2 hank and cody — the write side nothing guards

`docs/2026-10-14-ai-safeguards-spec.md` §7.6, new this batch.

**`sd_photos` syncs raw model prose to the database with no provenance field,
and it is in NONE of the three AI registries.** The `enforceAiApproval` gate is
opt-in by the writer (`api/_lib/ai-safeguards.js:190` returns on a missing
`ai_source`) and this writer does not opt in; the resource is in neither
`HIGH_RISK_AI` nor `NOT_HIGH_RISK_AI`; and it is absent from `AI_SCANNED_TEXT`
**while its three siblings — `rf_photos`, `bld_photo_analyses`,
`grd_progress_photos` — are all there.** That asymmetry is the evidence it is
an omission rather than a decision.

**AND IT IS NOT LOCAL, which is the part a reflex gets wrong:** `sd_photos` is
in `SD_SYNCED` (`stonedesk.html:2027`) and in `SD_LOCAL_RESOURCES`
(`api/sd-data.js:14184`).

**ONE THING MARKED UNVERIFIED AND IT MAY MATTER MORE THAN THE REST:**
`sql/stonedesk_data_schema.sql:343` caps the row at 64KB while the synced
payload carries a base64 image accepted up to 10MB, **and
`api/sd-data.js:14263` maps the resulting 400 to `503 NOT_PROVISIONED`
("tables are not set up yet").** So it is possible no `sd_photos` row has ever
landed and the failure has been reporting itself as an unprovisioned table.
**I did not run it. If the row never lands, the provenance gap is latent and
the size failure is the more urgent half.** hank's.

**`fqSaveQuote` is confirmed local-only on three independent legs** — and
**local-only is the finding, not the exemption**: a priced, signed, AI-written
quote that never reaches `/api/sd-data` is invisible to the server gate *by
construction*, and lives in one browser. **T18's control arm is the one a
reviewer would cut and the one that matters:** it asserts
`stonedesk_quotes` is **absent** from `SD_SYNCED` / `SD_LOCAL_RESOURCES`, so
the day somebody promotes the key, the arm fails loudly and the retention
question has to be answered rather than inherited.

**BOTH T17 AND T18 MUST FAIL ON TODAY'S CODE BEFORE ANY FIX LANDS. If the first
run passes, the arm is wrong, not the code.**

### 3.3 A HOME-CARE PRACTITIONER — one question, and it is the only one a measurement could answer

`docs/2026-10-14-fourth-b16-confirm-questions.md` **H8**: *when a referral comes
in by phone, does the coordinator who took the call have to ask an owner or a
billing manager to type it in?*

**Option B (management-only) stands until a practitioner answers** — per this
batch's standing decision — and `docs/2026-10-14-fourth-b17-sen-rf-write-map.md:162` records that switching is **one constant** (`SEN_INTAKE_WRITE_ROLES`).
**The failure direction of leaving B in place is a phone call, not data loss**,
so there is no urgency; the sheet says so to the reader as well.

**The sheet's own heading was corrected from TEN to ELEVEN** in three places. A
sheet that says ten and carries eleven is a document people stop trusting.

### 3.4 cc — the session-start surface, and the queue finding behind it

`docs/2026-10-14-fourth-b18-tier-a-triage.md`.

**THE FINDING THE TRIAGE PRODUCED: four open obligations are assigned to
`cloud`, which has not run since 2026-09-27** — and **two of the four were
created this week**, already unreviewable by their owner. The cause is one
function: `eligible_reviewers()` (`tools/tier_a_review_gate.py:1329`) tests
only that a claim file exists on disk. **There is no liveness test**, so a
session that stopped three weeks ago is still a candidate every time
`assign_owner` runs. An obligation owned by a dead session can only be closed
by `--takeover`, **and nothing surfaces that it needs one.**

**THE ASK (a request — `tools/` is cc's and nothing under it was written by
me):** a session-start surface printing (1) obligations **owned by this
session** over 48h, loudest first, with the ready-to-paste `--discharge`
command, and (2) obligations whose **owner has not run recently**, with the
measured liveness fact and the `--takeover` command. **Six failing-first arms
specified, and A3 and A6 are the load-bearing two:** A3 — a missing register is
**exit 2 COULD NOT RUN**, never a silent 0; A6 — an unreadable
`owner_assigned_at` is a **third state**, never coerced to 0 and never read as
fresh.

**And the figure nobody has looked at: 34 of 88 REVIEWED records carry a sha
that no longer resolves.** `--reseat-shas` says so itself and says its default
run proves nothing about them. Not urgent, not mine, larger than the open queue
in front of it.

### 3.5 THE THING THIS BATCH LEARNED, and it is mechanical

**Between measuring the queue and pushing, `git pull --rebase` brought in 50
commits — two of which touch `api/sd-data.js` and `api/_lib/auth.js`, the files
the discharge is about. EVERY citation into those two files had moved.**
`api/sd-data.js:7169` → `:7179`; `api/_lib/auth.js:482` → `:510`. They were
re-anchored on the quoted text, **not re-offset by a constant**, and
`b5ea4d3b` is that commit. **A verdict document rotted inside an hour of being
written**, which is the eighth cross-domain convention happening in real time
rather than in a retrospective. **Any session quoting a line number out of
either b18 document should re-derive it first** — including out of this
handoff.

### 3.6 Still open from earlier batches

* **cc:** `tools/batch_manifest.py:386` (the encoding crash — still worked
  around with `PYTHONIOENCODING=utf-8` on every call this batch);
  `tools/fixture_lock_check.py` (b13); the by-design validator (b12) and **four
  rulings still at `DECIDE_OR_NOT_PROMOTED`**; a lock reaper with a stated
  threshold; the `rm`-deny decision; `--read-the-line` on
  `citation_line_drift_check.py`; the corrupted register twin on `7bc26782e533`
  and the encoding-blind dedup test (b17 §3.5); **and now the session-start
  surface (§3.4) and the step-4a runbook omission (§3.1).**
* **cody:** the two SAIRNcash entitlement arms (b16, **ARM B first**); fixture
  rows 26–50 with row 39 first; b14's T7/T8/T9/T10/T14; **T16** (b17);
  **and now T17, T18 and the four b18 arms (N1–N4), all failing-first.**
* **hank:** the three role matrices, **SAIRNlegacy first**; the two b17
  conditions (`SEN_SETTING_PUBLIC_FIELDS` comment, `ai_source` required per
  surface); the four removal paths with `sv_scribe_consent` first; **and now
  F1 and N1–N4, plus §7.6's five implementation points. NOBODY DELETES
  `api/ai-notice.js`.**
* **MICHAEL:** the Option A / Option B write-map decision — **B stands and
  nothing is blocked**; the two `[DRAFT — LAWYER]` strings.
* **counsel:** three questions. **A funeral director:** five. **A vet
  practice:** two. **A home-care practitioner:** one (H8, new).
* **fourth (me):** **the two overdue Tier A obligations in §2, as b19 items 1
  and 2 in age order**; fixture row 11, whose code is cc's.

---

## 4. THE THING THE NEXT SESSION MUST DO FIRST

**Write the manifest. Then run `tier_a_review_gate.py --list` before anything
else and read the rows owned by `fourth`** — there are three, two overdue, and
one of them arrived three hours before this handoff was written. **That is
item 1 of b19 and it is not optional:** last batch's handoff named one overdue
obligation as the biggest open item, and the only reason it was discharged is
that the instruction named it explicitly. **A queue whose only reader is a
command nobody runs is the defect, not the forgetting.**

**And the b17 lesson still stands, because it applied again this batch in the
other direction:** when a batch hands you a premise — *"api/ai-notice.js
carries a second ack store"*, which was **my own** ruling — **measure it before
acting on it.** One `grep` over the endpoint's own body disproved it, and
acting on it would have deleted working code.

---

## 5. FINAL STEPS STILL AHEAD OF THIS HANDOFF

1. `PYTHONIOENCODING=utf-8 python tools/drive_upload_verify.py --agent fourth
   --batch b18` — **will report findings**, because the report and digest do not
   exist yet. Expected; the handoff is written first by instruction.
2. The report and digest, then the same upload-and-verify, then a **Drive-side
   API read** — the mount proves the bytes are in the sync set, not that Google
   acknowledged them.
3. `PYTHONIOENCODING=utf-8 python tools/batch_manifest.py --close --agent
   fourth --batch b18` — **after** all three are up, because closing is
   *defined* as all three verified.
4. Release the b18 claim and set the status row to `idle`.

**Nothing is partial.** Every open item above is another session's, or mine and
named as mine with its b19 slot, or a measurement with its command stated.
