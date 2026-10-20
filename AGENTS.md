# AGENTS.md — the per-repo context an agent needs before its first tool call

**What this is:** the facts a dispatch would otherwise have to restate every
time, in one short file at the repo root. Written 2026-10-19 (cc b19 item 4).

**What this is NOT, and the distinction is load-bearing:**

- **Not a replacement for `CLAUDE.md`.** That file is the authority on house
  rules and you still read it. This one exists so a *chat dispatch* does not
  have to paste the clone list, the claim commands and the artefact contract
  into every message.
- **Not a second copy of anything countable.** Every number below is a
  command, not a figure — because this repo has corrected a hardcoded count in
  three separate documents at once, and a ninth standing document that goes
  stale is worse than no ninth document.

---

## 1. Before the first tool call

    python tools/sairn_status.py                 # who is working, outside git
    python tools/sairn_claim.py check <subject> <task words>
    python tools/sairn_claim.py claim <subject> "<task>. FILES: <paths>"

**Declare a FILES list.** Without one the matcher falls back to words and
reports *could not compare* — which is not evidence of no overlap, it is
evidence that nothing looked.

**Claim before you start, release when you stop.** A claim that is not
committed is invisible to every other clone.

## 2. The clones, and the one that is not a build agent

**Count the directories, do not count this list** — it has been wrong before:

    ls ~/Documents | grep SAIRN

`SAIRN-hover` and `SAIRN-hover2` are **auditors**, not build agents. A build
agent does not write into an auditor's clone or its published files, including
to tidy them up.

## 3. Reading the big documents

`python tools/tooling_inventory.py --standing-doc-sizes` prints every tracked
document over 400,000 bytes and exits 1 while any exists. **Do not open those
files.** `grep -n`, `awk 'NR==n'`, `sed -n 'a,bp'`.

**A window that stops inside a table row or a tuple gives a wrong answer with
no warning.** Widen it until the structure closes, or measure the thing with a
parser instead of reading text.

## 4. Pushing

    git push origin main          # the gate runs; read what it says

- **Never `--force`.** Never a blanket override.
- A gate refusal is normally **satisfied at its cause**, not skipped. If a skip
  is genuinely right, it is **two commands**:
  `SAIRN_SKIP=<gate> SAIRN_SKIP_WHY="<why>" python tools/gate_skip.py` and then
  a plain push. Those variables in front of `git push` grant **nothing**.
- A rejected push is **not a no-op**: read `git status` first, not last.
  `python tools/sairn_rebase_resolve.py` handles generated documents and
  append-only ledgers; otherwise `git pull --rebase origin main`.
- **A rebase moves your shas.** Anything that cites one — the defect register
  especially — needs re-seating afterwards, and the hooks will tell you.

## 5. The artefact contract at the end of a batch

Four files, in this order, and the handoff is written **at a point where
nothing is half-finished**:

    SAIRN-handoff-cc-b<N>.md     committed/pushed state, open items + why,
                                 claims held, exact next step per item,
                                 transcript path
    SAIRN-report-cc-b<N>.txt     REPORT first line; SHA256 second-to-last;
                                 END-OF-REPORT last
    SAIRN-digest-cc-b<N>.txt     STATUS / DECISION-NEEDED / CHANGED /
                                 EVIDENCE-path / UNVERIFIED / NEXT / CONTEXT
    docs/batch-manifest-cc-b<N>.json

Then:

    python tools/digest_lint.py SAIRN-digest-cc-b<N>.txt    # 150-WORD CEILING
    cp SAIRN-{handoff,report,digest}-cc-b<N>.* "G:/My Drive/SAIRN-status/"
    python tools/drive_upload_verify.py --agent cc --batch b<N>
    python tools/batch_manifest.py --close --agent cc --batch b<N>

**THERE ARE TWO DIGEST CEILINGS AND THEY ARE NOT THE SAME NUMBER. Corrected
2026-10-20 (cc b27) — this paragraph previously named only the first.**

| ceiling | where | enforced |
|---|---|---|
| **150 words** | `tools/digest_lint.py`, `MAX_WORDS` | exits 1, but **no gate runs it** |
| **30 lines** | `CLAUDE.md` *"Batch deliverables"*, the standing rule | `tools/drive_upload_verify.py --max-lines`, default 30, **finding** |

**NEEDS MICHAEL'S CALL, and it is stated here rather than resolved quietly:**
the two are complementary in intent and far apart in practice. Measured
2026-10-20 over the newest digest of each of four agents — hank b23 **30 lines
/ 356 words**, fourth b38 **13 / 541**, cody b26 **239 / 2011**, cc b26 **10 /
213**. **Nobody meets 150 words and the figure has not been met in months**, so
it is a ceiling in writing only. Write to **30 lines**, which is the rule the
dispatches name and the one now mechanically checked, and expect
`digest_lint` to report over-length until the two are reconciled.

**What changed, so a stale sentence here is not read as current:** this file
used to say *"nothing blocks an over-length digest."* Since 2026-10-20
`drive_upload_verify` raises a finding at over 30 lines and exits 1, which is
what says do not mark the batch closed. It still uploads the file — a missing
deliverable is worse than a long one. The detail belongs in the report, which
is what `EVIDENCE-path` points at and which has no cap for that reason.

**And three more deliverable rules that lived in no file a fresh session reads
until 2026-10-20 — they are now in `CLAUDE.md` *"Batch deliverables"*, which
is the source:** wrap up at **80% of real context** (`python
tools/context_verify.py --digest-line`, measured, not estimated — cc breached
it at 81.9% in b25 and 89.0% in b26); **SQL goes in `sql/<name>.sql` and the
digest gives the path only**; and the **final chat message is exactly `done
b<n> <Drive file id of the digest>`**.

**The mount is not the API.** `drive_upload_verify` proves the bytes are in the
sync set. Only a Drive-side read from a chat turn proves Google acknowledged
them.

## 6. The things that have cost real time more than once

- **A backslash or a backtick in a CLI body is mangled.** Three batches
  running. Write the program to a file and run the file; "be careful" has
  already failed.
- **A line number in a routed note ages out within a batch.** Route a quoted
  span, never a number.
- **A check that fires on absence is the dangerous direction.** Drive it
  against the defect it was written for before believing a clean result. Two
  probes in b18-b19 reported nothing while looking straight at the thing they
  were built to catch.
- **A lock that crashes is not a lock that passed.** Exit 2 is a third state.
- **The shared Drive board is republished by whichever clone fires an event**,
  so a publisher fix is not live platform-wide until every clone fetches it.
  Since publisher revision `2026-10-19.1` a lower-revision clone refuses to
  overwrite a newer board instead of reverting it.

## 7. Where to look next

| question | file |
|---|---|
| house rules, the authority | `CLAUDE.md` |
| the judgement half of them | `docs/SAIRN-PROCESS-RULES.md` |
| conventions paid for by real defects | `docs/2026-09-13-cross-domain-disciplines.md` |
| what each tool catches | `docs/TOOLING-INVENTORY.md` (generated) |
| what is open | `docs/SAIRN-OPEN-WORK-INDEX.md` by grep only |
| what the last batch did | the newest `SAIRN-handoff-*-b<N>.md` |
