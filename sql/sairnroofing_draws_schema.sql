-- sql/sairnroofing_draws_schema.sql
-- SAIRNroofing gap B3 (part) -- progress billing: draw requests and retainage.
-- Run once in the Supabase SQL editor. Safe to re-run (idempotent).
--
-- ══ WHAT THIS COVERS, AND WHAT IT DELIBERATELY DOES NOT ════════════════════
-- The 2026-08-26 competitive-gap audit's Tier-B item B3 is three things:
-- WIP/percentage-of-completion accounting, RETAINAGE, and CERTIFIED PAYROLL.
-- This file covers the first two. Certified payroll is NOT here and is not
-- coming as a side effect: it needs Davis-Bacon and state prevailing-wage
-- DETERMINATIONS, which are external published rate schedules. Inventing a
-- wage rate would be the same class of fabrication as inventing a warranty
-- registration window, and the consequence is a federal filing rather than a
-- lost warranty. It stays a named gap until somebody picks a rate source.
--
-- ══ THE ENGINE IS SHARED; THIS TABLE IS NOT ════════════════════════════════
-- api/_lib/wip-accounting.js is unprefixed and app-agnostic because
-- cost-to-cost, retainage and over/under billing are standard construction
-- accounting, identical in every trade. This table is rf_-prefixed because it
-- hangs off rf_jobs. Said plainly in the engine's own header and repeated here:
-- SAIRNbuild ALREADY HAS retainage and WIP (sairnbuild.html:6263 jobWIP(), a
-- Draw Requests panel, bld_draws with retainage_pct/retainage_held). It is
-- client-side, in-file, over localStorage, and it is UNTOUCHED. So the engine
-- is the second implementation on the platform, deliberately, and repointing
-- SAIRNbuild onto it is its own task rather than a rider on this one.
--
-- ══ retainage_held IS NOT A COLUMN, ON PURPOSE ═════════════════════════════
-- bld_draws stores retainage_pct AND retainage_held, which can disagree the
-- moment anyone edits one of them. Here the percentage is stored and the held
-- amount is DERIVED on read by the engine -- the same rule the platform already
-- applies to invoice balances and subcontractor outstanding money.
--
-- retainage_pct is NULLABLE WITH NO DEFAULT, and that is the sharp bit. A
-- default of 10 would look harmless and would tell a contractor that a draw
-- nobody has priced holds 10% back. Null reads as "unknown" and the engine
-- refuses to compute what is collectable, which is the honest answer.
--
-- == RETAINAGE COMES BACK OUT (added 2026-09-03, BEFORE THIS FILE WAS RUN) ===
-- The first version of this table modelled retainage going IN and had no way to
-- record it coming back out, and the engine matched it: `retainage_held` was a
-- lifetime accrual that only grew, printed on screen under the words
-- "Retainage held" as though it were a current balance. A job whose retainage
-- had actually been paid would still have reported the money as withheld --
-- which is the single question retainage exists to answer.
--
-- Caught while writing the 2026-09-03 competitive-gap audit. THIS FILE HAD NOT
-- BEEN RUN YET, so the two columns below are an edit to an unrun schema rather
-- than a migration against live rows -- the cheapest possible moment to fix a
-- data model, and the reason it was worth doing immediately instead of filing.
--
-- retainage_released is NOT NULL DEFAULT 0, and the asymmetry with
-- retainage_pct above is deliberate rather than sloppy. A missing PERCENTAGE
-- means nobody agreed one, so it must read as unknown. A missing RELEASE means
-- no release happened -- retainage is held by default and released by an event.
-- Zero is also the conservative direction: it says the money is still being
-- withheld, which is the answer that makes somebody go and check.
--
-- retainage_released_at is nullable because a release entered without a date is
-- still a real payment; the engine records it and REPORTS that it cannot be
-- aged or reconciled, rather than refusing it and losing the fact.
--
-- ══ SIZE BOUNDS ARE NUMERIC ON PURPOSE ═════════════════════════════════════
-- tools/sairn_sql_preflight.py can only compare CHECK constraints where both
-- sides state a numeric bound. See docs/2026-09-02-constraints-not-comparable.md.

