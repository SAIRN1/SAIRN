# Per-app audit-table migrations — PRINTED, NOT APPLIED

**Nothing in this file has been run.** It is here so chat can hand Michael
one step at a time. Every statement is modelled on the three audit tables
that already exist (`sql/sairncode_audit_log_schema.sql`,
`sql/sairnlaw_audit_log_schema.sql`, `sql/stonedesk_audit_log_schema.sql`) —
not invented, and not generalised beyond what those three already do.

Re-derived at HEAD `4c574225`, 2026-10-07, with
`scratchpad/audit_gap.py` reading `api/*-auth.js`, `api/_lib/audit.js` and
every `create table ... audit_log` in `sql/`.

---

## READ THIS BEFORE THE TABLES: TWO `ALTER`s COME FIRST, AND THEY FIX WORK
## THAT IS ALREADY LANDED AND CURRENTLY INERT

Batch 11 added audit calls to `api/sc-auth.js`, `api/sd-auth.js`,
`api/stonedesk-track.js` and `api/sd-sub-data.js`. **Four of the event types
they emit are REJECTED by the CHECK constraint on the table they write to**,
so the insert fails, `writeAuditLog` returns false, and the response says
`attributed:false`. The attribution does not land.

| table | code emits | CHECK allows | verdict |
|---|---|---|---|
| `sairncode_audit_log` | `pin_setup`, `credential_change_refused`, `credential_deactivated`, `credential_reactivated` | `ai_call`, `ai_call_blocked`, `ai_injection_flagged`, `ai_call_failed` **only** | **every credential event is rejected** — and the `credential_*` ones predate batch 11 |
| `stonedesk_audit_log` | `pin_setup`, `sub_roster_write`, `order_link_created`, `order_link_revoked`, `credential_*` | the three `credential_*` **only** | **four new event types rejected** |

**HOW IT GOT PAST A GREEN SUITE, said plainly because it is the lesson:**
`tests/provisioning_attribution.js` asserts the POST the handler *issued* to
the audit table — which is correct and is what sairn-api-tester §7 asks for.
**A mocked `fetch` cannot see a CHECK constraint.** This is Guardian Check 29:
unit tests do not exercise the storage layer. The arms were right about the
request and silent about the database.

### STEP 0a — SAIRNcode

```sql
alter table public.sairncode_audit_log
  drop constraint if exists sairncode_audit_log_event_type_check;
alter table public.sairncode_audit_log
  add constraint sairncode_audit_log_event_type_check
  check (event_type in (
    'ai_call',
    'ai_call_blocked',
    'ai_injection_flagged',
    'ai_call_failed',
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  ));
```

### STEP 0b — StoneDesk

```sql
alter table public.stonedesk_audit_log
  drop constraint if exists stonedesk_audit_log_event_type_check;
alter table public.stonedesk_audit_log
  add constraint stonedesk_audit_log_event_type_check
  check (event_type in (
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused',
    'pin_bootstrap',
    'pin_setup',
    'sub_roster_write',
    'order_link_created',
    'order_link_revoked'
  ));
```

**The constraint name is a guess and must be checked before running.** Postgres
names an inline CHECK `<table>_<column>_check` by default, but if either table
was created differently the `drop constraint if exists` silently does nothing
and the `add` then fails on a duplicate. Confirm first:

```sql
select conname, pg_get_constraintdef(oid)
  from pg_constraint
 where conrelid = 'public.sairncode_audit_log'::regclass and contype = 'c';
select conname, pg_get_constraintdef(oid)
  from pg_constraint
 where conrelid = 'public.stonedesk_audit_log'::regclass and contype = 'c';
```

---

## THE COUNT IS 12 NEW TABLES, NOT 14 — and the correction matters

Batch 11 reported "14 blocked on a migration". Re-derived, two of the
fourteen are not blocked on a migration at all:

