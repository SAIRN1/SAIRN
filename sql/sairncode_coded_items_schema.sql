-- sql/sairncode_coded_items_schema.sql
-- Real server-synced table for SAIRNcode's per-coded-item citation and
-- review record (Phase 1 of the 2026-08-20 gap-closure arc, items 1+2).
-- Run this once in the Supabase SQL editor before api/sd-data.js's
-- sc_coded_items read/write/delete branch will work.
--
-- WHAT THIS TABLE IS FOR:
-- Before this table existed, suggestCodesFromNote() (sairncode.html) did
-- real work and then threw it away: it required the model to cite an exact
-- phrase from the note, independently verified that phrase was actually
-- present in the pasted text, and rendered the result -- but persisted
-- NOTHING. Confirmed by grep across that function's whole body before
-- building this: zero scData/localStorage writes. So a coder could see a
-- citation on screen and never be able to produce it again afterwards,
-- which is precisely backwards for a compliance tool where "why was this
-- code assigned" is the question that actually matters at audit time.
-- This table makes the citation + reasoning a real stored record.
--
-- WHY confidence IS A DERIVED LABEL AND NOT A MODEL-EMITTED NUMBER:
-- This is the single most important design decision in this table, and it
-- comes from this codebase's own history rather than from preference.
-- sairncode.html:2454 carries a standing comment recording that the Fraud
-- panel used to seed two fake alerts with a fabricated 82%/71% "confidence
-- score" -- removed in the 2026-08-18 fabrication audit as "claiming real
-- fraud-detection results that never ran." Asking a model for a confidence
-- percentage and storing it as though it measured something would recreate
-- exactly that bug, one panel over, with worse consequences (a percentage
-- on a code assignment reads as an accuracy claim to whoever sees it next).
--
-- So confidence here is computed by scDeriveCodedItemConfidence() from
-- signals that are mechanically checkable and already real:
--   * quote_verified === false  -> the cited phrase was NOT found in the
--     note text. This is a real string check this app already performs,
--     not an opinion.
--   * no quote returned at all  -> nothing to ground the code in.
--   * no source_rule recorded   -> no rule/edit cited behind the choice.
-- Any of those force review_status='needs_human_review'. The stored
-- confidence field is the string 'high' or 'low' ONLY, with a companion
-- confidence_basis listing which real signals fired. There is deliberately
-- no numeric score anywhere in this schema -- if a future phase wants one,
-- it needs a real measured base rate to compute it from, which does not
-- exist today.
--
-- WHY THERE IS NO "FORCE ASSIGN ANYWAY" PATH:
-- A low-confidence item is stored with review_status='needs_human_review'
-- and stays there until a real human sets it to reviewed_accepted or
-- reviewed_rejected, recording who and when. The app never silently
-- promotes a low-confidence suggestion into an assigned code, and never
-- picks a best guess when the signals say it does not have grounds -- that
-- was the explicit requirement ("never force a best-guess code").
--
-- Same generic shape as every other sc_* resource: one row per entry,
-- license_hash-scoped, a jsonb data column, so it rides api/sd-data.js's
-- existing SC_RESOURCES handler with no bespoke server branch. entry_id is
-- the client's own locally-generated id ('ci'+Date.now()).
--
-- Shape of the jsonb `data` column (documented here because the generic
-- handler does not validate it -- the client is the only place that knows
-- this shape, so it is written down where the table lives):
--   id                 text     'ci'+Date.now(), mirrors entry_id
--   code               text     the assigned/suggested code
--   code_type          text     'ICD-10' | 'CPT' | 'HCPCS'
--   encounter_ref      text     coder-supplied claim/encounter reference
--   quote              text     exact phrase cited from the note
--   quote_verified     boolean  REAL check result (substring match), not a claim
--   reasoning          text     why this code, from the suggestion
--   source_rule        text     which rule/edit/guideline supports it
--   confidence         text     'high' | 'low'  (derived, never numeric)
--   confidence_basis   text[]   which real signals fired
--   review_status      text     'auto_assigned' | 'needs_human_review'
--                             | 'reviewed_accepted' | 'reviewed_rejected'
--   escalation_reason  text     plain-language why this needs a human
--   reviewed_by        text     employee_id, set only on a real review
--   reviewed_at        text     ISO timestamp, set only on a real review
--   created_by         text     employee_id of whoever captured it
--   created_at         text     ISO timestamp

create table if not exists public.sc_coded_items (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairncode',
  entry_id     text not null,
  data         jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint sc_coded_items_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_sc_coded_items_license on public.sc_coded_items(license_hash);

alter table public.sc_coded_items enable row level security;
drop policy if exists "svc only sc_coded_items" on public.sc_coded_items;
create policy "svc only sc_coded_items" on public.sc_coded_items for all using (false) with check (false);

grant select, insert, update, delete on public.sc_coded_items to service_role;
revoke all on public.sc_coded_items from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from sc_coded_items;
