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
| ~~`api/sb-auth.js` / `api/dnt-auth.js` `setup` action~~ **FIXED, commit `16245537`** (`auditPinSetup`, see item 12 below) | employee-credential provisioning write body carries no caller/actor attribution field | `api/sb-auth.js:297-304`, `api/dnt-auth.js:403-410` | seq958 | **CLOSED** (was hank) |
| `sen_caregivers` `read` | any authenticated session (any role) gets the full `data` blob via a bare `verifySessionToken` check, no role gate -- deliberate-by-comment design (line 6027), same class as the already-fixed `alf_staff/read` (seq963) | `api/sd-data.js:6030-6039` | seq965 | **cody** |

Both re-confirmed STILL OPEN at `7671a011` as of batch b10; seq958 is
now CLOSED (see above, b14 item 5) and seq965 remains open (see the
follow-on section below, b13 item 5).

**seq958, batch b14 item 5 correction:** a naive grep for the new
`auditPinSetup` helper across all 17 `*-auth.js` files found 3 without
it (`law-auth.js`, `sc-auth.js`, `sd-auth.js`), which looked like 3
still-open files. All three already have real caller attribution via a
different/older mechanism -- `sc-auth.js`/`sd-auth.js` via a direct
`writeAuditLog` call dated to the original fix (commit `94becffb`,
confirmed back in batch b7), `law-auth.js` via its own pre-existing
local wrapper, deliberately left alone. True count: zero of 17 genuinely
open **at the application-code layer**. No routing needed for the code.

**seq958, batch b15 item 5 -- a DEEPER layer the b14 correction missed.**
`python tools/audit_event_type_check.py` (exit 1, code-level only, no
live writes) finds that 2 of those "fine" 17 map to a DATABASE table
whose `CHECK` constraint REJECTS the `event_type` they actually emit --
`writeAuditLog` is non-fatal and returns `false` on a CHECK violation,
so the row is silently absent, the SAME end result (no recoverable
grant record) as the original finding, at a different layer.

| File | Emits | Table | CHECK rejects it? |
|---|---|---|---|
| `api/sc-auth.js` | `pin_setup` | `sairncode_audit_log` | **YES** -- CHECK allows only `ai_call`/`ai_call_blocked`/`ai_call_failed`/`ai_injection_flagged` |
| `api/sd-auth.js` | `pin_setup` | `stonedesk_audit_log` | **YES** -- CHECK allows only `credential_change_refused`/`credential_deactivated`/`credential_reactivated` |
| `api/law-auth.js` | `pin_setup` | `sairnlaw_audit_log` | no -- `pin_setup` IS in its allowed list; its 6 rejected values (`ai_interaction` etc.) are unrelated to setup attribution |
| all 14 files using `auditPinSetup()` | (helper-resolved) | per-app, via `AUDIT_TABLE_BY_APP` | no -- not flagged by this run |

**Fix spec:** widen `sairncode_audit_log`'s and `stonedesk_audit_log`'s
`event_type` CHECK constraints (in their `sql/*.sql` DDL) to include
`pin_setup`, matching the shape already used for the other 14 tables.
A SQL DDL change, not a code change -- and per this tool's own stated
limit, its "CHECK" is read from the file in `sql/`, not proven live in
Supabase, so the fix also needs a live migration run, which this role
cannot do. **Routed to hank** (owns both `sc-auth.js`/`sairncode` and
`sd-auth.js`/stonedesk, the two affected apps).

**Update, H1 batch b16 items 3/4: the exact SQL already exists, written
by hank, in `docs/2026-10-07-hank-migration-sql-for-michael.md` STEP
0a (SAIRNcode), 0b (StoneDesk), 0c (SAIRNlaw). Per the new fact this
batch, Michael ran the full migration in Supabase on 2026-10-13.** But
the repo's own tracked `sql/sairncode_audit_log_schema.sql:56-61` and
`sql/stonedesk_audit_log_schema.sql` (same shape) still carry the OLD,
narrow `CHECK` -- confirmed by direct read, no `pin_setup` in either
file's list. **Two independent facts, neither proves the other**: a
live Supabase run does not update a checked-in `.sql` file, and this
role has no live DB access to confirm the live run's own success either.
`tools/audit_event_type_check.py` (file-based) will keep reporting
these as REJECTING until the DDL files themselves are edited to match
STEP 0a/0b/0c -- a real repo-vs-production sync gap, separate from
whether Michael's live run itself succeeded. **Still routed to hank**:
update the two DDL files to match what was actually run.

