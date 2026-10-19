-- sql/sairnlaw_countersign_schema.sql
-- The TWO-STAGE TRUST DISBURSEMENT for SAIRNlaw.
-- Run this AND sql/sairnlaw_employee_auth_schema.sql before
-- api/law-countersign.js will work. Neither is useful without the other: a
-- signature with no identity is a signature nobody signed.
--
-- ── WHY IT EXISTS (practitioner answer C2, 2026-10-17) ────────────────────
-- Michael's answer to practitioner question C2 is that a PARALEGAL MAY PREPARE
-- a trust disbursement FOR AN ATTORNEY TO AUTHORISE. Before b18 a paralegal
-- could not touch `law_trusttx` at all and that refusal was tested and
-- deliberate (api/b17-trust-lock-hard.test.js) -- which is exactly why it was
-- worth asking whether it was the right refusal. It was the right refusal for
-- AUTHORISING and the wrong one for PREPARING.
--
-- A PREPARED DISBURSEMENT MOVES NO MONEY. It is a pending row in this table
-- and nothing else; `law_trusttx` is written only when a bar-admitted person
-- has signed it. That property is what makes the carve-out safe and it is why
-- the trust lock in api/_lib/law-roles.js grants `prepare` and nothing wider.
--
-- ── THE ASYMMETRY WITH SAIRNlegacy, WHICH IS A DECISION AND NOT AN OVERSIGHT
-- sql/sairnlegacy_countersign_schema.sql locks EVERY write of a cremation
-- authorisation, including the owner's. THIS ONE DOES NOT lock an attorney's
-- or the owner's own trust write: C2 asked whether a paralegal may prepare,
-- and did not ask -- and Michael did not answer -- whether an attorney now
-- needs a second attorney to move client money. Deciding that here would be
-- this file answering a bar-rules question nobody put to it. The mode is
-- MODE_PREPARED_ONLY in api/law-countersign.js and it is named in the b18
-- handoff as the most likely thing in the batch to be wrong -- wrong in the
-- direction of changing less than was asked.
--
-- ── NO POLICY TABLE, UNLIKE SAIRNvet ──────────────────────────────────────
-- sql/sairnvet_witness_schema.sql ships a `require_two_person` setting because
-- a one-vet practice cannot staff a second witness. Here the requirement is
-- not a staffing question and not optional: a paralegal's disbursement needs a
-- bar-admitted signature or it is not a disbursement. One table, not two.

-- ── THE TOKENS ─────────────────────────────────────────────────────────────
-- A token is bound to a HASH OF THE EXACT RECORD about to be written, to the
-- identity of the person who PREPARED it and to the identity of the
-- bar-admitted person who AUTHORISED it, and it is SINGLE-USE.
--
-- BINDING TO THE CONTENT IS THE WHOLE MECHANISM. A token bound only to "a
-- write is coming" can be spent on a different record -- so an authorisation
-- for $500 to one client could file a $50,000 disbursement to another. That is
-- the hole the content hash closes and it is the reason the hash covers the
-- resource name too.
--
-- SINGLE-USE MATTERS FOR THE SAME REASON. A reusable token is an attorney who
-- authorised once for every disbursement that followed.
create table if not exists public.sairnlaw_countersign_tokens (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  -- WHICH RESOURCE. Inside the content hash as well, but stored separately so
  -- a human can read the table and so the index below can answer "which
  -- disbursements are waiting for an attorney".
  resource text not null,
  -- Stored HASHED, never in the clear. It is a bearer credential for exactly
  -- one movement of client trust money; a readable table of live tokens is a
  -- table of authorisations waiting to be borrowed.
  token_hash text not null,
  -- sha256 of the canonical JSON of the record, with the resource name inside.
  -- The write path recomputes this and refuses if it differs by a byte.
  content_hash text not null,
  -- WHO PREPARED IT. An employee_id from sairnlaw_employee_auth. A paralegal,
  -- or a bar-admitted person staging their own.
  prepared_by text not null,
  prepared_role text not null,
  -- WHO AUTHORISED IT. NULL until a DIFFERENT, bar-admitted employee signs,
  -- and never the same employee as `prepared_by`. The role is stored because
  -- the write path re-derives qualification from THIS column rather than from
  -- whoever happens to be saving -- it is the signer's standing the record
  -- claims, not the saver's.
  countersign_employee_id text,
  countersign_role text,
  countersigned_at timestamptz,
  -- Spent-ness is a timestamp rather than a boolean so the audit reads "when",
  -- not merely "yes".
  spent_at timestamptz,
  spent_on_resource text,
  -- Short-lived on purpose. An authorisation that outlives the moment it was
  -- given in is a signature detached from the act it authorised.
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  unique (license_hash, token_hash),
  -- THE SELF-SIGNATURE REFUSAL, IN THE DATABASE AS WELL AS THE CODE. The
  -- application refuses it at `countersign` and again at the write; this is
  -- the third place, deliberately, because both application checks live in one
  -- process and a future write path that forgets them would leave no trace. A
  -- constraint cannot be forgotten by a new caller.
  constraint sairnlaw_countersign_not_self
    check (countersign_employee_id is null
           or countersign_employee_id <> prepared_by),
  -- A signature has a time and a role or it is not a signature.
  constraint sairnlaw_countersign_complete
    check ((countersign_employee_id is null
            and countersign_role is null
            and countersigned_at is null)
        or (countersign_employee_id is not null
            and countersign_role is not null
            and countersigned_at is not null))
);

