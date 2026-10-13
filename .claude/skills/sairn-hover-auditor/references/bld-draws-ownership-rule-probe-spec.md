# bld_draws ownership-rule probe spec (NOT YET IMPLEMENTED)

Status: SPEC + BASELINE ONLY. Hover role — read-only. No fix is proposed or
applied here; see `tools/bld_draws_ownership_rule_probe.py` for the companion
static baseline probe.

## 1. The new rule, stated precisely

Requested rule: **`bld_draws` access (generic `read`/`write`) should be
restricted to owner and upper management only; supervisors and ordinary
employees should be denied.** Access is further supposed to be assignable "by
ownership" — i.e., which specific draws/jobs a given owner/manager is tied to.

This spec establishes what that maps to in SAIRNbuild's REAL vocabulary
(section 2), what "ownership" can actually mean given what exists on disk
today (section 3), and the adversarial test matrix against both the CURRENT
gate and the NEW rule once built (section 4).

## 2. Real role vocabulary — confirmed, not invented

`api/_lib/auth.js:203`, `ROLES_BY_APP`:

```js
sairnbuild: ['owner', 'pm', 'office'],
```

That is the complete, exact list. **There is no `supervisor` role and no
`employee` role in sairnbuild.** The task description's "supervisors and
ordinary employees" has no literal match in this app's vocabulary — flagged
rather than invented. The only real candidate for "should be denied" is `pm`.

Separately, `api/sd-data.js:5642` already defines a management tier for this
exact resource family:

```js
const BLD_BID_MANAGEMENT_ROLES = roleSet({ owner: true, office: true });
```

This is used today to gate the `bld_draws` `wip`/`release_retainage`
sub-actions (`api/sd-data.js:5673-5681`) and to gate `bld_bids` read/write
(`api/sd-data.js:5918-5965`). **"Owner and upper management" in this app's own
existing convention already means `owner` + `office`, with `pm` as the
excluded role.** This spec adopts that reading because it is the
precedent already built and named in this codebase, not a new invention — but
it is still a judgment call (not confirmed with Michael) exactly like the
disclosed, unconfirmed `sairnbuild` role-mapping call already on record at
`api/_lib/auth.js:200-202`. Note it as a call, do not silently treat it as
settled.

**If "upper management" was meant to exclude `office` too (owner-only), say
so explicitly before building — this spec does not resolve that ambiguity,
it names it.**

## 3. What "by ownership" can mean here — checked against real schema

The task asks whether access should be scoped per-job/per-draw ("which
specific draws/jobs a given owner/manager is tied to"), not just by role
company-wide. Checked against the real schema and the real dispatch code:

- **`bld_draws` table** (`sql/sairnbuild_data_schema.sql:90-100`) has columns
  `id, license_hash, app_id, draw_id, data, created_at, updated_at` only.
  **No `job_id` column. No `assigned_employee_id` column.** The only
  structural scoping is `license_hash` (tenant/business), enforced on every
  query (`bld_draws?license_hash=eq.<licHash>...`).
- **`bld_jobs` table** (`sql/sairnbuild_data_schema.sql:42-51`) is the same
  shape: `id, license_hash, app_id, job_id, data, created_at, updated_at`.
  **No `assigned_employee_id` column either.** `bld_jobs` is one of the 30
  entries in the generic `BLD_RESOURCES` dict (`api/sd-data.js:13213-13226`)
  with no per-employee scoping of any kind — "every role... reads them" is
  the file's own stated reasoning for that loop.
- `job_id` DOES appear on draw rows, but only as a plain string field **inside
  the unparsed client-side `data` jsonb blob** (`sairnbuild.html:3309`, e.g.
  `{id:'DR-01',job_id:'J-2601',...}`). The server never reads, indexes, or
  filters on it. It is a client-side convention, not an enforced boundary.
- **The one place in sairnbuild that DOES have a real, server-enforced
  per-employee ownership column is `bld_bids`**
  (`sql` migration implied by `api/sd-data.js:5944`'s error message
  `sql/sairnbuild_bids_schema.sql`): `assigned_employee_id` is a promoted
  column, read at `api/sd-data.js:5921`, filtered at `:5930-5931` (non-
  management sees only bids where `assigned_employee_id === session.employee_id`,
  an unassigned bid is management-only-visible), and reassignment is
  management-gated at `:5953-5964`.

**Conclusion: there is a real, working "ownership" pattern in this codebase —
it just does not extend to `bld_draws` or `bld_jobs` today.** Implementing
per-draw or per-job ownership scoping for `bld_draws` (beyond the existing
tenant-level `license_hash` scoping) would require NEW schema work — at
minimum promoting `job_id` to a real column on `bld_draws` and deciding how a
`pm`'s job assignment is determined (since `bld_jobs` itself has no
`assigned_employee_id` to join against) — none of which exists yet. **This
spec does not propose that schema change.** The adversarial matrix below
therefore tests the role-level gate only (company-wide owner/office vs pm),
which is the one piece that can be built today without new migrations, and
flags per-job ownership as a separate, not-yet-buildable extension.

