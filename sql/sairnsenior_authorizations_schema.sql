-- sql/sairnsenior_authorizations_schema.sql
-- SAIRNsenior payer authorisation tracking -- Supabase schema (2026-09-02)
--
-- Competitive-gap audit item A3 ("payer authorisation tracking with unit
-- burn-down"). The audit records this as a genuine differentiator rather than
-- catch-up: it was NOT found described in any Tier A product, and is named as a
-- Tier-B-only capability by the research. Additive and idempotent; run after
-- sql/sairnsenior_clients_schema.sql and
-- sql/sairnsenior_payer_contracts_schema.sql. Nothing in either is duplicated
-- here.
--
-- WHAT THIS STORES. One table:
--
--   sen_authorizations   ONE authorisation a payer issued for ONE client: its
--                        number, the period it covers, and how many units it
--                        approved.
--
-- ── WHAT WAS ALREADY THERE, AND WHY THIS IS NOT A DUPLICATE ─────────────
-- The Clients panel already has an "Authorization Burn-Down -- this week"
-- table. It is real and it stays. But it measures against
-- `sen_clients.authorized_hours`, which is a SINGLE WEEKLY HOURS FIGURE on the
-- client record: no number, no payer, no period, no expiry, no history. It
-- answers "is this week's schedule sane against the care plan."
--
-- IT CANNOT ANSWER THE QUESTION A PAYER ASKS. A Medicaid or MCO authorisation
-- is issued for a PERIOD -- e.g. 520 units between 1 January and 30 June -- and
-- the agency is paid for what falls inside it. A weekly hours figure with no
-- start and no end cannot tell anyone how much of that period authorisation is
-- left, cannot expire, and cannot be cited on a claim or in an appeal. That is
-- the record this table adds, and the weekly view now says on screen which of
-- the two questions it is answering.
--
-- ── UNITS ARE CONVERTED EXACTLY, AND NO STATE ROUNDING RULE IS INVENTED ──
-- Each authorisation declares its own `minutes_per_unit` (15, 30 or 60), and
-- consumption is hours x 60 / minutes_per_unit, computed exactly.
--
-- REAL MEDICAID PROGRAMMES ROUND PER VISIT, AND THE RULE DIFFERS BY STATE --
-- some round down, some apply an eight-minute rule, some bill exact. **No such
-- rule is applied here and none is guessed.** Picking one would make the
-- remaining-units figure quietly wrong for every state that uses a different
-- one, and a units figure that is confidently wrong is worse than an exact one
-- labelled as unrounded. The panel says so where the number is shown.
--
-- ── CONSUMPTION IS COMPUTED FROM VISITS, NEVER STORED ───────────────────
-- There is no `units_used` column and there must not be. A stored counter
-- drifts the moment a visit is edited, cancelled or re-clocked, and nothing
-- afterwards can say whether the counter or the visits are right. Burn-down is
-- recomputed from sen_visits every render, the same discipline as the branch
-- rollup (B1) and the hiring retention figures (A5).
--
-- DELIVERED AND SCHEDULED ARE NEVER MERGED. Delivered counts only real clocked
-- time; still-scheduled future visits are counted separately and shown as
-- their own column. Merging them is how a screen reports room that has already
-- been scheduled away. A PAST visit nobody clocked counts toward NEITHER and is
-- reported as its own number, because scheduling a visit is not evidence it
-- happened -- the same rule the weekly view already follows.
--
-- ── AMBIGUITY REFUSES, AS IT DOES FOR CONTRACTS ─────────────────────────
-- Where two authorisations for the same client are both in force on a service
-- date, NOTHING is applied -- not the newer, not the larger, not the first row.
-- Burning units off an authorisation nobody chose produces a remaining figure
-- that is wrong on both records at once. The overlap is surfaced on the panel
-- instead, to whoever can fix it.
--
-- ── service_code IS RECORDED AND REPORTED, AND NOTHING IS MATCHED ON IT ──
-- Real authorisations are issued per HCPCS code (T1019, S5125, ...) and a
-- biller needs it to cite the authorisation. It is stored and displayed. But
-- sen_visits carries NO service code, so matching on it would match nothing --
-- and pretending otherwise would make an authorisation look narrower than it
-- is being enforced. The panel states this rather than leaving it implied,
-- exactly as the branch panel states that its state column is not yet what EVV
-- is matched on.
--
-- SECURITY MODEL: service-role only, RLS enabled, no anon policy -- matching
-- every other sen_* table. The API gate is SPLIT, and differs from
-- sen_payer_contracts deliberately: READ is open to management, coordinators
-- and schedulers, because remaining units are SCHEDULING CAPACITY and the
-- person deciding whether to book another visit is exactly who needs them --
-- and an authorisation carries units, not money. WRITE is management-only:
-- recording what a payer approved is not a scheduling decision.
--
-- NO DELETE GRANT. sql/unused_delete_grant_revoke_2026-08-24.sql revoked it
-- platform-wide and no code path here deletes. A finished authorisation keeps
-- its history -- deleting it would leave every visit delivered under it with
-- nothing to say it was authorised at all, which is precisely the record an
-- appeal needs.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.sen_authorizations (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairnsenior',
  auth_id       text not null,
  data          jsonb not null default '{}'::jsonb,   -- client_id, client_name, payer, auth_number, service_code, units_authorized, minutes_per_unit (15|30|60), start_on, end_on, active, notes, created_at
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (license_hash, auth_id),
  constraint senaz_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_senaz_license on public.sen_authorizations(license_hash);

alter table public.sen_authorizations enable row level security;

drop policy if exists "svc only sen_authorizations" on public.sen_authorizations;

create policy "svc only sen_authorizations" on public.sen_authorizations
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant usage on schema public to service_role;
grant select, insert, update on public.sen_authorizations to service_role;
revoke all on public.sen_authorizations from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sen_authorizations;
--
-- Confirm no delete grant took hold (expect SELECT, INSERT, UPDATE only):
--   select privilege_type from information_schema.role_table_grants
--    where grantee = 'service_role' and table_name = 'sen_authorizations';
