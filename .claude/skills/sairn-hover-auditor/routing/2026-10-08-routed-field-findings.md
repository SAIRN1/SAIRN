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

## api/sb-auth.js, api/dnt-auth.js, api/sd-data.js -- 2 rows, CONFIRMED owner assignment, added H1 batch b10 item 4

Unlike the 15 rows above (proposed owner only, no durable per-app
assignment existed), these two were handed a CONFIRMED owner directly by
Michael this batch: seq958 -> hank, seq965 -> cody. Re-verified against
current HEAD `7671a011` before writing the row, not copied forward from
batch b8/b9's citations unchecked.

| Resource | Finding | File:line | Chain seq | Confirmed owner |
|---|---|---|---|---|
| `api/sb-auth.js` / `api/dnt-auth.js` `setup` action | employee-credential provisioning write body carries no caller/actor attribution field (`license_hash, employee_id, display_name, role, pin_hash, pin_salt, active, updated_at` only) | `api/sb-auth.js:297-304`, `api/dnt-auth.js:403-410` | seq958 | **hank** |
| `sen_caregivers` `read` | any authenticated session (any role) gets the full `data` blob via a bare `verifySessionToken` check, no role gate -- deliberate-by-comment design (line 6027), same class as the already-fixed `alf_staff/read` (seq963) | `api/sd-data.js:6030-6039` | seq965 | **cody** |

Both re-confirmed STILL OPEN and unchanged at `7671a011` -- no commit has
touched either file since batch b8's last re-verify (HEAD `d4ed1a98`).

## tools/sairn_status.py / tools/sairn_claim.py -- claim-liveness defect, added H1 batch b10 item 7

Audited by direct instruction: ted found that stripped hooks make a LIVE
session read as DEAD to every other clone's push gate. CONFIRMED by
reading the code and running status, not assumed from his write-up.

**Mechanism, traced exactly:**
`tools/sairn_claim.py:1281 registry_claims()` calls
`sairn_status.claim_liveness(sess)` (`tools/sairn_claim.py:1321` and the
`own` path at `:1378`). `claim_liveness()` (`tools/sairn_status.py:224`)
reads ONLY the status-registry row at `path_for(session)` and feeds its
`claude_pid` / `claude_start` fields into
`session_lock_check.owner_state()` (`tools/session_lock_check.py:313`),
which compares them against the CURRENT process's real identity and
returns DEAD the moment the pid they name no longer exists.

**Those two fields are refreshed by exactly two paths**: the
`SessionStart` hook (`tools/sairn_status.py --hook`) and the manual
`python tools/sairn_status.py set` CLI (`tools/sairn_status.py:577-578`,
inside the shared row-builder both paths call). **`sairn_claim.py`
itself never calls either.** Its only write to the registry is
`publish_claims()` (`tools/sairn_status.py:167-197`), which re-stamps
`claims`, `claims_updated` and `claims_heartbeat` -- but NOT
`claude_pid`/`claude_start`. The header comment directly above
`claim_liveness()` (`tools/sairn_status.py:212-213`, "the heartbeat is
re-stamped every time the session touches the claim tool") is **not what
the code does**: touching `sairn_claim.py` refreshes the heartbeat
timestamp (the UNKNOWN-fallback signal) but never the pid/start-time
pair that actually decides ALIVE vs DEAD. With the SessionStart hook off,
NOTHING refreshes `claude_pid`/`claude_start` for a session that only
ever runs the claim tool -- so a brand-new, genuinely live session whose
process ID differs from whatever this row last recorded reads as DEAD to
every other clone's push gate until that session happens to run
`sairn_status.py set` manually. Reproduced read-only on this clone:
`python tools/session_lock_check.py status` independently confirms this
session's real pid (`SELF`, matching live), while `claim_liveness()`'s
own verdict depends entirely on the registry row's possibly-stale
`claude_pid` -- the two can disagree exactly as ted described, and did,
in his clone.

**Exact fix needed**, per direct instruction: when
`session_lock_check.owner_state(row)` on the status-registry row answers
DEAD or UNKNOWN, `claim_liveness()` (`tools/sairn_status.py:224`) should
fall back to the SESSION LOCK FILE before concluding DEAD --
`session_lock_check.lock_path(session)` -> `read_lock()` ->
`owner_state()` again on that second, independently-maintained record --
rather than trusting the status-registry row alone. (A narrower
alternative also closes the gap: have `publish_claims()`
(`tools/sairn_status.py:167`) re-stamp `claude_pid`/`claude_start` via
`self_identity()` on every call, which would make the header comment's
existing claim true instead of aspirational -- but the lock-file fallback
is the fix named by this batch's own instruction and is the one being
routed.)

| File | Lines | Finding | Confirmed owner |
|---|---|---|---|
| `tools/sairn_status.py` | `:224` (`claim_liveness`), `:167-197` (`publish_claims`) | liveness depends on a registry row only the SessionStart hook or a manual `set` call refreshes; the claim tool's own touch does not, contrary to the header comment | **cc** (declared `tools/sairn_claim.py` and this liveness path in FILES, batch W) |
| `tools/sairn_claim.py` | `:1281` (`registry_claims`), `:1321`, `:1378` | calls the above without ever re-stamping its own session's pid/start first | **cc** |

## Push blocker: unindexed Drive handoff, added H1 batch b10 item 11

`docs/external-files-index.json` belongs to cc's batch W (declared in his
own `FILES` list) and is NOT in this role's `ALLOWED` scope -- not edited
here, read-only per direct instruction.

