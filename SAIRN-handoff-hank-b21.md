# SAIRN handoff — hank b21 — 2026-10-19

**Subject:** the platform's oldest review obligation discharged; `api/bridge.js`'s
unknown-action fall-through closed with an ablation; the three unrun SQL files
bundled and uploaded; the IOLTA attestation designed but not built; three
open-work rows. **Item 3 was correctly SKIPPED** — fourth holds
`stonedesk.html`.

**Written BEFORE the report, with nothing half-finished.** Every suite named
below was run at the sha this handoff describes.

---

## 1. COMMITTED AND PUSHED STATE

| commit | what |
|---|---|
| `review(hank b21)` | the 522h review obligation, discharged with a verdict |
| `fix(bridge b21)` | unknown `?action=` refused, + a 14-arm suite with an ablation |
| `docs(hank b21)` | three open-work rows, the attestation design note, the SQL bundle |
| `docs(hank b21)` | the active-work entry |
| `chore(b21)` | the renamed suite's header, and the derived documents regenerated |
| `chore(defect register b21)` | the register record the push gate required for the bridge fix |

**Re-derive the tip with `git rev-parse --short origin/main`.** Five sessions
push to one branch; it moved repeatedly during this batch and any sha written
here is stale by the time it is read. **Landing was confirmed by comparing
`origin/main` to `HEAD` by sha after a fresh fetch** — not by grepping the push
output, for the reason in §6.

**Files:** `api/bridge.js`, `api/b21-bridge-unknown-action.test.js` (new),
`docs/tier-a-reviews.json`, `docs/SAIRN-OPEN-WORK-INDEX.md`,
`docs/open-work/{ACTIVE,sairnlaw,stonedesk,tooling}.md`,
`docs/2026-10-19-hank-b21-attestation-design.md` (new),
`SAIRN-sql-hank-b21.txt` (new), `docs/MASTER-PLAN.md`,
`docs/traceability-matrix.md`, `SAIRN-ACTIVE-WORK-hank.md`.

**ZERO gate overrides.** No `SAIRN_GATE_EXEMPT`, no `SAIRN_SKIP`, no
`SAIRN_SEED_GATE`. Nothing to disclose under PR §3.3.

---

## 2. CLAIMS HELD

**Held, and released at the end of the batch:**

    hank -> hank    b21: discharge review obligations; b18 re-derive; api/bridge.js
                    unknown-action refusal + negative control + ablation; concat 3
                    sql files to Drive; attestation design note; 2 open-work rows.
                    FILES: api/bridge.js api/b21-bridge-unknown-action.test.js
                    docs/2026-10-19-hank-b21-attestation-design.md
                    docs/SAIRN-OPEN-WORK-INDEX.md SAIRN-handoff-hank-b21.md
                    SAIRN-report-hank-b21.txt SAIRN-digest-hank-b21.txt
                    SAIRN-ACTIVE-WORK-hank.md NOT-stonedesk.html-fourth-holds-it

**Claims held by OTHERS that shaped this batch:**

* **fourth → `stonedesk.html`** (b34, routing phase 1). `sairn_claim.py check`
  returned **BLOCKED** by name: *`session: fourth`, `blocked by: same app:
  stonedesk`*. **This is why item 3 was skipped**, and the endpoint half of the
  same problem was fixed instead.
* **cody → `api/sd-data.js`, `tests/`, `docs/known-red-suites.json`** (b26).
  Three things below route to cody for this reason.

---

## 3. THE SIX ITEMS

### Item 0 (dispatched first) — the review obligation

**Discharged the platform's oldest: 522h, author `fourth`, opened
2026-09-28T00:16:59Z**, assigned to hank, over `alf_facility` + 11 other named
resources. `obligation_surface.py` confirms it is gone: **15 open / 12 overdue
before, 14 / 11 after.**

**Reviewed against CURRENT HEAD, not the recorded sha, and the record's own
COULD-NOT-TELL stands:** `3e3e1cca210e` does not resolve in this clone. Said in
the verdict rather than glossed.

**ACCEPTED, with two findings.**

