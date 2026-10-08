# Per-app audit-table migrations — PRINTED, NOT APPLIED

**Nothing in this file has been run.** Every statement is modelled on the
three audit tables that already exist (`sql/sairncode_audit_log_schema.sql`,
`sql/sairnlaw_audit_log_schema.sql`, `sql/stonedesk_audit_log_schema.sql`) —
not invented, and not generalised beyond what those three already do.

**Re-derived at HEAD `4fd3b94f`, 2026-10-07**, by
`python tools/audit_event_type_check.py` (which this batch built) plus
`scratchpad/audit_gap.py` over `api/*-auth.js`, `api/_lib/audit.js` and every
`create table ... audit_log` in `sql/`.

## WHAT CHANGED SINCE THE FIRST PRINTING, and it is not cosmetic

| first printing | now | why |
|---|---|---|
| **two** ALTERs in STEP 0 | **THREE** | the sweep that found the first two was run by hand on two tables. Run over the whole population it found **3 of 3** tables carrying an `event_type` CHECK reject at least one value the code emits — **`sairnlaw_audit_log` was the one I missed**, and it is the biggest of the three. |
| SAIRNvet "needs a decision" | **DECIDED: reuse `sv_audit_log`** | and it needs **no SQL at all** — `sv_audit_log` carries **no `event_type` CHECK**, so there is nothing to alter. One line of JavaScript, in STEP 0d. |
| StoneDesk | **no table**, unchanged | its app id is `stonedesk`, whose table already exists and is allowlisted. Code only. |

**HOW `sairnlaw_audit_log` HID:** its four writers pass **no `table:`
argument**, so they fall through `const target = table || DEFAULT_AUDIT_TABLE`
(`api/_lib/audit.js:45`) to `sairnlaw_audit_log`. My first sweep bucketed them
as *"target could not be resolved"* and **left them out of the comparison** —
a could-not-tell that was really a known answer, hiding six of the eleven
rejected values. The checker now resolves the default and **refuses (exit 2)
if `DEFAULT_AUDIT_TABLE` cannot be found**, rather than guessing.

---

## STEP 0 — THREE `ALTER`s, AND THEY COME FIRST

**These repair code that is ALREADY PUSHED AND CURRENTLY INERT.** The twelve
tables further down enable code nobody has written yet. Measured by
`tools/audit_event_type_check.py`, EXIT 1, 2026-10-07:

| table | values its CHECK REJECTS | emitted by |
|---|---|---|
| `sairncode_audit_log` | `credential_change_refused`, `pin_setup` | `api/sc-ai.js`, `api/sc-auth.js` |
| `sairnlaw_audit_log` | `ai_interaction`, `ai_rejected`, `ai_reviewed`, `ai_used_in_filing`, `deadline_engine`, `legal_reference_lookup` | `api/law-auth.js`, `api/legal-citator.js`, `api/legal-deadlines.js`, `api/legal-reference.js` |
| `stonedesk_audit_log` | `order_link_created`, `order_link_revoked`, `pin_setup`, `sub_roster_write` | `api/sd-auth.js`, `api/sd-sub-data.js`, `api/stonedesk-track.js` |

**11 distinct values, 12 table-value pairs, 7 files.** Every one is a write
that fails at the database: `writeAuditLog` is non-fatal and returns false, so
the calling code carries on and the row is simply absent.

**CONFIRM THE CONSTRAINT NAMES FIRST.** Postgres names an inline CHECK
`<table>_<column>_check` by default, but if a table was created differently
the `drop constraint if exists` **silently does nothing** and the `add` then
fails on a duplicate. Run this before the three ALTERs:

```sql
-- STEP 0 PRE-FLIGHT -- read the three real constraint names.
select conrelid::regclass as tbl, conname, pg_get_constraintdef(oid)
  from pg_constraint
 where contype = 'c'
   and conrelid in (
         'public.sairncode_audit_log'::regclass,
         'public.sairnlaw_audit_log'::regclass,
         'public.stonedesk_audit_log'::regclass)
 order by 1, 2;
```

### ■ STEP 0a — SAIRNcode

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

### ■ STEP 0b — StoneDesk

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

### ■ STEP 0c — SAIRNlaw  (the one the first printing MISSED)

