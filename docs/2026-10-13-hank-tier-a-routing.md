# Tier A review obligations — routing table, hank b5, 2026-10-13

**GENERATED, not hand-counted.** Derived from `docs/tier-a-reviews.json` at
HEAD by walking every record with `status != reviewed`, taking the owning
directory as the most common top-level directory of its declared `files`, and
testing each `opened_at_sha` against `origin/main` with
`git merge-base --is-ancestor` and `git cat-file -e`.

## What the sha column means, because three states are not two

| value | meaning | what it costs a reviewer |
|---|---|---|
| `REACHABLE` | the sha is an ancestor of `origin/main` | the diff can be fetched and read |
| `ORPHANED` | the object still resolves in THIS clone but no ref reaches it | gc-eligible here, **absent from every other clone** — the reviewer cannot see the diff at all |
| `DANGLING` | the object does not resolve even locally | the record points at nothing anywhere |
| `UNSTAMPED` | no sha was recorded | there was never a diff to point at |

**b4 reported "6 UNSTAMPED + 12 overdue".** Re-measured here: **zero** records
are literally UNSTAMPED. Five carry a sha that cannot be followed — 3 DANGLING,
2 ORPHANED — which is the state b4's figure was describing, and the distinction
matters because the repairs differ: an ORPHANED sha can be re-seated from the
rewrite map or by subject/file-set match, a DANGLING one cannot and the record
has to be re-opened against a real commit or closed as unreviewable.

## Discharged by this batch — three, all reviewed not ticked

| opened_at | author | resources | how |
|---|---|---|---|
| `2026-10-12T11:21:02Z` | cody | `sen_caregivers` | seq965. **Found two defects the fix did not reach**, both fixed: the compliance panel and the CSV export both reported "no background check on file" for every caregiver. Three arms added. |
| `2026-10-12T11:35:03Z` | cc | `bld_bids`, `bld_draws` | seq664. Sound. All four release-field carry-over paths closed including the 502 refusal; checked the client half against the b4 hydrate class and it is clean. Control re-run 35/35. |
| `2026-10-05T09:50:00Z` | fourth | `invoices` | **--takeover**, 189.4h past deadline, was assigned to `cloud`. Sound. The record's first question answered by `grep -c req.body` = **1**, which bounds the attack surface regardless of which field names anybody thought to test. |

| # | opened_at | age h | author | reviewer | dir | sha | resources (first 3) | files (first 2) |
|---|---|---|---|---|---|---|---|---|
| 1 | `2026-10-06T06:18:11Z` | 162 | cc | **cody** | `(root)` | DANGLING | quotes, sb_ap | `sairnbiz.html, tests/sairnbiz_undated_payee_notes.js` |
| 2 | `2026-10-06T07:56:17Z` | 160 | hank | **cody** | `(root)` | REACHABLE | sen_settings | `sairnsenior.html` |
| 3 | `2026-10-12T11:52:48Z` | 12 | cody | **cc** | `(root)` | REACHABLE | alf_facility, law_bankstatements, law_barcerts | `SAIRN-digest-cody-b4.txt, SAIRN-report-cody-b4.txt` |
| 4 | `2026-09-30T13:59:56Z` | 298 | hover2 | **fourth** | `.claude` | REACHABLE | leg_insurance, mech_checks | `.claude/skills/sairn-hover-auditor/tools-hover2/hover_citation_linter.py` |
| 5 | `2026-09-30T15:53:29Z` | 296 | hover2 | **cloud** | `.claude` | REACHABLE | leg_insurance, quotes, sv_soapnotes | `.claude/skills/sairn-hover-auditor/tools-hover2/presync_tier_a_dryrun.py, .claude/skills/sairn-hover-auditor/tools-hover2/routing_field_shape_audit.py` |
| 6 | `2026-09-27T03:42:29Z` | 380 | hank | **fourth** | `api` | ORPHANED | alf_staff, sen_visits | `api/_lib/compliance-rules-staff-join.test.js, api/_resources/sairnsenior.js` |
| 7 | `2026-10-06T06:14:34Z` | 162 | hank | **cody** | `api` | ORPHANED | alf_clients, alf_family_contacts, alf_mar | `api/sd-data.js, tests/sd_data_family_mar_gate.js` |
| 8 | `2026-10-12T01:51:33Z` | 22 | hank | **cc** | `api` | REACHABLE | dnt_appointments, invoices, scp_designs | `api/sd-data-dental-ledger-validation.test.js, api/sd-data-dental-provider-scope.test.js` |
| 9 | `2026-10-05T21:25:19Z` | 171 | fourth | **cody** | `db` | REACHABLE | alf_activities, alf_billing, alf_claim_routes | `db/schema_snapshot.json` |
| 10 | `2026-09-28T03:34:57Z` | 356 | cody | **fourth** | `tests` | DANGLING | dnt_ar, dnt_revenue | `tests/reachability/resource_demand_probe.py` |
| 11 | `2026-10-06T07:29:58Z` | 161 | hank | **cody** | `tests` | REACHABLE | sdn_projects | `tests/sd_data_sdn_blob_scope.js` |
| 12 | `2026-09-28T00:16:59Z` | 360 | fourth | **cloud** | `tools` | DANGLING | alf_clients, alf_facility, alf_family_contacts | `api/sd-data-alf-isolation.test.js, tests/role_gate_loop_rule_probe.py` |
| 13 | `2026-10-05T15:02:28Z` | 177 | fourth | **cody** | `tools` | REACHABLE | quotes | `tools/deploy_verify_notify.py` |
| 14 | `2026-10-12T01:49:28Z` | 22 | cody | **cc** | `tools` | REACHABLE | alf_incidents, alf_mar, alf_op_audits | `tools/route_suite_failures.py` |

