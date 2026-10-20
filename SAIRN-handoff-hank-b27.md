# SAIRN handoff — hank b27 — 2026-10-20

**Subject:** the deployed limiter now reports its own mode (and it says production is
**ENFORCING at 1000 with the variable unset**); the `auth_observe` log fix proven in-process
with no production traffic; the Field Map map's dead call replaced; the SEN audit licence
SQL and the straight-time-floor fixtures ready to run the moment the key exists.
Written before the report, with nothing half-finished. Notes: `docs/2026-10-20-hank-b27-notes.md`.

## 1. PUSHED STATE
`origin/main` = **`73c36e3c1`** after the handoff push (re-derive before quoting: five clones push to one branch),
`0 ahead, 0 behind`, **NOT FORCED, ZERO gate overrides.** The b27 work is `436c11f02`
(the fix), `2a02d2267` (derived docs + register), `565daf33c` (wording fix + ledgers).
Gates met: **register-feed** (fed: one record, three factors), **derived-docs** (MASTER-PLAN
and traceability regenerated after the final rebase). A rebase conflict on the register was
resolved by taking upstream's re-seated file and re-adding my record against the new sha.
**Path-scope was clean:** every path owned, assigned (`stonedesk.html`) or self-named.

## 2. CLAIMS HELD
Mine (`hank`), released at the end of this batch. cc b28 still holds
`tools/tooling_inventory.py`, `CLAUDE.md`, `tools/digest_lint.py`; cody b29, fourth b42,
hover, hover2 hold theirs. **I edited none of cc's files.**

## 3. THE SIX ITEMS
1. **SEN-AUDIT-2026 SQL — WRITTEN, NOT RUN (no DB access).** CONCEPT: a test that writes
   payroll rows needs a licence holding no customer data; minting it is one idempotent insert.
   `sql/mint_sen_audit_2026.sql` — **run twice: second run inserts nothing and changes nothing,
   including status.** `sql/verify_sen_audit_2026.sql` — read-only, five PASS/FAIL lines;
   **run twice: identical; run before the mint: five FAILs, not an error.** Michael runs both.
   **For cc:** add `SEN-AUDIT-2026` to `KNOWN_AUDIT_KEYS` — hygiene only, nothing waits on it
   (`require_audit_licence` accepts an audit-shaped key with a NOTE).
2. **Mode echo — DONE and live-verified.** `rate_limit_mode`, `rate_limit_configured`,
   `rate_limit_limit` on any response that reached the limiter. In-process: A1–A7 + ablation.
   **Deployed, measured:** unauthenticated → 401 `NO_LICENSE`, **no `rate_limit_*` key**;
   one authenticated call → **`enforce`, `configured:false`, `1000`.** So the variable IS absent
   or misspelled in production, the limiter IS enforcing, at the ceiling set in b26.
3. **`auth_observe` log fix — PROVEN IN-PROCESS.** Real handler, forged `app_id`
   (LF, CR, CRLF, U+2028, U+2029, ESC, 300 chars), both console streams captured: one line,
   `state=absent`, still 401, recognised id still verbatim. **Ablation:** raw `body.app_id`
   restored → two lines, the forged one `state=valid`. 30 arms. No production request.
4. **Field Map map — DONE, driven on the live page.** The routing primitive has **no image verb**
   (it returns an order), so it could not be repointed; `fmRenderMap` now builds a Maps
   **directions link**. Live DOM (Chrome, spy on `fetch`): 0 stops → "No stops to map yet."
   (control); 1/3/12 stops → correct origin/destination/waypoints, `rel=noopener noreferrer`,
   **zero network calls, none to `api/bridge`.** Found and fixed my own wording bug on the
   12-stop note; re-verified offline, then **re-driven live after the fix deployed**: 3/10/11/12 stops read "1 stop … is left off" / "2 stops … are left off" correctly, 8 waypoints, zero network calls.
5. **Comments + fixtures.** `api/bridge.js` and the b21 test annotated (REPOINTED/DELETED).
   Fixtures: one JSON, **18 arms** against the real `sen-payroll.js` + `sen-evv-clock.js` incl. the
   guard ablated (H2's invariant breaks). The live probe is driven against a **fake server only**
   — its HTTP sequence is **unproven until the key exists.**
6. **Push:** §1.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | why | next step |
|---|---|---|---|
| A | cc: path-scope probe registry entry | cc's file + 300 s timeout (b26) | unchanged from b26 handoff §4 |
| B | **Michael runs the two SEN SQL files** | no DB access | mint → verify → bootstrap `audit-owner` via `/api/sen-auth` |
| C | straight-time-floor live proof | needs B | `SEN_LICENSE=SEN-AUDIT-2026 SEN_OWNER_PIN=… SEN_CAREGIVER_PIN=… python docs/2026-10-20-hank-b27-sen-straight-time-floor-live-probe.py`; read the first arm that fails |
| D | move probe + fixtures to `tools/` | needs an inventory line in cc's claimed file | rename, add one `PURPOSES` entry, drop the "why docs/" comment, add `assigned_overrides` or let cc own it |
| E | **production is enforcing because the variable is unset** | now measured | Michael: set `SAIRN_AI_RATE_LIMIT_MODE` to `observe` or `enforce` in Vercel — the response will then read `configured:true` |
| F | trust-lock re-drive | PINs (b26 §4 F) | unchanged |
| G | Field Map is a link, not an embedded image | smaller feature than designed | a decision on where a Maps key may live, if an image is wanted |
| H | b26 items I (override), J (gates), cc's CLAUDE.md figures | cc/fourth's | untouched, as instructed |

## 5. EVIDENCE (at the push)
`b27-claude-mode-echo-and-log` 30/0 · `b27-sen-straight-time-floor-fixtures` 18/0 · `claude-cost-controls` 31/0 ·
`ai-safeguards` 47/0 · `ai-rate-limit` exit 0 · `ai-rate-limit-tenant` 10/0 · `b22-claude-logline` 12/0 ·
`b25-revoke-race-and-failclosed` 30/0/0 · `b21-bridge-unknown-action` 20/0 · `bridge-push-auth` 27/0 ·
stonedesk 128 blocks 0 errors · live: unauth 401 no echo, authed 200 `enforce/false/1000`, Field Map DOM drive.
**Not covered:** the SQL files were never executed; the live probe never touched a server; no whole-tree run.

## 6. TRANSCRIPT
    C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\8dd2a9db-f15f-4fee-9950-08bcb26892c0.jsonl
Context at writing: 42.4% (424,103 of 1,000,000), from `context_verify.py --digest-line`. Trigger was 85%.

## 7. WHAT I GOT WRONG
1. Wrote the truncation note for the Maps link as "stops after the 10th" when the link keeps the first
   nine and the last; the live drive of the 12-stop case caught it.
2. Put the live probe under `docs/` because `tools/` needed cc's claimed file — a placement chosen to
   avoid a conflict, not because it is where the probe belongs (open item D).
3. Heredoc-wrote the probe into a bash command that mixed two heredocs and lost the whole command; no
   harm, but the file was written again with the Write tool.
