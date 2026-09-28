-- sql/zz_probe_residue_delete_2026-09-28.sql
-- ---------------------------------------------------------------------------
-- DELETE ONE ROW I CREATED WHILE LIVE-VERIFYING A FIX. Michael to run.
--
-- ── WHY THIS IS SQL AND NOT A TOOL ─────────────────────────────────────────
-- Neither I nor the platform can delete it. There is no delete action on
-- api/legal-deadlines.js (`ACTIONS = compute, rules_status, rules_fingerprint,
-- add_rule, add_holidays`), and `service_role` -- the role every endpoint uses
-- -- HAS NO DELETE ON THIS TABLE. That is deliberate and recorded in
-- sql/sairnlaw_deadline_rules_schema.sql:120-125:
--
--     "DELETE removed 2026-08-25 -- these lines previously granted it. The live
--      grant was revoked platform-wide by
--      sql/unused_delete_grant_revoke_2026-08-24.sql ... do NOT re-add `delete`
--      here when fixing a missing grant."
--
-- SO THE RIGHT ANSWER IS NOT TO RE-GRANT DELETE. A reference table that holds
-- the rules every filing deadline is computed from should not be deletable by
-- the web tier, and one probe row is not a reason to change that. This runs in
-- the Supabase SQL editor as `postgres`, once, by a human.
--
-- ── WHAT THE ROW IS, AND HOW IT GOT THERE ──────────────────────────────────
-- On 2026-09-28 I fixed an identity-forgery hole: `add_rule` merged the
-- caller's object into the stored row and an allowlist of three overridden keys
-- let `recorded_by`, `created_by` and `author` through verbatim, so a caller
-- could write somebody else's name into the provenance of a rule that decides
-- filing deadlines. Verifying that the DEPLOYED endpoint strips those fields
-- requires seeing what it STORES, which requires a write. So one rule was
-- written with forged identity fields, and the response confirmed all three
-- were stripped and `authority.verified_by` was re-derived from the session.
--
-- IT IS INERT, and that is checked rather than asserted:
--   * jurisdiction `zz-probe` appears in NO seed file under sql/ -- every
--     sairnlaw_deadline_seed_*.json names a real jurisdiction;
--   * rule selection is by (jurisdiction, domain, trigger_event), so nothing
--     reaches it without a caller asking for `zz-probe` by name;
--   * it is on LAW-TEST-2026, the test licence, not LAW-PINNACLE-2026.
-- Inert is not the same as wanted. It is visible in `rules_status` -- which is
-- how it was found again -- and a probe row in a legal reference table is
-- exactly the kind of thing that gets quoted in six months as a real rule.
--
-- ── SCOPED TWICE, ON PURPOSE ───────────────────────────────────────────────
-- `entry_id` AND the stored jurisdiction must BOTH match. Either alone would
-- be enough today; requiring both means a typo in one cannot widen the delete,
-- and it needs no `license_hash` -- which I do not have, and which would be a
-- third thing to get wrong.
-- ---------------------------------------------------------------------------

-- ── STEP 1. LOOK BEFORE YOU DELETE. Run this ALONE and read it. ────────────
-- Expect exactly ONE row, on one licence, with jurisdiction zz-probe.
-- If it returns 0, the row is already gone and there is nothing to do.
-- If it returns more than 1, STOP -- something else is using this jurisdiction
-- and the assumption in the header is wrong.
select 'law_deadline_rules' as tbl,
       id, license_hash, entry_id,
       data->>'jurisdiction'                 as jurisdiction,
       data->>'label'                        as label,
       data->'authority'->>'verified_by'     as verified_by,
       created_at
  from public.law_deadline_rules
 where entry_id = 'zz-probe-identity-20260928'
   and data->>'jurisdiction' = 'zz-probe';

-- And the other table the same probe COULD have touched but did not. This is
-- here so "I only wrote one row" is something you check rather than believe;
-- expect ZERO rows.
select 'law_holidays' as tbl, id, license_hash, entry_id, created_at
  from public.law_holidays
 where entry_id like 'zz-probe:%'
    or data->>'jurisdiction' = 'zz-probe';

-- ── STEP 2. THE DELETE. Only after step 1 returned exactly the one row. ────
-- Wrapped so the count is printed and the transaction is abandoned if it is
-- not 1. `delete ... returning` inside a CTE gives the count without a second
-- statement that could see a different state.
begin;

with removed as (
  delete from public.law_deadline_rules
   where entry_id = 'zz-probe-identity-20260928'
     and data->>'jurisdiction' = 'zz-probe'
  returning id, license_hash, entry_id
)
select count(*) as rows_deleted, min(license_hash) as license_hash from removed;

-- READ THE COUNT ABOVE.
--   rows_deleted = 1  -> commit;
--   anything else     -> rollback;  and say so, because a delete that removed a
--                        different number of rows than the SELECT found means
--                        the SELECT and the DELETE disagreed about the table.
-- Neither is typed here on purpose: a script that commits for you turns
-- "read the count" into a formality.

-- commit;
-- rollback;

-- ── STEP 3. VERIFY IT IS GONE, from the app rather than from this editor ───
-- The editor's own SELECT proving its own DELETE is one source checking itself.
-- The real check is that the APP no longer reports the jurisdiction:
--
--   python - <<'EOF'
--   import sys, json
--   sys.path.insert(0, 'tools'); import sairn_http
--   B='https://sairn.vercel.app'
--   t=sairn_http.fetch_json(B+'/api/law-auth', method='POST', key='LAW-TEST-2026',
--       payload={'action':'login','employee_id':'sairn-demo-owner','pin':'46201975'}).body['token']
--   r=sairn_http.fetch_json(B+'/api/legal-deadlines', method='POST', key='LAW-TEST-2026',
--       headers={'X-SD-Auth':t}, payload={'action':'rules_status'})
--   print('zz-probe still present:', 'zz-probe' in json.dumps(r.body))
--   EOF
--
-- Expect `False`.
-- ---------------------------------------------------------------------------