| app | what it actually needs |
|---|---|
| **StoneDesk** (`api/sd-sub-auth.js`) | **NOTHING.** Its app id is `stonedesk`, `stonedesk_audit_log` exists and is already allowlisted. **A CODE-ONLY fix** — the same six lines added to `sd-auth.js`. |
| **SAIRNvet** (`api/sv-auth.js`) | **A DECISION, THEN CODE.** `sv_audit_log` already exists (`sql/sairnvet_data_schema.sql:60`) under the resource naming, not the app naming. Either allowlist `sv_audit_log` in `api/_lib/audit.js` and reuse it, or create `sairnvet_audit_log` beside it. **Reusing it is one line of JavaScript; creating a second log for one app is a decision somebody should make deliberately, not a default.** |

So: **12 apps genuinely need a new table**, listed below one step at a time.

---

## THE EVENT VOCABULARY IS DELIBERATELY NARROW

Five values, and no more, taken from what the three existing logs already use
for the credential lifecycle. **An open `text` column would let any future
caller invent an event name and quietly change what the log means** —
`sql/stonedesk_audit_log_schema.sql` says exactly that in its own words, and
adding a value later should stay a reviewable migration.

**DELIBERATELY NOT STORED, in any of these:** PIN hashes, PIN salts, lockout
state, or any credential material. `detail` carries non-secret metadata only.
`employee_id` at the top level is **the ACTOR**, never the target — the target
belongs in `detail`, so "who did this to whom" survives.

---

## STEP 1 — `sairncare_audit_log`  (`api/alf-auth.js`)

SAIRNcare — assisted living. HIPAA-relevant.

Suggested file: `sql/sairncare_audit_log_schema.sql`

```sql
create table if not exists public.sairncare_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairncare_audit_log_license_time
  on public.sairncare_audit_log (license_hash, created_at desc);

alter table public.sairncare_audit_log enable row level security;
drop policy if exists "svc insert only sairncare_audit_log" on public.sairncare_audit_log;
create policy "svc insert only sairncare_audit_log" on public.sairncare_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairncare_audit_log from anon, authenticated;
revoke all on public.sairncare_audit_log from service_role;
grant select, insert on public.sairncare_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairncare_audit_log;
```

## STEP 2 — `sairnbuild_audit_log`  (`api/bld-auth.js`)

SAIRNbuild — construction.

Suggested file: `sql/sairnbuild_audit_log_schema.sql`

```sql
create table if not exists public.sairnbuild_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairnbuild_audit_log_license_time
  on public.sairnbuild_audit_log (license_hash, created_at desc);

alter table public.sairnbuild_audit_log enable row level security;
drop policy if exists "svc insert only sairnbuild_audit_log" on public.sairnbuild_audit_log;
create policy "svc insert only sairnbuild_audit_log" on public.sairnbuild_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairnbuild_audit_log from anon, authenticated;
revoke all on public.sairnbuild_audit_log from service_role;
grant select, insert on public.sairnbuild_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairnbuild_audit_log;
```

## STEP 3 — `sairndental_audit_log`  (`api/dnt-auth.js`)

SAIRNdental. HIPAA-relevant.

Suggested file: `sql/sairndental_audit_log_schema.sql`

```sql
create table if not exists public.sairndental_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairndental_audit_log_license_time
  on public.sairndental_audit_log (license_hash, created_at desc);

alter table public.sairndental_audit_log enable row level security;
drop policy if exists "svc insert only sairndental_audit_log" on public.sairndental_audit_log;
create policy "svc insert only sairndental_audit_log" on public.sairndental_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairndental_audit_log from anon, authenticated;
revoke all on public.sairndental_audit_log from service_role;
grant select, insert on public.sairndental_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairndental_audit_log;
```

## STEP 4 — `sairngrounds_audit_log`  (`api/grd-auth.js`)

SAIRNgrounds — grounds and golf.

Suggested file: `sql/sairngrounds_audit_log_schema.sql`

