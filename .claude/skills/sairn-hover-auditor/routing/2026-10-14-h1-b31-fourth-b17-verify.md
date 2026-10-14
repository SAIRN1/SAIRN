# Adversarial verification of fourth b17's hank-b9 Tier A review -- 2026-10-14, h1 b31

Not a routing doc in the usual sense (no action needed from anyone) --
filed under `routing/` because this role's three root deliverables are
reserved for the handoff/report/digest and this is supporting evidence
for the chain entry (`#1406`, check, target fourth) rather than its own
finding. Kept as a durable, human-readable record alongside the
append-only JSONL.

## What was checked, and the result on each

**1. The Tier A obligation itself is discharged, not self-reviewed.**
`docs/tier-a-reviews.json`, the hank record opened `2026-10-14T11:55:18Z`
(10 resources: `bld_photo_analyses`, `grd_progress_photos`,
`mech_checks`, `mech_quotes`, `sc_auth_requests`, `sen_branches`,
`sen_referrals`, `sen_settings`, `sen_training_records`,
`sen_training_rules`) shows `status: reviewed`, `reviewer_session:
fourth` -- a different session than the author, which is what the gate
requires. `python tools/tier_a_review_gate.py --validate` -> `251
record(s), identities unique, statuses in vocabulary`. CONFIRMED.

**2. The section 7.5 correction.** fourth's doc claims hank's migration
adds no second ack store -- only two columns on each `*_employee_auth`
table. `grep -nE "create table|alter table|add column"
sql/2026-10-14-hank-b9-ai-safeguards.sql` returns exactly one hit, the
`alter table public.%I ... add column if not exists ai_notice_version
... add column if not exists ai_notice_acked_at` block at lines 54-56,
looped over every table matching `%_employee_auth` in
`information_schema.tables`. No `create table` anywhere in the file.
CONFIRMED.

**3. The cross-tenant ack defenses in `api/ai-notice.js`.** Claimed:
`app_id` from the body is used only to pick a table (`:126`), then
`verifySessionToken` takes `app` as its third argument and refuses a
token minted for a different app (`:136`), and the row is selected by
`license_hash` + `employee_id` from the verified session, never from the
body (`:145-146`). Live grep confirms `LICENSE_WRONG_APP` at `:117`,
`verifySessionToken(tokenFromRequest(req), licHash, app)` at `:136`, and
the `mine = table + '?license_hash=eq.' + enc(licHash) +
'&employee_id=eq.' + enc(session.employee_id)` line at `:145-146`
(`session.employee_id`, not `body.employee_id`). CONFIRMED. The
fail-closed migration check (`looksUnmigrated`, defined `:161`, consumed
at `:170`/`:211`/`:233` to answer `503 AI_NOTICE_NOT_PROVISIONED` rather
than a false empty-ack state) also confirmed present and wired at all
three call sites.

**4. The write-map doc's line citations**, all six checked against
current `api/sd-data.js` and `api/sen-auth.js`:
- `api/sd-data.js:6721` -- `const SEN_REFERRAL_RESOURCES = {` -- MATCH.
- `api/sd-data.js:6608` -- `const SEN_CLIENT_BROAD_READ_ROLES =
  roleSet(...)` -- MATCH.
- `api/sd-data.js:8441` -- inside the `rf_cert_rules` write branch,
  `rfAuth.MANAGEMENT_ROLES[session.role]` check -- MATCH.
- `api/sd-data.js:8495` -- inside the `rf_certifications` write branch,
  same `MANAGEMENT_ROLES` check -- MATCH.
- `api/sen-auth.js:74` -- `const MANAGEMENT_ROLES = roleSet({ owner:
  true, billing: true });` -- MATCH.
All five land on the exact line named, not merely "nearby."

**5. The four removal-path specs.** `python tools/removal_path_check.py`
(live, current `origin/main`) reports exactly 4 findings --
`alf_family_contacts`, `mech_insurance_policies`, `sf_trustee_audits`,
`sv_scribe_consent` -- the same four, same order (`sv_scribe_consent`
first), as `docs/2026-10-14-fourth-b17-removal-path-specs.md`. CONFIRMED,
nothing added or dropped from the live tool's output since fourth wrote
the spec.

## Result

**NO DISCREPANCY FOUND on any of the five items.** Logged to the hover
chain as `#1406` (check, target fourth, `--source` stamped against the
five files' current blob shas).

## One process note, not a finding about fourth's work

hover2's own b29 claim (seen live in `sairn_claim.py list` while this
batch was running) independently tasked itself with "(3) verify fourth
b17 four removal-path specs + write-map doc (seven resources) against
current source" -- the same verification this doc performs, run by a
different hover instance in the same window. Not a conflict (both
read-only, no file overlap), but worth naming: two independent audits of
the same claim landing in the same rotation is duplicated effort, not
doubled confidence, unless each used a genuinely different method. This
one drove `tools/removal_path_check.py` and `tools/tier_a_review_gate.py`
live and grepped exact line numbers; hover2's method is not visible from
here. No action requested -- noted for whoever next schedules the
rotation.
