# Hank handoff — 2026-10-15, batch b13

**Written BEFORE the report, at a point where nothing is half-finished.** Every
dispatched item is done and pushed; the open list below is consequences and
decisions, not unfinished work.

---

## Push state — verified, not asserted

    git fetch origin
    git rev-parse --short HEAD        -> 58e67efa
    git rev-parse --short origin/main -> 58e67efa
    git rev-list --left-right --count HEAD...origin/main  -> 0  0

**NOT forced.** No `--force`, no `--force-with-lease`, no `--amend` after a
rebase. **Neither override form was used** — not `SAIRN_SEED_GATE=off` (which
is refused outright since 2026-10-13), not `SAIRN_GATE_EXEMPT=seed`, not
`SAIRN_SKIP`. **Three gate refusals, three satisfied, zero overridden:**

| refusal | what it wanted | what was done |
|---|---|---|
| register-feed | a defect record per commit | six records fed, `scratchpad/reg_b13.py` |
| derived-docs | MASTER-PLAN and traceability-matrix stale | regenerated, never hand-merged |
| tier-a | an independent-review obligation | opened, three resources, assigned to `fourth` |

**Six merges, every one `pull --no-rebase`**, so no register record's sha moved.
Four of them were lost ref races rather than refusals (`cannot lock ref`), with
five sessions pushing in the same window; the retry loop is
`scratchpad/pushloop.sh` and it **bails on any conflict outside the two
generated documents** rather than resolving one by guess.

**The b13 commits on `origin/main`:**

    07dfa24f  fix(sairnsenior,sairncare): T16 clock corrections are appended and approved, T18 position tokens validated
    f92fe10a  fix(sairnlegacy): F4 the leg_aftercare key is delimiter-safe, F5 the device adopts the server's id
    00f846de  fix(role-picker check): the 11 UNPROVEN apps resolved -- 9 were this check's fault, not the apps'
    0fdbaa19  chore(defect register): six records for b13
    6366bf65  docs(b13): the 26-suite run log, with the one pre-existing red named
    223fec4a  chore(tier-a): the b13 independent-review obligation

---

## Item by item

### 1. T18 and N3 — DONE, and a false-green arm was caught by reading output

`api/_lib/compliance-rules.js`. `mappable` accepted **any** non-empty
`applies_to_positions` array for being non-empty, while the leg **in the same
expression** validated `audience` against `STAFF_POSITIONS`. So a requirement
declaring `['rn']` was counted MAPPED, left out of
`unmapped_requirements_caveat`, and `matchAudience` then returned a **decided
`applies: false`** for every real position — a training requirement that applies
to nobody, reported to a surveyor as a determination about a person.

Now the list's **contents** are checked:

* **all tokens unreadable → UNDECIDED**, answered before the per-person branch
  because it is a property of the ROW and the same for everybody, with the
  unreadable token and the vocabulary both named in the reason.
* **partially valid → `true` stays true** for a person a real token names (an
  unreadable token can only widen an audience), and a **false is WITHHELD**
  while any token is unread — `'rn'` is most plausibly `'nursing'`, and a
  confident false would exclude exactly the person the typo was aimed at.
* **`positions_unknown` on the normalised row**, absent when every token is
  real. **Recorded, not repaired**, for the same reason the malformed-shape case
  is: choosing `nursing` would be this code deciding who a regulated
  requirement covers.

`api/t18-positions-vocabulary.test.js`, **17 arms, 6 of them controls that must
be green in both directions**. RED **9 failed / 8 passed** at HEAD in a detached
worktree, GREEN **17/0** — both with the FINAL arms, because two of the first
draft's arms were themselves wrong.

**Two arms were measuring the fixture and both were found by reading the output,
not the exit code.** (a) `unmapped_requirements` is computed inside
`if (Array.isArray(opts.staff))` at `:825`, so an arm that omitted `opts.staff`
failed against the FIXED code and reported the fix as absent. (b) `applicable`
filters on `s.applies_to` and **not** on `matchAudience` — the audience decision
is made by the CALLER and handed in — so an arm that omitted `applies_to` was
measuring a path production never takes. **Arm T18q now re-references that
mirror against `api/sd-data.js` itself** and fails if the endpoint stops
building `applies_to` from `.applies === true`.

