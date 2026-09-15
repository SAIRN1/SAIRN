-- sql/biometric_consent_schema.sql
-- Biometric consent and retention, cross-app. Additive, idempotent
-- (create table if not exists), safe to re-run.
--
-- ── WHY THIS IS SCHEMA AND NOT ONLY CODE ───────────────────────────────────
-- api/_lib/biometric-consent.js decides when a template must be destroyed.
-- THIS FILE MAKES IT IMPOSSIBLE TO STORE ONE THAT OUTLIVES THAT ANSWER, even
-- if that module has a bug, even if a caller bypasses it entirely, even if
-- somebody writes a row by hand in the Supabase console.
--
-- Application code is where a rule is APPLIED. A schema is where it cannot be
-- SKIPPED. Every prior retention promise on this platform lived only in the
-- first place.
--
-- ── WHO IS WHO ─────────────────────────────────────────────────────────────
-- SAIRN is the PROCESSOR. The SAIRN customer -- identified here by
-- license_hash -- is the CONTROLLER and bears the consent duty. Nothing in
-- this schema can create a consent; it records the three artefacts the
-- controller produced and refuses the ones that do not add up.
--
-- ── TWO TABLES, AND THE SPLIT IS THE POINT ─────────────────────────────────
-- biometric_consent   the RECORD that notice, purpose/duration and a signed
--                     release happened, in that order. RETAINED. It is the
--                     evidence that collection was lawful, and destroying it
--                     destroys the proof.
-- biometric_template  the identifier ITSELF. DESTROYED on schedule.
--
-- Conflating them gives exactly two outcomes and no third: keep everything and
-- blow the retention limit, or delete everything and have no evidence consent
-- was ever obtained.

create extension if not exists pgcrypto;

-- ───────────────────────────────────────────────────────────────────────────
-- 1. THE CONSENT RECORD -- retained
-- ───────────────────────────────────────────────────────────────────────────
create table if not exists public.biometric_consent (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,                 -- the CONTROLLER
  app_id text not null,
  subject_id text not null,                   -- the person, in the app's own id space
  -- THE THREE-PART SEQUENCE. All three NOT NULL: a partially-recorded sequence
  -- is not a consent, and a nullable column here would let one exist.
  notice_at timestamptz not null,
  purpose_duration_at timestamptz not null,
  release_at timestamptz not null,
  purpose text not null,
  disclosed_retention_days integer not null,
  release_signature text not null,
  withdrawn_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, app_id, subject_id),
  -- ORDER IS A CONSTRAINT, NOT A CONVENTION. Three present timestamps in the
  -- wrong order is the exact shape of a form assembled after the fact: a
  -- release signed before the person was told what it was about is not a
  -- release, and a purpose disclosed afterwards is not a disclosure.
  -- <= rather than <: one screen can legitimately carry notice and purpose
  -- together, and refusing that would be a rule about clock resolution.
  constraint biometric_consent_in_order
    check (notice_at <= purpose_duration_at and purpose_duration_at <= release_at),
  -- A DISCLOSED DURATION LONGER THAN THE CEILING IS NOT A DISCLOSURE, it is a
  -- promise that cannot be kept. Refused at write time rather than silently
  -- clamped, because clamping would leave the person holding a piece of paper
  -- that says something different from what the database does.
  constraint biometric_consent_duration_within_ceiling
    check (disclosed_retention_days > 0 and disclosed_retention_days <= 1095),
  constraint biometric_consent_purpose_specific
    check (length(btrim(purpose)) >= 8),
  constraint biometric_consent_signed
    check (length(btrim(release_signature)) > 0)
);
create index if not exists idx_biometric_consent_license
  on public.biometric_consent(license_hash);
alter table public.biometric_consent enable row level security;
revoke all on public.biometric_consent from service_role;
-- NO DELETE. The consent record is the evidence of compliance and outlives the
-- template it authorised. Withdrawal is `withdrawn_at`, which is an UPDATE.
grant select, insert, update on public.biometric_consent to service_role;

