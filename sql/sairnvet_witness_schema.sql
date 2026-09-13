-- sql/sairnvet_witness_schema.sql
-- The witnessing lock for SAIRNvet's controlled-substance register.
-- Run this AND sql/sairnvet_employee_auth_schema.sql before api/sv-witness.js
-- will work. Neither is useful without the other: a witness with no identity
-- is a signature nobody signed.
--
-- ── WHY A LOCK AND NOT A CHECKER ────────────────────────────────────────────
-- `sv_controlled` is ranked TIER A WITH NO REMOVAL PATH by
-- `python tools/removal_path_check.py --burn-down`, and api/_resources/sairnvet.js
-- calls it "the controlled-substance register (DEA-relevant)". A wrong row
-- cannot be taken back through the product at all: a correction is a SECOND
-- row and the wrong one stands forever. That is the correct shape for a
-- regulated record, and it is exactly why the verification has to happen
-- BEFORE the write rather than being reported after it.
--
-- The design comes from electronic witnessing in IVF/ART labs, where the next
-- handling step cannot begin until the current one is scanned. The finding
-- that motivates it is that even INDEPENDENT DOUBLE-REVIEW has a measured,
-- non-zero failure rate in domains where a mistake cannot be undone -- which
-- is an argument for a lock and equally an argument against believing a lock
-- makes anything safe. Both halves are carried in the code.
--
-- ── WHAT IS LOCKED AND WHAT IS NOT ──────────────────────────────────────────
-- ONLY `sv_controlled`. Not the other 40 SAIRNvet resources, and not the other
-- ~14 append-only resources across the platform -- those are Class A in
-- docs/2026-09-13-irreversible-write-witnessing-scoping.md and extending to
-- them is a later, separately-sized piece that should not start until this one
-- has been lived with.
--
-- ── SINGLE-OPERATOR CONFIRM, WITH TWO-PERSON AS A PER-LICENCE SETTING ───────
-- Michael's decision, 2026-09-13, and the reasoning is worth keeping because
-- both options are defensible. A single-operator confirm is WEAKER -- the
-- person who made the error is the person confirming it. A true second witness
-- is what the research is actually about and is not a workflow a one-vet
-- practice can produce at all. So the mechanism and the schema are built for
-- two and the REQUIREMENT is a per-licence setting: a practice that can staff
-- it turns it on, and the code path is the same either way rather than being
-- retrofitted later.