### 2. T16 — DONE as decided, and T17 was already closed

**T16, Michael's decision, replacing b12's own N1 refusal.** The 409
`CLOCK_ALREADY_RECORDED` closed the silent overwrite and left a hole beside it:
`propose_clock_correction` is **scheduler-only**, so a caregiver who clocked in
at the wrong time on their own visit had **no route at all**.

Now, in `api/sd-data.js`'s caregiver write branch:

* the original **stays on the row** — the submitted field is taken out of the
  copy loop rather than put back by a later line, because "relying on a later
  line to restore it" is one forgetful edit from the defect;
* the submission is **appended** to the same `clock_corrections` trail the
  scheduler route writes to, carrying the old value, the new value, the actor
  **from the verified session**, a reason and a server timestamp;
* it is **`pending`**, and `effectiveClock()` — the function every reader and
  every payroll calculation goes through — **ignores a pending entry**. That is
  where "a scheduler approves it before payroll uses it" is implemented; a
  `pending` nothing consults is a decoration;
* the 200 **says so**, naming the unchanged recorded time and who must approve:
  a 200 that looks like an accepted clock change is affirmative false success,
  which is worse than the refusal it replaced;
* **`approve_clock_correction`**, scheduler-tier only, **declared in
  `api/_resources/sairnsenior.js` in the same edit** — an
  implemented-and-undeclared verb is unreachable and its 400 reads like a client
  bug, which is how `tombstones` shipped dead;
* an entry with **no `status` at all is APPROVED**, because every correction
  written before today was effective the moment a scheduler filed it, and
  reading a missing status as pending would **silently revert every live
  corrected visit** — this change causing the defect it fixes;
* a submitted field's **stamps and flags follow the value they describe onto the
  entry**. Merging them onto the row would have overwritten the original clock
  event's observation with one describing a time the row does not hold, and
  would have dropped the original's `LATE_REPLAY` as "superseded" when nothing
  about it was.

`api/t16-clock-correction-record.test.js`, **27 arms**. RED **18 failed / 8
passed**, GREEN **27/0**. **One control was a FALSE GREEN in the RED run** —
T16t (a bad index refused 400) passed only because the action did not exist yet;
it is a real arm now.

**The scheduler route was nearly made a silent no-op by this change** and the
arm that catches it is T16aa: `proposeCorrection` now defaults to `pending`, so
`propose_clock_correction` — which was already scheduler-tier only, i.e. the
approving authority IS the caller — would have filed corrections that never
became effective. It approves at filing time, and T16aa fails if a later edit
removes that.

**N1b and N1e in `api/n1-n4-and-sf-delete.test.js` were REWRITTEN, not deleted**,
to the new contract, so the boundary stays covered in both suites. 21/21.

**T17 was already closed by b12's N2** and `api/sen-auth.js:263` carries the
`soleRoleDemotionRefusal()` call. **Necessity measured rather than assumed:**
ablating the guard in a detached worktree turns **N2a red and leaves all three
controls green** (`docs/hank-evidence/b13/t17_ABLATION.log`). 1 of 4 is the
correct number — the other three are controls that assert the non-refusal cases.
**No new code.**

### 3. N4 — DONE, and the first draft of the fix was flagged by the sweep

`api/sd-data-cross-tenant-dispatchers.test.js` claimed its SAIRNgrounds
session-gate coverage was held by an `api/` path with hyphens and a `.test.js`
suffix that **has never existed**. The real suite is `tests/sd_data_grd_session_gate.js`.
The comment now names it and says what it asserts.

**The first draft QUOTED the dead path to explain it and cody's sweep flagged
the FIX** — a sentence saying "X does not exist" is indistinguishable, to a text
sweep, from a claim that X holds something. The population went 330 → 332 and
the finding stayed. **The correction now describes the dead citation without
spelling it, and says why.**