```sql
alter table public.sairnlaw_audit_log
  drop constraint if exists sairnlaw_audit_log_event_type_check;
alter table public.sairnlaw_audit_log
  add constraint sairnlaw_audit_log_event_type_check
  check (event_type in (
    'login_success',
    'login_failed',
    'lockout',
    'pin_bootstrap',
    'pin_setup',
    'mfa_enrolled',
    'mfa_verified',
    'mfa_failed',
    'sso_login',
    'sso_link',
    'citator_lookup',
    'ai_interaction',
    'ai_rejected',
    'ai_reviewed',
    'ai_used_in_filing',
    'deadline_engine',
    'legal_reference_lookup'
  ));
```

### ■ STEP 0d — SAIRNvet: NO SQL. One line of JavaScript.

`sv_audit_log` already exists (`sql/sairnvet_data_schema.sql:60`) and carries
**no `event_type` CHECK**, so there is nothing to alter and no new table to
create. It is simply not in the allowlist, so every write to it is refused by
`api/_lib/audit.js` before it reaches Postgres. In `api/_lib/audit.js:40`:

```js
// before
const AUDIT_TABLES = { sairnlaw_audit_log: true, sairncode_audit_log: true, stonedesk_audit_log: true };
// after
const AUDIT_TABLES = { sairnlaw_audit_log: true, sairncode_audit_log: true, stonedesk_audit_log: true, sv_audit_log: true };
```

**NOT DONE BY ME, and the reason is worth stating:** `sv_audit_log` has no
`event_type` CHECK, which means it accepts *any* event name. Adding it to the
allowlist is correct and is also the moment to decide whether that table
should GAIN a CHECK — an open `text` column lets any future caller invent an
event name and quietly change what the log means, which is the reason
`sql/stonedesk_audit_log_schema.sql` gives for keeping its own list narrow.
That is a judgement about SAIRNvet, not a mechanical edit.

**PROVEN SUFFICIENT, NOT ASSUMED.** The three ALTERs above were applied to a
COPY of `sql/` and `tools/audit_event_type_check.py` was re-run against it:
**EXIT 0, "Every event_type emitted to a table with a CHECK constraint
appears in that constraint."** Before: EXIT 1, 3 of 3 tables. The live clone
was never written to — `git status` identical before and after.

---

## THE TWELVE NEW TABLES

**12, not 14.** StoneDesk needs none (code only) and SAIRNvet needs none
(STEP 0d). These twelve are the apps whose `*-auth.js` has a `setup` action,
records neither an audit row nor a `created_by`, and has nowhere to write one.

**THE EVENT VOCABULARY IS DELIBERATELY NARROW** — five values, taken from what
the three existing logs already use for the credential lifecycle. An open
`text` column would let any future caller invent an event name and quietly
change what the log means; adding a value later should stay a reviewable
migration. **And STEP 0 is the proof that it needs to be reviewable:** three
tables drifted out of sync with their own callers precisely because nobody
reviewed the pairing.

**DELIBERATELY NOT STORED, in any of these:** PIN hashes, PIN salts, lockout
state, or any credential material. `detail` carries non-secret metadata only.
`employee_id` at the top level is **the ACTOR**, never the target — the target
belongs in `detail`, so "who did this to whom" survives.

---

### ■ STEP 1 — `sairncare_audit_log`  (`api/alf-auth.js`)

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

### ■ STEP 2 — `sairnbuild_audit_log`  (`api/bld-auth.js`)

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

### ■ STEP 3 — `sairndental_audit_log`  (`api/dnt-auth.js`)

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

### ■ STEP 4 — `sairngrounds_audit_log`  (`api/grd-auth.js`)

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

### ■ STEP 5 — `sairnlegacy_audit_log`  (`api/leg-auth.js`)

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

### ■ STEP 6 — `sairnmechanical_audit_log`  (`api/mech-auth.js`)

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

### ■ STEP 7 — `sairnroofing_audit_log`  (`api/rf-auth.js`)

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

### ■ STEP 8 — `sairnbiz_audit_log`  (`api/sb-auth.js`)

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

### ■ STEP 9 — `sairnscape_audit_log`  (`api/scp-auth.js`)

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