-- ── 1. THE SETTING ──────────────────────────────────────────────────────────
-- One row per licence. Absent means single-operator, which is the safe default
-- to be missing: a practice that never configured this is not silently held to
-- a rule it cannot meet, and a practice that turned it ON has a row saying so.
create table if not exists public.sairnvet_witness_policy (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null unique,
  -- true = a SECOND person must countersign. false/absent = single-operator.
  require_two_person boolean not null default false,
  -- Who last changed it and when. A policy that can be relaxed silently is not
  -- a policy; this is the minimum that makes a relaxation reconstructable.
  updated_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ── 2. THE TOKENS ───────────────────────────────────────────────────────────
-- A token is bound to a HASH OF THE EXACT RECORD about to be written and to
-- the identity of the witness, and it is SINGLE-USE.
--
-- BINDING TO THE CONTENT IS THE WHOLE MECHANISM. A token bound only to "a
-- write is coming" can be spent on a different record -- which is the same
-- class as the session token that outlives its credential, one layer over.
--
-- SINGLE-USE MATTERS FOR THE SAME REASON. A reusable token is a witness who
-- signed once for everything that followed.
create table if not exists public.sairnvet_witness_tokens (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  -- The token itself is stored HASHED, never in the clear. It is a bearer
  -- credential for exactly one irreversible write; a readable table of live
  -- tokens is a table of signatures waiting to be borrowed.
  token_hash text not null,
  -- sha256 of the canonical JSON of the record. The write endpoint recomputes
  -- this and refuses if it differs by a byte.
  content_hash text not null,
  -- WHO witnessed. Both columns are employee_ids from sairnvet_employee_auth.
  -- `witness_employee_id` is the licensed practitioner who confirmed; on a
  -- two-person licence `countersign_employee_id` is the second, and it is NULL
  -- on a single-operator one rather than being set to the same person -- a
  -- countersignature by the author is not a countersignature.
  witness_employee_id text not null,
  witness_role text not null,
  countersign_employee_id text,
  countersign_role text,
  -- Spent-ness is a timestamp rather than a boolean so the audit reads
  -- "when", not merely "yes".
  spent_at timestamptz,
  spent_on_resource text,
  -- Short-lived on purpose. A token that outlives the moment it was issued in
  -- is a signature detached from the act it witnessed.
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  unique (license_hash, token_hash)
);

create index if not exists idx_sairnvet_witness_tokens_lookup
  on public.sairnvet_witness_tokens (license_hash, token_hash);
-- Finding live tokens for a licence, for the expiry sweep and for a human
-- asking what is outstanding.
create index if not exists idx_sairnvet_witness_tokens_open
  on public.sairnvet_witness_tokens (license_hash, expires_at)
  where spent_at is null;

alter table public.sairnvet_witness_policy enable row level security;
drop policy if exists "svc only sairnvet_witness_policy" on public.sairnvet_witness_policy;
create policy "svc only sairnvet_witness_policy" on public.sairnvet_witness_policy
  for all using (false) with check (false);

alter table public.sairnvet_witness_tokens enable row level security;
drop policy if exists "svc only sairnvet_witness_tokens" on public.sairnvet_witness_tokens;
create policy "svc only sairnvet_witness_tokens" on public.sairnvet_witness_tokens
  for all using (false) with check (false);

-- ── GRANTS ──────────────────────────────────────────────────────────────────
-- REVOKE ALL FIRST, then grant only what the code calls. Without the leading
-- revoke these inherit TRUNCATE/REFERENCES/TRIGGER from the platform default
-- ACL, and TRUNCATE on the TOKENS table would silently unlock every pending
-- write at once -- the failure this whole file exists to prevent, available in
-- one statement.
--
-- NO DELETE ON EITHER TABLE. A spent token is marked spent, never removed:
-- the row IS the record that a human confirmed a specific record at a specific
-- time, and on a DEA-relevant register that is the part worth keeping longest.
-- Expiry is a timestamp comparison, not a cleanup job.
revoke all on public.sairnvet_witness_policy from service_role;
grant select, insert, update on public.sairnvet_witness_policy to service_role;
revoke all on public.sairnvet_witness_policy from anon, authenticated;

revoke all on public.sairnvet_witness_tokens from service_role;
grant select, insert, update on public.sairnvet_witness_tokens to service_role;
revoke all on public.sairnvet_witness_tokens from anon, authenticated;

-- ── VERIFY AFTER RUNNING, one query per statement with its expected answer ──
-- A single count at the end cannot tell a full apply from a partial one.
--
--   select count(*) from public.sairnvet_witness_policy;
--     -- expect 0. Any other number means this was not a fresh provision.
--
--   select count(*) from public.sairnvet_witness_tokens;
--     -- expect 0.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name = 'sairnvet_witness_tokens' and grantee = 'service_role';
--     -- expect 3 (SELECT, INSERT, UPDATE). A 4th is a DELETE or TRUNCATE that
--     -- must not be there; 0 is the 42501 that looks like nothing else.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name in ('sairnvet_witness_tokens','sairnvet_witness_policy')
--      and grantee in ('anon','authenticated');
--     -- expect 0.
--
--   select count(*) from public.sairnvet_employee_auth;
--     -- expect >= 1. A witness needs an identity: if this is 0, the lock will
--     -- refuse every write and the practice cannot work. Run the auth schema
--     -- and bootstrap an Owner FIRST.
