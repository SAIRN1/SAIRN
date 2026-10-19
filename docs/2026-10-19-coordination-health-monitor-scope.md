# A live coordination-health monitor across the six-agent swarm — SCOPE ONLY

**cc, b21 item 4, 2026-10-19. NOTHING IS BUILT. No file in `tools/` was added
or changed for this item.** This is the design and the measurements that have
to exist before any threshold in it is allowed to be a number in code.

**The one-line concept:** *one read-only command that answers "is the swarm
coordinating right now" from sources no agent self-reports into, reporting
three named conditions — a board that stopped being written, a claim outliving
the session that holds it, a window near its ceiling — each with a measured
threshold and a COULD-NOT-TELL state, and it never fixes anything.*

---

## 1. Why this is not already answered

Seven tools each answer a piece and none answers the question. Measured by
reading them, 2026-10-19:

| tool | what it already answers | what it does not |
|---|---|---|
| `sairn_status.py` | each agent's own state, live, outside git | nothing cross-agent; every field is a self-report |
| `sairn_board_publish.py` | renders and publishes the board to Drive | whether anyone is reading it, or whether a row went quiet |
| `status_board_bridge_check.py` | does the registry actually REACH the board | nothing about the registry's own freshness or agreement with claims |
| `sairn_claim.py` | who holds what, 4h expiry | whether the holder still exists |
| `clone_health_check.py` | is THIS clone sick | the other five |
| `dispatch_state.py --reconcile` | per-agent disagreement across git/registry/claims | runs per agent, on a weekly practice, not as one live read |
| `context_verify.py` | real context% per build agent | nothing about what a high figure means for the swarm |

The gap is not a missing measurement. It is that **no single read puts them
beside each other**, so a disagreement between two sources is only ever found
by a human comparing two command outputs. `dispatch_state.py --reconcile` is
the closest existing thing and is the right thing to compose with rather than
replace.

## 2. The three conditions

Each is one arm. Each has a source, a threshold, and a third state.

**C1 — A BOARD ROW THAT STOPPED BEING WRITTEN.** Source: mtime of each
`~/SAIRN-SESSION-LOCKS/status/<agent>.json`, plus the Drive board's own
published-at stamp. A row whose mtime is older than its agent's claim is still
active says the agent stopped reporting while still holding work — which is
exactly the state a reader of the board cannot distinguish from "quietly
working".
*Measured now, as the anchor:* mtime ages 0.11h, 0.14h, 0.27h, 0.37h, 0.48h,
1.25h across the six. **That is a single snapshot and is NOT a threshold.**

**C2 — A CLAIM OUTLIVING ITS SESSION.** Source: `.claude/claims/*.json` for
the claim, the registry's `claude_pid` + `claude_start` for whether that
session still exists. `sairn_status.py` already prints "CLAUDE_PID 13728 no
longer exists"; nothing joins that to the claim the dead session still holds.
A claim held by a dead PID blocks live work for up to the 4h expiry and reads
identically to a claim held by somebody typing.

**C3 — A WINDOW NEAR ITS CEILING.** Source: `context_verify.py` for the four
build agents. The question is not the percentage, it is *an agent above its
own threshold while holding a claim and with no handoff written* — which is
the shape in which a batch is lost. **The hover clones are out of this arm by
the separation boundary**, the same boundary that keeps `context_verify.py`
out of their project folders; their registry rows and claims ARE in C1 and C2,
because they write those themselves.

## 3. What has to be measured before any threshold is written down

This is the part that makes it a design rather than a guess, and it is
discipline 1 (lock criteria against fixtures before running on real data) and
discipline 4 (set the alarm tighter than the failure point):

1. **The real quiet-interval distribution per agent.** C1 needs the
   distribution of gaps between consecutive registry writes over at least a
   week, per agent, not one snapshot. A threshold set from today's six numbers
   would fire on hank, whose 1.25h gap is almost certainly normal.
2. **How often a PID outlives its agent and vice versa.** C2's false-positive
   cost is accusing a live session of being dead. The PID check is a proxy and
   `sairn_status.py` already knows it.
3. **The context figure at which a batch actually got lost.** C3's threshold
   must come from real lost batches, not from a round number. b20's four
   figures (68.8, 66.3, 60.0, 70.3) are the only data and none of those
   sessions was lost, so **the threshold is currently unmeasurable and C3 must
   ship REPORT-ONLY until it is not.**

## 4. The contract

- **Read-only, and that is structural.** It may PROPOSE nothing and apply
  nothing (discipline 11: a detector that blesses its own fix is the problem
  one step later). No `set`, no claim release, no board write.
- **Exit 0 clean / 1 finding / 2 COULD NOT RUN**, per `checker_kit.py`.
- **An empty or unreadable source is COULD NOT RUN for that arm, named,
  never folded into clean** (PR §1.11). An empty registry is indistinguishable
  from one nothing writes to — `sairn_status.py` already says so and this must
  say the same thing rather than reporting all-clear.
- **Fixtures first, in both directions, before any real read**, with an
  ablation per arm: remove C1 alone on a clean swarm and measure what it and
  only it catches (discipline 12), per arm and not per exit code.
- **Not a push gate.** It describes a condition between agents, not a property
  of a diff; a gate on it would refuse a correct push because somebody else
  went quiet.

## 5. What it will not catch, stated now rather than discovered later

- An agent that reports a state truthfully and is doing the wrong work. Every
  arm here is about agreement between sources, not about correctness.
- Two agents doing the same work under non-overlapping claim strings. That is
  the claim matcher's problem and it is already measured at 153 lexical blocks
  / 43 real.
- A source that is fresh and wrong. **Measured today:** cc's registry row
  carried `context_pct 69.6` while the real figure was 19.3% — a fresh row,
  honestly written, four hours out of date, and no arm above would notice.
  That is the b20/b21 defect and it is closed at the digest instead.

## 6. Cost, honestly

Four to six hours for the tool plus its fixtures, and it cannot start until
measurement 1 above has a week of data. The cheap half — C1 and C2, which need
only the registry and the claims — is roughly a third of that and would land
first. **Nothing here is claimed as started.**
