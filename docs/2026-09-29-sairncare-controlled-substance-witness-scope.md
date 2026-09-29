# SAIRNcare controlled-substance counts: what a real witness would take

**Scope note only. Nothing is built.** It needs a schema migration, so this stops
where the instruction says to stop, and the SQL is at the bottom as its own
block.

**The finding this scopes** (registered HIGH, 2026-09-29): a SAIRNcare
controlled-substance count records `witness_id` as a caller-supplied string. One
employee alone can record a two-person count naming any colleague as the second
signature. The browser refuses to save without a witness selected — *"A witness
(second signature) is required for a controlled-substance count"* — and that is
the whole control. The client is what an attacker replaces.

---

## 1. What SAIRNvet's witness token actually enforces

`api/sv-witness.js` is not a validator. It is a **hard workflow lock**: the write
cannot fire at all until a verification step for *that exact record* has
completed. Four properties do the work, and only the first two are obvious.

**(a) The token is bound to a CONTENT HASH, not to a session or a resource.**
`sairnvet_witness_tokens.content_hash` pins the token to the bytes being
witnessed. A token minted while looking at one count cannot be spent on a
different one, and editing the payload after witnessing invalidates it. Without
this the witness attests to *an act*, not to *a record*.

**(b) The token is SPENT, once.** `spent_at` and `spent_on_resource` are written
when it is consumed, and `unique (license_hash, token_hash)` plus the
partial index on unspent tokens make a replay a database-level impossibility
rather than an application check. A second write cannot reuse the first
witnessing.

**(c) The witness identity is IN the token, put there server-side.**
`witness_employee_id` and `witness_role` are columns on the token row, not fields
on the payload. Nothing the caller sends decides who witnessed.

**(d) Two-person is a PER-LICENCE SETTING, not a platform policy.**
`sairnvet_witness_policy.require_two_person` defaults to **false**, and
`countersign_employee_id` / `countersign_role` are nullable columns that exist
from the start. The decision recorded in the file is Michael's, 2026-09-13:
*single-operator confirm now, two-person as a setting*, because **a true second
witness is not a workflow a one-vet practice can produce at all** — and building
the schema for two from the beginning means a practice that can staff it turns it
on without a code path changing.

**And what the file refuses to claim, which belongs in this note as much as the
mechanism:** *"A witness attests that somebody looked; it does not attest that
they were right."* Electronic witnessing exists because independent double-review
has a measured, non-zero failure rate. The lock is an argument for the mechanism
and equally an argument against believing the mechanism makes anything safe.

## 2. What the equivalent needs in SAIRNcare

| | SAIRNvet has | SAIRNcare has | Gap |
|---|---|---|---|
| policy row | `sairnvet_witness_policy` | — | **new table** |
| token store | `sairnvet_witness_tokens` | — | **new table** |
| auth to identify a witness | `api/sv-auth.js`, roles, sessions | `api/alf-auth.js`, roles, sessions | **none — this half already exists** |
| a resource to lock | `sv_controlled` | `alf_mar` entry_type `count` | **none — the branch exists** |
| an employee roster to pick from | yes | yes (`alf_staff_credentials`, `roster`) | **none** |

**So the auth half is already there and the storage half is not.** That is the
whole reason this stops at a note: there is nowhere to put a token.

### The narrower shape SAIRNcare needs

SAIRNvet locks a write that **cannot be taken back** — `sv_controlled` is Tier A
with no removal path, so a correction is a second row and the wrong one stands
forever. `alf_mar` is the same shape: append-only, no delete verb, driven and
confirmed 2026-09-29 (`soft_delete` and `delete` both answer
`400 action must be 'read' or 'write'`).

**Three differences that change the design, and they all narrow it:**

1. **Only `entry_type: 'count'` needs it.** An administration has one actor by
   definition. A reconciliation and an assessment refusal have one author. The
   count is the only MAR entry the regulation and the UI both treat as a
   two-signature act. Locking all four would be a gate in front of doors nobody
   meant to shut.
2. **`counted_by` is already server-set** as of `d6d7efd1`, so the *first*
   signature is already trustworthy. Only the second is not. SAIRNvet had to
   solve both at once; SAIRNcare has half of it.
3. **A self-witnessed count must be refused, not flagged** — and this is the one
   place I would diverge from the `sen_visits` clock-correction decision made the
   same day. There the flag was right because a one-person agency has nobody else
   and the correction still has to be possible. Here, a count whose witness is
   the counter is **not a two-person count at all**; recording it as one is the
   false record. The workflow that has nobody else available should be refused
   and the count deferred, exactly as `require_two_person = false` lets a
   single-operator practice proceed *without claiming a second signature*.

### What is NOT in scope, said plainly

* **No reading of the governing regulation was done.** This note argues from the
  platform's own precedent and from what the UI already requires, not from a
  citation. Whether a specific state requires a second signature on a PCH
  controlled-substance count, and who may give it, is a legal question this note
  does not answer and should not be read as answering.
* **Whether the default should be `require_two_person = true` for SAIRNcare** is
  a product decision. SAIRNvet defaulted to false for a one-vet practice; an
  assisted-living facility with a MAR is rarely single-staffed, so the argument
  may run the other way. Not chosen here.
