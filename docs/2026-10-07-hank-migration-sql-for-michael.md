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
| SAIRNvet "needs a decision" | **SUPERSEDED 2026-10-08 — see STEP 13** | The row below is left as written so the correction is visible. It said *"reuse `sv_audit_log`, no SQL at all, one line of JavaScript"*. **That was wrong and it was mine.** `sv_audit_log` has no `event_type` column AT ALL, and four of the five columns `writeAuditLog` posts are absent, so the one line would have made every SAIRNvet audit write record nothing. **CHAT DECIDED 13-ALT: a new `sairnvet_audit_log`.** |
| ~~SAIRNvet reuses `sv_audit_log`~~ | ~~no SQL, one line of JS~~ | ~~`sv_audit_log` carries no `event_type` CHECK so there is nothing to alter~~ — **the premise, kept struck through rather than removed** |
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

### ■ STEP 0d — **SUPERSEDED 2026-10-08. THE ANSWER IS STEP 13 (13-ALT).**

> **DO NOT RUN THE JAVASCRIPT BELOW.** This step said SAIRNvet needed no SQL
> and one line of JavaScript. **It is wrong.** `sv_audit_log` has no
> `event_type` column, and `employee_id`, `role`, `event_type` and `detail`
> — four of the five columns `writeAuditLog` posts — are all absent, while
> `audit_log_id` is `not null` with no default and is never sent. The one
> line would have sent every SAIRNvet audit write to a table that cannot
> take the row; `writeAuditLog` is non-fatal and returns false, so the row
> would be ABSENT with only a server log to say so.
>
> **`sv_audit_log` is the controlled-substance DOSING trail**, a per-app
> data table written through `api/sd-data.js`'s `SV_RESOURCES` dispatcher
> and carrying `grant ... update`, which the three real audit logs
> deliberately do not. It is not in the allowlist because it is not that
> kind of table.
>
> **GO TO STEP 13.** It creates `sairnvet_audit_log` with pre-flight and
> verify queries, and leaves the dosing trail alone.
>
> The original text is kept below, unedited. A superseded step that is
> deleted is a step somebody re-derives from scratch; a superseded step that
> is silently corrected is one nobody knows was ever wrong.

#### (superseded original, kept for the record)

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
`event_type` CHECK, which means it accepts *any* event name. ~~Adding it to the
allowlist is correct~~ — **IT IS NOT CORRECT; see the box above** — and is also
the moment to decide whether that table should GAIN a CHECK — an open `text` column lets any future caller invent an
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

## ■ STEP 13 — SAIRNvet gets its OWN audit log. **DECIDED 2026-10-08: 13-ALT.**

**CHAT DECIDED 13-ALT.** The earlier version of this step is replaced, not
amended: `sv_audit_log` is **left alone** and SAIRNvet gets a new
`sairnvet_audit_log` in exactly the form of the twelve tables above.

**WHY THE OTHER OPTION IS GONE, kept short because the long version is in
`docs/handoff-hank-2026-10-07d.md` item 8.** The original STEP 0d of this file
called adding `sv_audit_log` to `AUDIT_TABLES` *"one line of JavaScript"*. That
was wrong:

| `writeAuditLog` POSTs (`api/_lib/audit.js:59-64`) | `sv_audit_log` HAS (`sql/sairnvet_data_schema.sql:60-70`) |
|---|---|
| `license_hash` | `license_hash` ✓ |
| `employee_id` · `role` · `event_type` · `detail` | **all four ABSENT** |
| — | `audit_log_id` **`not null`, no default**, which `writeAuditLog` never sends |

Four of five posted columns do not exist, so every write would be refused by
Postgres — and `writeAuditLog` is **non-fatal and returns false**, so the row
would simply be absent with only a server log to say so.

**AND `sv_audit_log` IS NOT THAT KIND OF TABLE.** It is the SAIRNvet
controlled-substance **DOSING** trail: a per-app data table written through
`api/sd-data.js`'s `SV_RESOURCES` dispatcher (`api/sd-data.js:13100`, keyed
`audit_log_id`), declared as an app resource in `api/_resources/sairnvet.js:67`,
and carrying **`grant select, insert, update`**. The three real audit logs grant
only `select, insert`, and that grant pair *is* their immutability control
because `service_role` bypasses RLS. **One table cannot be both an immutable
audit log and a mutable dosing trail**, which is the whole reason 13-ALT wins:
it needs no `revoke update` argument, no nullable `event_type`, and no backfill.

**`tests/run_audit_event_type_probe.py` arms H0/H1/H2 enforce this decision
mechanically** — a table may be in `AUDIT_TABLES` only if it has the columns
`writeAuditLog` posts — so the rejected option now fails a probe rather than
living in prose.

---

### ■ STEP 13 PRE-FLIGHT — run all three BEFORE the DDL

```sql
-- 13-PRE (a) -- DOES THE NEW NAME COLLIDE WITH ANYTHING? Expect 0 rows.
-- `create table if not exists` is silent on a name that already exists, which
-- would leave you believing you made a table you did not. Ask first.
select table_name
  from information_schema.tables
 where table_schema = 'public'
   and table_name in ('sairnvet_audit_log', 'sv_audit_log')
 order by table_name;
-- EXPECTED: exactly ONE row, sv_audit_log. If sairnvet_audit_log is already
-- there, STOP and read it before running the DDL below.
```

