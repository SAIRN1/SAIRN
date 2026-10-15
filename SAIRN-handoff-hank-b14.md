# Hank handoff — 2026-10-15, batch b14

**Written BEFORE the report, at a point where nothing is half-finished.** All
six dispatched items are done and pushed. The open list below is consequences
and decisions, not unfinished work.

---

## Push state — verified, not asserted

    git fetch origin
    git rev-parse --short HEAD        -> 359858ad
    git rev-parse --short origin/main -> 359858ad   (at the moment of this check)
    git rev-list --left-right --count HEAD...origin/main  -> 0  0

**NOT forced.** No `--force`, no `--force-with-lease`, no `--amend` after a
rebase. **No override form was used** — not `SAIRN_SEED_GATE=off` (refused
outright since 2026-10-13), not `SAIRN_GATE_EXEMPT=seed`, not `SAIRN_SKIP`.

**Three gate refusals, three satisfied, zero overridden:**

| refusal | what it wanted | what was done |
|---|---|---|
| register-feed | a defect record per commit | seven records, `scratchpad/reg_b14.py` |
| tier-a | an obligation for `leg_custodylog` | opened, assigned to `fourth` |
| derived-docs | MASTER-PLAN + traceability-matrix stale | regenerated, never hand-merged |

Two push attempts lost the ref race (`cannot lock ref`) rather than being
refused, with four other sessions pushing in the same window. The loop is
`scratchpad/pushloop.sh` and it **bails on any conflict outside the two
generated documents**.

**The b14 commits on `origin/main`:**

    652f4034  feat(sairnsenior): no self-approval on clock corrections, and a queue that shows the pending ones
    20e14747  docs(census sql): a RUN ORDER header, and the jsonb path re-confirmed from the writer
    cb80fb32  fix(sairncare): X1 the comment was WRONG not merely unproven, X2 the cited field is now on the finding
    8627f4e4  fix(blob): the ten routed conversions, 58 -> 48 exactly, and nine of ten column lists are EMPTY
    9020156b  fix(checks): the misspelt-role blind spot is closed, and the leg-session-gate red was a FALSE red
    26d959f2  docs(b14): the 40-suite sweep, all green
    90811d64  chore(defect register): seven records for b14
    0e5178b7  chore(tier-a,derived): the b14 review obligation and the regenerated documents

**`origin/main` has moved on since** (other sessions pushing) — that is normal
and is why the sha above is stamped with when it was read.

---

## Item by item

### 1. The pending-corrections queue, and no self-approval — DONE

**The decision, applied to BOTH routes.** `approveCorrection()` in
`api/_lib/sen-evv-clock.js` refuses `SELF_APPROVAL_REFUSED` when the approver
is the submitter — **in the module, not only in the handler**, because a rule
enforced in one branch of one endpoint is a rule the next caller does not get.
The handler maps it to **403** with its own code: a caller cannot act on a
refusal they cannot tell apart from "you are the wrong role".

**`propose_clock_correction` no longer auto-approves.** On that route the
submitter and the approver were the same person *by construction* — the filing
itself approved — so b13's approve-at-filing is exactly what the decision
forbids. The entry stays `pending` and its 200 now carries
`status: 'pending'` and a sentence naming the unchanged recorded time.

**`self_approved` is gone** from the entry and the response; a field that can
no longer be true is one a consumer still branches on. **`self_correction`
stays** — who *filed* is a different fact from who approved.

**The queue, which is the half b13 shipped without.** A scheduler-tier
**Clock Corrections** tab, the count **on the button**, both times on every
row, an Approve control **disabled with the reason on screen** when this user
submitted it, and a sentence rather than a blank panel when nothing is waiting.
`senData()` gained **`senLastErr` per resource** — it returned a bare `null` and
a `console.warn` on every failure, so the Approve button would have been a
silent no-op on its single most common refusal.

**`api/b14-clock-approval-two-person.test.js`: RED 13 failed / 5 passed → GREEN
18/0.** Twelve server arms against the real handler and the real module; six UI
arms against the real render functions extracted into a vm.

**AND THE DOM WAS DRIVEN IN A REAL BROWSER, against the DEPLOYED page** —
`docs/hank-evidence/b14/dom_real_browser.md`. Playwright, jsdom and html5lib
are all absent from this clone and installing one is not a change this batch
may make; the Chrome tooling reaches something better than a local harness. No
credentials: the real render functions were driven against injected fixture
rows. `button.disabled === true` read as **a property of a real element**, not
a regex over markup — the arm a vm cannot give honestly — plus the refusal
line read back out of the live DOM in the **server's own words**.