create index if not exists idx_sairnlaw_countersign_lookup
  on public.sairnlaw_countersign_tokens (license_hash, token_hash);
-- What is outstanding: prepared, unauthorised, unspent, not yet expired. This
-- is the query an attorney's "needs your authorisation" list is built from.
create index if not exists idx_sairnlaw_countersign_open
  on public.sairnlaw_countersign_tokens (license_hash, resource, expires_at)
  where spent_at is null;

alter table public.sairnlaw_countersign_tokens enable row level security;
drop policy if exists "svc only sairnlaw_countersign_tokens"
  on public.sairnlaw_countersign_tokens;
create policy "svc only sairnlaw_countersign_tokens"
  on public.sairnlaw_countersign_tokens
  for all using (false) with check (false);

-- ── GRANTS ─────────────────────────────────────────────────────────────────
-- REVOKE ALL FIRST, then grant only what the code calls. Without the leading
-- revoke this inherits TRUNCATE/REFERENCES/TRIGGER from the platform default
-- ACL, and TRUNCATE here would silently unlock every pending disbursement at
-- once -- the failure this file exists to prevent, available in one statement.
--
-- NO DELETE. A spent token is marked spent, never removed: the row IS the
-- record that a named attorney authorised a specific movement of client trust
-- money at a specific time, and that is the single figure a bar association
-- audits. Expiry is a timestamp comparison, not a cleanup job.
revoke all on public.sairnlaw_countersign_tokens from service_role;
grant select, insert, update on public.sairnlaw_countersign_tokens to service_role;
revoke all on public.sairnlaw_countersign_tokens from anon, authenticated;

-- ── VERIFY AFTER RUNNING, one query per statement with its expected answer ──
-- A single count at the end cannot tell a full apply from a partial one.
--
--   select count(*) from public.sairnlaw_countersign_tokens;
--     -- expect 0. Any other number means this was not a fresh provision.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name = 'sairnlaw_countersign_tokens' and grantee = 'service_role';
--     -- expect EXACTLY 3 (SELECT, INSERT, UPDATE). A 4th is a DELETE or
--     -- TRUNCATE that must not be there; 0 is the 42501 that looks like
--     -- nothing else.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name = 'sairnlaw_countersign_tokens'
--      and grantee in ('anon','authenticated');
--     -- expect 0.
--
--   select conname from pg_constraint
--    where conrelid = 'public.sairnlaw_countersign_tokens'::regclass
--      and contype = 'c';
--     -- expect BOTH sairnlaw_countersign_not_self AND
--     -- sairnlaw_countersign_complete. If only one is listed the paste applied
--     -- partway and the self-signature refusal may be the missing one.
--
--   select count(*) from public.sairnlaw_employee_auth
--    where active and role in ('owner','attorney');
--     -- expect >= 1. A prepared disbursement needs a BAR-ADMITTED signer. With
--     -- no active owner or attorney this lock refuses every paralegal-prepared
--     -- disbursement, correctly and permanently.