1. **The ablation claim was RE-DRIVEN, not trusted.** A copy of `api/` in an
   isolated scratch dir — the live clone was never mutated. Baseline
   **28 passed / 0 failed**; the four-line `ALF_MANAGEMENT_ROLES` guard deleted
   from the `alf_facility` write branch; `node --check` clean;
   **23 passed / 5 FAILED** (the four role arms plus `[ROLE-ord]`), with
   `[ROLE-ctl]` **staying green**. One layer removed, not the floor.
2. **The author's own attack point on `caregiver` is HALF WRONG, and the wrong
   half matters.** The record says it *"refuses for the wrong reason and buys no
   measured coverage"*. **Measured:** `caregiver` **is** in
   `ROLES_BY_APP.sairncare` — driven, not read:
   `["owner","nursing","med_aide","caregiver","billing","activities","office_manager"]`
   — so `verifySessionToken` accepts the session and the 403 comes from the
   management gate. **The reason is right**, and the arm goes **red** under the
   ablation, so it **does** buy coverage. What is true is weaker: `caregiver`
   has **zero** `roleSet()` hits in `api/sd-data.js` (against nursing 9,
   activities 3, med_aide 1, billing 12, owner 27), so that one arm cannot
   distinguish this gate's refusal from a universal one.
3. **THE FINDING THE RECORD DOES NOT NAME.** `office_manager` is a real
   sairncare role, offered in **both** `sairncare.html` role dropdowns, present
   in `ROLES_BY_APP.sairncare`, with **zero** `roleSet()` hits — **and it is not
   in `ALF_NON_MGMT`**, which is exactly
   `['nursing','med_aide','caregiver','activities']`. **Five of seven roles are
   excluded from the gate and only four are asserted.**
4. **The mis-attribution the author declared is CONFIRMED with the measurement
   the record lacked:** `bld_draws`, `bld_tna`, `sdn_clients`, `sen_claims`,
   `sen_clients` appear **only** in `tests/role_gate_loop_rule_probe.py` (1–2
   hits each) and **zero** times in the other three recorded files — and that
   probe states at its own line 39 that it touches neither `api/sd-data.js` nor
   any real suite.
5. **The deployed gate remains UNVERIFIED and the author said so honestly.**
   `tools/alf_facility_role_gate_live_probe.py` re-driven at this sha exits
   **2**: *"UNVERIFIED — ALF_LICENSE is not set, so NOTHING was driven … This is
   the THIRD STATE. It is NOT 'the gate is fine'."* Every arm is against a mock
   and this review does not discharge that.

### Item 1 — the two b18 items, re-derived

**BOTH LANDED.** Both are in commit **`144dfb715`** (2026-10-16),
`git merge-base --is-ancestor 144dfb715 origin/main` → **true**.

| item | evidence at this sha |
|---|---|
| straight-time-floor sign guard | `api/b17-straight-time-floor.test.js` → **11 passed, 0 failed, 0 unproven**, including **A10 ABLATION** (without the guard the deduction returns `-2000`, total < gross) and **A11 CONTROL** |
| trust-lock hard-lock | `api/b17-trust-lock-hard.test.js` → **14 passed, 0 failed, 0 unproven**, including **T8d** — emptying `LAW_TRUST_LOCKED` now fails *this* file, which is fourth's H1 closed |

**NOTHING WAS OPEN, so nothing was finished.**

**LIVE PROOF IS NOT OBTAINABLE AND THAT IS REPORTED AS A THIRD STATE, NOT A
PASS.** Driven against the real deployed URL with `tools/sairn_http.py`:

    law_trusttx write, NO licence      -> 401
    law_trusttx write, bogus licence   -> 401
    sen_visits read, NO licence        -> 401

That is evidence about the **licence gate** and **none at all** about either
fix. Both live in pure modules (`api/_lib/sen-payroll.js`,
`api/_lib/law-roles.js`) reached only through a session-gated handler, so a
live assertion needs a real licence and a real employee session, which this
clone does not carry.

### Item 2 — `api/bridge.js` refuses an unknown `?action=`

The dispatch block ended `return handlePush(body, res, req)` with nothing
between it and the proxy_get branch, so **every `?action=` the endpoint did not
know became a push attempt**.