**T16aa in `api/t16-clock-correction-record.test.js` was rewritten, not
deleted**, to the new contract. 27/0.

### 2. The census SQL — DONE, and PART 0 was already right for a better reason

**PART 0 does not read `data->'stedi'->>'enc'` and that is correct.** It counts
the nested shape **generically** — every object-valued key carrying an `enc` —
and the writer is why: `api/sc-credentials.js:205` does
`next[service] = nextEntry`, and `stedi` is simply the only member of
`ALLOWED_SERVICES` (`:58`) today. **Confirmed from the writer, not from the
file's own comment.** Hardcoding the one service would under-report the moment
a second is added, and under-reporting here is what *authorises* clearing the
old key.

A **RUN ORDER header** was added saying what each part's answer means,
including the two STOP conditions a reader would otherwise take for a pass:
both-zero in part 0 means *"no credential exists"*, which is **not** the step-4
precondition, and a non-zero flat count means the census is **incomplete**.

**Uploaded and read back through the Drive API, not only through the sync
mount:** `SAIRN-census-sql.txt`, **13,261 bytes**, byte count matching local,
**Drive id `1cJ-Y68nBGd23IN08NbCcJfhhmCxVCsTO`**. **Michael runs it.**

### 3. cody's routed X1, X2, T16, T17, T18 — DONE

**X1 — the comment was WRONG, not merely unproven.** It claimed a person was
compliant the day before their hire anniversary and non-compliant on it.
Measured, the anniversary evaluation returns **`meets: null`** — the day-zero
withholding landed after that hand-drive and superseded it, and nobody re-read
the sentence the change had just made untrue. **It is the kind of claim a
reader checks least precisely because it names its own evidence.** Corrected
rather than deleted: the boundary it describes is real.

**X2 — a citation to a field that was not there.** `meets_unknown_reason` told
the reader a days-remaining field "says how much of it is left" and the finding
carried no such key; both numbers were computed and stayed on the internal
window object, while a third comment said the module hands "every consumer"
both. **`hours_window_days_elapsed` and `hours_window_days_remaining` are on
the staff finding now.** A citation to an absent field is worse than none: the
obvious conclusion when somebody cannot find it is that the response was
truncated.

**T16, T17, T18 all hold.** `python tests/run_b12_routed_findings_probe.py` →
**exit 0, NO FINDINGS, 8/8**. cody's window suite → **15/15**, was 13/15.

**TWO MORE COMMENTS WENT STALE THE DAY CODY'S ARMS LANDED, in the opposite
direction** — the leap-day note and the day-zero note both still said *no arm
drives this* and *routed to cody*. Both now cite the suite and what it
asserts, including that the leap-day case is driven in **both** directions
because either arm alone passes against the wrong rule. `N4b` in
`api/n1-n4-and-sf-delete.test.js` was rewritten for the same reason: it
*required* the module to keep confessing "no committed arm", which would have
pinned the comment to a sentence that had itself become false.

**A text check cannot tell a claim from a quotation of that claim** — X1 and
N4a both flagged my **fixes**, because the fixes quoted the superseded phrase to
explain it. Third and fourth instances after b13's N4. The corrections describe
the old wording without spelling it, and say so in the comment.

### 4. The ten blob conversions — DONE, 58 → 48 exactly

Done mechanically by `scratchpad/convert_blobs.py`, which **verifies every
target before changing anything** and refuses on the first mismatch — a partial
rewrite of a 2MB file is worse than none.

**Nine of the ten column lists came out EMPTY, and that is a finding about the
reads.** Where the read is `flat(data, {col})` the **column already wins**, so
stripping a payload copy removes a shadow nobody could read — that is site 2,
`business_profiles`, the one real key list (`['shop_id']`). Where the read
returns `x.data` **whole**, nothing re-adds a column and stripping a key
**deletes it from the client's view**. What all ten buy is the `NEVER_STORED`
strip, which is the defect the tool counts.

**Two sites were NOT stripped though their read is the shadowing shape.**
`SD_LINEAGE` and `SD_HR` read `Object.assign({id: x[idCol]}, x.data)`, so data
wins and a payload `id` shadows the column — exactly what `columnKeys` exists
for. Not stripped: the column is `String(payload.id)` while the blob keeps the
caller's type, so stripping silently changes **the type the client reads**, and
`stonedesk.html:39814` compares block ids with `===`. **Routed as a decision
with the measurement rather than changed on an argument about neatness.**

    UNCONVERTED 58 -> 48   exactly ten, so the drop is attributable
    CONVERTED   34 -> 45   ELEVEN -- and the extra one is the finding
    --repin run ONCE, after the conversions, never by hand

