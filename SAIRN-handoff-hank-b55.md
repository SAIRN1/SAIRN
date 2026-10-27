# SAIRN handoff — hank b55 — 2026-10-27

**Subject:** W2 (Michael's decision: fail closed) and W1, W3–W6, the six WRONG fail-opens from the b54 sweep, all
closed; the b54 item-2 assumption stated exactly. Written before the report, nothing half-finished.

**Methodology concept:** *the store answered and the answer cannot be read, so the protected thing is refused.
An unreadable 2xx is never "no row", never "empty", and never the transport blip a fail-open was written for.*

## 1. PUSHED STATE — NOT FORCED, LANDED on origin/main
- `da19dd707` fix(platform b55): all six sites, plus `api/b55-unreadable-fails-closed.test.js`.
- `86797a9fb` bookkeeping: register record and derived docs. **No Tier A obligation:** the gate found no Tier A
  resource named on a changed line.
- The handoff, report and digest are pushed after this file is written. Re-derive the tip.
- No override was consumed.

## 2. CLAIMS HELD
`fail-closed-w` (b55) is released at the end of the batch.

## 3. THE ITEMS
| # | site | before | now |
|---|---|---|---|
| W2 | `_lib/license.js` lookup + `claude.js` | an unparsable licence body threw a SyntaxError; claude.js caught it as "error" and ALLOWED the call | license.js throws `code: UPSTREAM, unparsable: true`; claude.js answers **502 LICENCE_UNREADABLE in every mode**, logged. A store that is *unreachable* still fails open, as documented |
| W1 | `_lib/auth.js` credentialStillActive | an unparsable 2xx fell into the transport catch → NO_ACTIVE_CHECK → both callers proceeded on the token alone | **ACTIVE_CHECK_UNREADABLE**; the sd-data pre-gate and bridge.js refuse it 502. A transport throw is still NO_ACTIVE_CHECK |
| W6 | `sd-data.js` derive_charges MAR / ADL / activity reads | `.catch(()=>[])` and !ok skipped → billable events silently dropped | **502 READ_FAILED** on !ok (except 404/400) and on a non-list body, matching the rate-card read |
| W3 | `audit-checkpoint.js` lastCheckpoint / earliestRow / allCheckpoints | a non-list body became `[]`/null, so verify answered ok:true | they **throw**, so verify cannot pass over an unread chain |
| W4 | `sairndental/public-complaint-submit.js` duplicate check | an unreadable 2xx filed a second complaint | **503 UNAVAILABLE**, like its !ok branch |
| W5 | `sairncash/trial-renew.js` CAS | an unreadable answer → 200 "renewed" | **502 RENEWAL_UNCONFIRMED** |

Tests:
- `api/b55-unreadable-fails-closed.test.js` 11/0.
  - W1 and W2 are DRIVEN with controls, and mutants M1–M2 go red.
  - W1c, W2b and W3–W6 are SOURCE pins.
- Full `api/` run: 5 red suites, each red identically at origin/main —
  - `_lib/law-trust-reconcile-endpoint` (10/2),
  - `sd-data-family-contacts`,
  - `sd-data-law-trusttx-clearance`,
  - `sd-data-leg-bookings-toctou`,
  - `sd-data-leg-session-gate`.

**Item 5: the b54 item-2 assumption, stated exactly.**
- Your b54 item 2 said "Close the 2 remaining OPEN guards from your b53 67-guard sweep."
- That sweep had exactly 2 OPEN, and **both were already closed in b53**, commit `dbbf43b6d`:
  - `api/sd-data.js` dnt_providers one-login-one-provider check, now 503 PROVIDER_CHECK_UNAVAILABLE;
  - `api/dnt-bi.js` feed-token cap, now 503 TOKEN_COUNT_UNAVAILABLE.
- So there was nothing left to close from that sweep. **I assumed you meant the 2 sites still OPEN from the b52
  63-site sweep**: the two non-Tier-A row-or-null folds in `api/sd-data.js` that b52 had listed as OPEN and
  unfixed. They are:
  - the supplier lead-time observe fold, `sd_supplier_lead_times`, ~line 3001;
  - the style-profile fold, `sairn_style_profiles`, ~line 3984.
  Both read the prior row, then fold onto it and upsert. On an unparsable/non-list body they folded onto null
  and wiped the accumulated stats.
- In b54, commit `45ba1d9f7`, both now refuse **502 UNREADABLE_PRIOR** on a non-list prior read.
- To confirm: (a) the b53 pair needed nothing (already closed); (b) the b52 pair was the intended target.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | owner | next step |
|---|---|---|---|
| Q5 | confirm item 5's assumption | Michael | yes/no |
| T1 | an informal review of `45ba1d9f7` (b54 lockout) and `da19dd707` (b55); the gate opened no obligation for either | cc | attack: (a) license.js now throws UPSTREAM to every validateLicenseKey caller on a non-list body; (b) LICENCE_UNREADABLE refused in observe mode while an invalid key is allowed there; (c) the pre-gate 502 fires before app scoping |
| C1 | credentialStillActive still answers NO_ACTIVE_CHECK on an answered !ok (4xx/5xx), by its documented availability decision | Michael | decide whether !ok should refuse like an unreadable 2xx |
| L2 | fold the 6 inline lockout PATCHes into a shared helper | hank | when dispatched |
| RS | the 5 api/ red suites above, plus tests/ ones | owners (law, leg = fourth) | diagnose or register |
| S3 | a static detector for these shapes | cc | still routed |

fourth b58 closed D-SD (vendor qty).

## 5. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