**THREE LIVE CALL SITES LAND THERE — measured by grepping every app file for
the URL, not reasoned about:**

| call site | sends | was answered |
|---|---|---|
| `stonedesk.html:12814` | `?action=maps-static` | 401 NO_LICENCE |
| `stonedesk.html:12927` | `?action=maps-optimize` | 401 NO_LICENCE |
| `stonedesk.html:7795` | **no action, no data_type**, a `sairn-mobile-sync` envelope | reaches `handlePush` |

So a caller asking for an action that **has never existed** was told its
**credentials** were wrong. Wrong diagnosis, wrong layer — the shape Guardian
check 30 records costing a session a hunt for a `RESEND_API_KEY` that was
present and correct the whole time.

**The change:** `KNOWN_ACTIONS = ['push', 'proxy_get']`, spelled once, and the
`400 UNKNOWN_ACTION` refusal **derives its message** from it — the same decision
`api/_lib/countersign-endpoint.js` made, so a fourth action cannot be added to
the gate without the message following. **`pull` is deliberately absent** and
arm B2 asserts that absence: it was removed 2026-09-17 for serving one tenant's
data to an unauthenticated GET keyed on a **raw licence key**, and a refusal
that advertises a withdrawn read side is worse than no refusal.

**`api/b21-bridge-unknown-action.test.js` — 14 arms, 0 failed.**

* **A1 — THE NEGATIVE CONTROL THE DISPATCH ASKED FOR.** A **licence-headed and
  session-headed** POST to `?action=maps-optimize` → **400 UNKNOWN_ACTION with
  ZERO `bridge_data` upserts.** The valid credentials are the point: without
  them a 401 arrives whether the refusal exists or not and the arm passes for
  the wrong reason.
* **A4** — an *unauthenticated* unknown action is **still** `UNKNOWN_ACTION`,
  never `NO_LICENCE`.
* **C1/C2/C3 — CONTROLS.** `?action=push` still upserts; both proxy_get
  spellings still route, including the query form nothing currently uses, which
  is exactly what a narrowing change breaks silently.
* **E1 — ABLATION.** With the guard cut from a lifted copy,
  `?action=maps-optimize` reaches `handlePush` **and upserts** — the pre-b21
  behaviour reproduced on purpose. **E2 — CLEAN:** the ablated copy still serves
  `?action=push`, so E1 is a removal and not a corrupted file.

**Regression:** `api/bridge-push-auth.test.js` still **27 passed, 0 failed**.

**AND THE ABLATION'S FIRST DRAFT FAILED ON A CORRECT ABLATION.** It asserted
`!ablated.includes('UNKNOWN_ACTION')`, which matched `KNOWN_ACTIONS`' own header
comment saying *"the UNKNOWN_ACTION refusal below"*. **An ablation check that
matches prose ABOUT the code cannot tell a removed guard from a described one.**
It now asserts the code literal, and the reason is written at the line.

### Item 3 — SKIPPED. **The claim holder is `fourth`.**

As the dispatch instructed, the claim list was checked first.
`python tools/sairn_claim.py check` returned:

    BLOCKED -- another session already claimed overlapping work:
      session   : fourth
      subject   : fourth
      task      : b34: routing phase 1 ... FILES: ... stonedesk.html ...
      blocked by: same app: stonedesk

**Live, not a stale claim** (claimed ~0.5h before the check). Nothing in
`stonedesk.html` was touched.

**The premise was verified live first, so the routed spec is accurate rather
than inherited:** both `?action=maps-optimize` and `?action=maps-static` answer
**401** against the deployed endpoint today.

**AND ONE CORRECTION TO THE DISPATCH'S PREMISE, which matters for whoever picks
this up:** after b21's endpoint fix deploys, those two call sites will answer
**`400 UNKNOWN_ACTION`**, not 401. The catch-arm messages naming the Maps API
key are wrong either way — the key was never the fault — but the status code in
the spec will have changed by the time the fix is written.

### Item 4 — the SQL bundle

**`SAIRN-sql-hank-b21.txt` — 49,450 bytes, 854 lines.** The three unrun schema
files in the dispatched order, each **VERBATIM**.