### ■ STEP 10 — `sairndesign_audit_log`  (`api/sdn-auth.js`)

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

### ■ STEP 11 — `sairnsenior_audit_log`  (`api/sen-auth.js`)

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

### ■ STEP 12 — `sairnfreedom_audit_log`  (`api/sf-auth.js`)

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

Each new table needs three things in its `api/*-auth.js` before anything is
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

**AND RUN `python tools/audit_event_type_check.py` AFTER EACH ONE.** It exits
1 and names the table and the value when a `setup` branch emits an event the
new CHECK does not list — which is the defect STEP 0 exists to repair,
arriving twelve more times if nobody looks.

---

# APPENDIX, ADDED 2026-10-07 (batch 18) — STEP 13 and STEP 14

**Still applied nowhere.** Same rule as the rest of this file: every statement
below is printed for Michael to run, and nothing has been run.

---

## ■ STEP 13 — SAIRNvet. **THE DECISION TO ADD `sv_audit_log` TO `AUDIT_TABLES` RESTS ON A FALSE PREMISE, AND THE ONE-LINE CHANGE WAS NOT MADE**

**STEP 0d of this file said the addition was "one line of JavaScript". THAT WAS
MINE AND IT WAS WRONG.** Re-derived at HEAD by reading both halves instead of
one:

| what `writeAuditLog` POSTs (`api/_lib/audit.js:59-64`) | what `sv_audit_log` HAS (`sql/sairnvet_data_schema.sql:60-70`) |
|---|---|
| `license_hash` | `license_hash` ✓ |
| `employee_id` | **absent** |
| `role` | **absent** |
| `event_type` | **absent** |
| `detail` | **absent** |
| — | `audit_log_id` **`not null`, no default** |
| — | `id`, `app_id`, `data jsonb`, `created_at`, `updated_at` |

**FOUR OF THE FIVE POSTED COLUMNS DO NOT EXIST.** Adding `sv_audit_log` to the
allowlist would send every SAIRNvet audit write to a table that cannot take the
row: PostgREST refuses it, `writeAuditLog` is **non-fatal and returns false**,
the calling code carries on, and **the row is simply absent** — reported only in
a server log. That is the exact defect STEP 0 of this file exists to repair,
created in one line.

**AND THERE IS NOTHING FOR A CHECK CONSTRAINT TO CONSTRAIN.** `sv_audit_log` has
no `event_type` column, so the five-value CHECK this step was asked to print
cannot be written against the table as it stands. The pre-flight select proves
it rather than asserting it:

```sql
-- STEP 13 PRE-FLIGHT (a) -- THIS IS EXPECTED TO FAIL, and the failure is the
-- answer. Run it first so the conclusion below is yours and not mine.
select distinct event_type
  from public.sv_audit_log
 order by 1;
-- EXPECTED: ERROR 42703 undefined_column: column "event_type" does not exist
```

```sql
-- STEP 13 PRE-FLIGHT (b) -- the query that DOES run, and the one to read.
select column_name, data_type, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public' and table_name = 'sv_audit_log'
 order by ordinal_position;
```

```sql
-- STEP 13 PRE-FLIGHT (c) -- how much is in there, and what shape it already is.
-- `data` is the blob the app writes through api/sd-data.js; its keys are the
-- nearest thing to an event vocabulary that exists today.
select count(*) as rows_total,
       min(created_at) as oldest,
       max(created_at) as newest
  from public.sv_audit_log;

select k as data_key, count(*) as n
  from public.sv_audit_log, jsonb_object_keys(data) as k
 group by k order by n desc limit 40;
```

### WHY IT IS NOT AN AUDIT LOG IN THIS MODULE'S SENSE

`sv_audit_log` is the SAIRNvet **controlled-substance DOSING trail**. It is a
per-app data table written through `api/sd-data.js`'s `SV_RESOURCES` dispatcher
(`api/sd-data.js:13100`, keyed `audit_log_id`), declared as an app resource in
`api/_resources/sairnvet.js:67`, and it carries:

```sql
grant select, insert, update on public.sv_audit_log to service_role;
```

