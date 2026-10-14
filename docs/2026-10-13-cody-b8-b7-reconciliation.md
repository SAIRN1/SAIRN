# The two b7 runs, reconciled into one authoritative record

**cody, batch b8, 2026-10-14 (the runs themselves are dated 2026-10-13).**
Two sessions both called themselves *cody b7*, both worked in
`C:\Users\marsh\Documents\SAIRN-cody`, and **both wrote the same two
filenames.** This document names which artefact is authoritative, says what is
recoverable only from the superseded one, and closes item 6 of run A's brief.

**DERIVED, not recalled.** Every claim below comes from `git log --diff-filter`,
`git show --stat`, `wc -c`, a recomputed SHA256, and a Drive folder listing —
commands named inline.

---

## 1. THE VERDICT FIRST

| artefact | authoritative copy | bytes | why |
|---|---|---|---|
| **handoff** | **`SAIRN-handoff-cody-b7.md`** (repo root) | **11,417** | it is the copy on Drive, byte-for-byte. `docs/SAIRN-handoff-cody-b7.md` is run A's and is **retained, not authoritative** — see §4, it is the ONLY record of two facts |
| **report** | **`SAIRN-report-cody-b7.txt`** (repo root) | **29,901** | on Drive, and its own SHA256 line **verifies** — see §3. Only one report file was ever written |
| **digest** | **`SAIRN-digest-cody-b7.txt`** (repo root) | **1,002** | on Drive, and **it already names the two-run condition in its own first line** |

**There is exactly one copy of the report and one of the digest, and three
copies of nothing.** The duplication is confined to the handoff. Verified:

    git ls-files | grep -i "cody-b7"
      SAIRN-digest-cody-b7.txt
      SAIRN-handoff-cody-b7.md
      SAIRN-report-cody-b7.txt
      docs/2026-10-13-cody-b7-seam-pair-owners.md
      docs/SAIRN-handoff-cody-b7.md

**AND THE DRIVE FOLDER HOLDS ONE OF EACH, NOT TWO.** Listing
`14Xc5oT0xzSLa_rTSOSXWVK3Kko1Fbx09` returns three b7 files, sizes 11,417 /
29,901 / 1,002 — identical to the three root files. **So Michael's copy is the
root trio and nothing has to be re-uploaded.** That is the single most useful
fact in this document.

---

## 2. THE TWO RUNS, AND THEY HAD DIFFERENT BRIEFS

This is the part that matters more than the filename collision. Items 1, 2, 3
and 5 were the SAME in both briefs. **Item 4 was a different task in each**, and
item 6 differed. Taken from each run's own item table:

| # | run A's item | run B's item | same? |
|---|---|---|---|
| 1 | driven SAIRNfreedom matrix + `bld_draws` role arms | same | ✓ |
| 2 | the three hank-authored `api/` Tier A records | same | ✓ |
| 3 | `unproven_arm_check` + the `check4_probe` WEAKENING flag | same | ✓ |
| 4 | **`verify_citator_feedback.py --check-only` then `--write`** | **`git worktree` / `.git/config` isolation** | **NO** |
| 5 | the 19 seam pairs → one owner per pair | same | ✓ |
| 6 | **commit/discard the edit to `docs/handoff-cody-2026-10-13c.md`**; push; release | push and confirm | **NO** |

**So "b7 item 4" is ambiguous and a reader must say which run.** The
authoritative digest handles this correctly and explicitly —
*"Item 4 differs per brief: git-config isolation IS done; the citator tool NEVER
RAN -- SUPABASE_URL and SERVICE_ROLE_KEY both missing"* — and that line is the
reason the digest is authoritative rather than merely final.

**They also disagree on a number for the same suite, and both are right.** Run A
reports `tests/sf_role_matrix_driven.test.js` as **540 driven cells**; run B
reports **720**. The denominator moved between the two runs: `api/sd-data.js`
commit `46d74678` gated the last nine `sf_` resources, taking the matrix from 27
to 36 session-gated resources. **A stale figure and a wrong figure look the
same; this one is stale with a cause, and run B's arm 4 is what caught it.**

---

## 3. PROVENANCE OF THE ROOT TRIO — the report is a HYBRID and that is disclosed

The root report and digest were **created by run A and then amended by run B.**
Ordered from `git show --stat --date=format:"%H:%M"`:

| time | commit | file | effect |
|---|---|---|---|
| 16:46 | `e8e9fe42` | `docs/SAIRN-handoff-cody-b7.md` | **run A** creates its handoff, +188 |
| 16:46 | `afcec177` | `SAIRN-handoff-cody-b7.md` | **run B** creates its handoff, +201 |
| 16:51 | `0d5c241a` | root report + digest | **run A** creates BOTH, +486 / +24 |
| 16:53 | `f52470d5` | `tests/sf_role_matrix_driven.test.js` | run B's arm-4 rewrite |
| 17:01 | `6de71700` | root handoff + report | **run B** edits run A's report, +43/−28 |
| 17:01 | `eec635ed` | root report + digest | run B, the 720-cell correction |
| 17:01 | `28c04e83` | digest | **"the digest said item 4 was DONE and b7 CLOSED. Item 4 never ran."** |
| 17:01 | `97f65ee1` | digest | **"name the two-run condition in the first line"** |
| 17:01 | `6cf8b370`, `34b6224f` | digest | word-ceiling fixes, `digest_lint` clean |