**"Verbatim" is PROVED, not claimed:** the builder asserts each repo file's
exact bytes appear in the bundle (all three `True`), and **each file's own
sha256 is printed at its separator** so the bundle can be checked against the
repo rather than trusted.

**The negative inserts, and which are new:**

* **File 1** (`sairnlegacy_settings_schema.sql`) ships its own two and they
  appear verbatim — the hyphenated enum value and a JSON string where the object
  belongs.
* **Files 2 and 3** (the two countersign schemas) **ship none.** Their
  verification blocks check counts and constraint names only, so **nothing in
  them is evidence the constraints refuse anything.** Negative inserts for both
  are **authored in the bundle** and labelled **"ADDED FOR b21 — NOT IN THE REPO
  FILE"**, so nobody diffs it against the repo and concludes the repo lost
  something it never had. Each covers the **self-signature** refusal and the
  **half-written signature** refusal, with the expected `ERROR 23514` and the
  constraint name.
* **Each added block carries a POSITIVE CONTROL that must SUCCEED**, because two
  erroring inserts are equally consistent with *"the constraints work"* and
  *"the table rejects everything I send"*, and only one of those is evidence.

**UPLOADED AND VERIFIED THROUGH THE API, not just the sync mount.** Copied to
`G:/My Drive/SAIRN-status` byte-identical (sha
`74ccb4f1…e881f5ea` both sides), then read back through the Drive API:

    id        1j0bFg1rVn-d4VpaHEXIxPvFhX3Ja2k93
    size      49450  (matches local exactly)
    title     SAIRN-sql-hank-b21.txt
    snippet   the bundle's real first lines

**That second step is what closes the limit `drive_upload_verify.py` prints on
every run** — a matching mount read-back proves the bytes are in the sync set
and **not** that Google acknowledged them.

### Item 5 — the attestation design note

`docs/2026-10-19-hank-b21-attestation-design.md`. **Design note only, no code**,
as dispatched. One-line concept first, then **Goals (5)**, **Non-goals (6)**,
**four alternatives** with the recommendation argued, and cross-cutting concerns
split **security / data / test plan**.

> **CONCEPT.** A completed three-way reconciliation becomes an ATTESTED record
> only when a bar-admitted person signs a hash of the exact comparison that was
> run — so "the three legs agree" and "a lawyer has attested that they agree"
> are two different stored facts, and the app can never present the first as the
> second.

**The sharpest decision in it: `MODE_ALWAYS`, not `MODE_PREPARED_ONLY`.** C2's
lock lets a bar-admitted person write `law_trusttx` with no token because C2
asked only whether a paralegal may *prepare*. Here that asymmetry **defeats the
purpose** — an attorney who ran the reconciliation would attest their own work
with no second party and no token, which is the shape b20 withdrew a grant to
avoid. SAIRNlegacy's F1 lock is `MODE_ALWAYS` for the same reason.

**And it names the one question it cannot answer rather than guessing:** under
`MODE_ALWAYS` a **solo practitioner cannot attest at all**. Three answers are
laid out and they are not equivalent; the one with the honesty in it changes
what the record **claims** (single-signer, recorded as such) rather than
weakening what it requires. **Alternative B is kept rather than dismissed
precisely because it solves that case** — the only reason to keep a rejected
design.

### Item 6 — THREE open-work rows, not two

Rows built **whole and joined**, never by splitting an existing row on a pipe
(PR §2.1), with each row's pipe count asserted at 8 **before** it was written.
Shards reconciled: `open_work_shard.py --write` then `--check` → **CLEAN, 817
rows, byte for byte.**

1. **`api/b20-countersign-open.test.js` IS TRACED TO NOTHING.** The row **is**
   the citation. **ACCEPTANCE TEST, written into the row then DRIVEN:**
   `traceability_matrix.traced()` now answers **True** for that file where it
   answered **False**.
2. **The `reconcile` verb STAYS UNDECLARED** — recorded as a **CLOSED
   DECISION**, not left open, because an undeclared verb nobody wrote down reads
   as an oversight and gets "fixed" by the next session. Three measurements in
   the row.
