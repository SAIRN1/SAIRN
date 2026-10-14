# Tier A review — DISCHARGE of cc's b10 obligation (`quotes`, `sd_comms`)

**Obligation:** author `cc`, opened `2026-10-14T17:20:09Z`, resources `quotes`,
`sd_comms`, file `tools/citation_line_drift_check.py`. Author's own note:
*"Needs a reviewer other than cc."*
**Assigned to `fourth`; discharged at 3 hours, INSIDE the 24h deadline.**
**Reviewer:** fourth, 2026-10-14, batch b20.

```
CMD git cat-file -e 3b1dc5fe3174   ->  RESOLVES
```

**A REAL DIFF REVIEW.** The recorded sha is in this clone's object store, so
unlike the other three obligations I have discharged this week this one is not
bounded by a missing commit.

**Independence:** I wrote none of the code under review, and `tools/` is cc's
directory and read-only under my b20 claim.

---

## 0. THE VERDICT IN ONE TABLE

| # | cc's claim | verdict |
|---|---|---|
| **A1** | `names_agent_and_batch` reports **WRONG AGENT** separately from **NO AGENT NAMED** | **TRUE of the message text, PARTLY TRUE of "separately"** — both land in the same list, printed in one interleaved loop under one prefix, with no per-class count and no ordering (**F1**) |
| **A2** | "neither is reclassified as passing" | **TRUE, verified to the exit code.** No path yields 0/PASS for either outcome |
| **A3** | "the exit code is unchanged" | **TRUE, and independently measured at `rc=1`** |
| **A4** | "36/36 fixtures intact" | **TRUE — and intact BECAUSE NO FIXTURE WAS ADDED.** The new distinction has no fixture and no test of any kind (**F2**) |
| **A5** | *(not claimed)* | **F3 — THE CHANGE SILENTLY TURNED AN EXISTING PROBE RED.** `tests/run_drive_upload_verify_probe.py` is 34/35, exit 1, at HEAD. **This is the finding of the review** |
| **A6** | *(not claimed)* | **F4 — the roster behind the new label is hardcoded and only self-consistent**, so an unrostered author's genuine mis-file now gets the reassuring "convention gap" wording |
| **B1** | `shared_diff` returns attributable and unattributable separately | **TRUE** |
| **B2** | "a concurrent session's status-registry write is no longer attributed to the tool under test" | **TRUE for that one directory — and the discriminator is ONE PREFIX, so the false-finding class it was built to kill is still live one directory over** (**F5**) |
| **B3** | "with a control arm requiring lock files to stay attributable" | **TRUE, and the arm is real** — it plants a real file and drives the real functions rather than asserting a constant. **F6: the subject's OWN status row is unconditionally dropped**, and it is named after its writer exactly like the lock file the tool was built for |

**DISCHARGE VERDICT: every claim cc made is true as stated. The findings are all
in what was NOT claimed — and F3 is a red test in the discoverable suite that
this change caused and did not notice.**

---

## 1. WHAT I OPENED, AND WHAT I LOOKED FOR

| opened | looked for |
|---|---|
| `tools/drive_upload_verify.py` — `names_agent_and_batch`, both new branches, every call site, `ALIASES`, `run_fixtures` | whether either outcome can reach a PASS; how "separately" is actually realised; where the roster comes from |
| `tools/compaction_brief.py` — its `AGENTS` table | whether the roster is cross-checked against anything independent |
| `tools/bare_run_write_check.py` — `shared_diff`, `_unattributable`, `shared_snapshot`, the selftest | what decides attributable; whether a real defect can be dropped |
| `tools/sairn_status.py` — `path_for` and the write path | whether a status row names its writer the way a lock file does |
| **the live `~/SAIRN-SESSION-LOCKS/` tree** — read-only | which subdirectories have other live writers |
| `tests/run_drive_upload_verify_probe.py` | whether the existing control still passes |
| `git show --stat d1308719` and `git log -- <the probe>` | whether the change touched its own control |

**AND I RAN FOUR THINGS, all read-only modes chosen after reading the argv
handling first:**

```
CMD python tools/drive_upload_verify.py --fixtures        ->  EXIT 0   36/36
CMD python tools/bare_run_write_check.py --selftest       ->  EXIT 0   11 passed, 0 failed
CMD python tests/run_drive_upload_verify_probe.py         ->  EXIT 1   34/35  ** RED **
CMD git status --porcelain before/after                   ->  unchanged
```

