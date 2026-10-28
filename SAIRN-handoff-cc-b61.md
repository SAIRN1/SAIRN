# SAIRN handoff: cc, batch b61, 2026-10-28

**Items 1, 2, 4, 5 and 6 are closed. Item 3, the sweep, ran in full. Its
results are routed below and none of them is fixed.**

- **Landed on origin/main:**
  - `f02a61f0`: the fix, the checker, the gate wiring and the manifest.
  - `a5601dc1` and the next commit: the register record and its re-seat.
  - `2753eaf6`: the inventory.
- The clone reads 0 0 against origin. Every changed blob is identical on
  origin.
- No `--force`, no override, no skip.
- Commits are authored "Michael Dibert" again (item 4).

| | |
|---|---|
| Claims held | `sairnsenior` (b61, released with this handoff) |
| Context | see the digest's CONTEXT line (measured) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\332ab89b-94aa-4880-931e-d17413636dfc.jsonl` |

## 1. Item 1: `tools/sairn_field_scope_check.py`, blocking pre-push check 4c, fails closed

**What it checks.**
- `tools/field_scope_rules.json` declares every rule from its write site and
  the decision behind it, never from the read branch.
- A rule lists, per role, which seeded fields that role MUST receive.
- Every other seeded field carries a unique marker, and that marker must be
  absent from the whole body. The comparison is closed-world and does not
  depend on the response's shape.
- `tools/field_scope_driver.js` drives the REAL `api/sd-data.js`. The token is
  signed by the real `api/_lib/auth`. Only the licence lookup and the database
  are stood in.

**Exit codes.**
- **Exit 1** on any of these:
  - LEAK;
  - MISSING (over-redaction, or a handler that returns nothing);
  - FLAG;
  - REFUSE;
  - COVERAGE: a read branch declaring a redaction or scope flag with no rule,
    an anchor that is not found exactly once, or a role in `ROLES_BY_APP` the
    rule does not declare.
- **Exit 2, COULD NOT RUN**, when node is missing, the driver crashes, or an arm
  is not served.
- **The gate denies on BOTH 1 and 2.** It runs at the pushed tip (`--ref`), on
  any `api/*.js` change and on any change to its own three files.

**Why pre-push is handler-level and not live.** A pre-push request against the
deployed endpoint reads the PREVIOUS code. It would refuse the push that fixes
a leak and pass the push that adds one. `--live` is the deployed half. It
reads per role, read-only, on an `*-AUDIT-*` licence, and is the post-push
check.

**Evidence it works:**

| Test | Result |
|---|---|
| Blind lock `--fixtures` | 16/16, both directions, including the sweep classifier |
| Real tree | 4 rules (`sen_caregivers`, `sen_settings`, `rf_settings`, `alf_facility`), 22/22 role arms clean |
| Ablation on the pre-fix handler | `LEAK sen_caregivers.read [caregiver]` for all 8 peer fields, plus 5 FLAG findings |
| End to end | A scratch `--local` clone with the leak put back. A real `git push --dry-run` through the full pre-push chain was REFUSED with check 4c's LEAK line. Capped: 213 s, peak 387 MB. |
| Coverage | It found `rf_settings`, a tiered read nobody had declared, on its first real run. That rule is now in the registry. |

## 2. Item 2: H1 #965 `sen_caregivers`, fixed

**Before:** after `b384a513`, every role received every caregiver's name,
phone, `cpr_expiry`, status, `aide_type`, program, `employee_id` and
`branch_id`.

**Now:**

| Role | Fields | Rows |
|---|---|---|
| owner, billing | all 12 | every row |
| scheduler, coordinator | the 9 scheduling fields | every row |
| caregiver | the same 9 | **its own record only** |

The response declares this as `roster_scope`.

**Why each tier is the size it is:**
- **Caregiver, own record only.** A caregiver assigns only itself
  (`saveClient` uses `senSession.employee_id`), so its cert gate needs its own
  row and nothing more.
- **Scheduler and coordinator, the full roster.** These are the
  `senIsScheduler()` tiers, and the assignment cert gate reads the assignee's
  `cpr_expiry`.
- This is the same tiering `sen_clients` already uses.

**DECISION, if wanted:** scheduler and coordinator still see `phone`, by the
reasoning above. Narrowing it is one line in `SEN_CAREGIVER_ROSTER_ROLES` and
two `sets` in the registry.

**Suites:**
- The two existing suites asserted that a caregiver gets the whole roster. They
  were updated to the own-row tier: 21/21 and 19/19.
