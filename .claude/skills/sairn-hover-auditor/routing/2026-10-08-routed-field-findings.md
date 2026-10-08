# Hover-routed field findings -- exact file/line, one row per finding

Written H1 batch U item 4. This batch's own task text said "8 still-open
ownership/field findings in api/sd-data.js" -- recounted directly rather
than trusted: 11 (7 ownership-pattern findings plus 4 other field
findings from the same hand-verification pass, batch S items 6-7). The
real count is stated here rather than silently matched to the given one,
the same discipline this role's own log already applies to every other
repeated number.

Every row already exists as its own `--routable` chain-log entry
(seq1146-1156, batch S); this doc exists so a build agent can act without
re-deriving a line number, not as a new finding.

None of these have been acted on as of this doc's own writing (confirmed
by `git log` showing no commit touching either source file for this
reason since the findings were logged).

## api/sd-data.js -- 7 ownership/assignment-field findings

| Resource | Field | File:line | Register row (docs/CRITICALITY-TIERS.md) | Chain seq |
|---|---|---|---|---|
| `alf_mar` | `assigned_employee_id` | `api/sd-data.js:10545` | Tier A, PHI | seq1146 |
| `alf_staff_credentials` | `staff_id` | `api/sd-data.js:12509` | Tier A, REGULATED/licensure | seq1147 |
| `bld_bids` | `assigned_employee_id` | `api/sd-data.js:5688` | Tier A, Money | seq1148 |
| `bld_tna` | `subject_employee_id` (and `assigned_employee_id` at :5858) | `api/sd-data.js:5767` | Tier A, both axes | seq1149 |
| `rf_certifications` | `employee_id` (two sites) | `api/sd-data.js:7568` and `:7650` | Tier A, REGULATED | seq1150 |
| `rf_claims` | `assigned_employee_id` | `api/sd-data.js:7698` | Tier A, Money | seq1151 |
| `sen_visits` | `assigned_employee_id` | `api/sd-data.js:6121` | Tier A, both axes | seq1152 |

## api/sd-data.js -- 4 more field findings, same hand-verification pass

| Resource | Field(s) | File:line | Register row | Chain seq |
|---|---|---|---|---|
| `alf_op_audits` | `temperature_f` (gated by `record_type`) | `api/sd-data.js:12700` (and `:12708`) | Tier A, REGULATED | seq1153 |
| `rf_claim_agreements` | `include_signature` | `api/sd-data.js:9202` (and `:10240`) | Tier A, Money+contract | seq1154 |
| `rf_jobs` | `source`, `material`, `tesla_certified` | `api/sd-data.js:7311`, `:7345`, `:7354` | (unassigned in the register's own scan) | seq1155 |
| `law_trusttx` | `type` | `api/sd-data.js:15789` | Tier A, REGULATED+Money | seq1156 |

## api/_lib/ai-scan-redaction.js -- 4 AI-redaction field candidates

| Resource | Field | File:line | Register row | Note |
|---|---|---|---|---|
| `memory` | (denominator gap -- no field-naming issue, no register row at all) | `api/_lib/ai-scan-redaction.js:84` | **none** | Corroborates the `shared`-app gap (seq1114/1122/1170) independently |
| `mech_quotes` | `text` | `api/_lib/ai-scan-redaction.js:48` | `docs/CRITICALITY-TIERS.md:495` | Evidence framed entirely around pricing, never the stored model text |
| `mech_takeoffs` | `text` | `api/_lib/ai-scan-redaction.js:44` | `docs/CRITICALITY-TIERS.md:497` | Register's own text already says "not individually read" |
| `scp_progress_photos` | `ai_analysis` | `api/_lib/ai-scan-redaction.js:72` | `docs/CRITICALITY-TIERS.md:543` | Register's own text already says "not individually read" |

## Totals

15 rows: 11 from `api/sd-data.js` (7 ownership + 4 other field), 4 from
`api/_lib/ai-scan-redaction.js`. All line numbers re-verified against
current HEAD at the time this doc was written (batch U), not copied
forward from an earlier batch unchecked.
