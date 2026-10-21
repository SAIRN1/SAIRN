# SAIRN handoff — cody b36 (2026-10-21)

Five items, **all five done**. Item 3 also measured something it was not asked to
fix: on 21 of the 22 paired resources, a legacy blob would override the column
(§3.3). Nothing is half-finished: all code is committed, pushed and read back.

## 0. The deploy-sha question from the dispatch, answered from git

- `792654a38` is the 9-character form of **`792654a388d6e0796e438ea749144e81c0d0d749`**,
  b35's **work** commit. `git merge-base --is-ancestor 792654a38 3ed60b07` → **true**.
  So production at hank's `3ed60b07` **contains b35's code**.
- `7719da747` (b35's handoff, report and digest, no code) sits **on top of** `3ed60b07`:
  `7719da747 → 1cdbec766 → 3ed60b07`. It is not underneath it.
- b35 reported the work tip and then the deliverables tip, and did not say which was
  which. From here on the report names every sha in full and says what it carries.
- b36 did not re-push over anything. Every push was a fast-forward, with no `--force`.

## 1. Committed / pushed state

- `origin/main` = **`eb23fd3ff0d8e287e166036ae01c8f8cba63c858`**, read with
  `git ls-remote`, and equal to local HEAD. After CR normalisation, all four b36 files
  match `origin/main` by sha256.
- b36 commits (after rebase): `ed9a16947` (work), `a3650f24b` (regenerated
  MASTER-PLAN and traceability matrix), plus the push gate's scrutiny bookkeeping.
- The push gate refused twice. Both refusals were fixed at the cause, with no skip:
  1. the generated docs were stale, so they were regenerated;
  2. a generated-doc rebase conflict (fourth regenerated in the same window). It was
     resolved by regenerating from the merged tree, not by picking a side.
  Four ref-lock races with other clones were retried by rebasing. None was forced.
- **Claim:** `platform` "b36 sd_customers deleted-employee gate, defect 8 reverify,
  projection runtime differential". **Release after this commit lands.**
- Tier A obligation **opened, assigned to cc** (`docs/tier-a-reviews.json`).

## 2. Per item — concept stated before the code each time

| # | item | concept | state |
|---|---|---|---|
| 1 | gate `sd_customers` against a DELETED employee row | A missing employee row counts as a deactivation once the resource's app is known. | **DONE** — 9/0; 5 arms red on the old file, all five verbs |
| 2 | re-verify defect 8 | — | **STILL OPEN, both halves** — §4 |
| 3 | runtime differential for the projection sites | A projection key is safe only if it is *executed* to be so. | **DONE** — 71/0; ablation turns exactly A8 red |
| 4 | concept before code | — | applied |
| 5 | push, confirm | — | **LANDED** (§1) |

## 3. What changed

### 3.1 `api/sd-data.js` — the pre-gate (+11/−1)
- `PRE_DECLARED_APP = { sd_customers: 'stonedesk' }`, looked up with `hasOwnProperty`,
  feeds `preExpectedApp` when the resource is not on `SD_SESSION_GATED`.
- A stonedesk token whose `sd_employee_auth` row is **gone** now takes the existing
  `CREDENTIAL_INACTIVE` refusal. That is the same path as `active:false`, and nothing
  else changed.
- Why it was open: `sd_customers` is not on `SD_SESSION_GATED`, so the pre-gate called
  its app "unknown", and a missing row fell through to the branch gate. The branch gate
  trusts the token's role. **Driven before the fix:** a deleted owner read customers
  (200) and wrote them (200).
- Safe for owners: `sd-auth.js` setup **inserts the owner's row before minting the
  token** (`api/sd-auth.js:~198–215`), so every legitimate stonedesk token has a row.
- Unchanged, and asserted: a **sairnbiz** token at `sd_customers` still gets the branch
  gate's answer, not "deactivated" (X1). A **failed** lookup is still not a
  deactivation (T1).
- Test: `api/b36-sd-customers-deleted-row.test.js`.

### 3.2 `api/b36-projection-runtime-differential.test.js` (no code change)
Drives the 22 PAIRED resources from `docs/b33-sweep/pair_by_resource.py` through
`sd-data.js` against a **store** mock: the write stores exactly the row the handler
sent, and the read returns it. The `alf_mar` RPC and `created_at` column defaults are
emulated, and the test says so. It checks three things:
- **A:** no planted projection key reaches the stored blob;
- **W:** the write response takes each key from a column;
- **B:** the read does the same.

The criteria were locked on synthetic fixtures F1–F5 in both directions before the real
run, and "could not run" fails. **Ablation**, in a separate worktree with the live clone
untouched: removing `sen_branches`' strip turns **exactly A8** red.

### 3.3 MEASURED, NOT ASSERTED: legacy-blob exposure
**21 of 22** reads are still `Object.assign(columns, data)`, so a blob that **carries**
the key overrides the column. The exception is `alf_incidents`. Today's writes cannot
produce such a blob (arm A proves that). A row written **before** its strip list existed
can. The ones that matter beyond `id`:

| resource | keys |
|---|---|
| `sd_crm`, `sdn_clients`, `bld_bids`, `sen_clients`, `alf_clients` | `assigned_employee_id` |
| `alf_mar` | `resident_id`, `entry_type`, `assigned_employee_id`, `created_at` |
| `alf_billing` | `resident_id` |
| `alf_signals` | `resident_id`, `signal_type`, `recorded_at` |
| `alf_claim_routes` | `resident_id`, `service_month`, `decided_by`, `created_at` |
| `alf_staff_credentials` | `staff_id`, `record_type`, `recorded_by`, `created_at` |

**`sql/b36-legacy-blob-projection-keys.sql`** is read-only: 21 SELECTs, and every count
is expected to be 0. Only it can say whether any live row is exposed.

## 4. Defect 8 (`sairnsenior.html`, fourth's) — re-verified at HEAD, STILL OPEN

- **Half 1. A contract or authorisation saved while its table is missing stays local
  and prices claims.**
  - `savePayerContract` writes `sen_payer_contracts` locally first (`:4738`), then
    calls `senData('write', …)` (`:4743`).
  - The server answers 503 NOT_PROVISIONED (`api/sd-data.js` sen_payer_contracts →
    `notProvisioned`). `senData` returns `null` and records the code only in
    `senLastErr`.
  - The toast then says *"server sync failed, try again with a connection"*
    (`:4744`). That names the **wrong cause**: it is not a connection problem, and
    retrying cannot help.
  - The local row stays in `ld('sen_payer_contracts')`, which is what claim pricing
    reads (`payerContracts()`, `:4562`).
  - `saveAuthorization` (`:5438`, toast at its end) has the same shape. Its local row
    feeds `azResolve` (`:5339`).
- **Half 2. With no contract, the prior-auth warning is skipped silently.**
  - The required-authorisation message is built only inside
    `if (rate.status==='applied' && rate.requires_authorization)` (`:4372`).
  - When no contract applies, no claim says anything about prior authorisation, even
    if none is on file. Whether the payer requires one is unknown, and that unknown is
    not surfaced.
  - Also, when the claim write fails, the whole toast is replaced by the generic
    device-only line (`:4390`), so the rate and auth messages are lost too.
- Not mine. **Routed to fourth**: read `senLastErr[resource].code` and say
  NOT_PROVISIONED plainly; when no contract applies, state that prior authorisation
  could not be checked.

## 5. Open — with the exact next step

1. **Michael:** run `sql/b36-legacy-blob-projection-keys.sql`, one statement at a
   time, and send the counts. If any is non-zero, the fix is the b32/b33 flip
   (`Object.assign({}, data, columns)`) at that resource's read sites. **Flip none
   blind**; the count decides.
2. **cc:** the Tier A reviews from b31–b36. Reviewer point for b36: is there any
   StoneDesk path that holds a valid token with no `sd_employee_auth` row?
3. **Routed to cody by cc b35 (§3(c)), NOT in this dispatch, not done:**
   - scope the revoke discard by `consent_id`. A repeat revoke of a stale Xero
     consent cleared an active QuickBooks connection. It is latent because OAuth
     returns 501;
   - add a two-consent arm;
   - b34 items: the `release_retainage` arm, the two-tenant `request_photos` arm, and
     the `dnt_referrals` map entry.
4. **fourth:** defect 7 (b35 handoff §4) and defect 8 (§4 above).
5. **hank:** defects 5 and 6. `api/sd-data-scp-licence-only.test.js` B arms (cc b35
   §3(b)).

## 6. Verification (this batch; exit code read per program)

```
EXIT=0 b36-sd-customers-deleted-row 9/0 · b36-projection-runtime-differential 71/0 (both re-run after the final rebase)
EXIT=0 b35-missing-table-writes · b35-accounting-revoke-repeat · b34-routed-defects · b33-projection-order-sweep
EXIT=0 b32-rf-jobs-projection · b30-cap-per-action · b29-error-detail · sd-data-cross-tenant-dispatchers
EXIT=0 preauth-envelope-ordering · sd-data-active-credential 13 · sd-data-mech-redaction-scope · employees-refusal
EXIT=0 tests/sd_data_not_provisioned_misclass · all 9 api/sd-data-*session*.test.js
EXIT=0 sd_customers suites: customer-soft-delete 10 · customers-batch · tombstone-propagation · unconfirmed-write-sweep 30
EXIT=0 stonedesk-track 19 · tests/: collection_delete 41 · customer_delete_does_not_resurrect 14 · quote_history_delete 24
EXIT=0 stonedesk_server_backup 23 · stonedesk_write_result_consumption 18 · provisioning_attribution 10 · exec_msgs_gate 13
RED ON OLD CODE: b36-sd-customers-deleted-row D1-D5 · ABLATION (worktree): exactly A8
```

## 7. Context

Measured **30.7% (306,562 / 1,000,000)**.
