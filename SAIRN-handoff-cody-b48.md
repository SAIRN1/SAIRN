# SAIRN handoff — cody b48 (2026-10-22)

Six items. Items 1, 2 and 5 are done and landed; items 3 and 4 were denied by the harness and need Michael.
Nothing is half-finished.

## Committed / pushed state
On origin/main, no force, via `push_retry.py --loop` (it landed on attempt 3; attempts 1–2 were transient races):
- `c53c75c1b` fix(sd-agent): the last catch no longer relays `err.message` (hover H1 #1684).
- `d6b37bb1c` feat(sairnlegacy): F3's apprentice prepare route reaches the countersignature lock.
- `3ba30b465` register record for the #1684 fix (`stonedesk`, `moderate`, `hover-audit`, found by hover).
- `f260e873d` Tier A review obligation for the F3 deferral, assigned to **cc**.
- Claims: b48 `platform` claimed in `ad85814d8`; the b47 `platform` claim was released (`6cc30fa29`).
- Register: my record cites `c53c75c1b` (re-seated by the loop). `--reseat` reports one COLLISION that is not mine:
  `f9a4e5a0032b` vs `5bb0950a51b6`, the same 2026-10-13 audit-checkpoint fix before and after a rebase. Left for a human.
- The path manifest's cody override for b48 replaces b47's. It names four api/ files: sd-agent.js, sd-data.js and the two b48 tests.
- Transcript: `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\2d1bcf76-c842-40ed-b21d-9b20d98e7d45.jsonl`

## Item 1 — #1684, `api/sd-agent.js:351`
**Concept:** the last catch never relays error text to the caller.
On that path, `err.message` is either Anthropic's own error body (callClaude's UPSTREAM throw) or an internal
exception. It is still logged, and the caller now gets the fixed sentence. The status is unchanged.
**Test:** `api/b48-sd-agent-error-leak.test.js` passes 3/3.
- Arm A: an upstream 400 with a message.
- Arm B: a fetch that throws.
- Arm X: an ablation that restores the old line and requires arm A's check to fail on it.

`sd-agent-budget` passes 7/7.

## Item 2 — "wire funeral F2/F3 into sd-data.js"
**What was already wired, verified at HEAD:**
- F2 was already wired: `decide(resource, role, action, legGrants, legHome)` at the leg role gate, with the settings read from
  `sairnlegacy_settings` (b27/b29).
- The owner write path is hank b45–b47.

**What was built but unusable:** F3's countersign route.
- `decide(..., 'prepare', grants, home)` allowed it.
- `api/leg-countersign.js` lets an apprentice prepare and a director sign.
- But the role gate's 403 refused the apprentice's WRITE before the leg_cremations lock ran, so a signed record
  could never be filed.

**Fix:** law C2's two-stage deferral. A write is deferred only when all three hold:
1. The verb is not read.
2. The resource carries the lock.
3. `decide(prepare)` with this home's settings ALLOWs it.

The lock is MODE_ALWAYS, so an unsigned, self-signed, spent or mismatched write is still refused.
I replaced the stale comment above the lock, which said "nothing stores it".

**Test:** `api/b48-leg-f3-prepare-deferral.test.js` passes 8/8.
- A signed write files.
- An unsigned write gets COUNTERSIGN_REQUIRED.
- These all get FORBIDDEN, with the token never read: no list, `forbidden`, an unlocked resource, another role.
- A self-signed write gets 409.
- Ablation X turns the filed arm into a 403.

**Regressions:** all green: b27 18/0, b22 23/0, b29 21/0, b45 32/0, b18 59/0, leg-role-matrix, b17, leg-overlap 36/0.
`tests/sairnlegacy_reservation_lock.js` fails 35/36, and that result is **identical at HEAD in a worktree**. It is pre-existing: hank b45 routed it as R1 to cody.

## Items 3 and 4 — DENIED by the harness, not retried
- `rm push_retry_last_refusal.txt`: denied. Per your note, run it from a plain CMD window.
- `npm ci --ignore-scripts --no-audit --no-fund`: denied, both in a compound command and as the exact command alone.
  **Measured:** none of b48's files are in 5f's scope. `dependency_integrity_check.py --paths api/sd-agent.js
  api/sd-data.js` reports "none of the four manifests", exit 0. So this batch's push was not affected. The install is still owed for a
  future SDK-touching push.

## Item 5 — push and landed
All four commits are ancestors of origin/main, checked with `git merge-base --is-ancestor` after a fetch.
**Live:** both endpoints are deployed and gated on https://sairn.vercel.app:
- sd-agent with no licence: 401 NO_LICENSE.
- sd-data leg_cremations write with licence LEG-PINNACLE-2026 and no session: 401 NO_SESSION.

**Not live-verified:** neither fixed path was driven. That needs an induced Anthropic error, and an apprentice session plus a
director-signed token.

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | the stray `push_retry_last_refusal.txt` at the clone root | Michael: delete it from a plain CMD window |
| O2 | `npm ci` in this clone | Michael: `! npm ci --ignore-scripts --no-audit --no-fund` in SAIRN-cody |
| O3 | Tier A review of `d6b37bb1c` (assigned cc) | cc: discharge it via `tools/tier_a_review_gate.py` |
| O4 | F3 live: apprentice prepare → director sign → apprentice file | whoever has a SAIRNlegacy apprentice and director session |
| O5 | presence_disclosure text is not shown on apprentice-entered records | fourth (sairnlegacy.html); the string is `LEG_APPRENTICE_PRESENCE_DISCLOSURE` |
| O6 | `tests/sairnlegacy_reservation_lock.js` 35/36 no-id arm (hank b45 R1) | cody, if dispatched |
| O7 | `.claude/settings.local.json.bak-cc-b48` appeared untracked in this clone; not mine, not touched | Michael / cc |
| O8 | `api/b27-leg-settings.test.js` section V still says the prepare route is routed. The verb is still undeclared (true), but the route now works without it | cody, if dispatched: reword V's comment |

Claim held: `platform` (b48). Release it at the start of the next batch.
