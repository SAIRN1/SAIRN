-- sql/sairncare_facility_schema.sql
-- SAIRNcare facility profile -- Supabase schema. Run this once in the
-- Supabase SQL editor before api/sd-data.js's alf_facility branch will work.
--
-- WHY THIS TABLE EXISTS AT ALL: the facility profile (name, company,
-- controlled-substance count policy, incident-reporting deadline, rate card)
-- previously lived ONLY in localStorage under the 'alf_facility' key, written
-- through st() and never synced anywhere. That was fine for a device
-- preference and wrong for what this data actually is -- a facility's
-- licensing state is a legal fact about a licensed entity, identical on every
-- device, and a later compliance-rules engine cannot trust a value that each
-- browser holds its own private copy of. Moving it server-side is the point of
-- this table; licensing_state is the field that forced it.
--
-- WHY IT IS KEYED BY facility_id AND NOT JUST license_hash: a CCRC campus
-- routinely holds MORE THAN ONE license -- in most states a skilled-nursing
-- unit is licensed separately from the assisted-living units it shares a
-- campus with, under different statutes with different reporting rules. One
-- row per (license_hash, facility_id) is therefore the honest shape from the
-- start. v1 writes a single 'FAC-DEFAULT' facility and ships no facility
-- switcher UI -- but the KEY is already right, so adding the second licensed
-- entity later is a new row rather than a migration of every existing one.
--
-- licensing_state IS VALIDATED, NOT FREE TEXT. The two existing state-ish
-- fields in this app are both free text (the incident deadline string and the
-- HCBS waiver state box), which is why neither can drive a rules engine. This
-- one is checked server-side against the real 50-state + DC USPS list. It
-- deliberately accepts ALL of them even though the compliance-rules engine
-- seeds on OH/IN/MI/PA only -- restricting the input to four states would
-- encode a limit that does not exist in reality. An unseeded state gets an
-- honest "no rules loaded for <state>", never silent coverage.
--
-- hcbs_state IS DELIBERATELY LEFT ALONE and is NOT derived from
-- licensing_state. They are normally the same value and it would be easy to
-- merge them; that is exactly why it is worth stating that we did not. The
-- existing Medicaid-toggle field gets sorted out when the payer-routing engine
-- phase actually touches it, not as a silent side effect of this one.

create table if not exists public.alf_facility (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncare',
  facility_id  text not null,                        -- 'FAC-DEFAULT' for single-facility operators
  data         jsonb not null default '{}'::jsonb,   -- name, company, licensing_state, license_number,
                                                     -- cs_policy, incident_deadline, and the rate card
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, facility_id),
  constraint alffacility_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alffacility_license on public.alf_facility(license_hash);

grant select, insert, update on public.alf_facility to service_role;
revoke all on public.alf_facility from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from alf_facility;
