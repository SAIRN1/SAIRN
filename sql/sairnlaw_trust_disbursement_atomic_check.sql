-- sql/sairnlaw_trust_disbursement_atomic_check.sql
-- SAIRNlaw trust disbursement server-sync, step 2: promotes amount/type/
-- status to real columns on law_trusttx and adds the atomic check-and-write
-- function. See docs/superpowers/specs/2026-08-16-sairnlaw-trust-disbursement-atomic-check-design.md.
-- Safe to re-run -- every statement is idempotent, and the backfill only
-- touches rows where the new columns are still null.

-- ═══════════════════════════════════════════════════════════════════════
-- FUNCTION DEFINITIONS REMOVED 2026-09-03 -- they now live in ONE file:
--
--     sql/sairnlaw_trusttx_functions.sql
--
-- They were removed rather than left here with a warning. Three files had
-- come to define law_check_and_insert_disbursement() with plain
-- `create or replace`, so re-running an older one for its OTHER contents
-- SILENTLY REVERTED the function to that file's version -- no error, no
-- warning, no diff. Two of the three already carried a prose warning about
-- the file before them; a comment does not stop a `\i` in a SQL editor.
--
-- The most recent revert would have restored a disbursement function that
-- returns ONE CLIENT'S TRUST ROW to ANOTHER CLIENT'S REQUEST. The trap is
-- gone now because the duplicate text is gone.
-- ═══════════════════════════════════════════════════════════════════════

-- THIS FILE IS NOW DDL ONLY: the columns, constraints and index below are
-- still live and this file is still the place to re-run them. Doing so no
-- longer touches any function.

alter table public.law_trusttx add column if not exists amount numeric;
alter table public.law_trusttx add column if not exists type text;
alter table public.law_trusttx add column if not exists status text;

-- Backfill any rows written before this migration (step 1's own
-- live-verification rows, e.g. TR-VERIFY-1, only carried these fields
-- inside the jsonb data blob):
update public.law_trusttx set amount = (data->>'amount')::numeric
  where amount is null and data->>'amount' is not null;
update public.law_trusttx set type = data->>'type'
  where type is null and data->>'type' is not null;
update public.law_trusttx set status = coalesce(data->>'status','Posted')
  where status is null;

-- Constraints added only after backfill, so existing rows already satisfy
-- them. drop-then-add makes re-running this file safe even if a prior
-- partial run already added one of these.
alter table public.law_trusttx drop constraint if exists lawtrusttx_type_check;
alter table public.law_trusttx add constraint lawtrusttx_type_check
  check (type in ('Deposit','Disbursement'));
alter table public.law_trusttx drop constraint if exists lawtrusttx_status_check;
alter table public.law_trusttx add constraint lawtrusttx_status_check
  check (status in ('Posted','Voided'));
alter table public.law_trusttx drop constraint if exists lawtrusttx_amount_positive;
alter table public.law_trusttx add constraint lawtrusttx_amount_positive
  check (amount is null or amount > 0);

create index if not exists idx_lawtrusttx_client_status
  on public.law_trusttx(license_hash, client_id, status);
