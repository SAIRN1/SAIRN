-- sql/sd_approvals_schema.sql
--
-- Signed customer approvals for StoneDesk estimates. Run once in the Supabase
-- SQL editor.
--
-- ── WHAT THIS RESCUES ───────────────────────────────────────────────────────
-- esigApprove() in stonedesk.html captures a real signature: the customer types
-- their name, draws on a canvas that is checked for being genuinely blank, and
-- the approval is written with the agreed total, the 50% deposit, a timestamp
-- and the signature image.
--
-- It was written to `localStorage['sd_approvals']` and NOWHERE ELSE. Read back
-- from nowhere in the entire file. So the document proving a customer agreed to
-- a price lived in exactly one browser, on one machine, invisible to every
-- other device and to everyone in the shop -- and one cache clear destroyed it.
-- The competitive audit had this backwards, incidentally: it recorded that
-- StoneDesk could not get a customer to e-sign a quote at all. It could. The
-- signature just had nowhere to go.
--
-- ── APPEND-ONLY, AND THAT IS THE POINT ──────────────────────────────────────
-- A signed approval is evidence. `unique (license_hash, approval_id)` plus an
-- INSERT that does NOT merge duplicates means a second write of the same id is
-- a 409, not an overwrite. There is no update path and no UPDATE grant: the
-- price a customer signed for cannot be edited afterwards from the app, which
-- is the only property that makes the record worth keeping.
--
-- Superseding one is a NEW approval with a new id. The old row stays.
--
-- ── NO DELETE GRANT ─────────────────────────────────────────────────────────
-- Same as sd_supplier_lead_times, sd_subs and sd_sub_jobs, and for a stronger
-- reason: this is the shop's own record of what a customer agreed to. Voiding
-- an approval is a status the app can carry on a NEW row, not an erasure.
--
-- ── THE SIGNATURE IMAGE ─────────────────────────────────────────────────────
-- `signature_png` holds a data: URL of the canvas. api/sd-data.js already caps
-- EVERY write at 64KB (MAX_PAYLOAD_BYTES), uniformly, so that is the real
-- budget and no second limit exists for this column -- a first draft added one
-- at 200KB and it was unreachable dead code. The client measures the signature
-- against the 64KB figure before sending and asks the customer to re-sign,
-- rather than truncating: half a signature is worse than a recorded absence,
-- because it still looks like a signature.
--
-- ── SECURITY ────────────────────────────────────────────────────────────────
-- service_role only, RLS on with no anon policy, api/sd-data.js the only door,
-- and the write is session-gated there: an approval is signed with shop staff
-- present, so there is always a real employee session. This table is NOT
-- reachable by any public or customer-facing route, because none exists --
-- see the competitive audit's GAP 1, which is a separate, unmade decision.

create table if not exists public.sd_approvals (
  id             uuid primary key default gen_random_uuid(),
  license_hash   text not null,
  approval_id    text not null,           -- the client's APPR<epoch> id
  client_name    text not null,
  quote_num      text,
  signed_date    text,                    -- the date the CUSTOMER put on it
  total_amount   numeric(12,2) not null,
  deposit_amount numeric(12,2) not null,
  signature_png  text,
  deposit_status text not null default 'pending',
  signed_by      text,                    -- employee_id of the staff member present
  created_at     timestamptz not null default now(),
  unique (license_hash, approval_id)
);

create index if not exists idx_sd_approvals_license
  on public.sd_approvals (license_hash, created_at desc);
-- "has the Smith quote been signed?" is the question this table is asked.
create index if not exists idx_sd_approvals_quote
  on public.sd_approvals (license_hash, quote_num);

alter table public.sd_approvals enable row level security;

-- SELECT and INSERT only. No UPDATE: a signed price is not editable. No
-- DELETE: it is not erasable.
grant select, insert on public.sd_approvals to service_role;

-- ── VERIFY ──────────────────────────────────────────────────────────────────
-- Expect the columns below and ZERO rows.
select column_name, data_type, is_nullable
  from information_schema.columns
 where table_schema = 'public' and table_name = 'sd_approvals'
 order by ordinal_position;

select count(*) as should_be_zero from public.sd_approvals;

-- And confirm the grant really is select+insert only -- an UPDATE here would
-- quietly make signed prices editable again:
select privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public' and table_name = 'sd_approvals' and grantee = 'service_role'
 order by privilege_type;
-- Expect exactly: INSERT, SELECT