3. **Three live `api/bridge` call sites ask for actions that do not exist** —
   opened because b21 fixed the endpoint half and the caller half is fourth's.
   It also carries **b21's own declared residual** (an absent `?action=` is
   still accepted) so it is tracked rather than living only in a test comment.

**AND THE SUITE WAS RENAMED** `api/bridge-unknown-action.test.js` →
`api/b21-bridge-unknown-action.test.js` so row 3 can cite it. **Without that it
would have landed UNTRACED in the same measurement that closed row 1** — the
exact gap item 6 exists to close, reproduced by the fix for it.

**Measured both ways:** test files on disk **996 → 997**, traced **771 → 773**,
so **untraced 225 → 224 — a net drop of one WITH a new suite added.** Both
suites answer `traced: True`.

---

## 4. WHAT IS OPEN, AND THE EXACT NEXT STEP

### A. `office_manager` is an unasserted excluded role on the `alf_facility` gate

**The finding from the 522h review.** `ALF_NON_MGMT` in
`api/sd-data-alf-isolation.test.js:362` is exactly
`['nursing','med_aide','caregiver','activities']`.

**Open because the file is cody's api/ test surface this batch.**

**NEXT STEP:** add `'office_manager'` to that array — a one-token change. The
suite's loop already builds a 403-and-no-upsert arm per role, so nothing else
is needed. **Then re-run the ablation** and confirm the new arm goes red with
the others; an arm that stays green under the ablation is testing nothing.

### B. The deployed `alf_facility` role gate is UNVERIFIED

`tools/alf_facility_role_gate_live_probe.py` exits **2** for want of
`ALF_LICENSE`. **NEXT STEP:** set `ALF_LICENSE` to a real SAIRNcare licence with
two active employees of different roles, then run it. Until then every arm on
that gate is against a mock, and the probe is right to refuse rather than report
clean.

### C. The two b18 items have no live proof

**NEXT STEP:** a live assertion needs a real SAIRNlaw licence **and** a signed
employee session. Not with bare `curl` — `tools/sairn_http.py` from a script or
`mcp__claude_ai_Vercel__web_fetch_vercel_url` from a turn. **A 401 means
UNVERIFIED, not verified-good** (PR §3.2).

### D. `stonedesk.html` — the Field Map catch arms and the `:7795` caller

**Open because fourth holds the file** (b34, live). Open-work row 3 carries the
full spec. **NEXT STEP, two separate things:** (1) the two catch arms must stop
naming the Maps API key — the action has never existed, so the key is not the
fault — and `fmRenderMap` should show *"Route preview is not available in this
build."*; (2) `:7795` should send a real action or be deleted, because a
`.catch(){}` around a write that stores three nulls is a silent failure by
construction.

### E. An ABSENT `?action=` on `api/bridge.js` is still accepted

**Declared, not discovered — arm D1 asserts it.** **NEXT STEP:** decide whether
an absent action is also refused. **If yes, D1 is the arm to update and
`api/bridge.js`'s comment must change with it. Do not "fix" D1 by deleting it.**

### F. The three SQL files are still UNRUN

**NEXT STEP:** run `SAIRN-sql-hank-b21.txt` **one file at a time**, and run each
file's verification block **before moving to the next** — including the negative
inserts, each of which must **ERROR**, and the positive controls, which must
**succeed**. **The Supabase editor reports success for the statements it did
run, so a partial apply is indistinguishable from a full one from the outside.**

### G. The attestation mechanism is designed and not built

**NEXT STEP:** answer §6 of the design note — *can a solo practitioner attest
their own reconciliation?* — **before any code.** The answer changes which
alternative is correct.

### H. cody's two b19 routed changes are STILL UNAPPLIED

Re-measured against origin this batch. `api/sd-data.js:18804` still carries
`roleSet({ owner: true })`; `legRoles.decide` is still called with **three**
arguments at `:16610`. **NEXT STEP:** get them applied or reassigned. b20 made
change 1 **safe** to paste.

### I. The three red arms in `api/b19-iolta-reconcile-carveout.test.js`

Unchanged from b20: R1c, R1f, R2, expected. The
`docs/known-red-suites.json` entry is routed in `SAIRN-handoff-hank-b20.md` in
pasteable form and **cody still holds that file.**