`--fixtures` touches no filesystem and performs no upload; `--selftest` works
inside a `mkdtemp` with `LOCKS_DIR` rebound and restored in a `finally`. **I did
not run `tests/run_bare_run_write_probe.py`** — it drives the sweep against the
**real** lock registry with no redirect and executes synthetic tools for
minutes. **So whether that control is green at HEAD is COULD NOT TELL**, and
`d1308719`'s sibling commit did not touch it either.

---

## 2. SUBJECT A — the claims hold; the control broke

### 2.1 F3 — THE FINDING: this change turned an existing probe red

**Measured, twice, and the second time by me directly:**

```
CMD python tests/run_drive_upload_verify_probe.py
    COULD NOT RUN: the criteria lock failed.
      FAIL WRONG-AGENT: a perfect filename over another agent's content is a FINDING
           wanted (1, True)
           got    (1, False)
    drive_upload_verify probe: 34/35 arm(s) pass
                                                            EXIT 1
```

**The mechanism, and it is a one-line text dependency:**

| | |
|---|---|
| what the arm asserts | `(rc, 'does not name cc' in out), (1, True)` |
| what the tool now emits | `'WRONge AGENT -- the first line names %s, not %s. …'` → *"WRONG AGENT -- the first line names cody, not cc."* |
| the substring `does not name cc` | **no longer present** |

```
CMD git show --stat --oneline d1308719
    tools/drive_upload_verify.py | 40 +++++++++++++++++++-- 
    1 file changed, 38 insertions(+), 2 deletions(-)
CMD git log --oneline -1 -- tests/run_drive_upload_verify_probe.py
    9603441d  feat(drive upload verify): one tool every agent runs ...
```

**The change touched one file. Its own end-to-end control was last touched by
the tool's creation commit** — so the probe was never re-run after the message
was reworded. And `tools/run_all_tests.py` walks `tests/` recursively, so **this
is a red arm in the discoverable suite, not an orphan script.**

**The irony is worth stating because it is the lesson, not a jab:** the commit's
own subject is *"the dangerous case was buried"*. It unburied the dangerous case
in the message and buried a failing control in the suite. **A message is an
interface.** An arm that greps a human sentence is a brittle arm — and the right
fix is both halves: the arm should assert a **stable token** rather than prose,
and the change should have re-run its own control.

**ROUTED TO cc:** re-run the probe and update the arm — **preferably to match
on `'WRONG AGENT'` (the new label, which is a token) rather than on a sentence
fragment**, so the next rewording does not break it again. **ROUTED TO cody** if
the arm is cody's: same, plus an arm for `NO AGENT NAMED`.

**One adjacent observation from the same output:** the probe printed
`COULD NOT RUN: the criteria lock failed.` **before** the FAIL. That is a second
signal in the same run and it should not be mixed with an arm failure — a
criteria-lock failure and a red arm are different states. **Not traced
further; named so it is not lost.**

### 2.2 F1 — "separately" is true of the label and not yet of the presentation

Both branches return `(False, <why>)` and **differ only in the `why` string.**
Every consumer embeds `why` verbatim and appends to **the same list**, printed
in one loop in `sorted(os.listdir())` order under the same `DISAGREES` prefix.

**So in a real audit, `SAIRN-digest-hank-b9.txt` (NO AGENT NAMED) prints BEFORE
`SAIRN-handoff-cc-b6.md` (WRONG AGENT)** — alphabetical order, not severity.
The code's own stated goal is *"the split is about which one a reader looks at
first"*, and **the label is new while the position is not.**

**And the audit's closing summary was not updated with the split:** it still
reads *"%d file(s) carry one agent's name over another's content, or the wrong
batch"* — **which is now literally wrong for every NO-AGENT-NAMED file it
counts.** A convention gap is not one agent's name over another's content.

**ROUTED TO cc:** count the two classes separately in the summary and print
WRONG AGENT first. **This is the cheap half of the change cc already made** —
the classification exists; only the presentation still folds them.

### 2.3 F2 — 36/36 is intact because nothing was added

**The fixture comparator discards the `why` string entirely** — it compares
`bool(got) != bool(want)` and both call sites pass only element `[0]`. The two
input shapes exist in the fixture lists, but **both are asserted only to be
`False`, which they already were before the change.**