**Current symptom** (moves as sessions index their own files, so the
exact path is a point-in-time example, not the whole of the problem):
`G:/My Drive/SAIRN-status/handoff-h2-2026-10-11b.md` is unindexed and
blocking every clone's push. Earlier this same batch cycle it was a
different file (`handoff-fourth-2026-10-11.md`); before that,
`handoff-h2-2026-10-11b.md` itself.

**Exact file:line of the check that refuses:**
`tools/sairn_push_gate_hook.py:1369` -- the `deny(...)` call fired when
`tools/external_file_index_check.py` (invoked as a subprocess at
`tools/sairn_push_gate_hook.py:1361-1363`) exits 1. That script's own
"UNINDEXED work file(s)" listing is generated at
`tools/external_file_index_check.py:350-354`. Note: the hook's own
in-code comment at `tools/sairn_push_gate_hook.py:1343-1345` attributes
`docs/external-files-index.json` to "cody's live claim" at the time this
gate was written; cc's own, more recent batch-W claim also declares the
same file in `FILES`. Routed to cc as the current, live-claimed owner --
not cody -- but the discrepancy is worth Michael knowing about rather
than silently picking one.

**What is actually needed, stated as a question for cc rather than a
fix**: this is not one file, it is a STRUCTURAL gap -- any session that
writes a tool/script/handoff into a declared external directory
(`G:/My Drive/SAIRN-status/` is one) without immediately registering it
in `docs/external-files-index.json` blocks every OTHER clone's push,
platform-wide, until someone who owns that index notices and fixes the
specific file. Worth asking whether the index-registration step should
be automated at write-time (a hook on the external directory itself) or
whether the push gate should warn-not-deny for a FIRST offense within
some window, since a hard platform-wide deny on one session's missed
step is a wide blast radius for a small omission.

| File:line | Finding | Confirmed owner |
|---|---|---|
| `tools/sairn_push_gate_hook.py:1369` (denies), `tools/external_file_index_check.py:350-354` (detects) | unindexed external handoffs/tools/scripts under a declared directory block every clone's push; the specific unindexed file rotates as sessions catch up, the structural gap does not | **cc** (owns `docs/external-files-index.json`, batch W) |

## Totals

15 rows (batch U/X) + 2 rows (batch b10 item 4, confirmed owner) + 1 item
(batch b10 item 7, claim-liveness defect) + 1 item (batch b10 item 11,
push-blocker structural gap) = 19. All line numbers re-verified against
current HEAD at the time each section was written, not copied forward
from an earlier batch unchecked.
