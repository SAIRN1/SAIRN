-- sql/sairnlegacy_countersign_schema.sql
-- The COUNTERSIGNATURE LOCK for SAIRNlegacy's cremation authorisations.
-- Run this AND sql/sairnlegacy_employee_auth_schema.sql before
-- api/leg-countersign.js will work. Neither is useful without the other: a
-- signature with no identity is a signature nobody signed.
--
-- ── WHY A LOCK AND NOT A CHECKER (practitioner answer F1, 2026-10-17) ──────
-- Michael's answer to practitioner question F1 is that a cremation
-- authorisation takes a SECOND NAMED, SIGNING PERSON. `leg_cremations` is the
-- sharpest irreversible act in the app and api/_lib/leg-roles.js's own row
-- says so: there is no undoing it and no amended record that helps, so the
-- verification has to happen BEFORE the write rather than be reported after.
--
-- The design is api/sv-witness.js's, which came from electronic witnessing in
-- IVF/ART labs where the next handling step cannot begin until the current one
-- is scanned. The finding that motivates it is that even INDEPENDENT
-- DOUBLE-REVIEW has a measured, non-zero failure rate in domains where a
-- mistake cannot be undone -- an argument for a lock, and equally an argument
-- against believing a lock makes anything safe. Both halves are carried in the
-- code's refusals.
--
-- ── WHAT IS LOCKED, AND WHAT IS NOT ───────────────────────────────────────
-- ONLY `leg_cremations`, and on EVERY write including the owner's. A rule the
-- owner is exempt from is not "the paperwork needs a second named person" --
-- the same reasoning as LEG_APPEND_ONLY, which binds the owner exactly as it
-- binds a driver. The other 35 leg_ resources are NOT locked and extending to
-- any of them is a separate decision with a separate answer behind it.
--
-- ── THERE IS NO POLICY TABLE, UNLIKE SAIRNvet, AND THAT IS DELIBERATE ─────
-- sql/sairnvet_witness_schema.sql ships a `require_two_person` setting because
-- a one-vet practice cannot staff a second witness and the controlled-
-- substance count still has to happen. HERE THE ANSWER IS A STATE-LAW
-- READING, NOT A STAFFING QUESTION: F1 asked whether the state requires the
-- second signature or the house does, and a legal requirement is not something
-- a licensee turns off in Settings. A home that cannot produce a second signer
-- cannot file the authorisation -- which is the paper position too. So ONE
-- table, not two.

-- ── THE TOKENS ─────────────────────────────────────────────────────────────
-- A token is bound to a HASH OF THE EXACT RECORD about to be written, to the
-- identity of the person who PREPARED it and to the identity of the person who
-- SIGNED it, and it is SINGLE-USE.
--
-- BINDING TO THE CONTENT IS THE WHOLE MECHANISM. A token bound only to "a
-- write is coming" can be spent on a different record -- the same class as a
-- session token that outlives its credential, one layer over.
--
-- SINGLE-USE MATTERS FOR THE SAME REASON. A reusable token is a director who
-- signed once for every cremation that followed.
create table if not exists public.sairnlegacy_countersign_tokens (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  -- WHICH RESOURCE this signature is for. Inside the content hash as well, but
  -- stored in its own column so a human can read the table and so the index
  -- below can answer "what cremations are awaiting a signature".
  resource text not null,
  -- The token itself is stored HASHED, never in the clear. It is a bearer
  -- credential for exactly one irreversible write; a readable table of live
  -- tokens is a table of signatures waiting to be borrowed.
  token_hash text not null,
  -- sha256 of the canonical JSON of the record, with the resource name inside
  -- it. The write path recomputes this and refuses if it differs by a byte.
  content_hash text not null,
  -- WHO PREPARED IT. An employee_id from sairnlegacy_employee_auth. Either a
  -- licensed director staging their own authorisation, or an apprentice the
  -- home's F3 config authorises to prepare one.
  prepared_by text not null,
  prepared_role text not null,
  -- WHO SIGNED IT. NULL until a DIFFERENT licensed director countersigns, and
  -- never set to the same employee as `prepared_by` -- a signature by the
  -- preparer is not a countersignature, which is the entire content of "a
  -- second named person". Enforced in the application AND by the CHECK below,
  -- because this is the one property the whole file exists for.
  countersign_employee_id text,
  countersign_role text,
  countersigned_at timestamptz,
  -- Spent-ness is a timestamp rather than a boolean so the audit reads "when",
  -- not merely "yes".
  spent_at timestamptz,
  spent_on_resource text,
  -- Short-lived on purpose. A signature that outlives the moment it was given
  -- in is a signature detached from the act it witnessed.
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  unique (license_hash, token_hash),
  -- THE SELF-SIGNATURE REFUSAL, IN THE DATABASE AS WELL AS THE CODE. The
  -- application refuses it at `countersign` and again at the write, and this
  -- is the third place -- deliberately, because the two application checks are
  -- both in one process and a future write path that forgets them would leave
  -- no trace. A constraint cannot be forgotten by a new caller.
  constraint sairnlegacy_countersign_not_self
    check (countersign_employee_id is null
           or countersign_employee_id <> prepared_by),
  -- AND A SIGNATURE HAS A TIME AND A ROLE OR IT IS NOT A SIGNATURE. Three
  -- columns that must be set together; a row with an id and no role is a
  -- half-written signature the write path would have to guess about.
  constraint sairnlegacy_countersign_complete
    check ((countersign_employee_id is null
            and countersign_role is null
            and countersigned_at is null)
        or (countersign_employee_id is not null
            and countersign_role is not null
            and countersigned_at is not null))
);

