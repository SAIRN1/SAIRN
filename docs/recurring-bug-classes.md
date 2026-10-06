# Recurring bug classes — a 3-level cause tag per confirmed defect

**Started 2026-10-06 (fourth).** Every confirmed defect gets one row:

    PHASE  ->  SUB-PHASE  ->  CAUSE ("due to X")

`unknown` is allowed at any level and is better than a plausible guess — a
cause column full of confident wrong answers is worse than one that admits
what nobody established. A row whose cause is `unknown` says so *and* says
what was tried.

**Why three levels and not a free-text note.** A note is searchable by whoever
remembers the words in it. A tag is countable: when the same SUB-PHASE appears
four times in a month, that is the finding, and no amount of good prose adds
up to it on its own.

**PHASES:** `requirement`, `design`, `coding`, `config`, `unknown` — the same
five `tools/defect_register.py` uses, so a row here and a register record
cannot drift into different vocabularies.

---

## 2026-10-06 — batch 10 (fourth)

| # | Defect | Phase | Sub-phase | Cause | Commit |
|---|---|---|---|---|---|
| 1 | `tests/seam_check/run_delegation_probe.py` left `api/sd-data.js` and `api/_lib/subcontractor-compliance.js` carrying planted sabotage, one of which does not parse | coding | error handling | **due to** a destructive mutation written as a straight line — `write()`, then work, then `git checkout --` — with no `finally`, so every exception, assertion and kill between the two kept the plant | this batch |
| 2 | The same probe's baseline read the LAST LINE of `tools/sairn_seam_check.py`'s output | coding | anchor selection | **due to** a positional anchor (`splitlines()[-1]`) on another tool's output, which moved the day that tool gained a three-line closing explanation | this batch |
| 3 | The same probe's baseline required `0 could-not-tell` — a PLATFORM total — while printing "canAssign resolves at baseline" | requirement | criterion definition | **due to** a proxy standing in for the property actually named: the platform figure is 19 today, every one a different seam, and none of them canAssign | this batch |
| 4 | `tests/push_gate/check8_probe.py` leaves `.git/config` with `core.bare = true` and a fixture identity, after which every git command in the clone fails | unknown | unknown | **unknown.** Pinned to one STEP — `dry_push(probe_env=False)`, the first dry-run push whose outgoing range resolves — and not to one command. Six isolations came back clean and all six exited early on "range could not be read", so none of them reached the code. Next place to look is named in the file; not guessed at here | contained this batch, not fixed |
| 5 | My own first version of the fix for #1: `--check-residue` DELETED the sentinel it had just reported | design | lifecycle | **due to** a cleanup handler registered at module import, so a read-only invocation ran it — a detector erasing its own evidence. Caught by the control on its first run, not by reading | this batch |

### What the five say together

**Three of the five (1, 2, 5) are the same shape one level apart: something
that was supposed to happen at the END did not happen on a path nobody
pictured.** A restore after an exception, an anchor after the output grew, a
cleanup on a read-only call. None is a logic error inside the thing being
tested; all three are about what happens on the way out.

**Two of the five are mine, from this batch, and #5 is mine from the fix for
#1.** That is the expected rate rather than an embarrassment: a fix written
and then controlled catches its own defect in the same hour. The rate worth
watching is fixes that ship WITHOUT a control, and that number is zero here.