```sql
-- 13-PRE (b) -- THE DOSING TRAIL IS THE THING BEING PROTECTED, so record its
-- shape and size BEFORE touching anything, and compare after. Nothing in this
-- step writes to it; this is the evidence that nothing did.
select count(*)              as rows_total,
       min(created_at)       as oldest,
       max(created_at)       as newest
  from public.sv_audit_log;

select column_name, data_type, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public' and table_name = 'sv_audit_log'
 order by ordinal_position;

select grantee, privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public' and table_name = 'sv_audit_log'
 order by grantee, privilege_type;
-- EXPECTED on the last one: service_role with SELECT, INSERT and UPDATE.
-- UPDATE is correct here and must still be there afterwards -- the dosing trail
-- is updated through sd-data.js. If it is gone, something revoked it.
```

```sql
-- 13-PRE (c) -- pgcrypto, because the DDL below defaults a uuid primary key.
-- sql/sairnvet_data_schema.sql already does `create extension if not exists
-- pgcrypto`, so this is almost certainly present -- asked rather than assumed,
-- because the failure mode is the DDL erroring half way through.
select extname from pg_extension where extname = 'pgcrypto';
-- EXPECTED: one row. If empty: create extension if not exists pgcrypto;
```

---

### ■ STEP 13 — THE DDL

```sql
-- A real audit log for SAIRNvet, identical in form to STEP 1-12.
-- sv_audit_log IS NOT TOUCHED BY ANY STATEMENT IN THIS STEP.
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
-- immutability -- these grants are. RLS is the second layer against anon and
-- authenticated, which have no grants at all.
revoke all on public.sairnvet_audit_log from anon, authenticated;
revoke all on public.sairnvet_audit_log from service_role;
grant select, insert on public.sairnvet_audit_log to service_role;
```

**THE EVENT VOCABULARY IS THE SAME FIVE AS STEP 1-12** and `event_type` is
`not null` with the **strict** `in (...)` — which is only possible because the
table is new and empty. (The rejected option could not use the strict form: 
`sv_audit_log`'s existing rows have no `event_type`, so it would have needed
`event_type is null or event_type in (...)`, a weaker constraint arrived at by
accident of history.)

---

### ■ STEP 13 VERIFY — four queries, and what each one would catch

```sql
-- 13-V (a) -- the table exists and is readable. Expect 0, no error.
select count(*) from public.sairnvet_audit_log;
```

```sql
-- 13-V (b) -- THE GRANTS, which are the immutability control and the one thing
-- most likely to be wrong. Expect EXACTLY two rows for service_role:
-- INSERT and SELECT. UPDATE or DELETE here means the revoke did not take.
select grantee, privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public' and table_name = 'sairnvet_audit_log'
 order by grantee, privilege_type;
```

```sql
-- 13-V (c) -- THE CHECK CONSTRAINT IS REALLY THERE AND LISTS FIVE VALUES.
-- A table created before the constraint was added would accept any event name
-- and nothing downstream would notice.
select conname, pg_get_constraintdef(oid)
  from pg_constraint
 where conrelid = 'public.sairnvet_audit_log'::regclass
   and contype = 'c'
 order by conname;
-- EXPECTED: sairnvet_audit_log_event_type_check, listing the five values.
```

```sql
-- 13-V (d) -- THE DOSING TRAIL IS UNCHANGED. Compare both numbers to 13-PRE(b).
-- This is the verify that matters most, because the whole point of 13-ALT is
-- that sv_audit_log was not the table to change.
select count(*) as rows_total, max(created_at) as newest
  from public.sv_audit_log;

select grantee, privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public' and table_name = 'sv_audit_log'
 order by grantee, privilege_type;
-- EXPECTED: identical to 13-PRE(b), INCLUDING service_role's UPDATE.
```

---

### ■ STEP 13 — THE CODE HALF, AND IT IS NOT IN THIS BATCH

**NOTHING IN `api/` WAS CHANGED, AND NOTHING WILL BE UNTIL MICHAEL CONFIRMS
STEP 13 HAS RUN.** Writing the code first makes every SAIRNvet audit write hit
a table that does not exist: PostgREST answers 404, `writeAuditLog` returns
false non-fatally, and **the row is absent with nothing on screen to say so** —
the exact defect this whole sequence exists to remove.

In order, after the SQL lands:

1. `api/_lib/audit.js:40` — add `sairnvet_audit_log: true` to `AUDIT_TABLES`.
   **The allowlist is not optional bookkeeping**: an unknown table is refused
   with `audit log write refused: unknown table` and the write records nothing.
2. `api/sv-auth.js` — `const { writeAuditLog } = require('./_lib/audit');` and
   `const AUDIT_TABLE = 'sairnvet_audit_log';`
3. The `setup` branch gets the same six lines `api/sc-auth.js` and
   `api/sd-auth.js` already carry, **including `attributed` on the response** so
   a failed write cannot look like a successful one.
4. `python tools/audit_event_type_check.py` — it must stay EXIT 0 for the new
   table. It exits 1 and names the table and the value if a branch emits an
   event the CHECK does not list.
5. `python tests/run_audit_event_type_probe.py` — **arm H1 is the one to watch.**
   It asserts every table in `AUDIT_TABLES` has the four columns
   `writeAuditLog` posts. `sairnvet_audit_log` has them by construction, so H1
   should stay green; if it goes red, the DDL above did not run the way step 1
   assumes.

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