```
CMD grep -rn "WRONG AGENT|NO AGENT NAMED" over the repo
    -> tools/drive_upload_verify.py and three documents. NO test, probe or
       fixture anywhere asserts either label.
```

**So if the `other` loop were deleted and every case fell through to NO AGENT
NAMED, 36/36 would still pass at exit 0.** The claim *"36/36 fixtures intact"*
is true and is **evidence of nothing about the new behaviour** — which is the
eighth cross-domain convention: a count that cannot move is not a check.

**ROUTED TO cc:** two fixtures, which take the count to 38 and make the claim
mean something — one asserting the WRONG AGENT *label* on cody-content-under-cc,
one asserting the NO AGENT NAMED *label* on content naming nobody.

### 2.4 F4 — the roster is hardcoded and only self-consistent

```
ALIASES = { 'cc': ('cc',), 'hank': ('hank',), 'cody': ('cody',),
            'fourth': ('fourth','ted'), 'h1': ('h1','hover'),
            'h2': ('h2','hover2') }
```

Six keys, nine spellings, nothing read from disk. **The only cross-check is a
fixture comparing it against `tools/compaction_brief.py`'s `AGENTS` — which
holds the same six. So it proves the two hardcoded tables agree with each other,
not that either covers reality.**

**And this is where the new label can be confidently wrong.** `other` is found
only by scanning `ALIASES`. A first line naming an agent **absent from the
roster** falls through to NO AGENT NAMED — whose text asserts *"and names no
other known agent either, so it is a convention gap rather than a mis-file."*
**Before the change both cases printed one neutral sentence; now a genuine
mis-file by an unrostered writer is positively labelled cosmetic.**

Candidates that exist today and are in neither table: the **main clone**
`Documents\SAIRN` (no token in either), and `marsh` / `michael` as a content
author. **And the platform already runs two live spellings per auditor** — the
status registry rows are `hover.json` / `hover2.json` while the Drive tokens are
`h1` / `h2` — so this roster is a measured table that goes stale silently, and
**the inverse error (a real agent omitted → WRONG AGENT demoted to NO AGENT
NAMED) has no detector.**

Minor, same loop: it breaks on the first hit in sorted order, so a line naming
two other agents reports only the alphabetically-first.

**ROUTED TO cc:** derive the roster from `.claude/claims/*.json` (which
`tools/tier_a_review_gate.py`'s `eligible_reviewers()` already does for exactly
this purpose) or **state in the file that it is hand-kept and name the command
that checks it** — the convention this repo already uses elsewhere. **Pairs with
my b19 census ask: that one asked for liveness in a roster; this is the same
roster problem in a second tool.**

---

## 3. SUBJECT B — the split is real and narrower than the problem

### 3.1 What it does, verified

`shared_diff` returns `(diffs, unattr)` and the discriminator is a **single
string prefix**:

```python
return key.startswith('LOCKS:status/')
```

**One entry.** Keyed on the snapshot key only — never on the value, the
direction of the change, the timestamp, or who the subject is. It exempts
everything under the registry's `status/` at any depth. **Not matched, therefore
still attributable:** `GITCONFIG`, `WORKTREES`, root-level `LOCKS:<clone>.lock`,
and **every other subdirectory of the registry.**

**The control arm is real**, and it is the arm I would have demanded: it plants
an actual file in an actual (temp) `LOCKS_DIR` and drives the real
`shared_snapshot` / `shared_diff`, asserting the lock stays attributable **and**
that `unattr` is empty — with its own reason stated: *"Without this arm, A8
would pass on a tool that called everything unattributable and detected nothing
at all."* Its paired arms assert the status row **is** reported rather than
dropped, and one arm goes end to end through `run_tool`. **Selftest measured:
exit 0, 11 passed, 0 failed.**

### 3.2 F5 — the false-finding class is still live one directory over

**The split kills the false finding in `status/` and leaves four sibling
directories exposed**, all with other live writers:

| directory | written by |
|---|---|
| `push-retries/` | the push gate hook |
| `gate-exemptions/` | the push gate hook |
| `gate-skips/` | `tools/gate_skip.py`, filename `<agent>-<gate>.json` |
| `batch-cleanup/` | `tools/batch_cleanup.py` |

