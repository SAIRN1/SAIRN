# SAIRN handoff — cody b35 (2026-10-21)

Six items. **All six done**, with two limits: item 4's premise was wrong
(same as b33: the "eight still-open defects" are **cc's** b29, not mine), and
item 6's live check is **UNVERIFIED for the specific fix** (see §5).
Nothing is half-finished: every code change is committed, pushed and read back.

## 1. Committed / pushed state

- `origin/main` = **`792654a38`**, read back with `git ls-remote`; local is 0 ahead
  and 0 behind; all five changed files match the remote by sha256 (after `tr -d '\r'`).
- b35 commits: `43c32bf6c` (work), `a7e349679` (MASTER-PLAN + traceability
  matrix regenerated, as the gate required), `5f6d18809` (scrutiny-flag write-back
  from the push gate), `792654a38` (path manifest + Tier A obligation).
- Pushed **without `--force`** and **without any skip or exemption**. The gate refused
  twice and both refusals were fixed at the cause: (1) generated docs were stale, so
  they were regenerated; (2) three `api/` test paths were outside cody's scope, so they
  were declared in `docs/sairn-path-manifest.json`, and a Tier A obligation was opened.
- **Claim:** `platform` / "b35 sd-data missing-table writes, accounting revoke guard,
  customer-soft-delete test", committed (`7a549be28`). **Release it after this handoff
  commit lands:** `python tools/sairn_claim.py release platform`.
- Context window declared as **1,000,000** this session (`--provision-window`).

## 2. Per item — the concept was stated before the code each time

| # | item | concept | state |
|---|---|---|---|
| 1 | 8 writes that return a generic 502 on a missing table | A missing table on a write is a 503 NOT_PROVISIONED naming the file that creates THAT table, classified from the response body, not a retryable 502. | **DONE** — 24/0, 16 arms red on the old file |
| 2 | A repeat revoke clobbers `revoked_on`/`revoked_by` | A revocation is a historical fact: the first revoke records it, and a repeat leaves it alone but still completes the discard. | **DONE** — 8/0, 5 arms red on the old file |
| 3 | `sd-data-customer-soft-delete` red at HEAD | A suite red at HEAD is stale when the code moved on purpose and the fixture did not. | **STALE TEST, fixed** — 10/0; the old test still exits 1 |
| 4 | Report "my b29 eight still-open defects" | — | **REPORTED** — they are cc's; §4 |
| 5 | Concept before code | — | applied, as in the table above and the test headers |
| 6 | Push, confirm it landed | — | **LANDED** (§1); live check partial (§5) |

## 3. What changed

- **`api/sd-data.js`** (+8 lines). At each of `subcontractors`, `sub_assignments`,
  `rf_safety_equipment`, `rf_job_hazard_assessments`, `rf_buildings`, `rf_roof_sections`,
  `rf_warranty_tiers` and `rf_job_warranties`, this line now sits ahead of
  `if (!w.ok) return upstream(res, saved);`:
  `if (w.status === 404 || w.status === 400) return notProvisioned(res, w, '<msg> — run sql/<file> in Supabase first.', saved);`
  It is the same line b34 put on prequal/bonding. Schema files were matched by their
  `create table`: `subcontractor_compliance_schema.sql`, `sairnroofing_safety_schema.sql`,
  `sairnroofing_asset_registry_schema.sql` and `sairnroofing_warranties_schema.sql`.
  The insert checked that the nearest write fetch above each site targets that
  resource's own table. Test: `api/b35-missing-table-writes.test.js`. Each resource
  gets a missing-table arm (→ 503), a 23514 arm (→ 400 ROW_REFUSED) and a control
  arm (present table → 200).
- **`api/accounting.js`** (revoke). The consent PATCH now carries `&revoked_on=is.null`.
  When zero rows match, the consent is re-read:
  - absent → 404 NO_CONSENT (unchanged);
  - already revoked → carry on to the token discard, with `already_revoked:true` and
    the ORIGINAL row as `data`;
  - re-read fails, or the consent still reads active → **502 REVOKE_UNCONFIRMED**,
    never a 404 and never a success.

  `already_revoked` is now on all three revoke responses. Test:
  `api/b35-accounting-revoke-repeat.test.js`. Its mock is a store that honours the
  PostgREST filter, so a PATCH with no guard really does overwrite the row. It includes
  V5, the retry that `TOKEN_DISCARD_UNCONFIRMED` invites.
- **`api/sd-data-customer-soft-delete.test.js`** (test only, no code change). Two causes:
  - its recorder never answered the active-credential pre-gate's `_employee_auth`
    read (`c8b5e5b12`, 2026-09-26, two days after the test was last touched). It now
    answers that read, outside `calls`, so "nothing touched" still means no customer data;
  - its pinned verb list lacked `write_batch` (`be352a7d0`, 2026-09-26).

## 4. cc's b29 eight defects (item 4) — state at HEAD `792654a38`

| # | defect (cc b29 notes §1) | owner | at HEAD |
|---|---|---|---|
| 1 | dental 503 named the wrong schema file | cody | **FIXED b34** (b34-routed-defects 12/0) |
| 2 | prequal/bonding write missing table → 502 | cody | **FIXED b34**; and its 8 siblings fixed **b35** |
| 3 | accounting revoke: false `tokens_discarded:true` | cody | **FIXED b34** (9/0); repeat-revoke clobber fixed **b35** |
| 4 | accounting: any 400 → NOT_PROVISIONED | cody | **FIXED b34** |
| 5 | `sd_quote_request_photos` written, never read | hank/cody | **server half FIXED b34** (`request_photos`); **client still has no caller** (grep `stonedesk.html`: 0 hits) → hank |
| 6 | `stonedesk.html` style profile tests `d.provisioned`/`d.ok` on the inner object | hank | **STILL OPEN**, re-read: `sdData` returns `j.data` (`stonedesk.html:~30420`), so `sdLoadStyleProfile` (`:30746`) and `sdObserveStyle` (`:30760`) read keys that are never there |
| 7 | `sairnroofing.html` JHA read error and job-warranty missing table read as "none" | fourth | **STILL OPEN**, re-read: JHA `!j.ok` → `jd={}` → empty list (`:4188`), while `provisioned:false` IS handled; warranties ignore both `ok` and `provisioned` (`:4845`) → "No roofs registered yet." |
| 8 | `sairnsenior.html` contract/authorisation stays local; prior-auth warning skipped | fourth | **not re-verified**: cc gave no line, and it is not my file |

## 5. What is open, and the exact next step

1. **Live check of the specific fix is UNVERIFIED.** Vercel `list_deployments` returned
   **403 forbidden**. `POST /api/sd-data` and `POST /api/accounting` with no licence both
   answer **401** live, so the deployed modules load and do not 500. A licence-less probe
   cannot reach the changed branches, so that is all it proves. *Next:* someone with
   deployment read access confirms the production deployment's sha is `792654a38` or later.
2. **Tier A obligation opened, assigned to cc** (`docs/tier-a-reviews.json`) on the
   seven roofing resources. *Reviewer point:* confirm no client relied on the 502 shape.
   cc still owes the b31–b34 obligations too.
3. **hank:** wire `request_photos` (defect 5) and fix the style-profile client (defect 6).
4. **fourth:** defect 7 (two `sairnroofing.html` sites in §4) and defect 8.
5. **Observation, not acted on:** `sd_customers` is not in `SD_SESSION_GATED`. A
   stonedesk token whose employee row is **deleted** (not deactivated) is passed to the
   branch gate, which trusts the token's role. Deactivation (`active:false`) is still
   refused. That is outside this batch's scope and is a gating (Tier A) decision.
6. **No real write against the real store was performed.** Guardian Check 29 asks for
   one. That needs a licence and live data, and this batch had no authorisation for
   live writes. The storage shape did not change, only the response classification and
   one PATCH filter.

## 6. Verification (run this batch, exit code read per suite)

```
EXIT=0 b35-missing-table-writes 24/0 · b35-accounting-revoke-repeat 8/0 · sd-data-customer-soft-delete 10
EXIT=0 b34-accounting-revoke 9/0 · b34-routed-defects 12/0 · b33-projection-order-sweep 12/0
EXIT=0 b32-rf-jobs-projection 7/0 · b30-cap-per-action 22/0 · b29-error-detail 11/0
EXIT=0 sd-data-quote-request-soft-delete 14 · sd-data-tombstone-propagation · sd-data-cross-tenant-dispatchers 418/0
EXIT=0 sd-data-unconfirmed-write-sweep 30/0 · sd-data-unconfirmed-write 9/0 · preauth-envelope-ordering 59/0
EXIT=0 sd-data-session-gate · fail-open-triage 15 · employees-refusal 10/10 · roofing-projected-isolation 30/0
EXIT=0 sd-data-sb-void-role 18 · tests/sd_data_not_provisioned_misclass 16/0 · role_maps_have_no_prototype · roofing_unprovisioned_is_not_empty
RED ON OLD CODE: b35-missing-table-writes 16 arms · b35-accounting-revoke-repeat 5 arms · old customer-soft-delete test exit 1
```

Guardian v2 on the diff: 0a `node --check` was clean on all five files. The diff had
no `api.anthropic`, `service_role`, `RESEND` or `process.env` additions, no
`verifySessionToken` change and no `console.log`. Line endings were preserved
(LF→LF). `git diff --cached --numstat` matched the intended shape.

## 7. Context

Measured **21.5% (214,975 / 1,000,000)** with `python tools/context_verify.py --digest-line`.