`python tests/run_b12_routed_findings_probe.py` → **exit 0, NO FINDINGS, 8 of 8
arms hold** (was exit 1, 5 holding / 3 findings).

### 4. F4 and F5 — DONE, F4 first

**F4.** The `leg_aftercare` key was `'AC-'+case_id+'-'+NORMALISED_TYPE`, and `-`
is **both** the joiner and the type normaliser's output character while
`case_id` went through with `trim()` alone — so the field boundary was not
recoverable and `('CS-7','1 Week')` collided with `('CS-7-1','Week')`. The
upsert is `merge-duplicates`: a collision **silently overwrote a different
case's grief-support check-in and returned 200**.

**Two forms, so existing ids survive byte for byte.** Every row the shipped app
has written has a `newId('CS')` case id (`^CS-[0-9]+-[0-9]+$`,
`sairnlegacy.html:1561`) with one of three fixed types, and for **that** shape
the boundary IS recoverable — strip a known type suffix, the rest is the case,
and the last case segment cannot contain a `-`. Those pairs keep the historic
key. Anything else takes `ACX-` + an escaped form in which no segment contains a
bare `-` at all. **A scheme that moved the historic keys would orphan every live
aftercare row:** the next write lands on a new row and the old one is stranded,
which is the duplicate the key exists to prevent.

**NOT hashed.** A hash is shorter and uniform, and a hash collision **silently
merges two records** — this defect with a smaller probability attached. The
escape is reversible, so it cannot collide at all.

**The guard is on the TRIMMED values on both sides now.** `case_id = ' '` passed
the old raw-truthiness guard and trimmed to `''`, producing a key that collides
with every other whitespace case id — the exact failure the code's own comment
warns about for a MISSING field, arriving through a present one.

**`case_id` is deliberately NOT case-folded and F4h asserts that as a decision.**
Folding only here would make the key say two cases are one while
`a.case_id===caseId` everywhere else in the page says they are two.

**F5.** `sdnData()` marked the **client's** id as synced and discarded the
server's rewritten one, so an un-upgraded device kept the random id, the next
hydrate pulled the canonical row, failed to match it and **pushed it back as a
second local row** — one check-in, two grief-support follow-ups to a bereaved
family, on exactly the "old page" device the canonicalisation comment invokes.
Now the local row **adopts** the server's id (`legAdoptServerId`, which also
**merges** onto an existing canonical row instead of keeping two) and **that** id
is what gets marked synced.

**The fix introduced a silent no-op of its own and it was closed in the same
edit.** The rows were rendered BEFORE the rename, so every Complete button would
have carried a dead id and `confirmAftercareComplete`'s `if(!a)return;` would
have done nothing with no message. Both aftercare callers re-render after the
write.

`api/leg-aftercare-key-unambiguous.test.js`, **14 arms**. RED **7 failed / 1
unproven / 6 passed** at HEAD, GREEN **14/0**. The client half is **extracted
from the HTML and run in a vm**, not reimplemented. **F4i found a divergence
nobody had asked about:** on an empty `checkin_type` the server kept the
caller's id and the page derived a key from nothing. Both now decline, and
`legAftercareId()` returns `null` with the caller falling back to `newId('AC')`.

**`api/sd-data-leg-role-matrix.test.js` E1/E3/E4 updated.** They pinned
`AC-CS-7-1-WEEK` — a key **no production row has**, because `'CS-7'` is not a
shape the generator can emit. Pinned to a real generated id now, which is what
makes them evidence that live ids did not move. 32/32.

### 5. The 11 UNPROVEN apps — DONE, 0 remain, and the check was sabotaged

Full account with the command per app:
**`docs/2026-10-15-hank-b13-unproven-apps-resolved.md`**.

**Nine of the eleven were defects in the check, not facts about the apps.**

* **Four** (`stonedesk`, `sairnbiz`, `sairngrounds`, `sairnscape`) — it built
  the table name as `app + '_employee_auth'`. `api/_lib/auth.js:1094` says in
  its own words there is no such rule: `sd`, `sb`, `grd`, `scp` use a prefix.
  It searched `sql/` for four names that do not exist. **All four tables DO
  carry a role CHECK.** The name now comes from the exported
  `AUTH_TABLE_BY_APP`, the same map the live session gate reads.
