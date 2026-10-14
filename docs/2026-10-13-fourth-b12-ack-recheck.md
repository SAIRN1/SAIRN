# RE-CHECK at current origin/main - the routed findings and the 36 undriven suites - 2026-10-13, fourth b12

**NEITHER COUNT MOVED, AND THAT IS MEASURED RATHER THAN SHRUGGED AT.** 27
commits landed on `origin/main` between b11 and this re-check and none of
them touched any subject either check reads. The commands are below; so is
the evidence that the absence of change is real and not a stale read.

**RE-MEASURED 2026-10-14** against `origin/main` at `90fa5e98`. The first
pass of this re-check ran against a 19-commit window; eight more commits
landed while the batch was open, so every figure below was driven again
rather than carried over. The counts are the same and the window is not.

---

## ITEM 4 - routed-finding acknowledgement, re-run

    CMD python scratchpad/ack_check.py        ->  exit 1

```
ROUTED-FINDING ACKNOWLEDGEMENT -- derived from the routing documents
  routing documents read     : 4
  file:line findings in scope: 9
  EXCLUDED, no line number:                        109 token(s), 98 distinct
  EXCLUDED, not on disk (illustrative or proposed): 2 token(s), 2 distinct
      ~ tools/bar_gate.py:140
      ~ tools/foo_gate.py:88

b    owner     file                                                 line   state        evidence
b10  cc        tools/hover_auditor_scope_gate.py                    409    MENTION_ONLY hover_auditor_scope_gate.py appears in NOT_PROMOTED prose but NOT about line 409 -- not an a
b9   cc        tools/session_lock_check.py                          128    MENTION_ONLY session_lock_check.py appears in NOT_PROMOTED prose but NOT about line 128 -- not an acknowl
b9   cody      tests/faults/grd_write_faults.js                     385    UNACK        no commit, claim, status row or NOT_PROMOTED entry
b9   cody      tests/push_gate/check8_probe.py                      209    UNACK        no commit, claim, status row or NOT_PROMOTED entry
b9   cody      tests/sairnlegacy_session_gate_review_probe.js       202    UNACK        no commit, claim, status row or NOT_PROMOTED entry
b9   cody      tests/seed_never_syncs_platform.js                   274    UNACK        no commit, claim, status row or NOT_PROMOTED entry
b9   cc        tools/register_feed_gate.py                          747    ACK_COMMIT   1 commit(s) since the routing, newest: ac9d47d8 fix(register feed gate): the UNREADABLE OUTG
b9   cc        tools/sairn_claim.py                                 1281   ACK_STATUS   cc status row names sairn_claim.py
b9   cc        tools/sairn_claim.py                                 1966   ACK_STATUS   cc status row names sairn_claim.py

BY STATE: {'UNACK': 4, 'MENTION_ONLY': 2, 'ACK_COMMIT': 1, 'ACK_STATUS': 2}
UNACKNOWLEDGED (UNACK + MENTION_ONLY): 6
  ! b9   cody      tests/faults/grd_write_faults.js:385  [UNACK]
  ! b9   cody      tests/push_gate/check8_probe.py:209  [UNACK]
  ! b9   cody      tests/sairnlegacy_session_gate_review_probe.js:202  [UNACK]
  ! b9   cody      tests/seed_never_syncs_platform.js:274  [UNACK]
  ! b10  cc        tools/hover_auditor_scope_gate.py:409  [MENTION_ONLY]
  ! b9   cc        tools/session_lock_check.py:128  [MENTION_ONLY]
```

| | b11 | b12 | moved? |
|---|---:|---:|---|
| findings in scope | 9 | 9 | no |
| UNACK | 4 | 4 | no |
| MENTION_ONLY | 2 | 2 | no |
| acknowledged | 3 | 3 | no |
| **unacknowledged total** | **6** | **6** | **no** |

**cody 4, cc 2, hank 0** - unchanged from b11.

---

## ITEM 5 - the 36-undriven-suites document, regenerated

    CMD python scratchpad/gen_undriven_doc.py        ->  exit 0

```
wrote docs/2026-10-13-fourth-b10-undriven-suites.md
undriven rows        : 36
list/TSV cross-check : IDENTICAL (36 names)
by owner             : {'hank': 5, 'cody': 79}
undriven by owner    : {'cody': 36}
driven b9 states     : {'RED': 43, 'COULD NOT RUN': 5}
entries with no why  : 21
```

**The regenerated file is byte-identical to the committed one:**

    CMD git diff --stat -- docs/2026-10-13-fourth-b10-undriven-suites.md
    (no output)

That is the generator doing its job rather than a skipped step: it re-read
its three inputs, re-asserted that the list and the TSV name the same 36
suites, and produced the same page. **A generator that refuses to write when
its inputs disagree also proves something when it writes the same bytes.**

---

## WHY NEITHER MOVED - the measurement, not an inference

```
CMD git rev-parse --short=8 origin/main
90fa5e98
CMD git rev-list --count 29f27993..origin/main   (commits landed since fourth b11's report)
27
CMD git log --format=%h origin/main --not 29f27993 -- <the 4 tests-owner routed files> <the 2 tools-owner routed files>
  (empty above = none of the six routed files was touched)
CMD git log --format='%h %s' origin/main --not 29f27993 -- tools/report_only_checks.py
  (empty above = no NOT_PROMOTED decision landed)
CMD git log --format=%h origin/main --not 29f27993 -- docs/known-red-suites.json docs/2026-10-13-fourth-b10-red-suite-owners.tsv
  (empty above = neither the red-suite register nor the owner TSV was touched)
```

**AND THE ONE THING THAT WOULD HAVE MOVED ITEM 5 IS A CLAIM, NOT A RESULT.**
The tests owner's latest push `433860be` declares
`docs/2026-10-13-cody-b8-undriven-suite-results.md` and *"first 12 undriven
suites from fourth b10"* in its claim text — and carries **one file**:

```
CMD git show --stat --format='%h %s' 433860be | tail -2
 .claude/claims/cody.json | 22 ++++++++++++++++++++++
 1 file changed, 22 insertions(+)
CMD git cat-file -e origin/main:docs/2026-10-13-cody-b8-undriven-suite-results.md
exit 128   (nonzero = that results document is NOT on origin/main)
CMD git log -1 --format='%h %cI' origin/main -- docs/known-red-suites.json
5bb0950a 2026-10-13T16:33:58-04:00
```

So the 36 is **not** a stale figure read before the owner's work landed: the
work is claimed and in flight, and the register it would move was last
touched before b11's own measurement. **A claim is not a result, and this is
the distinction a count that names its command is for** — "regenerated after
the tests owner's latest push" is true, and that push contains no results.

So the six routed findings are unacknowledged because **nothing happened to
them**, not because the checker is looking in the wrong place: the four
signals it reads are a commit on the file, an active claim naming it, the
owner status row, and a `NOT_PROMOTED` entry naming the file and the line -
and `tools/report_only_checks.py`, where a decline would land, has not been
touched either.

## WHAT THIS RE-CHECK CANNOT SAY

**It cannot distinguish an owner who read the routing and chose to do nothing
from one who never saw it.** That needs a reply channel this platform does
not have, which is the whole reason `docs/by-design-register.json` exists and
the reason its one row is at `DECIDE_OR_NOT_PROMOTED` - a state an owner can
answer in one token. The validator that would make that register checkable is
specified in `docs/2026-10-13-fourth-b12-routed-to-cc-bydesign-validator.md`
and is built by nobody.