```sql
create table if not exists public.sairngrounds_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairngrounds_audit_log_license_time
  on public.sairngrounds_audit_log (license_hash, created_at desc);

alter table public.sairngrounds_audit_log enable row level security;
drop policy if exists "svc insert only sairngrounds_audit_log" on public.sairngrounds_audit_log;
create policy "svc insert only sairngrounds_audit_log" on public.sairngrounds_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairngrounds_audit_log from anon, authenticated;
revoke all on public.sairngrounds_audit_log from service_role;
grant select, insert on public.sairngrounds_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairngrounds_audit_log;
```

## STEP 5 — `sairnlegacy_audit_log`  (`api/leg-auth.js`)

SAIRNlegacy — funeral. Statutory vital records.

Suggested file: `sql/sairnlegacy_audit_log_schema.sql`

```sql
create table if not exists public.sairnlegacy_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairnlegacy_audit_log_license_time
  on public.sairnlegacy_audit_log (license_hash, created_at desc);

alter table public.sairnlegacy_audit_log enable row level security;
drop policy if exists "svc insert only sairnlegacy_audit_log" on public.sairnlegacy_audit_log;
create policy "svc insert only sairnlegacy_audit_log" on public.sairnlegacy_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairnlegacy_audit_log from anon, authenticated;
revoke all on public.sairnlegacy_audit_log from service_role;
grant select, insert on public.sairnlegacy_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairnlegacy_audit_log;
```

## STEP 6 — `sairnmechanical_audit_log`  (`api/mech-auth.js`)

SAIRNmechanical.

Suggested file: `sql/sairnmechanical_audit_log_schema.sql`

```sql
create table if not exists public.sairnmechanical_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairnmechanical_audit_log_license_time
  on public.sairnmechanical_audit_log (license_hash, created_at desc);

alter table public.sairnmechanical_audit_log enable row level security;
drop policy if exists "svc insert only sairnmechanical_audit_log" on public.sairnmechanical_audit_log;
create policy "svc insert only sairnmechanical_audit_log" on public.sairnmechanical_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairnmechanical_audit_log from anon, authenticated;
revoke all on public.sairnmechanical_audit_log from service_role;
grant select, insert on public.sairnmechanical_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairnmechanical_audit_log;
```

## STEP 7 — `sairnroofing_audit_log`  (`api/rf-auth.js`)

SAIRNroofing.

Suggested file: `sql/sairnroofing_audit_log_schema.sql`

```sql
create table if not exists public.sairnroofing_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairnroofing_audit_log_license_time
  on public.sairnroofing_audit_log (license_hash, created_at desc);

alter table public.sairnroofing_audit_log enable row level security;
drop policy if exists "svc insert only sairnroofing_audit_log" on public.sairnroofing_audit_log;
create policy "svc insert only sairnroofing_audit_log" on public.sairnroofing_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairnroofing_audit_log from anon, authenticated;
revoke all on public.sairnroofing_audit_log from service_role;
grant select, insert on public.sairnroofing_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairnroofing_audit_log;
```

## STEP 8 — `sairnbiz_audit_log`  (`api/sb-auth.js`)

SAIRNbiz.

Suggested file: `sql/sairnbiz_audit_log_schema.sql`

```sql
create table if not exists public.sairnbiz_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairnbiz_audit_log_license_time
  on public.sairnbiz_audit_log (license_hash, created_at desc);

alter table public.sairnbiz_audit_log enable row level security;
drop policy if exists "svc insert only sairnbiz_audit_log" on public.sairnbiz_audit_log;
create policy "svc insert only sairnbiz_audit_log" on public.sairnbiz_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairnbiz_audit_log from anon, authenticated;
revoke all on public.sairnbiz_audit_log from service_role;
grant select, insert on public.sairnbiz_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairnbiz_audit_log;
```

## STEP 9 — `sairnscape_audit_log`  (`api/scp-auth.js`)

SAIRNscape.

Suggested file: `sql/sairnscape_audit_log_schema.sql`

