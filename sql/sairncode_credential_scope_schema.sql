-- sql/sairncode_credential_scope_schema.sql
-- Real server-synced table for SAIRNcode's provider credential scope
-- (Phase 4 item 7 of the 2026-08-20 gap-closure arc). Run this once in the
-- Supabase SQL editor before api/sd-data.js's sc_credential_scope
-- read/write/delete branch will work.
--
-- WHY THIS TABLE EXISTS AT ALL, and why sc_providers could not just be
-- extended: item 7 is "gate every code assignment on the billing provider's
-- actual credentialed specialty FOR THAT SPECIFIC CODE." The existing
-- sc_providers record cannot express that, checked directly before building
-- rather than assumed:
--   * its `cred` field is a Yes/No dropdown -- credentialed-at-all, not
--     credentialed-for-a-given-code;
--   * its `specialty` field is FREE TEXT, so "Cardiology", "cardiology" and
--     "Cards" are three different values and nothing can reliably match a
--     code against them;
--   * nothing anywhere linked a provider to a claim, coded item, or denial.
-- A credential grant is also genuinely a different object from a provider
-- (one provider holds many, each with its own source and its own scope),
-- the same reasoning that put sc_auth_requests in its own table rather than
-- overloading sc_auth.
--
-- WHY THIS TABLE STARTS EMPTY AND IS NEVER SEEDED:
-- Which specialties may bill which codes is exactly the class of claim this
-- project does not hardcode. Payer policy, state scope-of-practice law, and
-- plan-level credentialing all vary, and none of it was verified against a
-- primary source here. Seeding even one plausible-looking mapping into a
-- compliance tool would be the same fabrication class the 2026-08-18 audit
-- removed from this app elsewhere. So this is an honest empty table the
-- practice populates with scopes THEY have verified, and the Add form makes
-- `source` required for exactly that reason -- identical discipline to
-- sc_scrubrules and sc_specialty_checklists.
--
-- THE GATE FAILS CLOSED, BY DECISION (confirmed with Michael 2026-08-20):
-- when a provider has no credential rows, the gate does NOT pass the code.
-- It routes the coded item to human review with an honest "no credentialed-
-- specialty data on file for this provider" reason. An empty table silently
-- green-lighting every code would be worse than having no gate at all --
-- the same fail-closed principle as the quote_verified fix in Phase 1.
-- It is a disclosed SOFT block, not a hard stop: the coder can add the real
-- data, or accept the code on their own recorded judgment, so an empty
-- table never freezes the workflow.
--
-- Shape of the jsonb `data` column:
--   id           text  'cs'+Date.now(), mirrors entry_id
--   provider_id  text  the sc_providers entry this grant belongs to
--   provider_name text snapshot of the name at entry time, for display
--   specialty    text  from the app's existing 9-value specialty vocabulary
--   scope        text  which codes this grant covers -- see MATCHING below
--   source       text  REQUIRED. where the practice verified this grant
--   created_at   text  ISO timestamp
--
-- SCOPE MATCHING, deliberately literal and documented so a coder knows
-- exactly what they are entering (see scCodeInScope() in sairncode.html):
--   exact      "99291"       matches only 99291
--   prefix     "992*"        matches any code starting with 992
--   range      "99281-99285" matches codes numerically within, inclusive,
--                            comparing only the leading digits so an
--                            alphanumeric HCPCS code never silently falls
--                            into a numeric CPT range.
-- Nothing is inferred beyond these three forms. The app does not "know"
-- that a range is an E/M family or anything else about it -- it only
-- matches what the practice typed.

create table if not exists public.sc_credential_scope (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_credential_scope_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_credential_scope_license on public.sc_credential_scope(license_hash);

alter table public.sc_credential_scope enable row level security;
drop policy if exists "svc only sc_credential_scope" on public.sc_credential_scope;
create policy "svc only sc_credential_scope" on public.sc_credential_scope for all using (false) with check (false);

grant select, insert, update, delete on public.sc_credential_scope to service_role;
revoke all on public.sc_credential_scope from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_credential_scope;
