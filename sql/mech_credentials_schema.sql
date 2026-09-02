-- sql/mech_credentials_schema.sql
--
-- SAIRNmechanical technician credential registry. Run once in the Supabase SQL
-- editor. This is the FIRST data table this app has ever had.
--
-- ── WHY THIS FIRST ──────────────────────────────────────────────────────────
-- docs/superpowers/specs/2026-08-27-sairnmechanical-shared-platform-competitive-research.md
-- §9d ranks "Credential registry + expiry + dispatch eligibility" first of ten
-- capabilities: "Nothing else can be gated correctly until this exists."
--
-- Verified against the app before building rather than taken on faith. The
-- Technicians page is an honest empty state ("Technician certification tracking
-- is not live yet"), its "+ Add Tech" button has no handler, there was no
-- api/_resources/sairnmechanical.js, and the string `sairnmechanical` appeared
-- ZERO times in api/sd-data.js. The app has complete per-employee auth
-- (api/mech-auth.js, including the deactivation lifecycle) and, until now, no
-- data layer at all.
--
-- ── APPEND-ONLY, AND WHY THAT IS RIGHT HERE ─────────────────────────────────
-- A renewal is a NEW ROW, not an edit. api/_lib/mech-credentials.js picks the
-- latest per (technician, type, section-or-jurisdiction) by issue date, so the
-- history stays intact and "what did this technician hold on the day we
-- dispatched them" remains answerable. That question is the whole reason to
-- keep credential records at all -- editing a licence row in place destroys the
-- only evidence that matters after an incident.
--
-- No UPDATE grant and no DELETE grant, therefore. Correcting a mistyped row is
-- a new row that supersedes it; retiring a credential is a new row, not an
-- erasure.
--
-- ── has_expiry IS EXPLICIT, AND THAT IS THE POINT ───────────────────────────
-- EPA 608 certification does not expire (40 CFR 82.161 -- it is for life).
-- NATE does, on a two-year cycle. State HVAC/plumbing/electrical licences do,
-- on state-specific cycles. So `has_expiry` is stated per record and is NOT
-- NULL: a lifetime EPA card is has_expiry=false and reads 'current', while a
-- record that should have a date and has none reads 'unknown'. Collapsing
-- those into a null date would report a valid lifetime card as incomplete and
-- would hide a genuinely missing renewal behind the same symbol.
--
-- The endpoint REFUSES a write that omits has_expiry rather than defaulting it.
-- A default here would be the app guessing about a legal document.
--
-- ── epa_section IS NOT A QUALITY RANK ───────────────────────────────────────
-- Type I is small appliances, Type II high-pressure, Type III low-pressure,
-- Universal all three. A Type I technician is not "less certified" than a
-- Type II one; they are certified for different EQUIPMENT. Dispatching on
-- "has EPA 608" is how somebody gets sent to a chiller they may not legally
-- open, so the section is stored and matched on.
--
-- ── NO SEED DATA. NOT ONE ROW. ──────────────────────────────────────────────
-- This app's panels were de-fabricated on 2026-08-27 -- invented technicians
-- with invented NATE and EPA 608 certifications were presented as a live
-- roster. The table ships empty and the board says "nothing recorded" until a
-- real credential is entered. An invented certification is worse here than
-- anywhere else in the platform: it is a claim that a named person may legally
-- handle refrigerant.
--
-- ── SECURITY ────────────────────────────────────────────────────────────────
-- service_role only, RLS on with no anon policy, api/sd-data.js the only door.
-- Reads require a verified employee session; writes additionally require a
-- management role (api/mech-auth.js MANAGEMENT_ROLES). A technician must not be
-- able to record their own licence.

create table if not exists public.mech_credentials (
  id             uuid primary key default gen_random_uuid(),
  license_hash   text not null,
  credential_id  text not null,            -- client-generated, stable, unique per licence
  technician_id  text not null,            -- employee_id from mech_employee_auth
  record_type    text not null,            -- epa_608 | nate | state_license | manufacturer | safety_training | medical_gas | backflow
  epa_section    text,                     -- type_i | type_ii | type_iii | universal   (epa_608 only)
  jurisdiction   text,                     -- state/authority for state_license, backflow, medical_gas
  credential_no  text,
  issuer         text,
  issued_on      date,
  has_expiry     boolean not null,         -- stated, never defaulted -- see the header
  expires_on     date,
  notes          text,
  recorded_by    text,                     -- employee_id of the manager who entered it
  created_at     timestamptz not null default now(),
  unique (license_hash, credential_id)
);

create index if not exists idx_mech_cred_license
  on public.mech_credentials (license_hash, created_at desc);
-- The dispatch question is "what does THIS technician hold", asked per job.
create index if not exists idx_mech_cred_tech
  on public.mech_credentials (license_hash, technician_id, record_type);

alter table public.mech_credentials enable row level security;

-- SELECT and INSERT only. No UPDATE: a renewal is a new row and a licence
-- record must not be editable after the fact. No DELETE: it is evidence.
grant select, insert on public.mech_credentials to service_role;

-- ── VERIFY ──────────────────────────────────────────────────────────────────
-- Expect the columns below and ZERO rows.
select column_name, data_type, is_nullable
  from information_schema.columns
 where table_schema = 'public' and table_name = 'mech_credentials'
 order by ordinal_position;

select count(*) as should_be_zero from public.mech_credentials;

-- has_expiry must be NOT NULL -- if this says YES, the "stated, never guessed"
-- guarantee is not actually enforced by the table:
select is_nullable as has_expiry_is_nullable
  from information_schema.columns
 where table_schema = 'public' and table_name = 'mech_credentials'
   and column_name = 'has_expiry';
-- Expect: NO

-- And confirm the grant really is select+insert only. An UPDATE here would
-- quietly make a technician's licence history editable:
select privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public' and table_name = 'mech_credentials'
   and grantee = 'service_role'
 order by privilege_type;
-- Expect exactly: INSERT, SELECT