* **The existing rows.** Every `alf_mar` count written before such a lock carries
  a `witness_id` that is caller-supplied, and nothing distinguishes a real second
  signature from a typed name. No backfill is possible.

---

## 3. THE MIGRATION — run in the Supabase SQL editor

Idempotent, and its own VERIFY block is at the bottom. **Nothing reads these
tables yet**; applying it is safe and changes no behaviour.

```sql
-- sql/sairncare_witness_schema.sql
-- Two-person witnessing for SAIRNcare controlled-substance counts.
-- Modelled on sql/sairnvet_witness_schema.sql, deliberately, so the two apps do
-- not grow two different answers to one question. Safe to re-run.
--
-- NOTHING READS THESE TABLES YET. Applying this changes no behaviour; it makes
-- the lock buildable. The endpoint work is a separate change.

create table if not exists public.sairncare_witness_policy (
  id                 uuid primary key default gen_random_uuid(),
  license_hash       text not null unique,
  -- DEFAULTS FALSE, like SAIRNvet's, and for the reason recorded there: a true
  -- second witness is not a workflow every facility can produce, and a default
  -- that cannot be met is a default that gets switched off. A facility that can
  -- staff it turns it on; the code path does not change.
  require_two_person boolean not null default false,
  updated_by         text,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

create table if not exists public.sairncare_witness_tokens (
  id                     uuid primary key default gen_random_uuid(),
  license_hash           text not null,
  app_id                 text not null default 'sairncare',
  token_hash             text not null,
  -- BOUND TO THE BYTES, not to a session or a resource name. A token minted
  -- while looking at one count cannot be spent on another, and editing the
  -- payload after witnessing invalidates it. Without this the witness attests
  -- to an act rather than to a record.
  content_hash           text not null,
  -- SERVER-SET FROM THE VERIFIED SESSION, never from a payload. This is the
  -- entire point: witness_id on the alf_mar blob is caller-supplied today.
  witness_employee_id    text not null,
  witness_role           text not null,
  countersign_employee_id text,
  countersign_role        text,
  -- SPENT ONCE. The unique constraint and the partial index below make a replay
  -- a database-level impossibility rather than an application check.
  spent_at               timestamptz,
  spent_on_resource      text,
  spent_on_entry_id      text,
  expires_at             timestamptz not null,
  created_at             timestamptz not null default now(),
  unique (license_hash, token_hash),
  -- A WITNESS WHO IS THE COUNTER IS NOT A WITNESS. Enforced in the database as
  -- well as in the endpoint, because this is the single fact the whole control
  -- rests on and an application-only check shares state with the thing it
  -- checks. NULL countersign is allowed: that is the single-operator case,
  -- which is permitted and simply does not claim a second signature.
  constraint scwit_witness_is_not_countersigner
    check (countersign_employee_id is null
           or countersign_employee_id <> witness_employee_id)
);

create index if not exists idx_scwit_lookup
  on public.sairncare_witness_tokens (license_hash, token_hash);

create index if not exists idx_scwit_unspent
  on public.sairncare_witness_tokens (license_hash, expires_at)
  where spent_at is null;

alter table public.sairncare_witness_policy enable row level security;
alter table public.sairncare_witness_tokens enable row level security;

drop policy if exists "svc only sairncare_witness_policy" on public.sairncare_witness_policy;
create policy "svc only sairncare_witness_policy" on public.sairncare_witness_policy
  for all using (false) with check (false);

drop policy if exists "svc only sairncare_witness_tokens" on public.sairncare_witness_tokens;
create policy "svc only sairncare_witness_tokens" on public.sairncare_witness_tokens
  for all using (false) with check (false);

-- NO DELETE, on either table, matching every other regulated resource on this
-- platform. A spent token is evidence.
revoke all on public.sairncare_witness_policy from anon, authenticated, service_role;
revoke all on public.sairncare_witness_tokens from anon, authenticated, service_role;
grant select, insert, update on public.sairncare_witness_policy to service_role;
grant select, insert, update on public.sairncare_witness_tokens to service_role;

-- VERIFY, rather than assuming the editor reported success.
-- Expect: require_two_person NO/false; exactly one constraint row; and
-- exactly INSERT, SELECT, UPDATE on each table -- no DELETE.
select column_name, is_nullable, column_default
  from information_schema.columns
 where table_schema='public' and table_name='sairncare_witness_policy'
   and column_name='require_two_person';

select conname, pg_get_constraintdef(oid)
  from pg_constraint
 where conrelid='public.sairncare_witness_tokens'::regclass
   and conname='scwit_witness_is_not_countersigner';

select table_name, privilege_type from information_schema.role_table_grants
 where table_schema='public'
   and table_name in ('sairncare_witness_policy','sairncare_witness_tokens')
   and grantee='service_role'
 order by table_name, privilege_type;
```

**Not written to `sql/` as a file.** The instruction was to stop at the scope
note and hand over the SQL; a file in `sql/` reads as something somebody decided
to run.