**`update` is granted.** The three real audit logs deliberately grant only
`select, insert` — that grant pair *is* their immutability control, because
`service_role` bypasses RLS. So `sv_audit_log` is not in `AUDIT_TABLES` because
**it is not that kind of table**, not because somebody forgot a line.

### IF THE DECISION STILL STANDS, THIS IS WHAT IT COSTS — PRINTED, NOT APPLIED

```sql
-- STEP 13a -- the columns writeAuditLog posts. WITHOUT ALL FOUR, adding
-- sv_audit_log to AUDIT_TABLES records nothing.
-- `audit_log_id` is `not null` with no default and writeAuditLog does NOT
-- send it, so it needs a default as well or every insert violates not-null.
alter table public.sv_audit_log add column if not exists employee_id text;
alter table public.sv_audit_log add column if not exists role text;
alter table public.sv_audit_log add column if not exists event_type text;
alter table public.sv_audit_log add column if not exists detail jsonb;
alter table public.sv_audit_log
  alter column audit_log_id set default gen_random_uuid()::text;

-- STEP 13b -- THE FIVE-VALUE CREDENTIAL VOCABULARY, same form as the twelve
-- new tables in this file. NOT NULL is deliberately NOT added: 1,000+ existing
-- dosing rows have no event_type and a not-null column would reject them.
alter table public.sv_audit_log
  drop constraint if exists sv_audit_log_event_type_check;
alter table public.sv_audit_log
  add constraint sv_audit_log_event_type_check
  check (event_type is null or event_type in (
    'pin_bootstrap',
    'pin_setup',
    'credential_deactivated',
    'credential_reactivated',
    'credential_change_refused'
  ));

-- STEP 13c -- THE GRANT, and this is the part that is a real decision.
-- An audit log on this platform is select+insert only; that grant pair is the
-- immutability control, because service_role BYPASSES RLS. sv_audit_log has
-- `update` today because the dosing trail is updated through sd-data.js.
-- REVOKING IT WOULD BREAK THAT WRITE PATH. So one table cannot be both, and
-- this statement is printed to make the conflict visible, NOT recommended:
-- revoke update on public.sv_audit_log from service_role;
```

**`event_type is null or event_type in (...)`** rather than a bare `in (...)`
is the only form that can be added to a table with existing rows — a plain
CHECK would be rejected outright by the rows already there. Said here because
the twelve new tables in this file use the strict form and this one cannot.

### THE ALTERNATIVE, AND IT IS THE ONE I WOULD PUT IN FRONT OF CHAT FIRST

A new `sairnvet_audit_log`, in exactly the form of the twelve above, leaving the
dosing trail alone. It is more SQL and no judgement calls: no mixed-purpose
table, no `update` grant to argue about, no nullable `event_type`, and the
existing dosing rows keep their meaning.

```sql
-- STEP 13-ALT -- a real audit log for SAIRNvet, identical in form to STEP 1-12.
create table if not exists public.sairnvet_audit_log (
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

create index if not exists idx_sairnvet_audit_log_license_time
  on public.sairnvet_audit_log (license_hash, created_at desc);

alter table public.sairnvet_audit_log enable row level security;
drop policy if exists "svc insert only sairnvet_audit_log" on public.sairnvet_audit_log;
create policy "svc insert only sairnvet_audit_log" on public.sairnvet_audit_log for insert with check (true);

-- THE ACTUAL IMMUTABILITY CONTROL: select + insert only, no update, no delete.
-- service_role BYPASSES RLS, so the policy above is NOT what enforces
-- immutability -- these grants are.
revoke all on public.sairnvet_audit_log from anon, authenticated;
revoke all on public.sairnvet_audit_log from service_role;
grant select, insert on public.sairnvet_audit_log to service_role;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from public.sairnvet_audit_log;
```

**NO WRITER EXISTS EITHER WAY, AND THAT WAS CONFIRMED FIRST.** 28 `writeAuditLog`
call sites across `api/`; the only `AUDIT_TABLE` constants are
`sairncode_audit_log` (`api/sc-ai.js:61`, `api/sc-auth.js:46`),
`stonedesk_audit_log` (`api/sd-auth.js:47`, `api/sd-sub-data.js:45`,
`api/stonedesk-track.js:50`) and the `sairnlaw_audit_log` default
(`api/_lib/audit.js:41`). **Nothing targets `sv_audit_log`**, and
`tools/audit_event_type_check.py` reports it under *"tables WITHOUT one"* with
no writers found.