**`api/_lib/sd-store.js` `writeSlab` was not one of the ten because the
coverage tool files `data: slab` under BUILT** — *"already immune, a
field-by-field blob"* — which it is not. `slab` is the **raw caller argument**,
and the only thing distinguishing it from the counted sites is that the
identifier is not called `payload`. A raw site hiding in the immune bucket.
Converted here (`api/` is mine); **the tool is cc's and the misclassification is
routed, not edited.** The `id` duplication on that row **is deliberate** and now
says so: the read returns the blob whole.

**The `leg_aftercare` key agreement is PROVEN** by two arms that extract the
client copy and run it against the handler — `F4i` over eight pairs including
the colliding one, and `E4`. **The dispatch's cited lines have moved:** the
client half is `sairnlegacy.html:4256/:4269` and the server half
`api/sd-data.js:15869/:15875`, not 4214-4216 and 15610.

### 5. Methodology — DONE, both halves

**The misspelt-role blind spot is closed.** b13 left it open on the view that
closing it needed "a vocabulary nobody has written" of legitimate non-role
option values. **That framing was wrong:** the discriminator only needs to know
which values are **probable roles**, which the app's own vocabulary answers —
containment, or one edit.

**And b13's own sabotage FIXTURE was wrong as well as its check:**
`med_aide_II` is not a misspelling of any SAIRNsenior role (`med_aide` is
SAIRNcare's), so that plant could never have been caught by any
vocabulary-anchored rule. Re-sabotaged with `caregiver_II` and `office_II`:

    SABOTAGE 1  a misspelt role in a picker          -> exit 1, sairnsenior named
    SABOTAGE 1b the same, in an array role list      -> exit 1, sairnscape named
    SABOTAGE 2  a CHECK narrowed under a good picker -> exit 1, both named
    THE LIVE REPO                                    -> 17 clean, 0 refused, 0 unmeasurable

**The first draft manufactured two false positives** — edit distance 2 read
stonedesk's service-type dropdown offering `"other"` as a misspelling of
`"owner"`. The cause was not the distance but the **picker classifier**: "two or
more values in the vocabulary" was harmless while non-vocabulary values were
skipped, and stopped being harmless the moment one could fail. A picker must now
be **all roles or near-roles**, and the array path gained the same allowance —
without it, breaking one token made a list stop qualifying and **vanish** from
the comparison, so the breakage switched the detector off.

**The red suite is root-caused, and it was a FALSE RED.**
`api/sd-data-leg-session-gate.test.js` asserted every `leg_*` write returns 200
with a session, over a list containing `leg_custodylog`, which is
**append-only**: the handler answers `409 APPEND_ONLY`, refusing everyone
including the owner. Carried through b13 as a known red with "not mine" — true,
and not an answer. The replacement is **strictly stronger**: it asserts the
session gate was **passed** and then the append-only rule refused. 20/20.

**And a second false red, found while regressing item 4.**
`api/sd-data-memory-app-scope.test.js` asserted a line inside
`slice(at, at + 900)`; comments added to `sdData()` on 2026-10-14 pushed that
line to offset 1612, so it reported "sdData() now sends something else" about a
line that is byte-for-byte what it asserts. The window is the **function** now.

### 6. Push — DONE, `0 0`, three refusals satisfied

**40 suites driven, 40 green** (`docs/hank-evidence/b14/suite_run.log`). Both
app files syntax-checked per script block, zero errors.

---

## Live verification — PR §3.2, `verified=7 fail=0 couldnot=4`

    python docs/hank-evidence/b14_live_gate_probe.py   -> exit 0
    docs/hank-evidence/b14_live_gate_probe.out

Not bare `curl`: `tools/sairn_http.py`, which raises on a Vercel challenge
rather than handing back the challenge page. **A non-200 is UNVERIFIED and is
never folded into a pass.** Seven legs verified against the real deployed
pages — the queue's render functions, the disabled control's own text,
`vsApproveCorrection`, `senLastErr`, the tab, and b13's `legAdoptServerId`
re-checked rather than assumed still there.

**Four legs COULD NOT RUN and are counted, not only described** — both
`sen_visits` correction verbs, X1/X2's fields, and all ten blob conversions sit
behind `401 NO_LICENSE` or are write paths with no readable surface. b13's first
probe printed `couldnot=0` under a paragraph listing three unreachable legs;
that is fixed here by construction.

---

## Open, with the exact next step

1. **A ONE-PERSON AGENCY NOW HAS NO ROUTE TO CORRECT A CLOCK TIME AT ALL, AND
   THIS IS THE DECISION'S OWN CONSEQUENCE.** The owner is the assigned
   caregiver, the submitter, and the only possible approver. b13 chose
   flag-not-refusal for exactly this; the b14 decision overturned it, and
   applying it to both routes is the only consistent reading. **Next step:
   Michael decides whether that is accepted as-is, or whether a one-person
   licence gets a named exception** — and if it does, it must be a licence-level
   setting with an audit trail, not a fallback in the handler.

2. **THE QUEUE READS LOCAL ROWS.** `senPendingCorrections()` is built from
   `visits()`, which is server-merged by `senHydrateVisits()`. **A scheduler
   whose hydrate has not run sees an empty queue that is not empty** — and the
   empty state says "nothing is waiting", which would then be false. **Next
   step: either hydrate before rendering the tab, or make the empty state say
   when the data was last fetched. I would do the second.**

3. **`approve_clock_correction` HAS NEVER RUN AGAINST THE LIVE DATABASE.** The
   server half is proven against the real handler (18 arms) and the DOM against
   the deployed page, and neither is a production round trip. **Next step: one
   real approval on a real visit by a scheduler who is not the submitter.**

4. **THE TIER A OBLIGATION IS OPEN AND ASSIGNED TO `fourth`** —
   `leg_custodylog` and `sen_visits`. The three questions that matter, all of
   them things an author cannot answer about their own work: whether **409** is
   the status the handler *promises* rather than the one it happens to return;
   whether the replacement arm is strictly stronger **as written** rather than
   as described; and whether a **second** append-only resource belongs in the
   one-entry exception list I derived from a single measured failure. **Next
   step: `fourth` discharges.**

5. **SD_LINEAGE AND SD_HR STILL LET A PAYLOAD `id` SHADOW THE COLUMN.** Not
   stripped, because stripping changes the type the client reads and a `===`
   comparison on block ids exists at `stonedesk.html:39814`. **Next step: a
   decision — either the column write stops stringifying, or the read stops
   re-adding `id`, or the client stops comparing with `===`. Three one-line
   fixes, and only one of them is right; I did not pick.**

6. **THE COVERAGE TOOL'S `BUILT` BUCKET HIDES RAW SITES BEHIND AN IDENTIFIER
   NAME.** `data: slab` was filed as "already immune". Any other site whose
   payload variable is not called `payload` is still in that bucket and still
   uncounted, and **nothing here enumerates them** — that needs the classifier
   changed. **Next step: cc, who owns `tools/`.**

7. **THE CENSUS IS STILL UNRUN** and it is the only item on Michael's SQL list
   that has not been run. `SAIRN-census-sql.txt` on Drive, id
   `1cJ-Y68nBGd23IN08NbCcJfhhmCxVCsTO`. **Next step: Michael runs it and reads
   PART 0's grid first.** The run-order and MAR-grant files are confirmed run
   and are off the list.

8. **TWO LIMITS REMAIN ON THE ROLE-PICKER CHECK AND ARE PRINTED EVERY RUN:** a
   misspelt role in a **two-token** list is not caught (breaking one leaves
   fewer than two real roles and the list stops being distinguishable from any
   other pair of strings — a 3+ token list **is** caught), and a picker carrying
   a non-empty non-role placeholder is **disqualified**, so its app reports
   UNPROVEN rather than clean. **Next step: neither is worth closing until
   something real hits them; they are visible, not silent.**

9. **NOTHING SWEEPS COMMITTED SUITES FOR THE TWO FALSE-RED SHAPES** found this
   batch — a fixed-width source window, and a generic loop over a list with a
   known exception. Both were found by **running the suites and reading the
   output**, which is not a control. **Next step: a check that flags
   `slice(x, x + N)` over source in any `*.test.js`. Cheap, and it is the one of
   the two that is mechanical.**

10. **SEVEN `api/` SUITES ARE OWED GATE-DRIVER WIRING** — b12's three, b13's
    three, and `api/b14-clock-approval-two-person.test.js`. Nothing under
    `tools/` references any of them. **`tools/` is cc's. Next step: cc adds all
    seven** — and the role-picker one exits **3 by design** on an unmeasurable
    app, so whatever drives it must treat 3 as could-not-run.

11. **FMEA DRAFTS ARE OWED** for `api/_lib/sd-store.js`,
    `api/sd-data-memory-app-scope.test.js`, `api/sd-data-leg-session-gate.test.js`
    and `api/b14-clock-approval-two-person.test.js` — the register's own loop
    said `NO DRAFT` for each. `tools/fmea_draft.py` is **cc's**.

12. **NO ARM PROVES A SHARED CREDENTIAL CANNOT DEFEAT THE TWO-PERSON RULE.**
    The identity compared is the session's `employee_id`, so two people sharing
    one login are one person to this check and nothing detects that. **Next
    step: not closable in this mechanism — it belongs with credential hygiene,
    and it is named so nobody reads the rule as stronger than it is.**

---

## Register

**Seven records**, `docs/defect-density-register.json`, each with four
contributing factors and an explicit `recurrence-open`:

| commit | app | severity | what |
|---|---|---|---|
| 652f4034 | sairnsenior | high | **b13's approval route shipped with no UI** — 27 arms green on a mechanism no user could reach |
| 652f4034 | sairnsenior | moderate | b13 allowed self-approval by flag; the decision refuses it |
| cb80fb32 | sairncare | moderate | X1, a comment that was **wrong**, not unproven |
| cb80fb32 | sairncare | low | X2, a message citing a field the finding did not carry |
| 8627f4e4 | tooling | moderate | the coverage tool's `BUILT` bucket hiding a raw site |
| 9020156b | tooling | high | the role-picker check's misspelt-role blind spot, and its **fixture** |
| 9020156b | stonedesk | moderate | two false reds and one false green in committed suites |

One record was refused first time — `action_status: 'planned'` with a `note`
instead of an `action` — and re-fed with the action named. The feed script is
`scratchpad/reg_b14.py`; `--rule` takes a **`docs/SAIRN-PROCESS-RULES.md`
section id**, not prose.

---

## Claims held

**`hank`**, taken as the **first action** of this batch and **still held** —
release it when the uploads are verified:

    python tools/sairn_claim.py release hank

**Conflicts respected:**

* **`tests/` is cody's.** The dispatch named **two** of their files by name and
  those are the only ones touched: `tests/run_b12_routed_findings_probe.py` was
  **run, never edited**, and `tests/sairncare_compliance_window_boundary.test.js`
  was **run, never edited** — both X1 and X2 were fixed in `api/`, which is
  where the defects were. **Nothing else under `tests/` was touched.**
* **`tools/` is cc's.** `blob_conversion_coverage.py` was **run** (including
  `--repin`, which the routing doc assigns to me) and **not edited**. Two items
  routed to cc.
