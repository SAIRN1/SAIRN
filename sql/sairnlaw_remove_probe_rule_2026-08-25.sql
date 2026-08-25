-- sql/sairnlaw_remove_probe_rule_2026-08-25.sql
-- Removes ONE junk row from public.law_deadline_rules.
--
-- ══ WHAT THIS IS AND HOW IT GOT THERE ══════════════════════════════════════
-- On 2026-08-25, while loading North Carolina, I needed to know whether the
-- new `nc_rcp_6a` computation standard had finished deploying to Vercel. I
-- checked by POSTing `add_rule` to api/legal-deadlines.js with a dummy rule and
-- reading the error -- that is, I probed a deployment with a WRITE endpoint.
-- The dummy validated, so instead of erroring it was STORED. Three probes were
-- sent (one per standard being checked) but all shared one `rule_id`, and
-- add_rule upserts on (license_hash, entry_id), so exactly one row exists.
--
-- IMPACT, STATED HONESTLY: it cannot change any computed date. computeDeadline
-- filters rules by the caller's `jurisdiction`, and no caller asks for 'zz'.
-- What it does do is appear in `rules_status`, which is the action the SAIRNlaw
-- UI uses to state coverage -- so the app currently reports 14 jurisdictions
-- when 13 are real.
--
-- WHY A SQL FILE AND NOT AN API CALL: api/legal-deadlines.js implements exactly
-- four actions -- compute, rules_status, add_rule, add_holidays. There is NO
-- delete. This is the same platform-wide gap already tracked in
-- docs/SAIRN-OPEN-WORK-INDEX.md (delete exists only for the SAIRNcode
-- SC_RESOURCES family). The schema does grant delete on this table to
-- service_role (sql/sairnlaw_deadline_rules_schema.sql), so the SQL editor can
-- do it even though the API cannot.
--
-- ══ RUN THE SELECT FIRST. DO NOT SKIP IT. ══════════════════════════════════
-- Step 1 must return EXACTLY ONE ROW and it must look like the probe. If it
-- returns 0 rows the probe is already gone and there is nothing to do; if it
-- returns more than 1, STOP and report it rather than running the delete.

-- ── STEP 1: verify, before deleting anything ──────────────────────────────
select
  id,
  license_hash,
  app_id,
  entry_id,
  data->>'jurisdiction' as jurisdiction,
  data->>'domain'       as domain,
  data->>'computation'  as computation,
  created_at
from public.law_deadline_rules
where app_id      = 'sairnlaw'
  and entry_id    = '__probe__'
  and data->>'jurisdiction' = 'zz'
  and license_hash = '56c82eb727d6a71f1012d7fcf432bd44df099e70dc38de67698bd0c6366f374c';

-- Expected: 1 row. entry_id '__probe__', jurisdiction 'zz', domain 'd',
-- computation one of wv_rcp_6a / wv_rap_39a / nc_rcp_6a (whichever probe wrote
-- last), created_at 2026-08-25.

-- ── STEP 2: the delete ────────────────────────────────────────────────────
-- FOUR predicates, ANDed, and every one of them has to be wrong simultaneously
-- for this to touch a real rule:
--
--   app_id      = 'sairnlaw'   scopes to this app's rows only.
--   entry_id    = '__probe__'  entry_id is the rule_id. No real rule uses this
--                              name -- every one of the 153 is of the form
--                              '<jurisdiction>-<rule>-<description>', e.g.
--                              'nc-rcp-36-a-admission-response'.
--   jurisdiction = 'zz'        not a real jurisdiction. The 13 real codes are
--                              us-federal, ca, fl, ga, il, in, mi, nc, ny, oh,
--                              pa, tx, wv.
--   license_hash = '56c8...'   sha256('LAW-PINNACLE-2026'), the canonical
--                              license. Named explicitly so the statement
--                              cannot reach another tenant's rows even if a
--                              probe row somehow exists there too.
--
-- entry_id alone would be sufficient given the unique (license_hash, entry_id)
-- constraint. The other three are belt and braces on a destructive statement.
--
-- NOT USED ON PURPOSE: no `where data->>'jurisdiction' <> ...` style negative
-- predicate, no LIKE, no wildcard, and no bare `delete from` with a loose
-- filter. Every predicate is an exact equality against a known-literal value.

delete from public.law_deadline_rules
where app_id      = 'sairnlaw'
  and entry_id    = '__probe__'
  and data->>'jurisdiction' = 'zz'
  and license_hash = '56c82eb727d6a71f1012d7fcf432bd44df099e70dc38de67698bd0c6366f374c';

-- Expected: DELETE 1

-- ── STEP 3: confirm the store is clean and the real rules are untouched ───
-- 'zz' must be gone. The 13 real jurisdictions must still total 153.
select
  data->>'jurisdiction' as jurisdiction,
  count(*)              as rules
from public.law_deadline_rules
where app_id = 'sairnlaw'
  and license_hash = '56c82eb727d6a71f1012d7fcf432bd44df099e70dc38de67698bd0c6366f374c'
group by 1
order by 1;

-- Expected exactly, and nothing else:
--   ca 10, fl 7, ga 12, il 6, in 7, mi 18, nc 13, ny 11, oh 8, pa 11,
--   tx 11, us-federal 22, wv 17     -- 13 rows, 153 rules, no 'zz'.

-- ── AFTER RUNNING: verify through the API too, not just the table ─────────
--   curl -s -X POST https://sairn.vercel.app/api/legal-deadlines \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer LAW-PINNACLE-2026' \
--     -d '{"action":"rules_status"}'
--
-- The jurisdictions array must have 13 entries and none of them 'zz'.