* **Five** (`sairnbiz`, `sairngrounds`, `sairnscape`, `sairnvet`,
  `sairnfreedom`) — it scanned static `<option>` markup, and SAIRNfreedom's
  picker is an empty `<select>` filled at runtime from `CAPABILITIES`. A
  **second, structurally different method** (array literals, not a wider regex
  over the same text) closes it, strict in the safe direction: **ALL** quoted
  tokens must be roles.
* **Four** (`sairncode`, `sairndental`, `sairnmechanical`, `sairnroofing`) — they
  do not assign roles from their own pages at all (`grep -c "'setup'"` → 0 each;
  SAIRNmechanical says so in its UI text). **NOT APPLICABLE**, not unmeasurable.
* **`stonedesk_sub`** — deliberately absent from `AUTH_TABLE_BY_APP` because
  subcontractors use `sd_sub_auth` keyed on `sub_id`. **NOT APPLICABLE**, and if
  an app that SHOULD have credentials ever lands on that line, **the missing map
  entry is itself the finding**.

Final: **17 clean, 0 with a refused role, 0 could not be measured, exit 0** — 12
compared against a CHECK (7 with a static picker, **5 ARRAY-ONLY and labelled as
the weaker claim**), 5 NOT APPLICABLE.

**SABOTAGED, AND THE FIRST SABOTAGE WAS MISSED.** A **misspelt** role planted
into a picker (`med_aide_II`) is invisible — the comparison skips values not in
`ROLES_BY_APP`, because a picker legitimately carries `''` and non-role options.
**Exit 0, missed.** That is now a **printed limit on every run**, not fixed. The
second sabotage — a CHECK narrowed while the picker still offers the role — is
caught by **both methods independently**: exit 1, `sairnsenior` through the
static picker, `sairnscape` through the array literal.

### 6. Push — DONE, `0 0`, three refusals satisfied and six merges

See the table above. **Nothing was overridden.**

---

## Live verification — PR §3.2, `verified=5 fail=0 couldnot=3`

    python docs/hank-evidence/b13_live_gate_probe.py     -> exit 0
    docs/hank-evidence/b13_live_gate_probe.out

Not bare `curl`: `tools/sairn_http.py`, which raises on a Vercel challenge
rather than handing back the challenge page. **A non-200 is recorded as
UNVERIFIED and is never folded into a pass.**

**Five legs verified against the real deployed `sairnlegacy.html`** —
`legAcEsc`, the `ACX-` form, the `^CS-[0-9]+-[0-9]+$` legacy guard,
`legAdoptServerId`, and `legMarkSynced(resource,srvId)`. That is a real check
that the client halves of F4 and F5 shipped, by the same route a browser takes.

**Three legs COULD NOT RUN and are counted, not only described.** The first run
printed `couldnot=0` directly under a paragraph listing three unreachable legs,
because they lived in prose and never entered the counter — **a number beside
prose that contradicts it is the number people quote.** Fixed. The three:
`approve_clock_correction`, the `leg_aftercare` key derivation and T18's
validation all sit behind `401 NO_LICENSE`, which is answered before the action
dispatcher. A licence key would be a real credential in a script and was not
used. Each is driven against the **real handler** locally instead.

---

## Open, with the exact next step

1. **T16's APPROVAL ROUTE HAS NO UI AND NO QUEUE.** `approve_clock_correction`
   is API-only. A caregiver's submission is therefore **invisible to a scheduler
   who does not go looking**, and `effectiveClock()` returns
   `pending`/`pending_count`/`pending_entries` that nothing renders. **Next step:
   a pending-corrections list in `sairnsenior.html` with an Approve control, and
   a count badge. Until it exists the append path is strictly better than the
   409 for the caregiver and no better for payroll, because nobody approves.**

