# SAIRN handoff — hank b57 — 2026-10-27

**Subject:** W3 and the C1 failure path, verified on the deployed code in a Vercel Sandbox; the verification method
made standing. No code change. Written before the report, nothing half-finished.

**Methodology concept (standing from b57):** *a fail-open/fail-closed item is closed only when its failure branch
has run on the DEPLOYED code: the files at the production deployment's `githubCommitSha`, in a deny-all Vercel
Sandbox, with each file's sha256 checked inside the sandbox. A source pin or a local run is not verification.*
- Recorded in memory as `deployed-sandbox-verification-before-closing`.
- Large transfers go to a subagent so the main context is not spent on file bytes.

## 1. PUSHED STATE — NOT FORCED
- Only these three documents. Re-derive the tip after the push.
- The 404/400 decision on credentialStillActive needs no code change (Michael, b57).

## 2. CLAIMS HELD
None. No claim was taken: this batch is verification plus documents only.

## 3. THE ITEMS
**Provenance:** production deployment `dpl_67Y3hCGiPFgDcEMQxhx8TEc6JzD6` (READY), `githubCommitSha`
`ce2596cf0`, which contains `cf13093c8` (C1) and `da19dd707` (W3). The files were taken from git at that sha.

**Sandbox:** `sbx_F29RT2O0MalaOBDIGV57ixxKFDGI` (deny-all, node v24.22.1), driven by a subagent and now stopped.
All 6 sha256 values were re-hashed inside the sandbox and match: audit-checkpoint `8ee8f474`, _lib/audit
`50577749`, _lib/heartbeat `bd944e14`, _lib/auth `cedda455` (71,791 B), and both drivers.

**1. W3 — CLOSED.**
- With an unreadable 2xx on every checkpoint read, verify → **502 "Upstream error -- try again"**, logged
  "checkpoint read unreadable". It no longer answers ok:true over an unread chain.
- Control (empty lists) → 200 ok:true.

**2. C1 failure path — CLOSED.** credentialStillActive at the deployed sha:
- answered 500 / 503 / 403 / 401 → **ACTIVE_CHECK_FAILED**, status kept;
- unreadable or non-list 2xx → **ACTIVE_CHECK_UNREADABLE**;
- controls: 404 and 400 → NO_ACTIVE_CHECK (confirmed by Michael); transport throw → NO_ACTIVE_CHECK; active row →
  ok; inactive row → CREDENTIAL_INACTIVE.
- **11/11 PASS.**
- Scope, stated: this drives the FUNCTION. The two callers' 502 refusals (the sd-data pre-gate and bridge.js) are
  driven locally in the b55 suite, not in the sandbox; sd-data.js is about 1 MB.

**3. Methodology:** stated above.

Evidence:
- `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517\scratchpad\b57\sandbox_evidence.txt`
- Drivers: `...\scratchpad\b57\driver_w3.js` and `driver_c1.js`.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | owner | next step |
|---|---|---|---|
| CL | the callers' 502 on ACTIVE_CHECK_* in the deployed sd-data.js and bridge.js | hank, if Michael wants it | sandbox bridge.js (small) with auth.js; sd-data.js is about 1 MB, so it would need a subagent |
| T1 | an informal review of 45ba1d9f7, da19dd707, cf13093c8 | cc | unchanged |
| RS | 5 pre-existing red api/ suites | owners | unchanged |

All W1–W6 items and C1 are now verified on deployed code. W1 and W2 were driven in b55 at function level only,
under the same caller caveat.

## 5. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