The 13 new tables (STEPS 1-13) and `rf_schedule`'s 3 new columns (STEP
14) are confirmed present in `sql/` and self-consistent with current
code (zero rejections reported for any of them). The CODE that would
USE the 13 new tables (most of `api/_lib/audit.js`'s 14-file
`auditPinSetup()` set already does) and `rf_schedule/set_status`'s own
use of its 3 new columns are correctly EXPECTED still open pending
hank's next batch -- not re-flagged as a defect here, per this batch's
own instruction.

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

### Reproduction, H1 batch b13 item 10 -- a live claim read as DEAD, on demand

**Note on attribution: this batch's own dispatch said "cody reported" the
DEAD-from-stale-row symptom. The actual report found is `ted`/`fourth`'s**
(`docs/handoff-fourth-2026-10-11.md:81-91`), not cody's -- named here so
the record is accurate rather than silently going along with the wrong
name. Ted's own account: a push landed, the gate printed `CLAIM STATE:
DEAD -- CLAUDE_PID 64304 no longer exists` for the PREVIOUS session's
pid, while `sairn_claim.py check` had said `SAME WORK` and
`session_lock_check.py` correctly reported `SELF` -- because the
SessionStart hook (which writes the registry row) was one of the 23
disabled, so the row kept a dead pid from before.

**Reproduced directly on this clone, with a genuinely live, currently
held claim, not a hypothetical:**

1. Took a real local claim (`hover`, `--no-push`) -- confirmed `own`
   reports `HELD`, `CLAUDE_PID 30428` (this session's real, live pid).
2. Backed up `~/SAIRN-SESSION-LOCKS/status/hover.json`, then overwrote
   only `claude_pid` to `999999` (a pid that does not exist) and
   `claude_start` to `1` -- simulating exactly the stale-SessionStart-row
   state ted described, without touching anything else.
3. `python tools/sairn_claim.py own` immediately answered: *"WARNING:
   this session is working WITHOUT a held claim (DEAD)"* -- for a claim
   that had not changed, was not released, and was still genuinely held.
4. **At the same moment**, `python tools/session_lock_check.py status`
   correctly answered `state: SELF -- this session owns the lock
   (CLAUDE_PID 30428)` -- the two tools disagreed on the identical live
   session, in real time, confirming the exact split ted described.
5. Restored the backup verbatim, confirmed `own` returns to `HELD`, then
   released the test claim (`--no-push`) to leave no trace in the real
   claim record beyond the two reversible local commits.

This closes the loop from "confirmed by reading code" (batch b10 item 7,
b11 item 10, b12 item 10) to "confirmed by forcing the exact failure on
demand." The fix needed is unchanged from the rows above.

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

## seq1018/1022/1036 -> hank, seq1037 -> ted, added H1 batch b11 item 4

Lines re-verified fresh at current HEAD `f7e03133`, not copied from b10
-- all three api/sd-data.js citations had SHIFTED since b10 (other
sessions' commits landing on a shared file), confirmed via `git diff
HEAD -- api/sd-data.js` showing no local drift, so the shift is real
upstream movement, not a local error.

| Seq | Finding | File:line (current) | Fix spec | Owner |
|---|---|---|---|---|
| 1018 | `msb_sales`/`write` stores a sale/void record with no actor attribution | `api/sd-data.js:4929-4953` (was `:4686-4710` at b10, was `:4623-4649` originally -- shifted +243 then +203 lines across two batches of unrelated upstream commits) | Add a server-stamped `actor_employee_id` (or equivalent) field to the write body at `:4948`, sourced from a verified session token the way the void sub-path already derives `msbCaller` at `:4939`, not from client payload | **hank** |
| 1022 | Every resource gated through `SD_SESSION_GATED` (`api/sd-data.js:817-1437`, recount: 93 action-strings now, not 70 or 77 -- the comment's own count has drifted further) is session-verified but never attributed; `gateSession` (`api/sd-data.js:1753`, was `:1510`) resolves an identity and discards it -- `grep -c gateSession.employee_id` is still 0 | `api/sd-data.js:817`, `:1753` | Stamp `gateSession.employee_id` onto the write body wherever the generic `SD_SESSION_GATED` dispatch performs a write, mirroring the one-off pattern already used for `msbCaller`/`employeeCaller` elsewhere in this file -- a single shared fix point since the gate itself is one function | **hank** |
| 1036 | Stale comment: code says "70 action-pairs" twice (`:1629`, `:1765`, was `:1386`/`:1522`); real count is now 93, not 77 -- the drift has grown, not shrunk | `api/sd-data.js:1629`, `:1765` | Update both comment occurrences to the real, re-derived count (93 as of this batch) or better, replace the hardcoded number with a computed one (`Object.keys(SD_SESSION_GATED).length`-equivalent) so the comment cannot drift again | **hank** |
| 1037 | `docs/scrutiny-flags.json`'s commit `5080cf60`'s own WEAKENING-flag count no longer matches its landing-commit claim of "3 of 3 WEAKENING flags were PROSE" | `docs/scrutiny-flags.json`, the single entry with `sha` `5080cf60737544eb5f95cff4aa390a50ef9673e4` (1 entry now, `level: WEAKENING` -- unchanged from b10's re-verify, b10 noted this had already dropped from 9/2 to 1/1, likely corrected/deduplicated by cc) | Re-confirm against commit `5080cf60`'s actual diff whether 1 WEAKENING flag is the CORRECT count (it may already be fixed) or whether the ledger still owes a correction; if correct, update/retire the landing-commit's own prose claim ("3 of 3") rather than the ledger | **ted** (reassigned this batch; original target was `cc`) |

**Re-run H1 batch b14 item 3, by-directory routing confirmed** (`api/`
-> hank, `docs/` -> ted, matching the table above exactly): all four
re-confirmed STILL OPEN at current HEAD `5d753979` (after this batch's
own rebase onto real current origin/main) -- anchors unchanged from the
row above (`:4929`, `:817`/`:1753`, `:1629`/`:1765` all identical; the
`docs/scrutiny-flags.json` entry still 1/WEAKENING). No upstream
movement on any of the four this round.

## hover2 cluster (seq630-660), rotated in H1 batch b11 item 9

Skipped in b10 because hover2's own claim was active over this exact
scope; hover2's claim has since released (confirmed via `sairn_claim.py
list`, no hover2 row). Each verified against CURRENT code at HEAD
`f7e03133`, not against hover2's own log text, via a read-only Explore
pass over `api/sd-data.js` / `api/sairncash/verify.js`.

**RECONFIRMATION STAMP, applies to every row below unless the row
itself says otherwise**: re-reproduced via the real repro scripts
(`grd_session_gate_repro.py`, `scp_session_gate_repro.py`,
`derive-charges.test.js`) in **H1 batch b14 item 9**, and the `681` row
specifically flipped to FIXED in **H1 batch b15 item 8** (see that row's
own text). Added per batch b15 item 9 (every status line gets a
repro-date anchor, following the seq951 root cause) -- this single
stamp covers the whole table instead of repeating it in all 8 rows.

| Seq | Topic | Current file:line | Status | Owner |
|---|---|---|---|---|
| 630/634 | `grd_invasive_sightings`, `grd_cart_orders`, `grd_training_courses`, `grd_training_completions` -- originally "no session gate at all" | `api/sd-data.js:4343-4366` (shared `GRD_SESSION_RESOURCES` prelude) | **FIXED** -- a single shared gate now calls `verifySessionToken(..., 'sairngrounds')` ahead of all 20 `grd_*`/bare-name branches. Comment at `:4325-4329` ("ONE SHARED PRELUDE, NOT TWENTY-ONE COPIES") and `:4331-4338` log the remaining gap honestly: session-only, no role differentiation, as a stated open product decision, not an oversight | closed, no routing needed |
| 648/660 | `grd_session_gate` (the generic grd_ dispatch-region gate) | `api/sd-data.js:4343-4366` | **FIXED**, same mechanism as above | closed |
| 648/660 | `alf_mar_billing_disclosure` -- medication names leaking to `billing` role via `derive_charges` | `api/sd-data.js:11041-11047` (gate), `:11100`, `:11104` (fix) | **FIXED** -- `ALF_MAR_ROLES` (owner/nursing/med_aide) now gates `description`; a `billing`-role caller gets an empty string instead of the drug name | closed |
| 648 | `dnt_appointments_write_gate` -- write had no ownership restriction while read did | `api/sd-data.js:15560-15563` (session), `:15614-15660` (provider-ownership check) | **FIXED**, dated 2026-10-11 per in-code comment -- a non-broad-read-role caller is now checked against `provider_id` on both payload and existing row, 403 `NOT_YOUR_APPOINTMENT` on mismatch | closed |
| 652 | `scp_irr_zones` | `api/sd-data.js:5293-5313` | **STILL UNGATED, but DELIBERATE** -- comment at `:1372-1375` names it the test suite's `UNGATED_WITNESS` negative control | not routed -- intentional fixture, not a live finding |
| 652 | `scp_irr_schedules` | `api/sd-data.js:5314-5333` | **STILL UNGATED, genuinely open** -- no session/role check, not in `SD_SESSION_GATED` | **cody** (owns `tests/sairncode_gates.js` / sairnscape per prior batches) |
| 652 | `scp_water_features` | `api/sd-data.js:5335-5354` | **STILL UNGATED, genuinely open** -- same shape as above | **cody** |
| 681 | ~~`sairncash_verify_token_mint` -- a bare, valid `subscriptionId` mints a Firebase auth token with no ownership check~~ **FIXED, H1 batch b15 item 8** | `api/sairncash/verify.js:107-137` | Commit `16245537`'s sairncash half: a caller must now present both `subscriptionId` and the real Stripe customer id, checked against what Stripe returns -- a leaked `subscriptionId` alone no longer mints anything. Repro script re-run, now reports "NO FINDING", confirmed by direct code read at `:118-137`. | **CLOSED** (was hank, highest-severity item in that rotation) |

**seq701 explicitly NOT routed as open**: hover2's own log entry for it
reads "NOW RESOLVED, not undetermined" -- it is a closed audit-trail
review of a bypass-log cluster, not a live finding; it only appears in
`hover_routing_gap_check.py`'s UNROUTED list because it was never
written to the shared index, which is a reporting gap, not a defect.
Left alone rather than falsely routed as open.

## Totals

## Rotation, H1 batch b12 item 11 -- the next 5 oldest by seq with no row anywhere in this doc

Checked which of hover's own backlog (seq913-1037) still has no routing
row at all (searched this file for each seq number first, rather than
assuming): seq913, 920, 929, 946, 951, 959, 992 have none. The next 5
oldest by seq are 913/920/929/946/951.

**913, 920, 929, 946 are NOT independently routable findings.** Read in
full before writing this: all four are this role's own PROCESS/meta
entries (913: backfilling other entries' routing metadata; 920:
re-pulling a live unrouted count against a moving target; 929: already
IS a routing action in its own text, "ROUTED DIRECTLY TO HANK BY NAME
WITH THE FULL SPEC RESTATED"; 946: a rotation-draw pick log, not a code
defect). Writing a fix-spec row for a bookkeeping note would fabricate a
finding that does not exist. Not routed, named here instead so the next
session does not re-discover the same non-finding.

**951 is a real finding** and got a proper row (text left below as
originally written). **CORRECTED, H1 batch b13 item 6: this role's own
"still-open" call was WRONG.** The citation `:187` was a different,
unrelated, always-attributed write; the real write site (`logRec`) was
never re-read past that grep hit in either the b11 or the b12 check.
**ACTUALLY FIXED, commit `9bc99c05`, dated 2026-10-12** -- `logRec` at
`api/legal-citator.js:394` now carries `employee_id` and `employee_role`.
`sql/sairnlaw_citator_schema.sql:145-156` already declares both columns
(plus a defensive `alter table add column if not exists` at `:165-167`).
No further action needed on this row.

| Seq | Finding | File:line | Fix spec | Owner |
|---|---|---|---|---|
| 951 | ~~`api/legal-citator.js`'s feedback action (SAIRNlaw) never records which employee confirmed/corrected a legal-citation treatment~~ **FIXED, see correction above** | `api/legal-citator.js:187` (`employee_id: caller ? caller.employee_id : null`), write site `:380` (`logRec`) | Stamp a real session's `caller.employee_id` the way the sibling attribution fixes (commits `56bbce5e`, `4ec0d5d5`) already did for 15 other write paths across three apps -- this one was not among them | **CLOSED** (was: next claim on sairnlaw / api/legal-citator.js) |

**959 and 992 also checked, neither needs a new row.** seq959
(stonedesk-track/sd-sub-data attribution) re-confirmed FIXED this batch
(`employeeCaller.employee_id` present at `api/sd-sub-data.js:298, :427,
:508`) -- closed, no routing needed. seq992 (bypass-log blanket-form
ratio) is a standing metric re-measured every batch it comes up (most
recently this batch, item 6... no, item 13: 17.1%), not a single
fixable code location -- tracked by re-measurement, not a routing row.

## Totals

15 rows (batch U/X) + 2 rows (batch b10 item 4, confirmed owner) + 1 item
(batch b10 item 7, claim-liveness defect) + 1 item (batch b10 item 11,
push-blocker structural gap) + 4 rows (batch b11 item 4, fix specs) + 8
rows (batch b11 item 9, hover2 cluster re-verify) + 1 row (batch b12
item 11, seq951) + 7 rows (batch b12 item 7, Tier-register completeness)
= 39. All line numbers re-verified against current HEAD at the time
each section was written, not copied forward from an earlier batch
unchecked.

## Tier-register completeness (seq1150), resolved H1 batch b12 item 7

A background Explore pass compared `docs/CRITICALITY-TIERS.md`'s full
resource population against `api/_resources/*.js` (the canonical
per-app registries `api/sd-data.js` itself validates against -- more
authoritative than scanning `resource === '...'` dispatch alone, since
several resources are dispatched generically through verb-maps). Method
and files are stated here so the comparison is re-runnable, not just
asserted: register rows extracted from the per-app `###` sections
(`docs/CRITICALITY-TIERS.md:142-614`, `grep -oE "^\| \`[a-zA-Z0-9_]+\`"`,
deduped); code list from the 18 `api/_resources/*.js` files
(`sairncode.js` uses a differently-shaped `const RESOURCES = [...]`,
not the same literal-array style as the other 17 -- worth knowing if
anyone re-runs this).

**Register: 391 unique resource names. Code: 398.**

**Gap 1 (register -> code, stale rows): 0.** Every register row traces
to a real current resource. **No action needed.**

**Gap 2 (code -> register, unregistered): 7, all from
`api/_resources/shared.js:52-59`** -- cross-app resources with no single
owning app, and `docs/CRITICALITY-TIERS.md` has no `shared` section for
them to land in structurally:

| Resource | File:line | Register row | Note |
|---|---|---|---|
| `profile` | `api/_resources/shared.js:53` | none | |
| `memory` | `api/_resources/shared.js:54` | none | **UPDATES the existing row above** (seq1114/1122/1170, "not present in any `api/_resources/*.js` registry") -- that finding is now STALE in its exact claim: `shared.js` exists and lists `memory` directly. The underlying gap (no Tier row) is unchanged and real; only the described CAUSE has moved from "no registry at all" to "a registry with no register section to land in." |
| `employees` | `api/_resources/shared.js:55` | none | |
| `slabs` | `api/_resources/shared.js:56` | none | |
| `render_usage` | `api/_resources/shared.js:57` | none | |
| `shared_knowledge` | `api/_resources/shared.js:58` | none | |
| `employee_profile` | `api/_resources/shared.js:59` | none | |

**Fix spec, one for all seven:** add a `### \`shared\`` section to
`docs/CRITICALITY-TIERS.md` (matching the existing per-app `###`
pattern) and give each of these seven its own row -- this is a
`docs/CRITICALITY-TIERS.md` edit, outside this role's `ALLOWED` scope
(not `docs/defect-density-register.json`), so routed rather than done
here.

**Owner: next claim naming `docs/CRITICALITY-TIERS.md` or
`api/_resources/shared.js`** -- no durable per-app owner exists for
`shared`-scoped resources by construction (they belong to no one app),
same caveat the original 15-row table states for its own proposals.

## seq1150, the 7 unregistered resources named individually with suggested tiers -- H1 batch b13 item 3

CONFIRMED owner **hank** this batch (supersedes the proposed-owner line
above with a direct assignment). Anchors re-verified unchanged at HEAD
`90e1e21a` (`git diff HEAD origin/main -- api/_resources/shared.js
docs/CRITICALITY-TIERS.md` is empty -- neither file moved since the b12
check).

| Resource | File:line | Anchor | Dispatch branch | Suggested tier | Why |
|---|---|---|---|---|---|
| `profile` | `api/_resources/shared.js:53` | `'profile',` in the `resources:` array | `api/sd-data.js:1780` (read), `:1790` (write) | **B** | App/license-level profile data -- business-identifying, not individual PII |
| `memory` | `api/_resources/shared.js:54` | `'memory',` | `api/sd-data.js:1620` (`MEMORY_APPS` gate), `:1705`, `:1751` | **A** | AI memory storage can carry arbitrary stored content from any app, including PII fed to it elsewhere -- same concern already raised for the `shared`-app gap at `api/_lib/ai-scan-redaction.js:84` |
| `employees` | `api/_resources/shared.js:55` | `'employees',` | `api/sd-data.js:1843` (read), `:1969` (write) | **A** | StoneDesk's own employee roster -- names, roles, employment PII, already role-gated via `EMPLOYEES_READ_DENIED_ROLES` |
| `slabs` | `api/_resources/shared.js:56` | `'slabs',` | `api/sd-data.js:3114` (read), `:3121` (write), `:3302` (reserve/release) | **B** | StoneDesk material inventory -- business/money-adjacent, not PII |
| `render_usage` | `api/_resources/shared.js:57` | `'render_usage',` | `api/sd-data.js:5429` (read) | **C** | A monthly AI-render usage COUNT only (`sd_render_usage?...&select=count`) -- no PII, no direct dollar figure, though it may feed a billing limit elsewhere |
| `shared_knowledge` | `api/_resources/shared.js:58` | `'shared_knowledge',` | `api/sd-data.js:5478-5494` (read/write, SAIRNlegacy-scoped branch plus a generic one) | **B** | Cross-app knowledge-base content -- business-sensitive, content varies by app, not individual PII by construction |
| `employee_profile` | `api/_resources/shared.js:59` | `'employee_profile',` (comment above it: "StoneDesk Employee Profiles (2026-08-06)") | `api/sd-data.js:3053` (read), `:3079` (write) | **A** | Individual employee profile data -- PII, same class as `employees` |

These suggested tiers are this role's own read of the dispatch code, not
a verified register classification -- hank should confirm/adjust when
adding the `### \`shared\`` section, same as any other Tier assignment
on this platform.

## seq965 follow-on, a second read path -- H1 batch b13 item 5

Found while independently re-verifying every `sen_caregivers` read path
after commit `b384a513`'s fix. Not itself a PII value leak (traced all
the way through, see the self-log entry) -- a narrower presence-only
signal, named for tightening rather than as an open vulnerability.

| Finding | File:line | Anchor | Fix spec | Owner |
|---|---|---|---|---|
| `sen_visits`/`readiness` (`api/sd-data.js:6725`) reads `sen_caregivers` RAW at `:6746`, bypassing `SEN_CAREGIVER_HR_FIELD_ROLES`; reachable by the broader `SEN_READINESS_ROLES` (owner/billing/coordinator/scheduler) | `api/sd-data.js:6746`, `api/_lib/sen-evv-readiness.js:291` (`caregiver.state_caregiver_id` presence check) | `const gr = await fetch(rest('sen_caregivers?...` | Apply the same `SEN_CAREGIVER_HR_FIELD_ROLES`-style strip to the `caregiversById` map before passing it to `summarize()`, or have `checkVisit` only ever receive a pre-redacted caregiver object | **cody** (owns the seq965 area this batch) |

## seq992, recounted -- H1 batch b14 item 4

Recounted fresh, not copied: `docs/BYPASS-LOG.jsonl` now has 93 raw rows
(up from 77 at b13 -- 16 new rows all landed as `blanket`), 1 retraction,
92 live. **Scoped uses: still exactly 13** -- the dispatch's own figure
holds, unchanged from b13, because none of the 16 new entries used the
scoped form. Ratio: 13/92 = 14.1% (down from b13's 17.1%, purely from
blanket-row growth with zero new scoped adoption).

Exact `docs/BYPASS-LOG.jsonl` line numbers for the 13 scoped rows (1
line = 1 JSON object): `:42` (hank, 2026-09-26), `:58-69` (cc, all on
2026-10-07, the same adoption burst b7 first reported as "1->13"). No
scoped use has landed from ANY session since 2026-10-07T15:59:21Z --
the adoption trend has been flat for multiple batches running now, not
merely "plateaued."

**Routed to hank** (standing target for this platform-wide finding) --
not a single-file fix, a behavioral metric: worth a direct question
rather than another routing row, since re-measuring the same flat number
every batch adds no new information.

**Classified by owner, H1 batch b15 item 7.** Recounted again (origin
moved mid-batch): raw now 94, scoped still exactly 13, unchanged. The
13 split by the session that logged each (this file, `docs/`, is the
only location these uses live in -- there is no separate `api/`/
`tests/`/`tools/` file per bypass, so "owner" here is the session that
ran the bypassed push, not a directory):

| Owner | `docs/BYPASS-LOG.jsonl` line(s) | Count | Dates |
|---|---|---|---|
| **hank** | `:42` | 1 | 2026-09-26 |
| **cc** | `:58-69` | 12 | 2026-10-07, one adoption burst |

Routed: hank's 1 and cc's 12 are both already-landed historical pushes,
not open code to fix -- nothing to route per-row. The open question
remains the one stated above: zero NEW scoped uses from any session
(hank, cc, or otherwise) since 2026-10-07T15:59:21Z.

## seq664 (bld_draws), hover2's own repro DISAGREED WITH -- H1 batch b14 item 8

Ran `.claude/skills/sairn-hover-auditor/tools-hover2/bld_draws_bypass_repro.py`
against this clone's tree (confirmed byte-identical to origin/main on
`api/sd-data.js` first, so this stands in for a fresh clone). The script
says `BYPASS CONFIRMED`. **This role disagrees, by direct code read, not
by re-running the tool again**: commit `86189e37` added a dedicated
`resource === 'bld_draws' && (action === 'read' || action === 'write')`
branch at `api/sd-data.js:13273-13278` that requires a real session
(`verifySessionToken`) and returns 401 if absent -- placed BEFORE the
generic `BLD_RESOURCES` loop the script inspects (`:13310`, `:13322`).
The generic blocks genuinely have no session check of their own, but
execution only reaches them for `bld_draws` after the prepended gate has
already passed. **The fix is correct and complete; the script is stale**
and gives a false positive because it has no model of the new prepended
branch. Not fixed here -- `tools-hover2/` is hover2's own tooling, not
this role's to edit. Flagged so the next session does not trust the
script's bare exit code over the code itself.

**The exact false positive, for H2 -- H1 batch b15 item 3, not edited
in the script itself.**

`bld_draws_bypass_repro.py:53-55` (`GENERIC_READ` regex) inspects ONLY
the body of `if (BLD_RESOURCES[resource] && action === 'read') { ... }`
for `verifySessionToken`. `:56-59` (`BESPOKE_DRAWS` regex) looks for
exactly ONE other shape: `if (resource === 'bld_draws' &&
(action === 'wip' || action === 'release_retainage')) { ... }`. The
script's own docstring (around `:40-44`) already names the general
limitation -- "it cannot see a generic dict-keyed dispatch... or a
compound action condition... at all" -- but that was written before the
real fix landed in a THIRD shape neither regex matches.

**The exact input that triggers it**: the real fix at
`api/sd-data.js:13273-13278` --

```
if (resource === 'bld_draws' && (action === 'read' || action === 'write')) {
  const dSession = verifySessionToken(tokenFromRequest(req), licHash, 'sairnbuild');
  if (!dSession) { res.status(401).json(...); return; }
  ...
}
```

This is neither of the two shapes `GENERIC_READ`/`BESPOKE_DRAWS` were
written to recognize (its action condition is `'read' || 'write'`, not
`'wip' || 'release_retainage'`, and its resource test is
`resource === 'bld_draws'`, not the dict-keyed `BLD_RESOURCES[resource]`
the first regex requires). Neither regex matches this block, so
`analyze()` never sees that a session check already ran before the
generic blocks it DOES match -- and reports `BYPASS CONFIRMED` on code
that is actually gated. **Suggested fix, for H2 to apply in their own
script, not applied here**: add a third pattern matching
`if (resource === 'bld_draws' && (action === 'read' || action === 'write'))`
(or more generally, scan for ANY `if` block testing the same
`resource`/`action` pair that appears textually BEFORE the generic
block in the file, not just the two hardcoded shapes) before concluding
`bypass = True`.

**CLOSED, H1 batch b16 item 6.** H2 fixed it -- pulled 97 new lines in
`bld_draws_bypass_repro.py`. Ran it independently: main run now reports
`NO BYPASS` (a dedicated, gated branch is detected correctly); `--selftest`
now PASSES with a genuine control pair added (`dedicated-gated=no-bypass`
vs `dedicated-ungated=bypass`), proving the fix discriminates rather than
just reporting clean unconditionally. Confirmed real.

## Hooks-off exposure audit, 4 citation-drift findings -- H1 batch b15 item 4

Audited the 5 commits since 2026-10-11 touching `api/*-auth.js`,
`api/_lib/*`, or the `SD_SESSION_GATED` gate region, via a background
subagent. **Zero regressions traced to the hooks being off** --
`redaction_check.py` (clean, all 5), `html_script_check.py` (clean, the
3 that touch `.html`), `node --check` (clean), zero conflict markers.
`citation_drift_hook.py` was never in scope for any of the 5 (it only
ever covers `docs/CRITICALITY-TIERS.md` / `docs/tier-a-reviews.json`),
so its disablement is not the cause of what follows.

**What the audit DID surface, independently of the hooks question: 4
code-comment citations that were wrong at the moment they were
written**, not drift from later unrelated commits:

| Commit | Cited | Real location | Off by |
|---|---|---|---|
| `0442646c` | `api/sd-data.js:5231` (the `qc_status`/`verifySessionToken` branch) | `api/sd-data.js:5314` | 83 |
| `86189e37` | `api/sd-data.js:8496` (the `rf_draws` branch) | `api/sd-data.js:8796` | 300 |
| `86189e37` | `sairnbuild.html:5726` ("echoes them back into the local list") | `sairnbuild.html:5743-5745` | ~18 |
| `b7f6fb54` | `sairnfreedom.html:7684` (a `DOMContentLoaded` handler) | `sairnfreedom.html:7721` | 37 |
| `b7f6fb54` | 6 write-site citations in one block (`:3424,:3523,:3509,:4976,:4628,:4739,:5168`) | `:3479,:3578,:3564,:5031,:4683,:4794,:5223` | **55, uniformly** |

The `b7f6fb54` 6-citation block being off by the exact same 55 lines
each suggests the whole block was written against one stale snapshot of
the file, not six independent slips. **Routed to hank** (owns
`api/sd-data.js`, `sairnbuild.html`, `sairnfreedom.html`) -- fix spec:
re-point each citation to its real current line; no code-behavior
change needed, comment-only.

## Three new rules, spec + baseline only -- H1 batch b16 items 7-9, not implemented

Full detail in the three files below, not duplicated here. Each
confirms the baseline by an independently re-run, selftest-passing
probe, not assumed.

- **bld_draws, owner/upper-management-only rule**:
  `.claude/skills/sairn-hover-auditor/references/bld-draws-ownership-rule-probe-spec.md`
  + `.claude/skills/sairn-hover-auditor/tools/bld_draws_ownership_rule_probe.py`.
  Real sairnbuild roles: `owner`, `pm`, `office` -- no `supervisor`/`employee`
  role exists. Baseline gap: `pm` currently ALLOWED on `bld_draws`
  read/write (the new rule would DENY it); per-job ownership scoping
  does not exist on `bld_draws`/`bld_jobs` at all (new schema work, not
  invented here).
- **SAIRNfreedom post-staff gate, 5 named Tier A resources**:
  `.claude/skills/sairn-hover-auditor/references/sf-post-staff-gate-rule-probe-spec.md`
  + `.claude/skills/sairn-hover-auditor/tools/sf_post_staff_gate_probe.py`.
  Baseline: all 10 cells (5 resources x read/write) open on BOTH the
  unauthenticated and cross-post axes today, confirmed, no partial
  protection on any of them.
- **SAIRNfreedom per-resource role matrix (all 36 `sf_` resources)**:
  `.claude/skills/sairn-hover-auditor/references/sf-role-matrix-adversarial-checklist.md`.
  **Premise corrected in the file itself**: no real SAIRNlaw role-matrix
  template existed yet when this was written (cody's b5 landed later,
  mid-batch) -- built from cody's own DESCRIBED spec instead. Real role
  vocabulary: `post.govern`, `post.govern.deputy`, `records.write`,
  `finance.write`, `member.admit`, `services.refer`, `legal.review`,
  `history.write`, `ceremonial.manage`, `chaplain.pastoral` -- not
  "officers/canteen/members." Current state: 14/36 ungated, 22/36
  session-only, 0/36 role-checked.

**Routed to hank** (owns SAIRNbuild and SAIRNfreedom) as specs +
baselines for a future implementation decision -- no fix made, per
explicit instruction.

## Citation-drift findings re-verified against current HEAD -- H1 batch b18 item 3

Re-read each of the 4 citation-drift findings above directly against
origin/main HEAD (`618cbd9f`) rather than trusting the b15 table's "real
location" column, which was itself already two batches old. All 4 are
STILL OPEN -- none have been corrected -- and every one has drifted
FURTHER since b15, confirming these are genuinely stale comments (not
self-correcting) rather than a one-time miss:

| Stale comment, still at | Still cites | b15's real (now stale too) | REAL as of this batch | Drift since b15 |
|---|---|---|---|---|
| `api/sd-data.js:5422` (+3 others, see below) | `api/sd-data.js:5231` | `:5314` | `api/sd-data.js:5422` | +108 |
| `api/sd-data.js:13260` | `api/sd-data.js:8496` | `:8796` | `api/sd-data.js:8822` | +26 |
| `api/sd-data.js:13283` | `sairnbuild.html:5726` | `:5743-5745` | `sairnbuild.html:5743-5745` | **0 -- unchanged** |
| `api/sd-data.js:1145` (+3 others, see below) | `sairnfreedom.html:7684` | `:7721` | `sairnfreedom.html:7740` | +19 |

The 6/7-citation block (`api/sd-data.js:1139-1140`, unchanged location)
has drifted NON-uniformly this time -- b15's finding that it moved by a
uniform +55 across all 7 numbers no longer holds:

| Still cites | b16/b17's real (stale too) | REAL now | Drift since b16/b17 |
|---|---|---|---|
| `:3424` (sf_sessions write) | `:3479` | `sairnfreedom.html:3492` | +13 |
| `:3523` (inside sfRecordResults, `:3509`) | `:3578` (fn at `:3564`) | `:3591` (fn at `sairnfreedom.html:3577`) | +13 |
| `:4976` (sf_sessions write) | `:5031` | `sairnfreedom.html:5050` | +19 |
| `:4628` (sf_tickets write) | `:4683` | `sairnfreedom.html:4702` | +19 |
| `:4739` (sf_shifts write) | `:4794` | `sairnfreedom.html:4813` | +19 |
| `:5168` (sf_rentals write) | `:5223` | `sairnfreedom.html:5242` | +19 |

The split (+13 for the two sites inside/near `sfRecordResults`, +19 for
the four later sites) means something was inserted between those two
groups since b16/b17 -- the block is no longer drifting as one uniform
unit the way it was at b15. Named as its own small observation, not
chased further (out of this batch's scope to find what inserted those 6
lines).

Comment-only fix needed on all of the above; no code-behavior change.
Still routed to hank, same as b15/b16/b17 -- unchanged ownership, now
three batches open with no action taken.