2. **THE APPROVER MAY BE THE SUBMITTER, MARKED AND NOT REFUSED.** In a
   one-person agency the owner IS the assigned caregiver, and refusing would
   strand the only person who can act — the same trade `self_correction` already
   made. `self_approved: true` goes on the entry and `has_self_correction` on
   the row. **Nothing counts or reports those. Next step: `fourth` or Michael
   decides whether a marked self-approval is acceptable on a federal EVV record;
   it is in the Tier A obligation as a named question.**

3. **THE TIER A OBLIGATION IS OPEN AND ASSIGNED TO `fourth`** — `alf_staff`,
   `leg_aftercare`, `leg_cases`, `sen_visits`, each with its own REVIEW HARDEST
   list rather than one generic ask. The three that matter most: whether any
   consumer reads `clock_in_at`/`clock_corrections` directly and would see an
   unapproved time as recorded (**the `payroll` action on `sen_visits` is the
   first place to look**); whether treating a missing `status` as approved is
   right against the real rows rather than against my argument for it; and
   whether NO row any shipped build could have written changes aftercare key —
   **F4d is my evidence and it tests the shapes I believe exist**, which is the
   part an author cannot check on themselves. **Next step: `fourth` discharges.**

4. **A MISSPELT ROLE IN A PICKER IS STILL INVISIBLE.** Measured by sabotage, not
   reasoned about. Closing it means deciding which non-role option values are
   legitimate per app — a vocabulary nobody has written. **Next step: whoever
   owns that decision writes the per-app allowed-non-role list, or it stays a
   printed limit. It is NOT closed.**

5. **FIVE APPS' CLEAN VERDICT IS ARRAY-ONLY** (`sairnbiz`, `sairngrounds`,
   `sairnscape`, `sairnvet`, `sairnfreedom`). What is proven is *"no declared
   role list in this page carries a refused role"*, which is **broader and
   weaker** than *"the provisioning picker was checked"*. **Next step: for each,
   confirm by hand that the matched literal really is the picker's source — the
   run prints its line number.**

6. **cody's b14 CLAIM INCLUDES `tests/run_b14_leg_aftercare_probe.py`**, which
   is fourth's routed F4 collision arm. **My fix has landed and my own arms
   cover it** (`api/leg-aftercare-key-unambiguous.test.js` F4a drives the exact
   pair). Their arm should now go GREEN with no edit. **Next step: tell cody the
   fix is in, so they write the arm as a regression guard rather than as an open
   finding — and do not build a second copy of the derivation.**

7. **THE THREE SQL RUNS FROM b12 ARE STILL UNRUN.** Unchanged by this batch and
   still Michael's, in this order: (1) `sql/legacy_ciphertext_census.sql`, **PART
   0 FIRST** — both-zero means "no credential exists", which is NOT the step-4
   precondition; (2) `sql/2026-10-14-hank-b11-mar-grant.sql` blocks 1 and 2,
   block 2 pasted WHOLE because between its DROP and its ADD the audit table
   accepts any `event_type`; (3) b10 run-order block 5, which is **reachable from
   the SAIRNcare UI** — `sairncare.html:1018` offers `office_manager`, the server
   mints it and the database refuses 23514.

8. **`sql/2026-10-14-michael-run-order.sql` IS THE LAG THE ROLE-PICKER CHECK
   CANNOT SEE.** It widens `sairncare`'s and `sairnlegacy`'s role CHECKs by
   ALTER, so the repo's intention and production disagree until it runs. **Next
   step: Michael runs it, or answers the one query the check prints:**
   `select pg_get_constraintdef(oid) from pg_constraint where conname = '<app>_employee_auth_role_check';`

9. **`api/sd-data-leg-session-gate.test.js` IS RED AND IT IS NOT MINE.**
   `leg_custodylog write with a session -> 200`, 19 passed / 1 failed. **Verified
   identical at the pre-b13 HEAD in a detached worktree**, so it is pre-existing.
   **Next step: whoever owns `leg_custodylog`'s write gate.** Recorded in
   `docs/hank-evidence/b13/suite_run.log`.

