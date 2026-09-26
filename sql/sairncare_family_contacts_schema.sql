-- sql/sairncare_family_contacts_schema.sql
-- SAIRNcare -- the family / responsible-party record on a resident, and the
-- per-contact MAR consent flag.
--
-- Run as the project owner in the Supabase SQL editor. Idempotent.
--
-- ── WHY THIS TABLE EXISTS ──────────────────────────────────────────────────
-- Measured 2026-09-25 before it was scoped: SAIRNcare had NO family or
-- responsible-party record of any kind. `sql/sairncare_clients_schema.sql`'s
-- own comment lists `emergency_contact` among the `data` jsonb fields and the
-- UI never writes or reads it -- the only "emergency" in sairncare.html is
-- preparedness drills in the Operational Audit panel.
--
-- A family portal cannot exist without this. It is also the precondition for
-- the MAR decision below: consent is granted PER CONTACT, so there has to be a
-- contact to grant it to.
--
-- ── THE DECISION THIS TABLE ENFORCES ───────────────────────────────────────
-- Michael, 2026-09-26: family MAR access is READ-ONLY and CONSENT-GATED, and
-- consent is OFF until explicitly granted. Once granted, a family member sees
-- medication administration STATUS only -- given/missed, scheduled time,
-- adherence -- and never the full editable MAR, never PRN clinical reasoning,
-- never controlled-substance counts.
--
-- Two things agree on that shape, from opposite directions: HIPAA's MINIMUM
-- NECESSARY standard (the purpose a relative has is "is my mother being
-- looked after", which a medication LIST is not needed to answer -- and a
-- medication list is a diagnosis by inference), and the category's settled
-- competitive pattern, where PointClickCare's Connected Care Center and
-- AlayaCare's family portal both surface care-event STATUS rather than the
-- clinical record. `api/_lib/alf-family-mar.js` is where the projection lives
-- and it names every stripped field with its reason.
--
-- ── `mar_consent` IS NOT NULL DEFAULT false, AND THAT IS THE WHOLE POINT ────
-- Not nullable-with-a-null-default, which would make "nobody has decided" and
-- "decided no" the same value and tempt a reader into treating NULL as
-- permissive. FALSE is a decision this table asserts on every row: a contact
-- that exists has not consented until somebody records that they did.
--
-- A default of `true` would be unthinkable; a NULLABLE column here is the same
-- mistake one step quieter, because every place that reads it would have to
-- remember `=== true` and one of them eventually will not. The engine checks
-- `!== true` regardless -- belt and braces, on the one flag where a coercion
-- ('true' as a string is truthy) discloses clinical information.
--
-- ── REVOCATION IS `active = false`, NOT A DELETE ───────────────────────────
-- Same discipline as every *_employee_auth table. A revoked contact stays on
-- the record with `revoked_at`, so the facility can show WHO had access and
-- WHEN it ended -- which is the question anybody asks after the fact. The
-- engine refuses an inactive contact even when mar_consent is still true, so
-- revocation never depends on remembering to unset a second field.

create table if not exists public.alf_family_contacts (
  id                 uuid primary key default gen_random_uuid(),
  license_hash       text not null,
  app_id             text not null default 'sairncare',
  contact_id         text not null,          -- client-generated, stable (FC-<timestamp>)
  resident_id        text not null,          -- references alf_clients.client_id
  name               text not null,
  relationship       text,                   -- daughter, son, POA, guardian, friend...
  -- CONTACT DETAILS ARE PII AND ARE NOT SURFACED BY THE PORTAL. They exist so
  -- the facility can reach the family, not so the portal can display them.
  email              text,
  phone              text,
  -- ── THE CONSENT FLAG ───────────────────────────────────────────────────
  -- NOT NULL, DEFAULT FALSE. See the header: a nullable column here makes
  -- "nobody decided" and "decided no" the same value, and every reader would
  -- have to remember `= true`.
  mar_consent        boolean not null default false,
  consent_granted_at timestamptz,            -- null while mar_consent is false
  consent_granted_by text,                   -- employee_id from the verified session
  consent_revoked_at timestamptz,            -- set when consent is withdrawn; the
                                             -- grant timestamps are NOT cleared, so the
                                             -- record still says who granted it and when
  -- Revocation of the CONTACT itself. Deactivate, never delete.
  active             boolean not null default true,
  revoked_at         timestamptz,
  notes              text,
  recorded_by        text,                   -- employee_id from the verified session
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (license_hash, contact_id),
  constraint alffam_data_size check (octet_length(coalesce(notes, '')) <= 4096),
  -- A grant with no timestamp is a grant nobody can audit. Enforced in the
  -- database rather than only in the handler, because this is the row an
  -- auditor reads.
  constraint alffam_consent_has_a_date check (mar_consent = false or consent_granted_at is not null)
);

-- Idempotent for an install that ran an earlier version of this file.
alter table public.alf_family_contacts
  add column if not exists consent_revoked_at timestamptz,
  add column if not exists revoked_at         timestamptz,
  add column if not exists notes              text;

create index if not exists idx_alffam_license
  on public.alf_family_contacts (license_hash, created_at desc);
-- "who is family to this resident" is the question this table is asked.
create index if not exists idx_alffam_resident
  on public.alf_family_contacts (license_hash, resident_id);
-- And the one the portal asks: which contacts may currently see medication status.
create index if not exists idx_alffam_consent
  on public.alf_family_contacts (license_hash, resident_id, mar_consent, active);

alter table public.alf_family_contacts enable row level security;

-- SELECT, INSERT and UPDATE. UPDATE is required -- granting and revoking
-- consent, and deactivating a contact, are all updates. Still NO DELETE: who
-- had access to a resident's medication status, and when, is a record the
-- facility may have to produce.
grant select, insert, update on public.alf_family_contacts to service_role;
revoke all on public.alf_family_contacts from anon, authenticated;

-- ── VERIFY ──────────────────────────────────────────────────────────────────
-- Expect the columns below and ZERO rows.
select column_name, data_type, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public' and table_name = 'alf_family_contacts'
 order by ordinal_position;

select count(*) as should_be_zero from public.alf_family_contacts;

-- THE CONSENT FLAG MUST BE NOT NULL WITH DEFAULT false. If is_nullable says
-- YES, "nobody has decided" and "decided no" have become the same value and a
-- reader that forgets `= true` will disclose medication information. If the
-- default is anything but false, every contact ever created is consented:
select column_name, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public' and table_name = 'alf_family_contacts'
   and column_name in ('mar_consent', 'active')
 order by column_name;
-- Expect: mar_consent NO / false, active NO / true.

-- And the constraint that stops an unauditable grant:
select conname, pg_get_constraintdef(oid) as definition
  from pg_constraint
 where conrelid = 'public.alf_family_contacts'::regclass
   and conname = 'alffam_consent_has_a_date';
-- Expect ONE row. Its absence means a row can claim consent with no date on it.

-- And confirm the grant is select+insert+update, with NO delete:
select privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public' and table_name = 'alf_family_contacts'
   and grantee = 'service_role'
 order by privilege_type;
-- Expect exactly: INSERT, SELECT, UPDATE
