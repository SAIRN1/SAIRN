-- sql/sairncare_mar_access_grants_schema.sql
-- ---------------------------------------------------------------------------
-- MAR ACCESS GRANTS (SAIRNcare) -- 2026-10-14, hank b11.
--
-- THE DECISION THIS TABLE IMPLEMENTS (Michael, 2026-10-13):
--   "Billing never reads the MAR by default. For coding work only, an office
--    manager may grant billing access to a MAR, time-limited, expiring on its
--    own, and audit-logged."
--
-- One row is ONE grant: one named employee, one family contact and the one
-- resident on that contact's stored row, with an expiry. The code half is the
-- `mar_access_grant` action in api/sd-data.js and the grant lookup in that
-- file's `family_mar` path; tests/mar_billing_grant.test.js is the spec.
--
-- EXPIRY IS EVALUATED AT READ TIME, NOT BY A SWEEPER, and that is why there is
-- no scheduled delete here and why `expires_at` is NOT NULL. A grant that only
-- stops working when something removes the row is live for as long as that
-- something is down, and nothing anywhere would say so. Rows are kept after
-- they expire on purpose: the audit question is "was this read inside its
-- window", and deleting the window makes it unanswerable.
--
-- NOT RUN. Nothing in this file has been executed against Supabase. Until
-- Michael runs sql/2026-10-14-hank-b11-mar-grant.sql (block 1 is this file,
-- verbatim), the `mar_access_grant` action answers 503 NOT_PROVISIONED naming
-- that file, and the read path treats the absent table as "no grant" and
-- refuses -- fail-closed, so the only cost of the unrun migration is that no
-- grant can be exercised yet.
-- ---------------------------------------------------------------------------

create table if not exists public.alf_mar_access_grants (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  grant_id text not null,
  contact_id text not null,
  resident_id text not null,
  grantee_employee_id text not null,
  granted_by text not null,
  reason text,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  unique (license_hash, grant_id)
);

-- The read path's exact query shape: licence + contact + grantee.
create index if not exists idx_alf_mar_access_grants_lookup
  on public.alf_mar_access_grants (license_hash, contact_id, grantee_employee_id);

alter table public.alf_mar_access_grants enable row level security;
drop policy if exists "svc all alf_mar_access_grants" on public.alf_mar_access_grants;
create policy "svc all alf_mar_access_grants" on public.alf_mar_access_grants for all using (true) with check (true);

-- REVOCATION IS AN UPDATE, SO UPDATE IS GRANTED -- and that is a deliberate
-- difference from the audit log, which is insert-only. An office manager who
-- grants in error must be able to shut it off before the expiry; the read path
-- already refuses any row with a non-null `revoked_at`. DELETE is NOT granted:
-- a deleted grant is an access decision nobody can reconstruct, and the reads
-- it authorised are in sairncare_audit_log pointing at a grant_id that would
-- no longer resolve.
revoke all on public.alf_mar_access_grants from anon, authenticated;
revoke all on public.alf_mar_access_grants from service_role;
grant select, insert, update on public.alf_mar_access_grants to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.alf_mar_access_grants;