**So `SAIRN-report-cody-b7.txt` is 486 lines of run A with 43 lines of run B
written over it, and it reads as one document because run B edited rather than
replaced.** Call it authoritative, not single-authored. Nothing in it is known
to be wrong — but anyone quoting it should know a second session's hand is in
it, which is exactly what a shared filename hides.

**ITS SHA256 LINE IS NOT TAKEN ON TRUST. RECOMPUTED HERE, by the report's own
stated rule (body = line 2 through the line before the SHA line, LF, UTF-8):**

    python -c "import hashlib,io;L=io.open('SAIRN-report-cody-b7.txt',encoding='utf-8',newline='').read().split(chr(10));b=chr(10).join(L[1:-3]);print(hashlib.sha256(b.encode()).hexdigest())"
    recomputed  4d32d6c58aa77a2dd87e416bcf1cac251fc3d63ee798cdb9cdabd7c72e8ebe46
    stated      4d32d6c58aa77a2dd87e416bcf1cac251fc3d63ee798cdb9cdabd7c72e8ebe46

**MATCH.** The hybrid is intact and unedited since it was sealed. That is the
one thing a recomputed hash can actually prove here, and it is worth more than
the provenance table above.

---

## 4. WHAT IS RECOVERABLE ONLY FROM THE SUPERSEDED HANDOFF

`docs/SAIRN-handoff-cody-b7.md` (13,016 bytes, first line *"# Handoff — cody,
batch 28 (b7), 2026-10-13"*) **stays in the repo and must not be deleted**, for
two reasons that exist nowhere else:

1. **Run A's item 4 — the citator tool.** `verify_citator_feedback.py` was
   **STOPPED AS INSTRUCTED: both `SUPABASE_URL` and `SERVICE_ROLE_KEY` are
   missing**, and `--write` was never run. The authoritative handoff's item 4 is
   a different task entirely, so deleting run A's copy would lose the only
   account of a tool that never ran. (The digest carries one line about it; the
   handoff carries the section.)
2. **Run A's item 6 — the answer this document was also asked to give**, §5.

It is also the only place the concurrent-writer condition is described from run
A's side (`docs/SAIRN-handoff-cody-b7.md:117` — `a339112d` re-staged a
concurrent re-add its author had not made).

**Retained ≠ authoritative, and the distinction is the whole point.** A reader
who finds two handoffs must be told which one Michael has, and must not be told
the other is garbage.

---

## 5. `docs/handoff-cody-2026-10-13c.md` — NOTHING TO COMMIT OR DISCARD

Item 2's second half asked for the uncommitted edit to that file to be committed
or discarded. **There is no uncommitted edit. There was none when b7 started
either.** Measured now, three ways:

    git status --short docs/handoff-cody-2026-10-13c.md     # no output
    git diff --stat HEAD -- docs/handoff-cody-2026-10-13c.md # no output
    git log --oneline -1 -- docs/handoff-cody-2026-10-13c.md
      72ca3ad1 docs(b6 tail): the regress-proof cleanup count, and the
               15-line b6 handoff Michael asked for by name

**The edit was committed at `72ca3ad1`, in b6's tail, before either b7 run
began.** It is a 6-line change (+5/−1) to the cleanup-count paragraph: it
records that the cleanup record's own push then produced five more scratch files
(`pfx mx tx gx px`), so the count is stated as *"the 41 named here plus the
handful the final push makes"* rather than as a total that goes stale the moment
it is written.

**Run A already reached this answer and recorded it** —
`docs/SAIRN-handoff-cody-b7.md:33`, *"NOTHING TO COMMIT OR DISCARD. That file
was already committed at `72ca3ad1` before this session began."* **This section
is an independent re-measurement that agrees with it, not a rediscovery.** The
task carried forward into b8 because it was answered in the handoff that is NOT
the authoritative one — which is the collision's one concrete cost.

`72ca3ad1` is an ancestor of `origin/main`:

    git merge-base --is-ancestor 72ca3ad1 origin/main   # exit 0

---

## 6. THE RULE THIS PAYS FOR

**A batch label is not a lock.** Two sessions can hold the same batch number,
the same clone and the same output filenames with nothing refusing, and the
second writer's edits land inside the first writer's file with a clean
`git status` the whole way. Nothing in the push protocol, the claim record or
the status registry noticed: run A and run B were both *cody*, so a claim on
`tests` matched itself.

What actually limited the damage was ordinary discipline, and it is worth naming
because it is repeatable:

* **the digest named the condition in its own first line** (`97f65ee1`) instead
  of describing a single coherent run that did not exist;
* **a digest commit corrected its own predecessor out loud** (`28c04e83`:
  *"the digest said item 4 was DONE and b7 CLOSED. Item 4 never ran."*);
* **both handoffs were kept.** A merge that dropped one would have produced a
  record that read cleanly and was missing a tool that never ran.

**The cheap mechanical fix, if anyone wants one:** make the report/digest/handoff
writer refuse when a file of that exact name already exists at a different
content hash, and print both. `tools/drive_upload_verify.py` (cc, b7) already
checks title ↔ first-line ↔ bytes ↔ sha256 against Drive; **the gap is
local-vs-local, before upload, which is where this one happened.** Routed as an
observation, not a claim that it is worth building.

---

*b8 wrote nothing into the b7 artefacts. The root trio is unchanged, its hash
still verifies, and the Drive copies were not re-uploaded because they already
match.*