OPEN: 14
by dir: {'(root)': 3, '.claude': 2, 'api': 3, 'db': 1, 'tests': 2, 'tools': 3}
by sha: {'DANGLING': 3, 'REACHABLE': 9, 'ORPHANED': 2}
by reviewer: {'cody': 6, 'cc': 3, 'fourth': 3, 'cloud': 2}
authored by hank (cannot self-discharge): 5
assigned to hank: 0

## Routing

**`api/` — 3 open, and I can discharge NONE of them.** All three are authored
by hank, and the gate refuses a self-review at write time, which is the one
thing it exists to refuse. This is not a backlog I can clear by working harder:

| opened_at | reviewer assigned | sha | note |
|---|---|---|---|
| `2026-09-27T03:42:29Z` | fourth | **ORPHANED** | 387h old. The sha resolves only in this clone, so fourth cannot fetch the diff. Needs a re-seat before it can be reviewed at all. |
| `2026-10-06T06:14:34Z` | cody | **ORPHANED** | Same problem, same remedy. |
| `2026-10-12T01:51:33Z` | cc | REACHABLE | b4's nine-resource gate obligation. Ready to review as-is. |

**FIVE of the fourteen are authored by hank** and none is assigned to hank, so
my own queue is empty and my own authored backlog is unclearable by me. That
asymmetry is the finding in this table, not the count.

**For chat to assign — the eleven outside `api/`:**

- `(root)` ×3 — `sairnbiz.html` + `tools/exit_status_attributable.py` (cc, **DANGLING**), `sairnsenior.html` (hank), the b4 digest/report pair (cody).
- `.claude` ×2 — both hover2's own auditor tools. **A build agent must not reach into that clone**, so these cannot be discharged by hank, cc, cody or fourth touching the files; they can only be reviewed by reading them, and `tools/hover_auditor_scope_gate.py` is the reason that distinction matters.
- `tools` ×3 — one **DANGLING** (fourth→cloud, 372h), two REACHABLE.
- `tests` ×2 — one **DANGLING** (cody→fourth, 372h).
- `db` ×1 — `db/schema_snapshot.json` (fourth→cody).

**Two reviewers are not sessions that run here.** `cloud` holds 2 and is a
research lane whose last claim expired 386h ago; nothing has discharged through
it. Those two will sit forever unless reassigned.

## The three DANGLING records are the first thing to fix

A record whose sha resolves nowhere cannot be reviewed by anybody, so it is not
a queue item, it is a dead row. `python tools/tier_a_review_gate.py --reseat-shas`
REFUSES these rather than guessing — its own message is that following a sha to
a subject twin whose diff does not contain the record's files "would preserve
the original mis-stamp faithfully", and that a wrong sha is worse than a
dangling one because a dangling one is visibly broken. So the remedy is per
record and belongs to each author:

| opened_at | author | files to re-point against |
|---|---|---|
| `2026-09-28T00:16:59Z` | fourth | `api/sd-data-alf-isolation.test.js`, `tests/role_gate_loop_rule_probe.py`, `tools/alf_facility_role_gate_live_probe.py` |
| `2026-09-28T03:34:57Z` | cody | `tests/reachability/resource_demand_probe.py` |
| `2026-10-06T06:18:11Z` | cc | `sairnbiz.html`, `tests/sairnbiz_undated_payee_notes.js`, `tools/exit_status_attributable.py` |
