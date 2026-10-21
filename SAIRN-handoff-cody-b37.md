# SAIRN handoff — cody b37 (2026-10-21)

Four items, **all four done**: one defect fix, one map entry, and two guard arms.
All three items came from cc's reviews (b34 §3(a), b35 §3(c)). Nothing is
half-finished.

## 1. State

- `origin/main` = **`b05869ff6ac3a5c56d6aeebb00742354a3a418c1`**, read with
  `git ls-remote`, and equal to local HEAD. The four changed files match origin by
  sha256.
- Commits: `a0cb367af` (work, with the regenerated MASTER-PLAN and traceability
  matrix, and the manifest) and `b05869ff6` (the Tier A obligation on
  `sd_quote_requests`), plus the push gate's bookkeeping.
- No `--force` and no skip. The gate refused once, because a Tier A obligation did
  not name `sd_quote_requests`; it was recorded and the push went through. There was
  one ref-lock race.
- Tier A obligations **opened, assigned to cc**: `bld_draws`, `dnt_referrals`,
  `dnt_vendor_orders` and `sd_quote_requests`.
- Claim `platform` (b37): **release after this commit.**

## 2. Items — concept first

| # | item | concept | result |
|---|---|---|---|
| 1 | revoke discard, scoped by consent_id, plus a two-consent arm | A revoke may discard only the credentials its own consent authorised. | `api/accounting.js` now filters the connection PATCH by `consent_id`, not by the payload's `provider`. `api/b37-accounting-revoke-scope.test.js` 5/0; S1 and S2 are red on the old file (a stale C-OLD revoke wiped C-NEW's live tokens). The b34/b35 revoke suites still pass, 9/0 and 8/0 |
| 2 | `release_retainage` forged-blob `draw_id` arm | The row's key comes from its column, never its blob. | `api/b37-routed-arms.test.js` R1–R2: the summary and the atomic release both use the column draw. The guard was already right (b33). Removing `draw_id: curRow.draw_id` in a worktree turns **R1 red** |
| 3 | two-tenant `request_photos` arm | A read returns only the caller's licence's rows. | P1–P2 use a filter-honouring store (the complaint-respond pattern). The guard was already right (b34). Removing the licence filter in a worktree turns **P1 and P2 red** |
| 4 | `dnt_referrals` map entry | A "not set up" message names the file that creates THIS table. | `DNT_SCHEMA_FILE.dnt_referrals = 'sql/sairndental_referrals_schema.sql'`. N1 is red on the old file. N2 checks that file really creates the table |

Mapping all seven dental generic resources to their `create table` showed
`dnt_referrals` was the only gap.

## 3. Verification

The regression set was 30 suites, every exit code read individually: 29 exited 0.
The b37 suites were re-run after the final rebase, both exit 0.

**1 red, not mine:** `tests/sairnfreedom_auth_review_probe.js` exits 1 at HEAD with
or without b37 (stash differential). Its message is *"the sf-auth setup guard anchor
has moved"*, so it is a stale anchor in a review probe.

## 4. Open

- **cc:** the Tier A reviews from b31–b37. b37 reviewer point: every
  `accounting_connections` row must carry its `consent_id`. The schema says
  `not null`, and live rows are unverified.
- **Not routed to anyone yet:** `tests/sairnfreedom_auth_review_probe.js` stale
  anchor. Owner unknown; it is the sairnfreedom auth reviewer's probe.
- Carried, unchanged: fourth (defects 7 and 8), hank (defects 5 and 6, scp-licence-only).

## 5. Context

Measured **36.5% (364,686 / 1,000,000)**.
