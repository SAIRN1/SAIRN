-- sql/sairnlegacy_audit_licence_seed_2026-10-30.sql
--
-- WHY (fourth b70, Michael's b70 item 2): live-drive the F3 refusals P1, P4
-- and P8 (api/b69-leg-f3-supervisor.test.js) against the deployed
-- /api/leg-countersign "using one apprentice credential plus an F3 row on the
-- audit licence". MEASURED 2026-10-30, read-only against project
-- ejrlrrkvhtllxbbypdjb: SAIRNlegacy has exactly ONE licence row (active, not
-- an audit key) and ZERO apprentice credentials. There is no SAIRNlegacy
-- audit licence, so the drive could not run. A live probe that writes must be
-- on an audit licence, never the demo/customer one -- the F3 residue that
-- sql/2026-10-22-cody-b49-leg-f3-residue-removal.sql had to clean up off
-- LEG-PINNACLE-2026 is the reason.
--
-- WHAT THIS DOES: one licence row, LEG-AUDIT-2026, the same shape as
-- sql/audit_license_seed_mech_law_2026-09-28.sql. Nothing else. The F3 row and
-- the credentials are NOT seeded here: once the licence exists, the owner
-- bootstraps through the app (bootstrap only works on a licence with zero
-- credentials), adds one Director and one Apprentice under Settings > Access,
-- and the F3 config is written through the app's own leg_settings path --
-- so the drive exercises the real write paths instead of rows typed into SQL.
--
-- Idempotent: on conflict do nothing. Safe to re-run.

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values
  ('LEG-AUDIT-2026', 'active', 'audit@sairnlegacy.example', 'sairnlegacy', 'demo', null)
on conflict (key) do nothing;

-- READ BACK -- expect exactly one row: LEG-AUDIT-2026 | active | sairnlegacy | demo
select key, status, app_id, plan, created_at
  from public.license_keys
 where key = 'LEG-AUDIT-2026';