---

## 5. EVIDENCE — EVERY SUITE RE-DRIVEN AT THIS SHA

| suite | result |
|---|---|
| `api/b21-bridge-unknown-action.test.js` | **14 passed, 0 failed** (new) |
| `api/bridge-push-auth.test.js` | 27 passed, 0 failed |
| `api/sd-data-alf-isolation.test.js` | 28 passed, 0 failed |
| …ablated (`ALF_MANAGEMENT_ROLES` guard cut) | **23 passed, 5 FAILED** — the ablation |
| `api/b17-straight-time-floor.test.js` | 11 passed, 0 failed, 0 unproven |
| `api/b17-trust-lock-hard.test.js` | 14 passed, 0 failed, 0 unproven |
| `tools/alf_facility_role_gate_live_probe.py` | **exit 2 COULD NOT RUN** |
| `tools/open_work_shard.py --check` | CLEAN, 817 rows byte for byte |
| `tools/obligation_surface.py` | 15/12 → **14/11** |
| live `api/sd-data` ×3 | **401** — licence-gate evidence only |
| live `api/bridge` ×2 | **401** — pre-deploy, confirming item 3's premise |

**WHAT THIS DOES NOT COVER:**

* **No whole-tree suite run.** The suites above were chosen by what the diff
  touches; a regression elsewhere would not appear.
* **No live probe of the bridge refusal.** It is not deployed at the time of
  writing. Arms prove what the handler answers, not what the URL answers.
* **No rendered pass anywhere.** Nothing visual was looked at this batch.
* **The 522h review is against a mock** and against **current HEAD**, not the
  recorded sha, which does not resolve here.

---

## 6. TRANSCRIPT

    C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\c6aa6115-6c83-4e85-839e-9d1825f2115a.jsonl

---

## 7. THINGS I GOT WRONG IN THIS BATCH

1. **My ablation check matched prose about the code.**
   `!ablated.includes('UNKNOWN_ACTION')` failed on a *correct* ablation because
   `KNOWN_ACTIONS`' header comment says "the UNKNOWN_ACTION refusal below". It
   now asserts the code literal.
2. **I wrote the ablated copy to `os.tmpdir()`**, where `require('./_lib/license')`
   cannot resolve — a `MODULE_NOT_FOUND` that presents as an arm failure. The
   copy now lands in `api/`.
3. **I shipped the new suite UNTRACED while closing a row about an untraced
   suite.** Caught by re-running the generator instead of assuming the count
   moved. Fixed by renaming the file so a row could cite it.
4. **A commit message used backticks inside a double-quoted shell string**, so
   the shell ran `` `reconcile` `` as a command and the word vanished from the
   message. Repaired with `--amend -F`.
5. **My push loop assumed `git rebase` would succeed.** It refused on a dirty
   tree (the doc-reseat hook had rewritten generated docs), so five attempts
   reported a non-fast-forward that was really an unconsumed working tree. The
   loop now resolves conflicts with `tools/sairn_rebase_resolve.py` and
   `--continue` before retrying.
6. **My push loop ran `git add -A docs/` and staged a file with live conflict
   markers.** `docs/defect-density-register.json` went out with
   `<<<<<<<`/`>>>>>>>` in it, because `git add -A` during a conflicted rebase
   **cannot tell a resolved file from an unmerged one** — and the gate said
   exactly that back to me. Caught by the gate, not by me. Restored from HEAD
   and the record re-derived.
7. **The first defect-register record was pinned to a sha a rebase destroyed.**
   `62825f3d` no longer resolves, which is precisely the COULD-NOT-TELL state
   the 522h obligation discharged earlier in this same batch had been stuck in
   for 120 hours. Re-derived against the live sha **after** the final rebase and
   verified: exactly 1 record cites `1813a231d`, 0 cite the dead sha.
8. **Carried from b20 and still true:** a success test must not match the
   failure string. Landing is confirmed here by comparing `origin/main` to
   `HEAD` by sha after a fresh fetch, never by grepping for `main -> main`,
   which also appears in git's rejection line.
