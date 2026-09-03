-- sql/sairnsenior_franchise_schema.sql
-- SAIRNsenior franchise agreements and royalty reporting -- Supabase schema
-- (2026-09-02)
--
-- Competitive-gap audit item B3 ("franchise-network reporting and royalty
-- calculation", Tier-B-defining). The audit records WellSky's claim of 8 of the
-- 10 largest personal-care franchise networks as a real moat, and notes that
-- most Tier A tools do not attempt this at all. Additive and idempotent; run
-- after sql/sairnsenior_branches_schema.sql. Nothing there is duplicated here.
--
-- WHAT THIS STORES. One table:
--
--   sen_franchise_agreements   the agreement between the franchisor and ONE
--                              unit: the royalty percentage, WHAT it is
--                              charged on, the ad-fund percentage, and the
--                              period the agreement covers.
--
-- ── THE UNIT IS THE BRANCH. NOTHING NEW IS INVENTED TO HOLD ONE ─────────
-- A franchise unit is an office with its own territory, which is exactly what
-- sen_branches already models (B1). A parallel "unit" table would drift from
-- the branch the moment either was edited, and every royalty would then be
-- computed against whichever copy the reader happened to open.
--
-- ── THE ROYALTY BASE IS DECLARED PER AGREEMENT, NEVER ASSUMED ───────────
-- Real franchise agreements charge royalty on different things: some on GROSS
-- BILLED revenue, some on COLLECTED revenue. The difference is months of cash
-- and it runs in the franchisee's favour or the franchisor's depending which
-- way you guess. `royalty_base` is therefore a required, stored choice and the
-- statement prints which one was used. Defaulting it silently would be picking
-- a side of a contract this software has not read.
--
-- ── A DENIED CLAIM IS NOT REVENUE, AND THIS IS THE EXPENSIVE ONE ────────
-- The branch rollup (B1) counts every non-draft claim as "billed", which is
-- defensible for an operational rollup: it WAS billed. It is NOT defensible as
-- a royalty base. A claim the payer denied and never paid produces no money,
-- and charging a franchisee a percentage of it takes real cash for work nobody
-- was paid for. Denied and appeal-denied claims are excluded from every basis.
--
-- ── AND AN APPEALED CLAIM IS IN NEITHER BUCKET ─────────────────────────
-- A claim under appeal was billed, then denied, and its outcome is undecided.
-- Counting it would overstate what is owed; silently dropping it would let a
-- franchisor quietly under-collect and leave a franchisee with a statement that
-- does not reconcile. It is reported as its own IN DISPUTE line, in neither the
-- included nor the plainly-excluded total, so both sides can see it and agree
-- what to do.
--
-- ── COLLECTED REVENUE NEEDS A PAYMENT DATE, AND OLD ROWS DO NOT HAVE ONE ─
-- `blMarkPaid` records `paid_date` as of 2026-09-02. Every claim marked paid
-- before that has none. Those are counted separately as "paid, date not
-- recorded" and land in NO period -- back-filling them with the service date or
-- with today would invent the month a payment arrived and change what a unit
-- owes. The statement prints the count so the gap is visible rather than
-- absorbed.
--
-- ── THE AD FUND IS A SEPARATE LINE, NOT PART OF THE ROYALTY ─────────────
-- National advertising-fund contributions are a distinct obligation with
-- distinct accounting, and folding them into one number is exactly what
-- franchisees dispute. Both are computed on the same declared base and printed
-- on their own rows with their own percentages.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- every other sen_* table. The API gate is MANAGEMENT-ONLY for read AND write,
-- matching sen_payer_contracts and sen_pay_rates: a royalty rate is the
-- commercial term of the franchise agreement and nothing on a caregiver's,
-- coordinator's or scheduler's screen needs it.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide and no code path here deletes. A superseded agreement is given
-- a term_on and keeps its history -- deleting it would leave every royalty
-- statement already issued under it with nothing on file to justify the
-- percentage that was charged, which is precisely the record a franchisee
-- disputing a statement asks for.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sen_franchise_agreements (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairnsenior',
  agreement_id  text not null,
  data          jsonb not null default '{}'::jsonb,   -- branch_id, branch_name, unit_code, franchisee_name, royalty_pct, royalty_base ('billed'|'collected'), ad_fund_pct, effective_on, term_on, notes, created_at
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, agreement_id),
  constraint senfr_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_senfr_license on public.sen_franchise_agreements(license_hash);

alter table public.sen_franchise_agreements enable row level security;

drop policy if exists "svc only sen_franchise_agreements" on public.sen_franchise_agreements;

create policy "svc only sen_franchise_agreements" on public.sen_franchise_agreements
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.sen_franchise_agreements to service_role;
revoke all on public.sen_franchise_agreements from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sen_franchise_agreements;
--
-- Confirm no delete grant took hold (expect SELECT, INSERT, UPDATE only):
--   select privilege_type from information_schema.role_table_grants
--    where grantee = 'service_role' and table_name = 'sen_franchise_agreements';
