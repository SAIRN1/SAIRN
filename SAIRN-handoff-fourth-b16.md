# HANDOFF — fourth / ted, batch b16, 2026-10-14

**Written BEFORE the report**, at a point where nothing is half-finished: items
1–6 are committed and pushed in one commit, `HEAD == origin/main`, the working
tree is clean, no rebase or stash in progress.

**EVERY FIGURE NAMES THE COMMAND THAT PRODUCED IT.** Two figures I was handed
turned out wrong in my favour and are corrected in §3.2; one citation in my own
b15 work turned out wrong and is corrected in §3.4.

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\240036a6-0d02-441d-a22d-73ed022c11a3\scratchpad\`
New this batch: `cite_recheck_b16.py`.
Logs: `row44_read.log`, `row50_read.log`, `row44_drive.log`, `row50_drive.log`,
`removal_live_b16.log`, `item3_measure.log`, `register_readers.log`,
`cite_recheck_b16.log`, `context_measure_b16.log`, `settings_check_b16.log`,
`manifest_set_b16.log`, `push_b16.log`, `landed_b16.log`.

---

## 0. COMMITTED / PUSHED STATE

| | | command |
|---|---|---|
| HEAD | `3a76b690` | `git -C <repo> rev-parse HEAD` |
| `origin/main` | `3a76b690` | `git -C <repo> rev-parse origin/main` |
| behind / ahead | **0 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| working tree | clean | `git status --porcelain` (empty) |
| the b16 work commit | `3a76b690`, 6 files | `git log origin/main --oneline -1` |
| push forced? | **NO** | one rebase, then `1c4e1466..3a76b690` |
| `SAIRN_SEED_GATE=off` | **not used**, any form | — |
| `.claude/settings.json` | **not edited, not committed by me** | `git show --stat 3a76b690` and the claim commit both contain 0 settings.json lines |
| **hooks** | **0 groups, 0 entries — changed since b15, and NOT by me** | §5 |
| files written outside `docs/` | **0** (plus my three root deliverables) | by instruction |
| b16 manifest | 6 of 6 `done`, close pending the deliverables | `batch_manifest.py --check` |

**`3a76b690` IS THE STATE AT FINALISATION OF THIS HANDOFF** — the report, the
digest, the b16 close and the claim release all land after it. **Re-derive HEAD
rather than quoting this table.**

---

## 1. ITEM BY ITEM

| # | item | state | exact next step |
|---|---|---|---|
| 1 | manifest written first, closed with the env var | **DONE** | **cc fixes `tools/batch_manifest.py:386`** so the env var stops being needed |
| 2 | the row 44 and row 50 probes | **DONE — and both were already locked; driving them found two real holes** | **cody adds 2 arms to the SAIRNcash suite; hank answers 4 removal paths** (§3.1) |
| 3 | one routing note to cc | **DONE — with two of its four numbers corrected** | **cc: four decisions, none urgent** (§3.2) |
| 4 | the ten `[CONFIRM]` questions | **DONE — one page, plain English** | **counsel 3; a funeral director 5; a vet practice 2** (§3.3) |
| 5 | re-derive every b15 `file:line` at HEAD | **DONE — 45 checked, 1 wrong, fixed visibly** | **cc adds `--read-the-line`** to `tools/citation_line_drift_check.py` (§3.4) |
| 6 | push without force | **DONE — `1c4e1466..3a76b690`, 0/0** | nothing |
| — | this handoff, before the report | **DONE** | — |

---

## 2. CLAIMS, LOCKS AND HOLDS

| hold | count | detail | command |
|---|---:|---|---|
| repo claims held | **1** | b16, published on `origin/main`; release after the report and digest are up | `sairn_claim.py list` |
| session locks held | **1** | `fourth.lock`, 26.8h, still carrying the dead `claude_pid 53204` — **five batches now** | `ls ~/SAIRN-SESSION-LOCKS/*.lock` |
| locks over 160h | **8 of 14** | was 7 in b14; `sairn_idem_uw3ebld2.lock` crossed the line since | §3.2 |
| locks removed by me | **0** | `rm` is denied and I did **not** route around it | — |
| worktrees besides main | **4** | **none mine**; `.claude/worktrees/` appeared empty during a probe run and the probe's own arm confirms it left nothing newly dirty | `git worktree list` |
| `git stash` | **0** | | `git stash list` |

**One subagent was dispatched and could not run:** `Bash` is disabled inside
subagents, so the sweep-runner returned **COULD NOT RUN** rather than a
fabricated exit code — and it read the harness instead, which is where
`tests/sabotage_harness.py:328-330`'s baseline arm came from. **I then drove
that probe myself.** Worth knowing before anybody else routes execution to a
subagent in this harness.

---

## 3. WHAT IS OPEN, AND WHY

### 3.1 cody and hank — the two holes the probes found

**cody — `tests/sairncash_entitlement_gate.js` misses two of eight
mutations.** Measured:

```
CMD python tests/sairncash_entitlement_gate_probe.py    ->  EXIT 1
  ok   0. the suite is GREEN in the worktree before anything is planted
  FAIL 3. a server answer of INVALID is treated as valid
  FAIL 5. the gate stops asking the server AT ALL -> the client-only check
  2 ARM(S) FAILED
```

**A FAIL there is the probe working**: the suite did not go red when the gate
was sabotaged. Mutation 3 means a revoked or refunded subscription keeps
working; mutation 5 means `reverifySubscription()` degenerates into the
client-only check **that the suite itself asserts believes a forged record**.
Mutation 1 — the headline forgery — *is* caught, which is why these went
unnoticed.

**Exact next step:** the two arms are written out as code in
`docs/2026-10-14-fourth-b16-row44-row50-probes.md` §3.2. **ARM B first** (the
server must actually be asked); ARM A carries a `calls.length >= 1` assertion
so it cannot pass for ARM B's reason. Then re-run the probe and require **8 of
8** — the probe is the acceptance test and it already fails.

**hank — four resources a record cannot be removed from.** Measured:

```
CMD python tools/removal_path_check.py    ->  EXIT 1
  keyed, no removal path, NOT in the baseline : 4
    alf_family_contacts (sairncare) · sv_scribe_consent (sairnvet)
    sf_trustee_audits (sairnfreedom) · mech_insurance_policies (sairnmechanical)
  grandfathered in the baseline : 321
```

**`sv_scribe_consent` is the sharpest: a consent record that cannot be
withdrawn through the product**, and it is one of the 42 resources my b15
SAIRNvet role matrix gates. `alf_family_contacts` holds a named family member's
contact details. **Exact next step:** a removal path per resource, or four
baseline rows **each with a reason** — the tool already separates grandfathered
from new, so adding them silently is the one answer that destroys the
information.

### 3.2 cc — four decisions, two corrected numbers

`docs/2026-10-14-fourth-b16-routed-to-cc.md`.

1. **`tools/fixture_lock_check.py`** — absent, **never committed on any
   branch**. Spec is b13's. Build it or a `NOT_PROMOTED` with the reason.
2. **`docs/by-design-register.json` — CORRECTION: two files name it, neither
   reads it.** `tools/batch_manifest.py:559` is a fixture's evidence string;
   `tools/report_only_checks.py:3553` is a comment. **Two mentions, zero
   readers, four rulings, all at `DECIDE_OR_NOT_PROMOTED`** — and all four are
   addressed to cc.
3. **Session locks — CORRECTION: 8 of 14 over 160h, not 7.** Oldest 355.4h.
   Three locks share two dead PIDs. **The count moving on its own is the
   argument for a threshold in a tool rather than a number in a document.**
4. **Scratchpad litter: 58 files / 54 MB** in b11's dead session (54 MB of it
   one salvage bundle) and **101 files / 608 KB** here. Nothing deleted since
   b13 because `rm` is denied. **Ruling
   `2026-10-14-rm-deny-bypassed-by-python` is the decision that unblocks it.**

**Also cc, from item 5:** a `--read-the-line` mode on
`tools/citation_line_drift_check.py` — report-only, exit 2 when no citation
parses, and **a banner saying what it cannot do**, because an off-by-one needs
a reader.

**Also cc, from item 1:** `tools/batch_manifest.py:386` still crashes `--close`
on a non-ASCII first line. Every close in this batch used
`PYTHONIOENCODING=utf-8`.

### 3.3 Counsel and the practitioners — the ten questions

`docs/2026-10-14-fourth-b16-confirm-questions.md`, one page, each a yes/no with
what changes either way.

* **Counsel, 3:** is embalming its own licence tier (SAIRNlegacy `prep`); does
  a cremation authorisation need two named people (`leg_cremations`); may a
  paralegal **prepare** a trust disbursement (SAIRNlaw).
* **A funeral director, 5:** is there a non-director arranger; does the office
  role need to read death and cremation records; do apprentices log in; are
  livery staff employees; is livery invoiced through the home.
* **A veterinary practice, 2:** does the practice manager read clinical
  records; may a technician record a controlled-substance administration under
  your state board's rules.
* **One law-firm org question is listed outside the ten** — in-house or
  outsourced bookkeeping — because it is neither legal nor answerable by a
  funeral home or a vet.

**Nothing is blocked on these.** Each answer sets one permission row; today the
software's default answer is "everyone can do everything", which is the finding
the three b15 matrices exist to end.

### 3.4 The one citation that was wrong — and it was never right

```
CMD python scratchpad/cite_recheck_b16.py   ->  exit 0
    45 citation(s) across 9 document(s); 0 unresolvable
CMD awk 'NR>=274 && NR<=278' api/_lib/auth.js
    276:   //   manager    -- Practice Manager. Runs the office; NOT a clinician.
    277:   //   frontdesk  -- Front Desk / reception.
```

The b15 SAIRNvet matrix cited `api/_lib/auth.js:277` **twice** for the
manager-is-not-a-clinician claim. It is at `:276`. **Fixed in place, with the
correction left visible in the sentence** — a corrected citation that hides
having been wrong teaches nobody anything. **It did not drift; it was wrong
from the first commit**, which is exactly what a baseline-diffing drift checker
would have called clean.

**The two sealed b15 artefacts carry 12 of the 45 and all 12 are correct.** Had
one been wrong, the correction would go in a new dated document, **never into a
sealed report**.

### 3.5 Still open from earlier batches

* **hank:** delete `api/ai-notice.js` and migrate the ack (b15 §7.5); the three
  role matrices, **SAIRNlegacy first** — zero gates, widest exposure, and its
  `staff` migration must go to the narrowest band.
* **cody:** fixture rows 26–50, **row 39 first**; b14's T7/T8/T9/T10/T14 arms;
  the one arm for the deleted ai-notice endpoint.
* **cc:** everything in §3.2.
* **fourth (me):** **rows 44 and 50 are now struck as false positives**, so my
  own open fixture work is **row 11 only** — `tools/text_gate_literal_sweep.py`,
  whose build spec is written and whose code is cc's.

---

## 4. THE THING THE NEXT SESSION MUST DO FIRST

**Write the batch manifest before any item** —
`python tools/batch_manifest.py --new fourth b<n> --items <n>` — and close it
with **`PYTHONIOENCODING=utf-8`** until §3.2's line 386 is fixed. **And when a
list of "unfixtured" checkers says to write a fixture: drive the file first.**
Two of the two rows I was sent to write this batch were already locked, and
driving them was worth more than writing them.

---

## 5. HOOKS — THE STATE CHANGED AGAIN, AND NOT BY ME

```
CMD python -c "json.load(.claude/settings.json)['hooks']"
    groups 0, entries 0
CMD git log --format=%h HEAD --not 54d40b62 -- .claude/settings.json
    3857890a
CMD git log -1 --format='%h %cI %s' 3857890a
    3857890a 2026-10-14T08:15:47-04:00 Merge origin/main into hank b9 ...
```

**b14 and b15 recorded 1 group / 1 entry; it is now 0 / 0.** The
`SessionStart`/`compact` hook group that cc's b8 claim said it would remove has
gone, arriving here through hank's merge. **I added nothing, restored nothing,
removed nothing and committed nothing to that file** — neither of my two
commits touches it.

**Consequence for the open work:** the `compact` matcher **can never now be
observed firing**, so b13's third hook finding closes by deletion rather than
by evidence. **And `tools/hook_integrity_check.py`'s predicate accepts an empty
`hooks` object**, so this state is the one it was originally written for.

---

## 6. FINAL STEPS STILL AHEAD OF THIS HANDOFF

1. `PYTHONIOENCODING=utf-8 python tools/drive_upload_verify.py --agent fourth
   --batch b16` — **will report 2 findings**, because the report and digest do
   not exist yet. Expected; the handoff is written first by instruction.
2. The report and digest, then the same upload-and-verify, then a Drive-side
   API read, because the mount proves the sync set and not Google's
   acknowledgement.
3. `PYTHONIOENCODING=utf-8 python tools/batch_manifest.py --close --agent
   fourth --batch b16` — **after** all three are up, because closing is
   *defined* as all three verified.
4. Release the b16 claim.

**Nothing is partial.** Every open item above is another session's, or mine and
named as mine, or a measurement with its command stated.