* **`docs/` specs are fourth's** —
  `docs/2026-10-14-cody-b14-blob-conversion-routed-to-hank.md` was read, not
  edited.
* **No auditor clone was entered.**

Files written outside `api/`, `sql/` and the app HTML: the `docs/` files **the
push gate itself requires** (`defect-density-register.json`, `MASTER-PLAN.md`,
`traceability-matrix.md`, `tier-a-reviews.json`, plus `scrutiny-flags.json`
which the gate writes), `docs/blob-conversion-coverage.json` (written by
`--repin`), and my own `docs/hank-evidence/b14/`.

---

## Stashes — checked, not assumed

    git stash list
    stash@{0}  On main: b10-settings-park
    stash@{1}  On main: my 3 register records, re-addable from scratchpad/reg_add.py

**Neither was popped, dropped or inspected beyond `git stash list`.** No `git
stash` command of any kind was run in this batch. `.claude/settings.json` was
**never committed**; `.claude/settings.json.bak` and
`.claude/settings.json.hooks.bak` remain untracked and were left alone. **No
hook was restored or added.**

---

## Transcript

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\9ab77c34-c203-458f-9e45-7f384a672a77\

Scratch artefacts there, not committed. **The three worth keeping:**
`scratchpad/convert_blobs.py` (the blob converter — verify-all-then-apply, with
the derived column list and its reason per site), `scratchpad/reg_b14.py` (the
seven-record register feed) and `scratchpad/pushloop.sh`.

**The detached worktree the REDs and all three sabotages were captured in is
REMOVED, not left for somebody else:** `wt-b14base` deleted with
`git worktree remove --force`; `git worktree list` shows **none** under the
scratchpad.

**The Chrome tab opened for the real-DOM check was closed** —
`tabs_close_mcp`, group auto-removed. Nothing was left open in the browser.