-- ───────────────────────────────────────────────────────────────────────────
-- 2. THE TEMPLATE -- destroyed on schedule
-- ───────────────────────────────────────────────────────────────────────────
create table if not exists public.biometric_template (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null,
  subject_id text not null,
  -- The identifier itself, always encrypted by the caller before it arrives.
  -- This column is never read back by any SAIRN surface; it exists to be
  -- matched against and then destroyed.
  template bytea not null,
  -- The clock the deadline is measured from. Bumped on every interaction, so a
  -- person who keeps using the system keeps a live template, and a person who
  -- stops starts the three-year countdown at their LAST use rather than their
  -- first.
  last_interaction_at timestamptz not null default now(),
  disclosed_retention_days integer not null,
  -- ── THE CEILING, ENFORCED WHERE IT CANNOT BE SKIPPED ─────────────────────
  -- GENERATED, so no writer chooses it. The earlier of the controller's own
  -- disclosed duration and three years from the last interaction.
  destroy_by timestamptz generated always as (
    least(last_interaction_at + (disclosed_retention_days || ' days')::interval,
          last_interaction_at + interval '3 years')
  ) stored,
  destroyed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (license_hash, app_id, subject_id),
  -- BELT AND BRACES ON THE GENERATED COLUMN. If somebody later edits that
  -- expression, this check still refuses anything past the ceiling. The
  -- generated column is the MECHANISM and this is the RULE, and they are
  -- deliberately not the same statement.
  constraint biometric_template_ceiling
    check (destroy_by <= last_interaction_at + interval '3 years'),
  constraint biometric_template_duration_within_ceiling
    check (disclosed_retention_days > 0 and disclosed_retention_days <= 1095)
);
create index if not exists idx_biometric_template_license
  on public.biometric_template(license_hash);
-- The destruction job's whole query: everything past its deadline and not yet
-- destroyed. Indexed, because a retention job that gets slow is a retention job
-- somebody turns off.
create index if not exists idx_biometric_template_due
  on public.biometric_template(destroy_by) where destroyed_at is null;
alter table public.biometric_template enable row level security;
revoke all on public.biometric_template from service_role;
-- ── DELETE IS GRANTED HERE, AND ONLY HERE, AND IT IS A DECISION ────────────
-- Every non-sc_* schema on this platform has had its delete grant removed
-- since 2026-08-25, and this file deliberately departs from that.
--
-- A RETENTION POLICY THAT CANNOT DELETE IS NOT A RETENTION POLICY. Soft delete
-- is the right answer everywhere else precisely because the record is worth
-- keeping; here the whole obligation is that the identifier STOPS EXISTING. A
-- `_deleted_at` marker on a biometric template is a template that is still in
-- the database with a note on it.
--
-- The blast radius is bounded by the split above: the CONSENT record has no
-- delete grant, so nothing here can destroy the evidence that collection was
-- lawful. What this grant can destroy is the thing that is supposed to be
-- destroyed.
grant select, insert, update, delete on public.biometric_template to service_role;

-- ───────────────────────────────────────────────────────────────────────────
-- Verify after running.
--
--   select table_name, count(*) from information_schema.columns
--    where table_schema = 'public' and table_name like 'biometric%'
--    group by table_name order by table_name;
--
-- Then prove the ceiling is REAL rather than documented. Both of these must be
-- REFUSED; a run where either succeeds means the constraint did not apply and
-- the policy is back to being a paragraph:
--
--   insert into public.biometric_template
--     (license_hash, app_id, subject_id, template, disclosed_retention_days)
--   values ('zz-probe', 'zz', 'zz', decode('00', 'hex'), 4000);
--   -- expected: violates check constraint
--   --           "biometric_template_duration_within_ceiling"
--
--   insert into public.biometric_consent
--     (license_hash, app_id, subject_id, notice_at, purpose_duration_at,
--      release_at, purpose, disclosed_retention_days, release_signature)
--   values ('zz-probe', 'zz', 'zz', now(), now(), now() - interval '1 hour',
--           'clock-in verification', 365, 'ZZ Probe');
--   -- expected: violates check constraint "biometric_consent_in_order"
--
-- And that destroy_by is computed rather than accepted:
--
--   insert into public.biometric_template
--     (license_hash, app_id, subject_id, template, disclosed_retention_days,
--      last_interaction_at)
--   values ('zz-probe', 'zz', 'zz2', decode('00','hex'), 1095, now());
--   select destroy_by - last_interaction_at from public.biometric_template
--    where subject_id = 'zz2';
--   -- expected: 1095 days, and NOT a value the insert chose
--
--   delete from public.biometric_consent where license_hash = 'zz-probe';
--   -- expected: permission denied -- the evidence is not deletable
--   delete from public.biometric_template where license_hash = 'zz-probe';
--   -- expected: succeeds -- the identifier is
