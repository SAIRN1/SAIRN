# SAIRN handoff — hank b54 — 2026-10-27

**Subject:** the sd-render cap decision recorded; the remaining OPEN fold guards; R1, the unrecorded lockout PATCH;
the "fails open on an unparsable 2xx" sweep. Written before the report, nothing half-finished.

**Methodology concept:** *a lockout that cannot be recorded is not a lockout, and a fail-open is only acceptable
where it is a written decision. Every fail-open either carries the decision inline or is flagged.*

## 1. PUSHED STATE — NOT FORCED, LANDED on origin/main
- `45ba1d9f7` fix(platform b54): R1 lockout (17 PIN auth files) and the two sd-data folds; sd-render comment.
- `af81fd003` docs(code): three KEEP fail-open sites commented. Comments only.
- `8b74884e9` bookkeeping: register record and derived docs.
  **No Tier A obligation:** the gate found no Tier A resource named in the diff. An informal review is
  routed to cc; see T1.
- The handoff, report and digest are pushed after this file is written. Re-derive the tip.
- No override was consumed; there is no new BYPASS-LOG row.

## 2. CLAIMS HELD
`auth-lockout` (b54) is released at the end of the batch.

## 3. THE ITEMS
**1. sd-render.js — DONE.** One inline comment records Michael's b54 KEEP (fail-open on an unparsable 2xx,
cost control). No behaviour change.

**2. "The 2 remaining OPEN guards."** Assumption, stated: the b53 sweep's two OPEN guards (dnt_providers link check,
dnt-bi token cap) were already closed in `dbbf43b6d` and are verified present at `sd-data.js:18114` and
`dnt-bi.js:452`. So I read "remaining" as the two OPEN sites the b52 sweep left, both in sd-data.js:
- the supplier lead-time fold (~3001);
- the style-profile fold (~3984).
Both now refuse 502 on a non-list prior read instead of folding onto null and wiping stats. Source pin: S2.
If you meant something else, say so; it is cheap to redo.

**3. R1 recordFailure lockout PATCH — FIXED.**
- All 17 PIN `*-auth.js` files: 11 through the shared `recordFailure` (it returns null when the attempt is
  unrecorded, and callers answer 503), 6 inline (grd, sb, sc, scp, sd, sd-sub).
- They answer **503 LOCKOUT_UNAVAILABLE** and log when the failed-attempt PATCH fails.
- `api/b54-lockout-unrecorded-refused.test.js` 6/0:
  - D1 alf-auth (helper) and D2 sd-auth (inline) are driven: PATCH 500 → 503, and the control PATCH ok → 401;
  - S1 pins all 17 files; S2 pins the item-2 folds;
  - mutants M1–M2 go red.
- Every auth suite that was green stays green.
- Residual risks, recorded in the register:
  - a 503 fires only when the row exists, so while the write path is broken it is an employee_id oracle;
  - a CORRECT PIN still logs in while the lockout cannot be written.

**4. Sweep for the sd-render shape** (a read-only agent, 69 hits): KEEP 3, WRONG 6, ALREADY-CLOSED 60.

KEEP, now with an inline decision comment (`af81fd003`):
- `_lib/ai-rate-limit.js:410`, the usage-row link (metering);
- `_lib/ai-rate-limit.js:~559`, recordAiUsage (telemetry);
- `sd-data.js:~6612`, the shared-knowledge topic counter (analytics). Its comment records that an unparsable read
  makes the upsert OVERWRITE the stored counts.

**FLAGGED as wrong, not changed** (each needs a dispatch or a decision):
| # | site | what an unparsable 2xx does | owner |
|---|---|---|---|
| W1 | `_lib/auth.js:1179` credentialStillActive | json() throws → NO_ACTIVE_CHECK; the sd-data pre-gate (:2293) and bridge.js:564 proceed on the token alone, so the **deactivation check is skipped** | hank (shared auth) |
| W2 | `claude.js:378` / `license.js:169` | licence gate in enforce mode: authState 'error' → request ALLOWED. The documented fail-open covers "unreachable" only | Michael decides |
| W3 | `audit-checkpoint.js:337` allCheckpoints | `[]` → verify ok:true, a false pass on the tamper chain | cc / hank |
| W4 | `sairndental/public-complaint-submit.js:92` | duplicate check null → a second complaint is filed | hank |
| W5 | `sairncash/trial-renew.js:178` | CAS `patched` null → 200 "renewed" with the write unconfirmed | SAIRNcash owner |
| W6 | `sd-data.js:13325/13366/13384` derive_charges MAR/ADL/activity reads | `.catch(()=>[])` and !ok skipped → billable events silently dropped (**money**) | hank |

Also noted: `alf-alerts.js:64` refuses, but with the misleading NO_WINDOW_POLICY;
`audit-checkpoint.js:320` is saved only by a unique constraint.

**5. Red suites seen** in the live clone. All are red identically at origin/main (checked with node_modules
junctioned into a scratch worktree), none from b54:
- `api/sd-data-leg-bookings-toctou`, `api/sd-data-leg-session-gate`: `sdnData` is gone from sairnlegacy.html
  (fourth b56 F3 UI). **Routed to fourth.**
- `tests/sd_data_write_attribution_three_apps`: rf_schedule attribution.
- `tests/sairnlaw_clearance_refusal_review_probe`.
- `api/sd-data-law-trusttx-clearance`, `tests/stonedesk_exec_msgs_gate`, `api/sd-data-family-contacts`,
  `tests/sairnlegacy_reservation_lock`.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | owner | next step |
|---|---|---|---|
| T1 | review of `45ba1d9f7` (auth lockout; the gate saw no Tier A name) | cc | informal review of risks (a)–(c) above |
| W1–W6 | the flagged fail-opens | as in the table | W1 and W6 first (deactivation; money) |
| L2 | fold the 6 inline lockout PATCHes into a shared helper | hank | refactor when dispatched |
| RS | the red suites above | fourth (leg), the owners | diagnose or register |
| Q2 | item 2's reading of "remaining" | Michael | confirm |
| carried | Tier A by cc on 76193dc91, 6a3755cac+29739fe14, 8e617d197+dbbf43b6d; fourth D-SD stonedesk.html:27173 | cc / fourth | unchanged |

## 5. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
