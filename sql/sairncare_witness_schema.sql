-- sql/sairncare_witness_schema.sql
--
-- TWO-PERSON WITNESSING FOR SAIRNCARE CONTROLLED-SUBSTANCE COUNTS.
--
-- Modelled on sql/sairnvet_witness_schema.sql deliberately, so the two apps do
-- not grow two different answers to one question. Safe to re-run: every
-- statement is idempotent and nothing here drops or alters existing data.
--
-- ── THE DEFECT THIS EXISTS FOR ────────────────────────────────────────────
-- A SAIRNcare controlled-substance count records `witness_id` as a
-- caller-supplied string. One employee alone can record a two-person count
-- naming any colleague as the second signature. The browser refuses to save
-- without a witness selected -- "A witness (second signature) is required for a
-- controlled-substance count" -- and that is the whole control. The client is
-- what an attacker replaces.
--
-- api/sd-data.js says so in its own words at the alf_mar write: "`witness_id`
-- IS DELIBERATELY NOT HERE. It names a SECOND person who is by definition not
-- the caller, so it cannot come from the session. SAIRNcare has no server-side
-- witness verification at all." This is that verification's storage half.
--
-- ── WHAT IS DIFFERENT FROM SAIRNVET, AND IT ALL NARROWS ───────────────────
-- 1. ONLY entry_type 'count' is locked. An administration has one actor by
--    definition; a reconciliation and an assessment refusal have one author.
--    The count is the only MAR entry the regulation and the UI both treat as a
--    two-signature act. Locking all five would be a gate in front of doors
--    nobody meant to shut.
-- 2. THE FIRST SIGNATURE IS ALREADY TRUSTWORTHY. `counted_by` has been
--    server-set since d6d7efd1, so only the SECOND one is unverified. SAIRNvet
--    had to solve both at once.
-- 3. A SELF-WITNESSED COUNT IS REFUSED, NOT FLAGGED, and that is a deliberate
--    divergence from the sen_visits clock-correction decision made the same
--    day. There a flag was right because a one-person agency has nobody else
--    and the correction still has to be possible. Here, a count whose witness
--    is the counter is NOT A TWO-PERSON COUNT AT ALL; recording it as one is
--    the false record. A shift that cannot produce a second person defers the
--    count -- which is what `require_two_person = false` already permits,
--    WITHOUT claiming a signature nobody gave.
--
-- ── WHAT THIS DOES NOT CLAIM ─────────────────────────────────────────────
-- A witness attests that somebody looked. It does not attest that they were
-- right. Electronic witnessing exists because independent double-review has a
-- measured, non-zero failure rate -- which is an argument for the mechanism
-- and equally an argument against believing the mechanism makes anything safe.
--
-- NO READING OF ANY GOVERNING REGULATION WAS DONE. Whether a specific state
-- requires a second signature on a personal-care-home controlled-substance
-- count, and who may give it, is a legal question this file does not answer.
-- It implements the platform's own precedent and what the UI already demands.
--
-- EXISTING ROWS CANNOT BE REPAIRED. Every alf_mar count written before this
-- carries a caller-supplied witness_id and nothing distinguishes a real second
-- signature from a typed name. No backfill is possible and none is attempted.

