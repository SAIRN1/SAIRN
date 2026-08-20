-- sql/sairncare_billing_schema.sql
-- SAIRNcare Billing (private-pay + state-gated Medicaid HCBS waiver) --
-- Supabase schema.
--
-- WHY THIS IS A SEPARATE TABLE, NOT folded into alf_clients.data like ADL:
-- alf_clients' read endpoint returns the resident's ENTIRE data blob to
-- anyone who can read that resident, including a Med Aide or Caregiver
-- (narrow tier) reading their own assigned resident. Billing amounts are
-- not clinical/care data and have no minimum-necessary reason to reach a
-- clinical role -- same reasoning that put alf_mar in its own gated table
-- rather than the general resident-edit path. Management-only, full stop,
-- same simplification sen_claims already established: "financial/billing
-- data, not clinical assignment data, no assignee-based visibility at all."
--
-- WHY PRIVATE-PAY AND MEDICAID HCBS ARE TWO SEPARATE AMOUNT FIELDS ON THE
-- SAME INVOICE ROW, never summed into one figure: real research (logged
-- in the original SAIRNcare v1 scope doc) found assisted-living billing is
-- primarily private-pay (room/board + care-level rate); where Medicaid
-- coverage exists it runs through a state HCBS waiver that covers ONLY the
-- care portion, NEVER room/board, and many facilities don't accept
-- Medicaid at all. Structurally separating room_board_amount (always
-- private, always owed by the resident/family) from care_amount (which
-- MAY be billed to Medicaid HCBS only if the facility is actually enrolled
-- for it) makes the two figures impossible to accidentally conflate in
-- code, rather than relying on every call site remembering the rule.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.alf_billing (
  id                    uuid primary key default gen_random_uuid(),
  license_hash          text not null,
  app_id                text not null default 'sairncare',
  entry_id              text not null,                 -- stable per resident+month
                                                          -- (INV-<resident_id>-<YYYY-MM>) so
                                                          -- regenerating a month's invoice
                                                          -- corrects it in place, real mutable
                                                          -- record, not an append-only log.
  resident_id           text not null,                  -- references alf_clients.client_id
  data                  jsonb not null default '{}'::jsonb,    -- month, room_board_amount,
                                                          -- care_amount, private_total,
                                                          -- private_status, hcbs_claim_amount,
                                                          -- hcbs_status, generated_by, notes
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfbilling_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfbilling_license on public.alf_billing(license_hash);
create index if not exists idx_alfbilling_resident on public.alf_billing(license_hash, resident_id);

grant select, insert, update on public.alf_billing to service_role;
revoke all on public.alf_billing from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from alf_billing;
