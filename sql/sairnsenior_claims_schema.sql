-- sql/sairnsenior_claims_schema.sql
-- SAIRNsenior billing claims -- Supabase schema
--
-- WHY THIS EXISTS: matches the app's own real SOP User Guide (Step 4 --
-- "Submit Claims: Go to Billing -> Ready to Bill. All completed visits
-- with EVV verification appear."). A claim is generated FROM a completed,
-- EVV-verified visit (sen_visits, status='completed') -- it references
-- that visit and the client's payer, and carries its own submit ->
-- paid/denied lifecycle.
--
-- ACCESS, deliberately simpler than sen_clients/sen_visits: this is
-- financial/billing data, not clinical assignment data -- a caregiver has
-- no legitimate reason to see claim amounts or payer reimbursement
-- status under HIPAA minimum-necessary (their job is delivering and
-- documenting care, not billing it), and a coordinator/scheduler's
-- "broad caseload visibility" was scoped to CLIENT and VISIT data, not
-- financial records. Management (owner/billing) only, both read and
-- write -- no assignee-based visibility needed at all.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sen_claims (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnsenior',
  claim_id     text not null,                        -- client-generated id (CLM-<timestamp>)
  data         jsonb not null default '{}'::jsonb,    -- visit_id, client_id, client_name, payer,
                                                        -- service_date, hours_billed, rate, amount,
                                                        -- status, denial_reason, submitted_date
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, claim_id),
  constraint senclaims_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_senclaims_license on public.sen_claims(license_hash);

-- ---------------------------------------------------------------------------
-- GRANTS -- explicit up front, same reasoning as every other data table's
-- own header this session.
grant select, insert, update on public.sen_claims to service_role;
revoke all on public.sen_claims from anon, authenticated;