- `tests/sairnsenior_cert_gate.js` 18/18.
- `law-role-matrix` 29/29.
- `b36` 71/71.
- `tests/sd_data_write_attribution_three_apps.js` has 3 `rf_` failures. They
  are **identical at HEAD**, so they predate this batch.

**Deployed (live verification):**
- Production `dpl_C224AwCk9ALTWdzggUaE1xxiKvQM` at `2753eaf6` is **READY**.
- The deployed `/api/sd-data` answers 401 INVALID_LICENSE to a bogus key. That
  proves the endpoint is up and says **nothing** about the role scope.
- **The per-role live read is UNVERIFIED.** `--live` exits 2 because no
  `SEN_AUDIT_LICENSE` / `SEN_*_EMP` / `SEN_*_PIN` are in the environment.
- **Next (Michael):** export those variables for a scheduler, a coordinator and
  a caregiver on SEN-AUDIT-2026, then run
  `python tools/sairn_field_scope_check.py --live`.

**Residual (ROUTE to the sairnsenior.html owner, not fixed):**
`senServerWinsMerge` is additive-only, and `SEN_SCOPED_CACHES` is purged only
when the person or role changes. A caregiver device that cached the full roster
BEFORE this fix keeps the colleagues' rows until a different sign-in happens.

## 3. Item 3: the platform sweep (`--sweep`). ROUTED, not fixed

**23 role-scoped read branches** in `api/sd-data.js` have no declared rule. The
sweep seeded an own row and a peer row, then drove every role of each app.

| Verdict | Count | Branches |
|---|---|---|
| **SUSPECT** (every role sees peer rows alike) | 0 | none |
| **DIFFERENTIATED**: roles differ, but there is no design to diff against | 12 | `sd_crm`, `sdn_clients`, `bld_bids`, `sen_clients`, `sen_visits`, `alf_clients`, `rf_jobs`, `rf_certifications`, `rf_claims`, `alf_staff`, `alf_mar`, `alf_staff_credentials` |
| **OWN-ROW ONLY** | 4 | `employee_profile`, `rf_company_programs`, `alf_billing`, `alf_claim_routes` |
| **COULD NOT TELL** | 7 | `employees`, `rf_warranty_tiers`, `alf_incidents` and `dnt_rollup` have no table or app parse; `exec_context` needs a payload; `bld_tna` and `rf_schedule` have an unmodelled filter |

**Route to each app owner:** declare the 12 DIFFERENTIATED reads and the 7
COULD NOT TELL reads in `tools/field_scope_rules.json`. Until then the gate does
not cover them.
- **`alf_mar` first.** It is the known same-ID-different-facility class, and
  the single-licence mock cannot see it without a declared facility column.

**Not covered at all:**
- dispatch shapes outside `resource === / action ===`, for example the dental,
  mech and law branches that use other shapes;
- writes;
- tenant scope across licences;
- the `payload.all` variant of `employee_profile`.

## 4. Item 4: identity, done

- `git config --local --unset user.name` and `user.email`.
- The effective identity is now "Michael Dibert", from `~/.gitconfig`.
- The rest of `--local` is exactly a fresh `git init`'s six `core.*` keys, plus
  `core.hookspath`, `remote.origin.*` and `branch.main.*`. **Nothing else
  leaked.**
- A copy of the config before the change is in
  `scratchpad\config.before-b61-unset`.

## 5. Item 5: the truncation, logged unresolved

- It is in `SAIRN-ACTIVE-WORK-cc.md` as UNRESOLVED / UNREPRODUCED / LOW
  PRIORITY.
- Repro has stopped. Revisit only on a new lead.

## 6. OPEN

| Item | Owner | Next step |
|---|---|---|
| Live per-role verification of #965 | Michael, then cc | Set the SEN_AUDIT_LICENSE and role EMP/PIN variables, then run `--live`. |
| 19 undeclared role-scoped reads | each app owner | Declare them in the registry. `alf_mar` first. |
| Caregiver devices holding a pre-fix roster cache | sairnsenior.html owner | Purge, or replace on hydrate, for `sen_caregivers` when `roster_scope` is `own`. |
| `phone` for scheduler/coordinator | Michael | Keep it (current) or narrow it. |
| The `sen_visits/readiness` presence side door (H1 1274, low) | hank | Unchanged by this batch. |
| `tests/sd_data_write_attribution_three_apps.js` 3 `rf_` fails | owner of rf_schedule | Pre-existing. |
| The truncation | none | Dormant, low priority. |