```sql
create table if not exists public.sairnscape_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairnscape_audit_log_license_time
  on public.sairnscape_audit_log (license_hash, created_at desc);

alter table public.sairnscape_audit_log enable row level security;
drop policy if exists "svc insert only sairnscape_audit_log" on public.sairnscape_audit_log;
create policy "svc insert only sairnscape_audit_log" on public.sairnscape_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairnscape_audit_log from anon, authenticated;
revoke all on public.sairnscape_audit_log from service_role;
grant select, insert on public.sairnscape_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairnscape_audit_log;
```

## STEP 10 — `sairndesign_audit_log`  (`api/sdn-auth.js`)

SAIRNdesign.

Suggested file: `sql/sairndesign_audit_log_schema.sql`

```sql
create table if not exists public.sairndesign_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairndesign_audit_log_license_time
  on public.sairndesign_audit_log (license_hash, created_at desc);

alter table public.sairndesign_audit_log enable row level security;
drop policy if exists "svc insert only sairndesign_audit_log" on public.sairndesign_audit_log;
create policy "svc insert only sairndesign_audit_log" on public.sairndesign_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairndesign_audit_log from anon, authenticated;
revoke all on public.sairndesign_audit_log from service_role;
grant select, insert on public.sairndesign_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairndesign_audit_log;
```

## STEP 11 — `sairnsenior_audit_log`  (`api/sen-auth.js`)

SAIRNsenior — home care. HIPAA-relevant.

Suggested file: `sql/sairnsenior_audit_log_schema.sql`

```sql
create table if not exists public.sairnsenior_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairnsenior_audit_log_license_time
  on public.sairnsenior_audit_log (license_hash, created_at desc);

alter table public.sairnsenior_audit_log enable row level security;
drop policy if exists "svc insert only sairnsenior_audit_log" on public.sairnsenior_audit_log;
create policy "svc insert only sairnsenior_audit_log" on public.sairnsenior_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairnsenior_audit_log from anon, authenticated;
revoke all on public.sairnsenior_audit_log from service_role;
grant select, insert on public.sairnsenior_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairnsenior_audit_log;
```

## STEP 12 — `sairnfreedom_audit_log`  (`api/sf-auth.js`)

SAIRNfreedom — veterans organisation.

Suggested file: `sql/sairnfreedom_audit_log_schema.sql`

```sql
create table if not exists public.sairnfreedom_audit_log (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text,
  role text,
  event_type text not null check (event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  )),
  detail jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairnfreedom_audit_log_license_time
  on public.sairnfreedom_audit_log (license_hash, created_at desc);

alter table public.sairnfreedom_audit_log enable row level security;
drop policy if exists "svc insert only sairnfreedom_audit_log" on public.sairnfreedom_audit_log;
create policy "svc insert only sairnfreedom_audit_log" on public.sairnfreedom_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairnfreedom_audit_log from anon, authenticated;
revoke all on public.sairnfreedom_audit_log from service_role;
grant select, insert on public.sairnfreedom_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairnfreedom_audit_log;
```

---

## AFTER THE SQL: THE CODE HALF, WHICH IS NOT IN THIS FILE

Each table needs three things in its `api/*-auth.js` before anything is
recorded, and **none of it is done**:

1. `const { writeAuditLog } = require('./_lib/audit');`
2. `const AUDIT_TABLE = '<app>_audit_log';`
3. the table name added to `AUDIT_TABLES` in `api/_lib/audit.js` — that
   allowlist refuses an unknown table and logs `audit log write refused:
   unknown table`, so a migration without this step records nothing and says
   so only in a server log.

Then the `setup` branch gets the same six lines `api/sc-auth.js` and
`api/sd-auth.js` now carry, including `attributed` on the response so a failed
write cannot look like a successful one.

**ORDER MATTERS AND IT IS NOT THE OBVIOUS ONE: do the two `ALTER`s in step 0
FIRST.** They make already-landed, already-pushed code work. The twelve new
tables enable code nobody has written yet.
