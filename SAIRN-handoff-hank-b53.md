# SAIRN handoff — hank b53 — 2026-10-22

**Subject:** soft-delete guards fail closed on an unreadable read (Michael's b53 decision), plus the sweep for the
"skip the check on an unreadable read" shape. Written before the report, nothing half-finished.

**Methodology concept:** *a guard that cannot read its subject has not checked it. It refuses, and only a readable
answer ("no row", "not deleted", or 404/400 = not provisioned) lets the protected action proceed.*

## 1. PUSHED STATE — NOT FORCED, LANDED
- `8e617d197` fix: the sd_customers single-row guard and the SAIRNcode soft-delete-only guard → 502 UNREADABLE_PRIOR.
- `dbbf43b6d` fix: the sweep —
  - write_batch tombstones → 502;
  - dnt_providers one-login check → 503;
  - dnt-bi token cap → 503;
  - sd-sub-data compliance gate → 503 except 400/404.
- `efde99fea` bookkeeping: register records, Tier A obligation (assigned to cc), derived docs.
- The handoff, report and digest are pushed after this file is written. Re-derive the tip.
- No override was consumed. The retry script pre-granted the scoped external-files skip, and no new
  BYPASS-LOG row was written.

## 2. CLAIMS HELD
`soft-delete-guard` (b53) is released at the end of the batch.

## 3. THE ITEMS
**1. sd-data.js 4946 / 20236 — FIXED (`8e617d197`).**
- A 4xx/5xx or non-list pre-read → 502 UNREADABLE_PRIOR, nothing written.
- 404/400 still falls through to the upsert's NOT_PROVISIONED; there is no row to resurrect.
- `api/b53-soft-delete-guard-fail-closed.test.js`: C1–C2 and S1–S2 are driven, with controls for deleted → 409,
  live/no row → written, and 404 → not this refusal. Mutants M1–M4 red.
- `api/sd-data-tombstone-propagation.test.js` re-anchored on the guard banner instead of a fixed char window: 13/0.

**2. Sweep (methodology).** 67 candidate guards: OPEN 2, CLOSED 60, INTENTIONAL-DOCUMENTED 5. Fixed in `dbbf43b6d`:
- the **write_batch** tombstone pre-read. It was documented as a fall-through using the same argument item 1
  reversed, so it now matches;
- the **dnt_providers** one-login-one-provider check (OPEN, Tier A), following the coverage-rules precedent;
- the **dnt-bi** feed-token cap (OPEN);
- the **sd-sub-data** COI/licence gate, narrowed to its documented 400/404 case.

Tests:
- `api/sd-data-customers-batch.test.js`: the arm that pinned the old fall-through now expects 502 (15/15).
- b53 suite 12/0; P1–P4 are SOURCE pins.

Left in place as documented cost/availability decisions (not Tier A):
- `_lib/ai-rate-limit.js`;
- `claude.js`, licence fail-open;
- `sd-render.js` cap. Its comment says only "never got a response", but an unparsable 2xx also fails open.

**3. Push:** landed, as above.

Red suites seen, both failing identically at origin/main and neither registered:
- `api/sd-data-law-trusttx-clearance.test.js` (8 FAIL lines);
- `tests/stonedesk_exec_msgs_gate.js` (9/4).

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | owner | next step |
|---|---|---|---|
| T1 | Tier A on `8e617d197` + `dbbf43b6d` | cc | review points (a)–(c) in the obligation |
| R1 | `recordFailure()` in 11 `*-auth` files never checks its failed_attempts/locked_until PATCH, so lockout may never engage | hank, if dispatched | check the PATCH result; refuse the login if the lockout cannot be recorded |
| R2 | `sd-render.js:228`: an unparsable 2xx fails the cap open, which is wider than its comment | hank / Michael | narrow it to a transport failure, or fix the comment |
| R3 | DNT drivers for P1–P3 (currently source pins) | hank | add driven arms |
| R4 | the trusttx-clearance and exec_msgs suites are red and unregistered | owners (law / stonedesk) | diagnose, or register in known-red-suites.json |
| R5 | carried from b52: fourth's D-SD stonedesk.html:27173; the b48/G2 gaps; the cc static detector | as in the b52 handoff | unchanged |

## 5. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
