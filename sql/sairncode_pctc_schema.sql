-- sql/sairncode_pctc_schema.sql
-- Real server-synced table for SAIRNcode's PC/TC Indicator Reference
-- (professional/technical component split billing, gap-closure pass 2
-- item 3, 2026-08-21). Run this once in the Supabase SQL editor before
-- api/sd-data.js's sc_pctc read/write/delete branch will work.
--
-- WHY THIS TABLE EXISTS AT ALL RATHER THAN THE CHECK BEING PURE ARITHMETIC:
-- whether a code can be split into -26 and -TC at all is not derivable from
-- the code number, the specialty, or anything else on the claim. It is a
-- per-code value CMS publishes in the PC/TC Indicator field (position 139)
-- of the National Physician Fee Schedule Relative Value File, and it is
-- revised annually with that file. A gate that guessed it from "this looks
-- like a radiology code" would be wrong for a large share of real codes --
-- see the indicator definitions in Attachment A of CMS's RVU file
-- documentation, where indicators 2, 3 and 4 describe codes that ARE the
-- professional-only / technical-only / global split expressed as separate
-- standalone codes, and for which modifiers 26 and TC explicitly "cannot be
-- used." Offering -26 on a 93010 is a real denial, not a harmless extra.
--
-- WHY IT STARTS EMPTY AND IS NEVER SEEDED:
-- the authoritative indicator list covers roughly ten thousand codes and is
-- reissued every year. Shipping a partial or stale copy inside this file
-- would be exactly the fabrication class the 2026-08-18 audit removed from
-- every other panel: data that looks authoritative, is not verifiable by the
-- person relying on it, and silently goes stale. So this is an honest empty
-- reference a practice populates from the real CMS RVU file for the year
-- they are billing, with a required Source field on the Add form, the same
-- discipline as sc_scrubrules, sc_anesthesia_base_units and
-- sc_credential_scope already follow. A code absent from this table returns
-- "not in your reference" and the gate fails closed -- it never assumes the
-- code is splittable, and never assumes it is not.
--
-- Same shape as every other sc_* resource: one row per entry, license_hash-
-- scoped, a jsonb data column. entry_id is the client's own locally-
-- generated id ('pt'+Date.now()).

create table if not exists public.sc_pctc (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_pctc_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_pctc_license on public.sc_pctc(license_hash);

alter table public.sc_pctc enable row level security;
drop policy if exists "svc only sc_pctc" on public.sc_pctc;
create policy "svc only sc_pctc" on public.sc_pctc for all using (false) with check (false);

grant select, insert, update, delete on public.sc_pctc to service_role;
revoke all on public.sc_pctc from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_pctc;