create table if not exists public.rf_draws (
  id              uuid primary key default gen_random_uuid(),
  license_hash    text not null,
  draw_id         text not null,                 -- client-generated
  job_id          text not null,
  draw_no         integer,
  period_end      date,
  -- What the contractor STATED, usually off squares installed. The engine
  -- labels every result built on this `contractor_stated_percent` and never
  -- reports it as cost-to-cost, which is a different basis an accountant would
  -- reproduce differently.
  pct_complete    numeric(5,2),
  amount          numeric(12,2),
  retainage_pct   numeric(5,2),                  -- nullable, NO default: see above
  -- Retainage coming back OUT. See the header: default 0 means "none released",
  -- which is both true and the conservative direction.
  retainage_released    numeric(12,2) not null default 0,
  retainage_released_at date,                    -- nullable: an undated release is still a real one
  amount_received numeric(12,2) not null default 0,
  status          text not null default 'draft',
  requested_at    date,                          -- the ageing clock starts here, not at period_end
  received_at     date,
  notes           text,
  data            jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  updated_by      text,
  unique (license_hash, draw_id),
  constraint rfdraw_status_check check (status in ('draft','requested','approved','received','rejected')),
  constraint rfdraw_pct_sane check (pct_complete is null or (pct_complete >= 0 and pct_complete <= 100)),
  constraint rfdraw_ret_sane check (retainage_pct is null or (retainage_pct >= 0 and retainage_pct <= 100)),
  constraint rfdraw_amount_not_negative check (amount is null or amount >= 0),
  constraint rfdraw_received_not_negative check (amount_received >= 0),
  -- Negative released is a typo, never a credit -- the same reason
  -- saveBenEnroll refuses a negative benefit cost rather than storing it.
  -- NOT constrained against the held amount: held is DERIVED from a percentage
  -- and is not a column here, so the database cannot see it. Over-release is
  -- caught and REPORTED by api/_lib/wip-accounting.js instead, which is the
  -- only layer that knows both numbers.
  constraint rfdraw_released_not_negative check (retainage_released >= 0),
  constraint rfdraw_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfdraw_license on public.rf_draws(license_hash);
create index if not exists idx_rfdraw_job on public.rf_draws(license_hash, job_id);
-- The query this table exists to answer quickly: what has been requested and
-- not received.
create index if not exists idx_rfdraw_status on public.rf_draws(license_hash, status, requested_at);

-- ---------------------------------------------------------------------------
-- RLS and grants. Service-role only, matching every other rf_ table.
-- SELECT/INSERT/UPDATE and no DELETE: a draw entered in error is rejected,
-- which the next reconciliation needs to see, not deleted.
-- ---------------------------------------------------------------------------
alter table public.rf_draws enable row level security;
drop policy if exists "svc only rf_draws" on public.rf_draws;
create policy "svc only rf_draws" on public.rf_draws
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.rf_draws from service_role;
grant select, insert, update on public.rf_draws to service_role;
revoke all on public.rf_draws from anon, authenticated;

-- ---------------------------------------------------------------------------
-- Verify, do not assume.
-- ---------------------------------------------------------------------------
--   select count(*) from rf_draws;   -- expect 0, nothing is seeded
--
-- Grants (expect INSERT,SELECT,UPDATE; no DELETE, no TRUNCATE):
--   select string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name = 'rf_draws';
--
-- Confirm the retainage-range constraint bites (expect an ERROR, not a row):
--   insert into public.rf_draws (license_hash, draw_id, job_id, retainage_pct)
--   values ('test', 'RFDRAW-CHECK', 'J', 140);
--
-- Then re-run sql/schema_snapshot_query.sql so db/schema_snapshot.json carries
-- this table.