create index if not exists idx_sairnlegacy_countersign_lookup
  on public.sairnlegacy_countersign_tokens (license_hash, token_hash);
-- What is outstanding: prepared, unsigned, unspent and not yet expired. This
-- is the query a director's "needs your signature" list is built from, and the
-- reason the resource column exists separately from the hash.
create index if not exists idx_sairnlegacy_countersign_open
  on public.sairnlegacy_countersign_tokens (license_hash, resource, expires_at)
  where spent_at is null;

alter table public.sairnlegacy_countersign_tokens enable row level security;
drop policy if exists "svc only sairnlegacy_countersign_tokens"
  on public.sairnlegacy_countersign_tokens;
create policy "svc only sairnlegacy_countersign_tokens"
  on public.sairnlegacy_countersign_tokens
  for all using (false) with check (false);

-- ── GRANTS ─────────────────────────────────────────────────────────────────
-- REVOKE ALL FIRST, then grant only what the code calls. Without the leading
-- revoke this inherits TRUNCATE/REFERENCES/TRIGGER from the platform default
-- ACL, and TRUNCATE here would silently unlock every pending authorisation at
-- once -- the failure this whole file exists to prevent, available in one
-- statement.
--
-- NO DELETE. A spent token is marked spent, never removed: the row IS the
-- record that two named people signed a specific cremation authorisation at a
-- specific time, and on an irreversible act that is the part worth keeping
-- longest. Expiry is a timestamp comparison, not a cleanup job.
revoke all on public.sairnlegacy_countersign_tokens from service_role;
grant select, insert, update on public.sairnlegacy_countersign_tokens to service_role;
revoke all on public.sairnlegacy_countersign_tokens from anon, authenticated;

-- ── VERIFY AFTER RUNNING, one query per statement with its expected answer ──
-- A single count at the end cannot tell a full apply from a partial one.
--
--   select count(*) from public.sairnlegacy_countersign_tokens;
--     -- expect 0. Any other number means this was not a fresh provision.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name = 'sairnlegacy_countersign_tokens' and grantee = 'service_role';
--     -- expect EXACTLY 3 (SELECT, INSERT, UPDATE). A 4th is a DELETE or
--     -- TRUNCATE that must not be there; 0 is the 42501 that looks like
--     -- nothing else.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name = 'sairnlegacy_countersign_tokens'
--      and grantee in ('anon','authenticated');
--     -- expect 0.
--
--   select conname from pg_constraint
--    where conrelid = 'public.sairnlegacy_countersign_tokens'::regclass
--      and contype = 'c';
--     -- expect BOTH sairnlegacy_countersign_not_self AND
--     -- sairnlegacy_countersign_complete. If only one is listed the paste
--     -- applied partway and the self-signature refusal may be the missing one.
--
--   select count(*) from public.sairnlegacy_employee_auth where active;
--     -- expect >= 2. A SECOND NAMED PERSON NEEDS A SECOND ACTIVE CREDENTIAL.
--     -- With one active employee this lock refuses every cremation
--     -- authorisation the home tries to file, correctly and permanently. Run
--     -- the auth schema and provision a second licensed director FIRST.