10. **NOTHING UNDER `tools/` INVOKES THE THREE NEW SUITES.**
    `api/t18-positions-vocabulary.test.js`,
    `api/t16-clock-correction-record.test.js` and
    `api/leg-aftercare-key-unambiguous.test.js` are referenced by no file under
    `tools/`, which is **cc's**. **Next step: cc adds all three to the gate
    driver.** Note that b12's three are still owed the same wiring.

11. **FMEA DRAFTS ARE OWED** for `api/leg-aftercare-key-unambiguous.test.js`,
    `api/t16-clock-correction-record.test.js`,
    `api/t18-positions-vocabulary.test.js` and
    `api/role-picker-vs-check-constraint.test.js` — the register's own loop said
    `NO DRAFT` for each. `tools/fmea_draft.py` is **cc's**. **Next step:
    `python tools/fmea_draft.py <file> --save` by whoever owns `tools/`.**

12. **13 TIER A OBLIGATIONS ARE PAST THE 24h DEADLINE** platform-wide (printed
    by `python tools/tier_a_review_gate.py --list`), now 14 with mine. **Next
    step: not mine to discharge — but `--auto-discharge` closes the ones a
    defect-register record already covers, and nobody has run it.**

---

## Register

**Six records**, `docs/defect-density-register.json`, each with four
contributing factors and an explicit `recurrence-open`:

| commit | app | severity | what |
|---|---|---|---|
| 07dfa24f | sairnsenior | high | **b12's own remedy**: the 409 removed the only route the person who made the mistake had. Injection `31406a87`. |
| 07dfa24f | sairncare | moderate | T18, the unvalidated `applies_to_positions` leg |
| 07dfa24f | stonedesk | low | the coverage claim naming a file that has never existed |
| f92fe10a | sairnlegacy | high | F4, the delimiter-ambiguous key |
| f92fe10a | sairnlegacy | moderate | F5, the local duplicate the canonicalisation left |
| 00f846de | tooling | high | the role-picker check's own nine-of-eleven blind spot |

The feed script is `scratchpad/reg_b13.py` (in the transcript directory, not
committed). `--rule` takes a **`docs/SAIRN-PROCESS-RULES.md` section id**, not
prose, and `--phase` is one of `requirement|design|coding|config|unknown` —
both discovered by reading the tool's refusals.

---

## Claims held

**`hank`**, taken as the FIRST action of this batch and **still held** —
release it when the report and the uploads are done:

    python tools/sairn_claim.py release hank

b12 ran with **no claim at all** and said so; this one did not repeat that.

**Conflicts respected:**

* **`tests/` is cody's** — `tests/run_b12_routed_findings_probe.py` was **RUN,
  never edited**, including after the fix went in. `tests/sd_data_grd_session_gate.js`
  was read to confirm what it asserts before citing it.
* **`tools/` is cc's** — no file under it was edited. Four routed items (10, 11
  above).
* **`docs/` specs are fourth's** — `docs/2026-10-14-fourth-b20-leg-role-matrix-discharge.md`
  was read and not edited.
* **No auditor clone was entered.**

Files written outside `api/`, `sql/` and the app HTML: the four `docs/` files
**the push gate itself requires** (`defect-density-register.json`,
`MASTER-PLAN.md`, `traceability-matrix.md`, `tier-a-reviews.json`, plus
`scrutiny-flags.json` which the gate writes), my own
`docs/2026-10-15-hank-b13-unproven-apps-resolved.md`, `docs/hank-evidence/b13/`
and `docs/hank-evidence/b13_live_gate_probe.py`.

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

Scratch artefacts there, not committed. **The two worth keeping are
`scratchpad/reg_b13.py`** (the six-record register feed, re-runnable) **and
`scratchpad/pushloop.sh`** — the pull/push retry loop, which auto-resolves ONLY
the two generated documents by **re-deriving** them and **bails on any other
conflict** so a human decides it. It also distinguishes a lost ref race from a
gate refusal, and its first version did not: it matched `FAIL:` anywhere in the
output and read a gate's own explanatory prose as a refusal.

**The detached worktree the REDs and the ablation were captured in is REMOVED,
not left for somebody else:** `wt-b13head` deleted with
`git worktree remove --force`; `git worktree list` shows none under the
scratchpad.