## 4. Adversarial test matrix

Target branch: the dedicated `bld_draws` read/write gate,
`api/sd-data.js:13273-13309`
(`if (resource === 'bld_draws' && (action === 'read' || action === 'write'))`).
Today it requires only `verifySessionToken(...)` to return non-null — **no
role check of any kind.** Compare against the already-correct sibling branch
`api/sd-data.js:5673-5681` (`wip`/`release_retainage`), which already does
session + `BLD_BID_MANAGEMENT_ROLES`.

| # | Caller | Current code (today, HEAD) | New rule (once built) |
|---|---|---|---|
| 1 | No token / unauthenticated | **DENY** — 401 `NO_SESSION` (`verifySessionToken` returns null at `:13274-13278`; this part is already correct and unaffected by the new rule) | DENY (unchanged) |
| 2 | Valid session, role=`pm`, same tenant | **ALLOW** — session-only gate, no role check; `pm` reaches `read`/`write` identically to `owner`/`office` | **DENY** — `pm` is not in `BLD_BID_MANAGEMENT_ROLES` |
| 3 | Valid session, role=`office`, same tenant | **ALLOW** | **ALLOW** (unchanged — `office` is in `BLD_BID_MANAGEMENT_ROLES`) |
| 4 | Valid session, role=`owner`, same tenant | **ALLOW** | **ALLOW** (unchanged) |
| 5 | Cross-tenant: a valid session token issued for license_hash A, used against a request resolved to license_hash B (any role) | **DENY** — `verifySessionToken(token, license_hash, expectedApp)` at `api/_lib/auth.js:606` checks `payload.license_hash !== license_hash` and returns `null` on mismatch; this is a pre-existing, independent control, not something the new rule touches | DENY (unchanged — orthogonal to the role gate; a role-based fix must not weaken or bypass this existing binding check) |
| 6 | Valid session, role=`pm`, same tenant, requesting a draw tied to a job they ARE assigned to (per-job "ownership") | **ALLOW** (no ownership concept exists at all today; see §3) | **NOT YET DEFINABLE** — no schema exists to express "tied to." Out of scope until `job_id`/assignment is promoted to a real column on `bld_draws` or `bld_jobs`. Flagged, not answered. |
| 7 | Valid session, role=`pm`, same tenant, requesting a draw tied to a job they are NOT assigned to | **ALLOW** (same reason as #6) | Same as #6 — not definable without new schema |

**Row 2 is the actual gap the new rule closes.** Rows 1, 3, 4, 5 are either
already correct or already orthogonal controls that must not regress. Rows
6-7 are explicitly out of scope until schema work lands — do not let an
implementation quietly narrow `pm` to zero access company-wide while calling
that "ownership scoping," when no ownership data exists to scope by; that
would be a stricter rule than requested, delivered silently.

## 5. What the baseline probe checks

`tools/bld_draws_ownership_rule_probe.py` performs static analysis only (no
live HTTP, no server running — same constraint as every other repro script in
`.claude/skills/sairn-hover-auditor/tools-hover2/`, mirrored under this role's
own `tools/` directory). It:

1. Extracts the dedicated `bld_draws` read/write branch
   (`api/sd-data.js:13273` through the next known anchor, the generic
   `BLD_RESOURCES` loop) and reports whether it contains a session check
   (`verifySessionToken`) and a role check (any `*_ROLES` guard, e.g.
   `BLD_BID_MANAGEMENT_ROLES`).
2. Extracts `verifySessionToken`'s own body from `api/_lib/auth.js` and
   confirms the `payload.license_hash !== license_hash` binding check is
   present (row 5's control).
3. Prints the 7-row matrix above with CURRENT (derived from 1-2) vs NEW-RULE
   columns, so a future implementer has a single baseline to diff against
   once the role check is added.

It asserts nothing about `pm`, `office`, or `owner` PASSING any particular
HTTP call — there is no live session or server to call. It asserts what the
SOURCE currently gates, which is the thing this role can check mechanically.
