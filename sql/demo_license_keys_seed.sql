-- sql/demo_license_keys_seed.sql
-- Provisions demo license_keys rows for SAIRNbiz, SAIRNgrounds, SAIRNscape
--
-- WHY THIS EXISTS: api/_lib/license.js validates against public.license_keys
-- by raw `key` -- there is no self-service key-generation system anywhere in
-- this codebase yet (that's separate, unbuilt, tied to next week's Stripe
-- integration -- see SAIRN-PLATFORM-SESSION1-HANDOFF.md). SAIRNbuild's own
-- demo key (BLD-PINNACLE-2026) was already manually provisioned this same
-- way (see SAIRNBUILD-SCOPE.md section 6) and is confirmed working. These
-- three apps' equivalent demo keys were never created -- confirmed live,
-- not assumed: GRD-DEMO-2026, SCP-DEMO-2026, and SB-PINNACLE-2026 (the
-- exact placeholder each app's own license-gate error message already
-- suggests, e.g. sairnbiz.html: "Invalid key. Try SB-PINNACLE-2026") all
-- return 401 INVALID_LICENSE against the live endpoint -- the row is
-- absent, not expired/misconfigured/wrong-table. No code fix exists here
-- because there is no bug in the validation code; this is a missing-data
-- gap, same category as every other Supabase provisioning step in this
-- project (run by Michael in the SQL editor, service-role only -- anon
-- cannot read or insert license_keys by design, confirmed by probe
-- returning 42501 against SAIRNbuild's own equivalent provisioning).
--
-- Client-side prefix allowlists already accept these keys with no further
-- code change needed -- confirmed by reading each app's own gate:
--   sairnbiz.html:841     VALID=['SB-','SD-','DEMO-','SAIRN-','BIZ-']
--   sairngrounds.html:1094 VALID=['GRD-','DEMO-','SAIRN-']
--   sairnscape.html:1627   SCP_VALID=['SCP-','DEMO-','SAIRN-']
--
-- CORRECTED (first run failed, 42703: column "trial_ends_at" does not
-- exist) -- the original column list was copied from api/_lib/license.js's
-- own SELECT/output shape, which turned out to be aspirational for that
-- one field, not a reliable schema source. Re-derived the REAL column list
-- directly from the live table via PostgREST's own error-ordering behavior
-- (the same zero-write column-existence probe already used and documented
-- in SAIRNBIZ-SESSION1-HANDOFF.md): a single-column anon POST returns
-- 42501 (permission denied) when the column exists and is merely
-- permission-blocked, and PGRST204 when the column doesn't exist at all --
-- distinguishable without ever writing a row. Probed 23 candidate names;
-- confirmed REAL: key, status, customer_email, app_id, plan,
-- stripe_subscription_id, id, created_at, updated_at. Confirmed ABSENT:
-- trial_ends_at, trial_end, trial_expires_at, expires_at, plan_tier,
-- license_hash, active, notes, tenant_id, org_id, seats, max_seats,
-- source, created_by, owner_email, raw_key. There is currently no
-- trial-tracking column on this table at all -- license.js's own
-- `row.trial_ends_at || null` already degrades gracefully to null (not
-- expired) when the column is simply absent from the row, so dropping it
-- here changes no runtime behavior, it just stops the insert from failing.
--
-- Verify after running, before writing/re-running any client code against
-- these keys (same "verify against the deployed endpoint" discipline
-- SAIRNBUILD-SCOPE.md section 6 already used for BLD-PINNACLE-2026):
--
--   curl -s -X POST https://sairn.vercel.app/api/sd-data \
--     -H 'Content-Type: application/json' \
--     -H 'Authorization: Bearer SB-PINNACLE-2026' \
--     -d '{"action":"read","resource":"profile","app_id":"sairnbiz"}'
--
-- (repeat for GRD-DEMO-2026/app_id sairngrounds and SCP-DEMO-2026/app_id
-- sairnscape). 401 INVALID_LICENSE -> row still absent. 403
-- LICENSE_INACTIVE -> status not 'active'. 200 -> provisioned correctly.

-- ON CONFLICT (key) DO NOTHING -- CORRECTED 2026-08-28. This paragraph
-- previously said the opposite, and every other license seed in this repo
-- cites it, so the correction is recorded here in full and referenced from
-- the rest.
--
-- What it used to say: use WHERE NOT EXISTS rather than ON CONFLICT,
-- because this repo has no tracked CREATE TABLE for license_keys and so a
-- UNIQUE constraint on `key` can't be confirmed without live DB access --
-- and ON CONFLICT against a column with no matching constraint fails 42P10.
--
-- Both halves of that were wrong:
--   1. The constraint is real. Confirmed live 2026-08-28:
--      license_keys_key_key, UNIQUE (key). ON CONFLICT (key) is valid.
--   2. The repo DID have a tracked CREATE TABLE the whole time, declaring
--      `key TEXT UNIQUE NOT NULL` (which is exactly what generates the
--      auto-named license_keys_key_key). It was on an unmerged branch, and
--      is now at archive/branch-lucid-ptolemy-b73vu0/db/schema_license_keys.sql.
--      "No tracked CREATE TABLE" was a claim about the working tree stated
--      as a claim about the repo -- the same mistake, on the same archived
--      branch, that CLAUDE.md already records for sairn-code-guardian.
--
-- DO NOTHING, not DO UPDATE. Preserves the exact semantics of the NOT
-- EXISTS it replaces: an existing row wins. That matters here -- a live row
-- may have been deliberately suspended (status 'cancelled'/'suspended') or
-- re-assigned to a real customer_email, and re-running a seed must never
-- silently reactivate or overwrite it. Matches sql/sairndental_demo_seed_
-- 2026-08-27.sql; the DO UPDATE seeds in this directory (sairncode/
-- sairnroofing verify_admin) are deliberately-refreshable test credentials,
-- a different case. Still safe to re-run.

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('SB-PINNACLE-2026', 'active', 'demo@pinnaclestone.example', 'sairnbiz', 'demo', null)
on conflict (key) do nothing;

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('GRD-DEMO-2026', 'active', 'demo@pinnaclestone.example', 'sairngrounds', 'demo', null)
on conflict (key) do nothing;

insert into public.license_keys (key, status, customer_email, app_id, plan, stripe_subscription_id)
values ('SCP-DEMO-2026', 'active', 'demo@pinnaclestone.example', 'sairnscape', 'demo', null)
on conflict (key) do nothing;
