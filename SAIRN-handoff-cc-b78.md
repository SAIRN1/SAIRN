# SAIRN handoff: cc, batch b78, 2026-10-30

- **Context:** CONTEXT 28.1% of 1,000,000 -- 281,095 tokens, measured. The declared window is 1,000,000.
- **Transcript:**
  `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\a046cdf7-9eaf-4291-b1ac-b9b8bb34da67.jsonl`
- **Claims:** none. No app or api file changed this batch.

## 1. Item 1 (N-5): payload.app_id sweep. No C7 bypass found, nothing to fix.

`grep -n "payload.app_id" api/sd-data.js` returns 0 hits. The only reads of
`app_id` from the payload use the alias `p = payload` in the
`rt_routes`/`rt_stops` branch (`api/sd-data.js` ~:20678-20835).

The session check there is `verifySessionToken(token, licHash, p.app_id)`,
so the caller's `app_id` must equal the token's app. An absent `app_id`
skips the app match (`api/_lib/auth.js:683`), but `RT.validateRouteKey`
(`api/_lib/routes.js:454`) then refuses it with 400 before any data call.

**Driven, not read.** The probe is
`docs/2026-10-30-cc-b78-rt-routes-app-id-probe.js.txt`; run it from the repo
root with `node`. Literal output:

    token sairngrounds, payload.app_id sairngrounds -> 200 ok rtCalls=1
    token sairngrounds, payload.app_id ABSENT -> 400 BAD_REQUEST rtCalls=0
    token sairngrounds, payload.app_id stonedesk -> 403 FORBIDDEN rtCalls=0
    token stonedesk, payload.app_id sairngrounds -> 403 FORBIDDEN rtCalls=0

**Residual risk.** The 400 depends on the validator running before any data
call. If someone reorders it after a data read, an absent `app_id` would pass
the session check for any app. This is noted only; nothing was changed.

## 2. Item 2: carried items

| # | Status | Reason |
|---|---|---|
| F-1 | **DONE** (fourth) | Fixed in `c7d7e74d`. The cc b74 probe now prints `0 of 10 wrong`, exit 0. |
| L-1 | **OPEN** | §7 of `docs/licensing-product-plan.md` needs Michael's decisions. Nothing in the repo records an answer. |
| C-3 | **BLOCKED** | `ctxmeter.py` is still not found: `find . -name "ctxmeter*"` returns nothing. Michael has to name the path. |
| C-4 | **BLOCKED** | `tools/field_scope_rules.json` still has no `live` block for sd_crm.read, dnt_rollup.read or exec_context.read. That needs the SD-AUDIT-2026 admin/sales/install credentials and a dental audit licence from Michael. |
| C-5 | **BLOCKED** | It needs readable SEN-AUDIT-0002 caregiver credentials for the #1756 device run. |

## 3. Item 3

- **580h quotes record: DONE.** cody discharged it first, on 2026-10-29
  (SOUND-WITH-GAPS). cc's b74 second review found the echo-chain miss (F-1),
  and fourth has now fixed it in `c7d7e74d`. It is not in the open list.
- **Hook presence was 3 of 4 at the start of this batch, not 4 of 4.** cc's
  installed `.git/sairn-hooks/sairn_done_line.py` was stale (blob
  `6b3fba6e` against origin's `01cd849f`), because cody b66 changed it in
  `bea26370`.
  - Refreshed with `builder_hook_presence.py --install --only cc`.
  - After the refresh, presence is **4 of 4**, exit 0, and the regression is
    37/0, exit 0.
- **Open list:** 3 obligations. One is still assigned to cc: hover b92
  `test_965`, overdue 36h. It stays dropped as Michael directed, but its
  owner has not been changed yet. Literal output is in the report.

## 4. Item 4: manifest edits

**None this batch.** The line-delta is 0, so there was nothing to diff.

## 5. Item 5: the defect-register row is written

`docs/defect-density-register.json` has 1 record whose summary names the b77
shared_knowledge fix.
- Its commit is `52b9ca3a`, which resolves to "fix(api, cc b77):
  shared_knowledge legacy permission keys on lic.app_id ...".
- Fields: sairnlegacy, high, code-review.
- `defect_register.py --check` reports OK for 810 records, exit 0.

Literal output is in the report.
