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
