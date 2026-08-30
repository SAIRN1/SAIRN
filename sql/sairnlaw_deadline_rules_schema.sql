-- sql/sairnlaw_deadline_rules_schema.sql
-- SAIRNlaw deadline rules engine (2026-08-21). Run once in the Supabase SQL
-- editor. See docs/superpowers/specs/2026-08-21-sairnlaw-deadline-rules-engine-design.md
--
-- ══ law_deadlines FIXES A REAL PRE-EXISTING BREAK ═══════════════════════════
-- sairnlaw.html has been calling sdnData('write','law_deadlines') since before
-- this work (lines ~2188 and ~2195) against a resource that was never
-- registered. Production returned 400 "unrecognized resource" while
-- law_matters returned 200. It failed HONESTLY -- the toast reads "Saved on
-- this device only -- server sync not yet enabled for this app" -- but every
-- deadline in SAIRNlaw lived on exactly one browser, was never hydrated back,
-- and was lost with the profile.
--
-- This table is created FIRST, before the engine, because an engine that
-- computes a correct statutory date into a resource that 400s is worse than no
-- engine at all: the user then believes the date is recorded.
--
-- ══ WHY RULES ARE DATA ROWS AND NOT HANDLER CODE ═══════════════════════════
-- 1. The law changes. A handler must be redeployed; a row can be superseded.
-- 2. A rule must be auditable -- a partner has to see WHICH authority produced
--    a date and follow it to the source. Hence the required authority URL.
-- 3. A deadline must be computable as the law stood at the TRIGGER date, not
--    as it stands today. A matter triggered in 2023 must compute against the
--    2023 rule. That is impossible if the rule is code.
-- Rules are therefore superseded ADDITIVELY: an amendment is a new row
-- pointing at the old one via supersedes. Never edited in place, never deleted.
--
-- ══ WHY HOLIDAYS ARE A SEPARATE TABLE KEYED BY JURISDICTION *AND YEAR* ══════
-- FRCP 6(a)(6) counts any day declared a holiday by the President or Congress
-- -- those appear with little notice and cannot live in code. It also makes
-- the definition DIRECTION-DEPENDENT: a holiday declared by the state where
-- the district court sits counts only for FORWARD-counted periods. A flat
-- holiday array silently gets backward counting wrong, so each row carries a
-- `kind` ('federal' | 'declared' | 'state') that the engine consults against
-- the direction of the count.
--
-- Keying by year is not cosmetic. A 21-day period triggered 20 December runs
-- into the following year, so the engine must refuse on the year it ACTUALLY
-- NEEDS rather than the year of the trigger. Computing against a missing
-- calendar would silently skip New Year's Day.

-- ── Deadlines (the pre-existing break) ────────────────────────────────────
create table if not exists public.law_deadlines (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnlaw',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint law_deadlines_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_deadlines_license on public.law_deadlines(license_hash);

-- ── Deadline rules ────────────────────────────────────────────────────────
-- Shape of `data` (validated client-side and by api/legal-deadlines.js; the
-- generic sc_*-style handler does not inspect jsonb, so it is documented where
-- the table lives):
--   rule_id, jurisdiction, domain, label, trigger_event,
--   count: { value, unit: calendar_days|business_days|months|years,
--            direction: forward|backward },
--   computation: 'frcp_6a' | 'frap_26a' | 'bankr_9006a'   (named, versioned)
--   service_extension: { standard, add, unit, applies_when[], order }
--   authority: { citation, url, retrieved_at, verified_by }   -- URL REQUIRED
--     `verified_by` is the odd one out and is NOT provenance. Corrected
--     2026-08-29: it records whoever was SIGNED IN when the row was written --
--     a bearer-key load stamps null, a session load stamps an employee id --
--     not who verified the rule. citation / url / retrieved_at are the real
--     provenance and are what a partner would follow to the source.
--     BECAUSE IT LIVES INSIDE `data` HERE, it is part of the blob hash, so a
--     session-loaded licence and a loader-loaded licence differ on EVERY row.
--     That produced a false 87-rules / 48-calendars "divergence" on 2026-08-28.
--     Both the platform divergence query and api/reference-fingerprint.js now
--     subtract this one field by name -- and NOTHING ELSE from `authority`,
--     since a changed citation or URL is a real defect they must still catch.
--   effective_from, effective_to, version, supersedes
create table if not exists public.law_deadline_rules (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnlaw',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint law_deadline_rules_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_deadline_rules_license on public.law_deadline_rules(license_hash);

-- ── Holiday calendars ─────────────────────────────────────────────────────
-- entry_id is '<jurisdiction>:<year>' so a year can be loaded independently.
-- data: { jurisdiction, year, dates: [{date,name,kind}], authority:{...} }
create table if not exists public.law_holidays (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnlaw',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint law_holidays_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_law_holidays_license on public.law_holidays(license_hash);

-- ── RLS: service-role only, same posture as every other SAIRNlaw table ────
alter table public.law_deadlines       enable row level security;
alter table public.law_deadline_rules  enable row level security;
alter table public.law_holidays        enable row level security;

drop policy if exists "svc only law_deadlines"      on public.law_deadlines;
drop policy if exists "svc only law_deadline_rules" on public.law_deadline_rules;
drop policy if exists "svc only law_holidays"       on public.law_holidays;

create policy "svc only law_deadlines"      on public.law_deadlines      for all using (false) with check (false);
create policy "svc only law_deadline_rules" on public.law_deadline_rules for all using (false) with check (false);
create policy "svc only law_holidays"       on public.law_holidays       for all using (false) with check (false);

-- DELETE removed 2026-08-25 -- these lines previously granted it. The live
-- grant was revoked platform-wide by sql/unused_delete_grant_revoke_2026-08-24.sql
-- (134 tables, verified 134 LOST / 0 GAINED). This file is `create table if not
-- exists` and safe to re-run, so leaving `delete` here would silently restore it.
-- The platform's ONLY reachable delete path is api/sd-data.js's SC_RESOURCES
-- (SAIRNcode) branch; do NOT re-add `delete` here when fixing a missing grant.
grant select, insert, update on public.law_deadlines      to service_role;
grant select, insert, update on public.law_deadline_rules to service_role;
grant select, insert, update on public.law_holidays       to service_role;

revoke all on public.law_deadlines      from anon, authenticated;
revoke all on public.law_deadline_rules from anon, authenticated;
revoke all on public.law_holidays       from anon, authenticated;

-- ══ SEEDING IS DELIBERATELY NOT DONE HERE ══════════════════════════════════
-- No rules and no holiday calendars are inserted by this migration. Same
-- discipline as sc_scrubrules and sc_credential_scope in SAIRNcode: a rule
-- with no traceable, human-verified source must not exist, and a migration
-- cannot carry that verification.
--
-- The seed set (US Federal civil, FRCP Rule 12 responses) is loaded through
-- api/legal-deadlines.js's add_rule action, which REJECTS any rule lacking an
-- authority URL. That way every row in this table was put there by someone who
-- read the rule, and the row records who and when.
--
-- Verify after running (expect 0, 0, 0 and no error):
--   select
--     (select count(*) from law_deadlines)      as deadlines,
--     (select count(*) from law_deadline_rules) as rules,
--     (select count(*) from law_holidays)       as holidays;