-- ═══ 1. THE POLICY ROW ════════════════════════════════════════════════════
create table if not exists public.sairncare_witness_policy (
  id                 uuid primary key default gen_random_uuid(),
  license_hash       text not null unique,
  -- DEFAULTS FALSE, like SAIRNvet's, and for the reason recorded there: a
  -- default that cannot be met is a default that gets switched off. A facility
  -- that can staff a second signature turns it on; the code path does not
  -- change. Whether an assisted-living facility SHOULD default to true is a
  -- product decision and is deliberately not made here.
  require_two_person boolean not null default false,
  updated_by         text,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

-- ═══ 2. THE TOKEN STORE ═══════════════════════════════════════════════════
create table if not exists public.sairncare_witness_tokens (
  id                      uuid primary key default gen_random_uuid(),
  license_hash            text not null,
  app_id                  text not null default 'sairncare',
  token_hash              text not null,
  -- BOUND TO THE BYTES, not to a session and not to a resource name alone. A
  -- token minted while looking at one count cannot be spent on another, and
  -- editing the payload after witnessing invalidates it. Without this the
  -- witness attests to an act rather than to a record.
  content_hash            text not null,
  -- SERVER-SET FROM THE VERIFIED SESSION, never from a payload. This is the
  -- entire point: witness_id on the alf_mar blob is caller-supplied today.
  witness_employee_id     text not null,
  witness_role            text not null,
  countersign_employee_id text,
  countersign_role        text,
  -- SPENT ONCE. The unique constraint and the partial index below make a
  -- replay a database-level impossibility rather than an application check.
  spent_at                timestamptz,
  spent_on_resource       text,
  spent_on_entry_id       text,
  expires_at              timestamptz not null,
  created_at              timestamptz not null default now(),
  unique (license_hash, token_hash),
  -- A WITNESS WHO IS THE COUNTERSIGNER IS NOT A SECOND PERSON. Enforced in the
  -- database as well as in the endpoint, because this is the single fact the
  -- whole control rests on and an application-only check shares state with the
  -- thing it checks. NULL countersign is allowed: that is the single-operator
  -- case, which is permitted and simply does not claim a second signature.
  constraint scwit_witness_is_not_countersigner
    check (countersign_employee_id is null
           or countersign_employee_id <> witness_employee_id)
);

create index if not exists idx_scwit_lookup
  on public.sairncare_witness_tokens (license_hash, token_hash);

create index if not exists idx_scwit_unspent
  on public.sairncare_witness_tokens (license_hash, expires_at)
  where spent_at is null;

-- ═══ 3. RLS ON, SERVICE-ROLE ONLY ═════════════════════════════════════════
alter table public.sairncare_witness_policy enable row level security;
alter table public.sairncare_witness_tokens enable row level security;

drop policy if exists "svc only sairncare_witness_policy" on public.sairncare_witness_policy;
create policy "svc only sairncare_witness_policy" on public.sairncare_witness_policy
  for all using (false) with check (false);

drop policy if exists "svc only sairncare_witness_tokens" on public.sairncare_witness_tokens;
create policy "svc only sairncare_witness_tokens" on public.sairncare_witness_tokens
  for all using (false) with check (false);

-- ═══ 4. NO DELETE GRANT, ON EITHER TABLE ══════════════════════════════════
-- Matching every other regulated resource on this platform. A spent token is
-- evidence: it records who attested to what and when, on a MAR a state
-- surveyor reads. UPDATE is granted because spending and countersigning are
-- updates; DELETE is not granted and is not coming.
revoke all on public.sairncare_witness_policy from anon, authenticated, service_role;
revoke all on public.sairncare_witness_tokens from anon, authenticated, service_role;
grant select, insert, update on public.sairncare_witness_policy to service_role;
grant select, insert, update on public.sairncare_witness_tokens to service_role;

-- ═══ 5. VERIFY, rather than assuming the editor reported success ══════════
-- Expect, in order:
--   (a) require_two_person: is_nullable NO, column_default false
--   (b) exactly ONE constraint row, the witness-is-not-countersigner check
--   (c) exactly INSERT, SELECT, UPDATE on each table -- and NO DELETE.
--       Six rows. A seventh naming DELETE means step 4 did not take.
select column_name, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public'
   and table_name = 'sairncare_witness_policy'
   and column_name = 'require_two_person';

select conname, pg_get_constraintdef(oid)
  from pg_constraint
 where conrelid = 'public.sairncare_witness_tokens'::regclass
   and conname = 'scwit_witness_is_not_countersigner';

select table_name, privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public'
   and table_name in ('sairncare_witness_policy', 'sairncare_witness_tokens')
   and grantee = 'service_role'
 order by table_name, privilege_type;
