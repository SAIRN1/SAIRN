# SAIRN handoff — hank b56 — 2026-10-27

**Subject:** credentialStillActive also refuses an answered 4xx/5xx; W3/W4/W5 verified against the deployed code.
Written before the report, nothing half-finished.

**Methodology concept (item 5, standing from b56):** *an item whose failure path is checked only by a source pin
is not closed. The deployed-behaviour check runs in the SAME batch as the fix. Where the failure path cannot be
reached on the live API, the deployed code is driven in an isolated sandbox, and the item stays OPEN for whatever
was not driven.*

## 1. PUSHED STATE — NOT FORCED, LANDED on origin/main
- `cf13093c8` fix(platform b56): ACTIVE_CHECK_FAILED, plus the test changes.
- `8632435a8` bookkeeping: register record and derived docs. The gate found no Tier A name, so there is no
  obligation.
- The handoff, report and digest are pushed after this file is written. Re-derive the tip.
- No override was used.

## 2. CLAIMS HELD
`active-check` (b56) is released at the end of the batch.

## 3. THE ITEMS
**1. credentialStillActive — DONE.**
- An answered non-OK response → `ACTIVE_CHECK_FAILED` (with its status). The sd-data pre-gate and bridge.js
  refuse it 502.
- **One stated exception: 404/400 stays `NO_ACTIVE_CHECK`.** That is PostgREST's not-provisioned answer, the same
  exception every b52–b55 guard keeps. Without it, every suite whose mock answers an unmocked employee_auth read
  with 404 went red. **Michael: confirm or overrule.**
- Tests:
  - b55 suite 13/0. W1d drives answered 500/503/403/401 distinctly from W1a (the unreadable 2xx); W1b adds the
    404/400 control; mutant M3 goes red.
  - Three arms that pinned the old "continue" behaviour were reversed: auth.test.js (61/0), b36 T1 (9/0), and
    b28 R4, which now accepts either fail-closed refusal (15/0).
- Full api/ run: only the 5 suites already red at origin/main.
- **Live: UNVERIFIED.** The failure path needs the auth table to answer a 4xx/5xx, which no outside caller can
  cause. It is OPEN under item 5; next step under C1L below.

**2–4. W3 / W4 / W5, verified against the deployed code** (Michael chose option 1: run the deployed code in a
sandbox).
- **Provenance:** production deployment `dpl_6D5AiVWxSdGQz6VyxFvy27xnv8AK` (READY), githubCommitSha
  `d5362736c`. The files were taken from git at that sha; the blobs are identical at the new tip `8632435a8`.
  Vercel serves no file tree for git deployments, so the sha is the provenance.
- **Vercel Sandbox** `sbx_9VJ56PtnuszULpNusAI6AG9FZm1G` (node v24, network deny-all, stopped). The sha256 of
  every shipped file was checked INSIDE the sandbox and matches.
- Results with a stub upstream answering a 2xx with an unreadable body:
  - **W4** → **503 UNAVAILABLE**, logged "refusing rather than filing unchecked". Control (no duplicate) → 200.
  - **W5** → **502 RENEWAL_UNCONFIRMED**, logged. Controls: CAS lost → 409 CONCURRENT_RENEWAL; CAS won → 200.
- **W3 was NOT run in the sandbox.** audit-checkpoint plus its deps is 54 KB, and shipping it would have pushed
  this session past its context budget. The identical deployed-sha files were run locally with the same stub:
  unreadable 2xx → 502; control → 200 ok:true. **W3 stays OPEN for the sandbox run.**
- **Live reachable paths** on sairn.vercel.app; none of these requests writes anything:
  - W3: no auth → 401; wrong bearer → 401.
  - W4: `{slug}` only → 400 "slug and message are required".
  - W5: no auth → 401; wrong bearer → 401.
- Evidence files:
  - `C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517\scratchpad\b56\sandbox_evidence.txt`
  - `...\scratchpad\b56\live_reach.json`
  - `...\scratchpad\b56\sbx\driver.js`

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | owner | next step |
|---|---|---|---|
| C1X | the 404/400 exception in credentialStillActive | Michael | confirm, or say refuse 404/400 too (then update the ~20 suites whose mocks answer 404) |
| C1L | C1's failure path on deployed code | hank | sandbox run of `_lib/auth.js` at the deployed sha with an employee_auth stub answering 500 (the auth.js closure is small) |
| W3S | W3 in the sandbox | hank, a fresh session | ship the 3 files (54 KB) with the b56 writer pattern (`run_session_command` with wait:false); expect 502 and control 200 |
| T1 | an informal review of 45ba1d9f7, da19dd707, cf13093c8 (no Tier A obligation opened) | cc | as routed in b55 |
| RS | 5 pre-existing red api/ suites | owners | unchanged |

**Process note for the next sandbox run:** `run_session_command` with `wait:true` echoes the arguments twice, and
a base64 tarball tokenizes at about 1.7 tokens per character. Ship files as JSON-escaped text with `wait:false`,
then read the hash from `get_session_command_logs`.

## 5. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