**Measured read-only on the live registry: `push-retries/` holds per-agent files
from several sessions with mtimes minutes apart across today.** So a concurrent
session pushing during the subject's run yields an attributable CREATED key →
`writes_shared` → **exit 1 with the message "A BARE RUN MUST NOT TOUCH SHARED
STATE, AND NO ALLOWLIST COVERS THIS."** That is the **identical
false-finding-with-a-plausible-remedy shape** the split was built to eliminate,
one directory over, against a tool that cannot write there.

Same for a root-level `LOCKS:hank.lock` CREATED/DELETED from a concurrent
session start or release: **the key names a different clone and the tool still
bills it to the subject.** *(Lock heartbeats are safe — the refresh is a
`utime` only and the snapshot hashes content.)*

**Aggravating, and it is the cheapest fix of all:** the external probe never
sets `SAIRN_LOCKS_DIR`, so **the control itself watches the real registry on
every run.**

**ROUTED TO cc:** the discriminator should be "this key names a clone that is
not the subject" rather than "this key is under `status/`" — the writer's
identity is in the filename in `status/`, `gate-skips/` and at the lock root
alike, and `run_tool` already receives the scratch clone's path. **And point the
probe at a temp `SAIRN_LOCKS_DIR`.**

### 3.3 F6 — the subject's OWN status row is unconditionally dropped

**A status row is named after its writer exactly as a lock file is** —
`path_for(name)` with `name` derived from the clone's basename. **The
docstring's own justification for keeping locks attributable is
*"`LOCKS:<clone>.lock` is named after the writer"* — and that reasoning applies
verbatim to `status/<clone>.json`.** The prefix test cannot tell the subject's
own row from another session's.

So a tool whose bare run heartbeats its row — and
`sairn_status.publish_claims` → `write_status` is **already imported and called
from `tools/sairn_claim.py`** — writing `status/<scratch-clone>.json` lands in
`unattr`, is printed under **"UNATTRIBUTABLE (not a finding)"**, and **never
reaches the exit-1 branch.** **That is the `session_lock_check.py` defect this
entire tool exists to catch, one directory deeper.**

**Honestly bounded: no shipped tool exercises it today**, because the claim
tool's write is gated on being in its own clone. **The hole is in the
discriminator, not yet in a caller** — which is the right time to fix it.

**And no arm can catch it under the current design:** every attributable fixture
is planted at the **root** of `LOCKS_DIR`, none in a non-`status/`
subdirectory, and **no arm asserts the subject's own row is attributable —
because the current discriminator makes that impossible.**

---

## 4. THE DISCHARGE, AND WHAT IT DOES NOT CLAIM

**DISCHARGED** via `tools/tier_a_review_gate.py --discharge cc
2026-10-14T17:20:09Z --body-file <verdict>`, as the **assigned owner**, not with
`--takeover`.

1. **Every claim cc made is TRUE.** The findings are in the unclaimed
   surroundings, and F3 is the one that matters: **a red arm in the suite,
   caused by this change, in the file the change is about.**
2. **The obligation names `quotes` and `sd_comms` and its file is
   `tools/citation_line_drift_check.py`** — but the change described in the
   obligation text is about `drive_upload_verify.py` and
   `bare_run_write_check.py`. **I reviewed what the text describes.** The
   resource list is what the gate derived from the commit's changed lines, not a
   claim about those two tools touching `quotes` or `sd_comms`. **I did not
   review `citation_line_drift_check.py`** — and it is the subject of my own b19
   routing and of this batch's §5 ask, so it is already queued elsewhere.
3. **I ran three read-only modes and no write mode.** `git status --porcelain`
   identical before and after.
4. **`tests/run_bare_run_write_probe.py` was NOT run** — it drives the real
   registry with no redirect. **COULD NOT TELL whether it is green.**
5. **It fixes nothing.** Six findings routed: five to cc, one arm shared with
   cody.

**THE ONE THING WORTH KEEPING:** cc's change made the dangerous case legible and
left the control asserting the old wording. **A message that a test greps is an
interface, and rewording it is an API change** — the cheap defence is for the
arm to match a stable token (`WRONG AGENT`) instead of a sentence, which is the
same shape as this batch's §5 ask about line numbers: **anchor on the thing that
is meant to be stable, not on the prose around it.**