**WHAT WAS BUILT INSTEAD OF THE ONE-LINE EDIT:** `tests/run_audit_event_type_probe.py`
arms **H0 / H1 / H2** — a table may be in `AUDIT_TABLES` only if it has the
columns `writeAuditLog` posts, with the paired negative measured off
`sv_audit_log`'s real DDL so H1 is evidence rather than a tautology. **If
anybody makes this change later, that arm goes red.** That is worth more than
the change was.

---

## ■ STEP 14 — `rf_schedule.status_changed_by`, which closes the lost-update window batch b1 accepted

**WHAT IT IS FOR.** `rf_schedule/set_status` (`api/sd-data.js`) PATCHes two
scalar columns and sends no `data`, so batch b1 attributed it with a
**read-then-merge** onto the row the branch already reads for its
`canSeeSchedule` gate. That merge accepts a narrow lost-update window: a
concurrent writer changing `rf_schedule.data` between the select and the PATCH
has its blob change overwritten. The window is two awaits, the only other
writer of that blob is `rf_schedule/write` (management only), and `wroteRow()`
still detects a PATCH that matched nothing — but the trade is real and it was
named rather than hidden.

**A dedicated column removes the trade entirely**: the status change writes its
own scalar column and never touches the blob, so there is nothing to lose.

**`created_by` IS NOT REUSABLE AND THAT IS THE WHOLE REASON THIS IS A
MIGRATION.** `sql/sairnroofing_locations_schema.sql:92` is
`created_by text not null, -- server-stamped from the session`. It means who
**created** the day. Overwriting it on a status change would destroy the
creation record in order to record an edit.

```sql
-- STEP 14 -- rf_schedule gains status_changed_by. NULLABLE on purpose.
-- Every row that exists today had its status set before this column did, and
-- a `not null` column would either reject them or need a backfilled value
-- that names an employee who did not do it -- a fabricated actor, which is
-- worse than an honest null. NULL means "set before this column existed".
alter table public.rf_schedule
  add column if not exists status_changed_by text;

alter table public.rf_schedule
  add column if not exists status_changed_by_role text;

alter table public.rf_schedule
  add column if not exists status_changed_at timestamptz;

-- created_by IS UNTOUCHED. It is `not null` and means who CREATED the day.
-- No statement in this step alters, drops or backfills it.

-- Verify after running -- expect the three new columns present and nullable,
-- and created_by still NOT NULL:
--   select column_name, data_type, is_nullable
--     from information_schema.columns
--    where table_schema = 'public' and table_name = 'rf_schedule'
--      and column_name in ('created_by', 'status_changed_by',
--                          'status_changed_by_role', 'status_changed_at')
--    order by column_name;
```

**THE CODE CHANGE IS NOT IN THIS BATCH AND IS NOT WRITTEN.** `api/sd-data.js`
keeps the read-then-merge until **Michael confirms STEP 14 has run**. Writing
the column before it exists would make every `set_status` PATCH fail with
`42703 undefined_column` — PostgREST returns 400, and `rf_schedule/set_status`
answers 502 `Data store error`. **A status change that silently stops working
is a worse outcome than the lost-update window it was meant to close.**

**THE EXACT CODE CHANGE, FOR WHOEVER TAKES IT AFTER THE SQL LANDS:**

1. In `rf_schedule/set_status`, drop `data` from the select added in b1 and drop
   the `schedBlob` merge entirely.
2. Send `status_changed_by: session.employee_id`,
   `status_changed_by_role: session.role`, `status_changed_at: nowISO()`
   alongside `status` and `updated_at`.
3. Add `status_changed_by` to the `rf_schedule/read` select and to the row the
   read reconstructs, so the field is visible rather than write-only.
4. `tests/sd_data_write_attribution_three_apps.js` arm **D3** asserts the merge
   exists and MUST be rewritten in the same commit — it currently pins the
   read-then-merge, which is the right thing to pin until the column exists and
   the wrong thing afterwards. **A stale arm that passes is how the next reader
   concludes the merge is still needed.**
