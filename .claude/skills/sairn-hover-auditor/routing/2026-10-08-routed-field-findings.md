# Hover-routed field findings -- exact file/line, one row per finding

**Owner proposals added H1 batch X (b6) item 4, per direct instruction.**
Checked before proposing anything, rather than guessed: (1) this
platform has **no durable per-app build-agent assignment** -- all four of
`SAIRN-ACTIVE-WORK-hank.md`, `-cc.md`, `-cody.md`, `-fourth.md` mention
every one of these resource names somewhere in their history (expected,
given their size and age), but a direct grep for each finding's own exact
`file:line` citation against all four active-work files returns **zero
matches, for all 15 rows** -- none of these findings has been individually
picked up by any agent yet. (2) None of the four agents' *current live*
claim (`python tools/sairn_claim.py list`, checked live this session)
declares `api/sd-data.js` or `api/_lib/ai-scan-redaction.js` in its `FILES`.
There is therefore no evidence-based way to name a specific build agent
(Hank/CC/Fourth/Cody) as the real current owner of any one row, and naming
one anyway would be a fabricated claim, not a proposal.

**What IS a real, derived fact, and the actual routing unit this platform's
own claim system uses: the SAIRN app each resource belongs to.** Resolved
via `hover_cold_scan_pool.resource_app_map()` -- the same derived-never-
hand-mapped mechanism this role's own rotation tooling already relies on,
reading `api/_resources/*.js` directly rather than guessing from the
resource name's prefix. Added as its own column below. **Proposed owner,
stated honestly as a proposal and not a verified assignment: whichever
build agent next takes a claim naming that row's app or `api/sd-data.js`
itself** -- the only routing claim this role can make that is not invented.

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

| Resource | App (derived) | Field | File:line | Register row (docs/CRITICALITY-TIERS.md) | Chain seq | Proposed owner |
|---|---|---|---|---|---|---|
| `alf_mar` | sairncare | `assigned_employee_id` | `api/sd-data.js:10545` | Tier A, PHI | seq1146 | next claim on sairncare / api/sd-data.js |
| `alf_staff_credentials` | sairncare | `staff_id` | `api/sd-data.js:12509` | Tier A, REGULATED/licensure | seq1147 | next claim on sairncare / api/sd-data.js |
| `bld_bids` | sairnbuild | `assigned_employee_id` | `api/sd-data.js:5688` | Tier A, Money | seq1148 | next claim on sairnbuild / api/sd-data.js |
| `bld_tna` | sairnbuild | `subject_employee_id` (and `assigned_employee_id` at :5858) | `api/sd-data.js:5767` | Tier A, both axes | seq1149 | next claim on sairnbuild / api/sd-data.js |
| `rf_certifications` | sairnroofing | `employee_id` (two sites) | `api/sd-data.js:7568` and `:7650` | Tier A, REGULATED | seq1150 | next claim on sairnroofing / api/sd-data.js |
| `rf_claims` | sairnroofing | `assigned_employee_id` | `api/sd-data.js:7698` | Tier A, Money | seq1151 | next claim on sairnroofing / api/sd-data.js |
| `sen_visits` | sairnsenior | `assigned_employee_id` | `api/sd-data.js:6121` | Tier A, both axes | seq1152 | next claim on sairnsenior / api/sd-data.js |

## api/sd-data.js -- 4 more field findings, same hand-verification pass

| Resource | App (derived) | Field(s) | File:line | Register row | Chain seq | Proposed owner |
|---|---|---|---|---|---|---|
| `alf_op_audits` | sairncare | `temperature_f` (gated by `record_type`) | `api/sd-data.js:12700` (and `:12708`) | Tier A, REGULATED | seq1153 | next claim on sairncare / api/sd-data.js |
| `rf_claim_agreements` | sairnroofing | `include_signature` | `api/sd-data.js:9202` (and `:10240`) | Tier A, Money+contract | seq1154 | next claim on sairnroofing / api/sd-data.js |
| `rf_jobs` | sairnroofing | `source`, `material`, `tesla_certified` | `api/sd-data.js:7311`, `:7345`, `:7354` | (unassigned in the register's own scan) | seq1155 | next claim on sairnroofing / api/sd-data.js |
| `law_trusttx` | sairnlaw | `type` | `api/sd-data.js:15789` | Tier A, REGULATED+Money | seq1156 | next claim on sairnlaw / api/sd-data.js |

## api/_lib/ai-scan-redaction.js -- 4 AI-redaction field candidates

| Resource | App (derived) | Field | File:line | Register row | Note | Proposed owner |
|---|---|---|---|---|---|---|
| `memory` | **UNRESOLVED** -- not present in any `api/_resources/*.js` registry; the derivation itself names the gap, not a guess | (denominator gap -- no field-naming issue, no register row at all) | `api/_lib/ai-scan-redaction.js:84` | **none** | Corroborates the `shared`-app gap (seq1114/1122/1170) independently | whoever owns the `shared`-app gap already routed at those seqs |
| `mech_quotes` | sairnmechanical | `text` | `api/_lib/ai-scan-redaction.js:48` | `docs/CRITICALITY-TIERS.md:495` | Evidence framed entirely around pricing, never the stored model text | next claim on sairnmechanical / api/_lib/ai-scan-redaction.js |
| `mech_takeoffs` | sairnmechanical | `text` | `api/_lib/ai-scan-redaction.js:44` | `docs/CRITICALITY-TIERS.md:497` | Register's own text already says "not individually read" | next claim on sairnmechanical / api/_lib/ai-scan-redaction.js |
| `scp_progress_photos` | sairnscape | `ai_analysis` | `api/_lib/ai-scan-redaction.js:72` | `docs/CRITICALITY-TIERS.md:543` | Register's own text already says "not individually read" | next claim on sairnscape / api/_lib/ai-scan-redaction.js |

## Totals

15 rows: 11 from `api/sd-data.js` (7 ownership + 4 other field), 4 from
`api/_lib/ai-scan-redaction.js`. All line numbers re-verified against
current HEAD at the time this doc was written (batch U), not copied
forward from an earlier batch unchecked.
