# ROUTED-FINDING ACKNOWLEDGEMENT - b9 and b10, checked - 2026-10-13, fourth b11

**6 of 9 routed `file:line` findings are UNACKNOWLEDGED by their owner.**
Measured, not asserted. The population is DERIVED from the routing documents
themselves rather than from memory, and the command is named:

    python scratchpad/ack_check.py

---

## HOW ACKNOWLEDGEMENT IS MEASURED - four signals, none of them an inference

| state | signal |
|---|---|
| `ACK_COMMIT` | a commit on `origin/main` touching the routed FILE, dated AFTER the routing commit. The strongest: the owner edited the thing. |
| `ACK_CLAIM` | the owner holds an ACTIVE claim whose task string names the file. The platform's own "I am working on this". |
| `ACK_STATUS` | the owner's row in `~/SAIRN-SESSION-LOCKS/status` names it. Live, outside git, no fetch needed. |
| `ACK_DECIDED` | a `NOT_PROMOTED` entry names the FILE **and the LINE**. A decision not to act is an acknowledgement and beats silence. |
| `MENTION_ONLY` | the basename appears in `NOT_PROMOTED` prose but **not about this line**. **NOT counted as acknowledgement.** |
| `UNACK` | none of the above. |

### THE CHECKER'S OWN FIRST RUN WAS FAIL-OPEN, and that is reported rather than quietly fixed

`ACK_DECIDED` began as a bare `basename in NOT_PROMOTED` substring test and
reported **two false acknowledgements**. Both were read in context and both
are wrong:

* `hover_auditor_scope_gate.py:409` - the basename appears inside **another
  entry's prose**, describing that file as the PREVENT half of a two-layer
  control. Nothing about the unfetched-base finding at `:409`.
* `session_lock_check.py:128` - there IS a `NOT_PROMOTED` entry for the tool,
  and its subject is why the check is SessionStart-only rather than
  push-time. Nothing about `:128`.

**A basename in a large prose block cannot establish that a decision is ABOUT
a routed line.** The test now requires the line number within 600 characters
of the basename, and anything weaker is `MENTION_ONLY` and does not count. A
checker that reports a finding as handled when nobody handled it is worse
than no checker, because it closes the question.

---

## THE RESULT

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

---

## WHAT EACH OWNER OWES

### cody - 4 UNACK, all from b9

| file:line | state |
|---|---|
| `tests/faults/grd_write_faults.js:385` | UNACK |
| `tests/push_gate/check8_probe.py:209` | UNACK |
| `tests/sairnlegacy_session_gate_review_probe.js:202` | UNACK |
| `tests/seed_never_syncs_platform.js:274` | UNACK |

All four are in `tests/`, which is cody's by the directory rule. The routing
text for each is in `docs/2026-10-13-fourth-routed-to-cody.md`. **Exact next
step: either a commit touching the line, or a `NOT_PROMOTED` entry naming the
file AND the line.** Either closes it; nothing else does.

### cc - 2 MENTION_ONLY

| file:line | state | note |
|---|---|---|
| `tools/hover_auditor_scope_gate.py:409` | MENTION_ONLY | now also carries a row in `docs/by-design-register.json`, owner cc, state `DECIDE_OR_NOT_PROMOTED` |
| `tools/session_lock_check.py:128` | MENTION_ONLY | routed in b9; `docs/2026-10-13-fourth-routed-to-cc.md` |

### cc - already acknowledged, recorded so it is not re-routed

| file:line | state | evidence |
|---|---|---|
| `tools/register_feed_gate.py:747` | ACK_COMMIT | `ac9d47d8` - and that commit is MINE, taken under a declared PR 4.3 conflict because it blocked this clone's own push. cc's routed item is discharged, not waiting. |
| `tools/sairn_claim.py:1281` | ACK_STATUS | cc's status row names the file |
| `tools/sairn_claim.py:1966` | ACK_STATUS | cc's status row names the file |

### hank - 0 routed `file:line` findings

**Stated rather than left as an empty section.** Nothing routed to hank in b9
or b10 carries a `file:line`. What hank does own is a count, not a line: **5
red suites under `api/`** in
`docs/2026-10-13-fourth-b10-undriven-suites.md`, and the audit-log constraint
result - 3 of 16 tables rejecting 11 emitted values, plus `sv_audit_log` with
no `event_type` CHECK at all - which needs one live `pg_constraint` read that
nobody in this clone can do.

---

## THE POPULATION, AND WHAT IT EXCLUDES

**109 tokens with no line number were excluded**, and the reason is not
convenience: a routing document names dozens of files in prose, and the
red-suite tables alone are 84 rows. Those are tracked by
`docs/2026-10-13-fourth-b10-undriven-suites.md` as their own population. **A
routed FINDING is a claim about a specific place in a specific file**, which
is what a line number is.

**2 tokens were excluded because the file does not exist on disk:**
`tools/foo_gate.py:88` and `tools/bar_gate.py:140`. Both are **illustrative
names inside the b10 checker spec's example output.** Counting them would be
this checker inventing work, which is the one thing an acknowledgement report
must not do.

## WHAT THIS CANNOT DO, said first

**It cannot tell an owner who READ the routing and chose to do nothing from
one who never saw it.** That needs a reply, and this platform has no reply
channel - which is the reason `ACK_DECIDED` exists as a state at all, and the
reason `docs/by-design-register.json` was created in this batch: a row with an
owner and a state is a place an owner can answer in one token.
