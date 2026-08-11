# SAIRNdental Availability + Self-Scheduling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Real recurring availability + multi-provider conflict
prevention + a genuinely public self-scheduling page, per
`docs/superpowers/specs/2026-08-10-sairndental-availability-booking-design.md`.

**Architecture decision, stated here (not a question — there's a clear
right answer for security isolation): the public booking page is a
separate file, `sairndental-book.html`**, not a "public mode" of the
main app. Keeping it physically separate makes "the license key never
appears on the public page" structurally true rather than something
that has to be maintained by discipline inside one shared file — no
internal-app code path (gate, PINs, `dntLicenseKey()`) exists in this
file at all to accidentally leak.

## Global Constraints

- `dnt_appointments` writes go through a **new, dedicated handler**
  in `api/sd-data.js` (not the existing generic `DNT_RESOURCES` block)
  once Task 1 lands — the generic block writes everything into the
  `data` jsonb blob only; this resource now also needs
  `provider_id`/`operatory_id`/`start_time`/`end_time`/`status`
  promoted to real columns on every write, or the `EXCLUDE`
  constraints have nothing to check against.
- `api/sairndental/public-availability.js` and `public-book.js` never
  return or accept a `license_hash`/license key from the client —
  only the public `booking_slug`, resolved server-side.
- `public-availability.js`'s response is exactly `[{start_time,
  end_time, provider_id}]` — no other field, ever, ok'd by an explicit
  test (Task 6).
- Rate limiting checked before any other work happens in
  `public-book.js` (fail fast, don't do a DB write's worth of work
  before discovering the request should have been rejected).
- Push Protocol: full local checks before push, real live-verify
  after, including the two-request race test (not assumed safe from
  reading the `EXCLUDE` constraint's SQL alone).

---

### Task 1: SQL migration — settings, promoted appointment columns, exclusion constraints, rate-limit table

**Files:** Create `sql/sairndental_availability_booking_schema.sql`

- [ ] **Step 1: Write the migration**

```sql
-- dnt_settings: new generic-jsonb resource, but booking_slug also
-- gets a real, indexed, unique column for fast/safe slug resolution.
create table if not exists public.dnt_settings (
  id uuid primary key default gen_random_uuid(), license_hash text not null, app_id text not null default 'sairndental',
  settings_id text not null, booking_slug text unique, data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique (license_hash, settings_id), constraint dntst_data_size check (octet_length(data::text) <= 65536)
);
create index if not exists idx_dntst_license on public.dnt_settings(license_hash);
create index if not exists idx_dntst_slug on public.dnt_settings(booking_slug);

-- dnt_appointments: promote real columns alongside the existing
-- generic data jsonb (kept for any fields not needed in a constraint
-- or a fast lookup -- patient_id, procedure_type_id, source, notes).
alter table public.dnt_appointments
  add column if not exists provider_id text,
  add column if not exists operatory_id text,
  add column if not exists start_time timestamptz,
  add column if not exists end_time timestamptz,
  add column if not exists status text;

create extension if not exists btree_gist;

alter table public.dnt_appointments
  add constraint dntap_no_provider_overlap
    exclude using gist (
      license_hash with =, provider_id with =,
      tsrange(start_time, end_time) with &&
    ) where (status in ('Pending','Confirmed')),
  add constraint dntap_no_operatory_overlap
    exclude using gist (
      license_hash with =, operatory_id with =,
      tsrange(start_time, end_time) with &&
    ) where (status in ('Pending','Confirmed'));

-- Real, new rate-limit table -- first on this platform, stated
-- plainly, not presented as reusing an existing pattern.
create table if not exists public.dnt_booking_rate_limits (
  id uuid primary key default gen_random_uuid(),
  ip_hash text not null, window_start timestamptz not null, count int not null default 1,
  unique (ip_hash, window_start)
);
create index if not exists idx_dntbrl_iphash on public.dnt_booking_rate_limits(ip_hash);

-- RLS: service-role only, same as every table on this platform.
alter table public.dnt_settings enable row level security;
drop policy if exists "svc only dnt_settings" on public.dnt_settings;
create policy "svc only dnt_settings" on public.dnt_settings
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
grant select, insert, update, delete on public.dnt_settings to service_role;

alter table public.dnt_booking_rate_limits enable row level security;
drop policy if exists "svc only dnt_booking_rate_limits" on public.dnt_booking_rate_limits;
create policy "svc only dnt_booking_rate_limits" on public.dnt_booking_rate_limits
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
grant select, insert, update, delete on public.dnt_booking_rate_limits to service_role;
```

- [ ] **Step 2: Flag to the user**

Not run as part of this plan's execution — Supabase SQL editor access
required, same as every migration this session.

---

### Task 2: `api/sd-data.js` — register `dnt_settings`, dedicated `dnt_appointments` write handler

**Files:** Modify `api/sd-data.js`

- [ ] **Step 1: Add `dnt_settings` to `RESOURCES` + the 400 error list**

Same pattern as Task 2 of the foundation plan — check for collision
first (`grep -n "dnt_settings" api/sd-data.js` before adding).

- [ ] **Step 2: Replace `dnt_appointments`'s handling in the `DNT_RESOURCES` block with a dedicated one**

Remove `dnt_appointments` from the generic `DNT_RESOURCES` map (Task 2
of the foundation plan added it there) — its write path now needs to
promote real columns, which the generic block doesn't do:

```js
// dnt_appointments (2026-08-10): promoted real columns
// (provider_id/operatory_id/start_time/end_time/status), not the
// generic DNT_RESOURCES jsonb-only block -- see
// docs/superpowers/specs/2026-08-10-sairndental-availability-booking-design.md
// §1 for why this resource specifically needs real columns (the
// EXCLUDE constraints in sql/sairndental_availability_booking_schema.sql
// can't check a jsonb-buried value).
if (resource === 'dnt_appointments' && action === 'read') {
  const r = await fetch(rest('dnt_appointments?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
  if (r.status === 404 || r.status === 400) { res.status(200).json({ ok: true, data: [], provisioned: false }); return; }
  const rows = await r.json();
  if (!r.ok) return upstream(res, rows);
  res.status(200).json({ ok: true, data: (rows || []).map((x) => x.data), provisioned: true });
  return;
}
if (resource === 'dnt_appointments' && action === 'write') {
  if (!payload || !payload.id) { res.status(400).json({ error: { message: 'dnt_appointments payload.id is required' } }); return; }
  const r = await fetch(rest('dnt_appointments?on_conflict=license_hash,appointment_id'), {
    method: 'POST',
    headers: Object.assign({}, headers, { Prefer: 'resolution=merge-duplicates,return=representation' }),
    body: JSON.stringify({
      license_hash: licHash, app_id: 'sairndental', appointment_id: String(payload.id), data: payload,
      provider_id: payload.provider_id || null, operatory_id: payload.operatory_id || null,
      start_time: payload.start_time || null, end_time: payload.end_time || null, status: payload.status || null,
      updated_at: nowISO()
    })
  });
  if (r.status === 404 || r.status === 400) { res.status(503).json({ error: { code: 'NOT_PROVISIONED', message: 'SAIRNdental data tables are not set up yet — run sql/sairndental_data_schema.sql and sql/sairndental_availability_booking_schema.sql in Supabase first.' } }); return; }
  if (r.status === 409) { res.status(409).json({ error: { code: 'SLOT_TAKEN', message: 'This time slot conflicts with an existing appointment for this provider or operatory.' } }); return; }
  const rows = await r.json();
  if (!r.ok) return upstream(res, rows);
  res.status(200).json({ ok: true, data: (Array.isArray(rows) && rows[0]) ? rows[0].data : payload });
  return;
}
```

Note: internal-app staff-created appointments (not self-scheduled)
also go through this same handler — the `EXCLUDE` constraints protect
every appointment write, not just the public path, which is correct
(a staff member should also be blocked from double-booking a
provider).

- [ ] **Step 3: Syntax-check + commit**

```
node --check api/sd-data.js
```

```
git add api/sd-data.js
git commit -m "feat: api/sd-data.js -- dedicated dnt_appointments write handler (real columns for the EXCLUDE constraints), register dnt_settings

..."
```

---

### Task 3: Public endpoints — availability + booking

**Files:** Create `api/sairndental/public-availability.js`,
`api/sairndental/public-book.js`

- [ ] **Step 1: Shared slug-resolution + rate-limit helpers**

Both files need: resolve `slug` -> `license_hash` via
`dnt_settings?booking_slug=eq.<slug>&select=license_hash`, and (for
`public-book.js`) a rate-limit check/increment against
`dnt_booking_rate_limits` keyed by `sha256(request IP + a server-side
salt env var)`.

- [ ] **Step 2: `public-availability.js`**

Input: `{slug, provider_id, procedure_type_id, date_range}`. Resolves
`license_hash`, reads `dnt_provider_hours` + `dnt_procedure_types`
(for `default_length_minutes`) + existing `dnt_appointments` for that
provider (real columns, not the jsonb blob) within the date range,
computes open slots server-side, returns **only**
`[{start_time, end_time, provider_id}]` — per spec §2's hard
requirement, verified in Task 6, not just intended here.

- [ ] **Step 3: `public-book.js`**

Rate-limit check first (fail fast). Input: `{slug, patient: {name,
dob, phone, email}, provider_id, procedure_type_id, start_time}`.
Resolves `license_hash` and `end_time` (from the procedure type's
`default_length_minutes`), creates the patient record (or matches an
existing one by name+dob+phone — exact match only, never fuzzy, to
avoid accidentally attaching a stranger's booking to the wrong
patient's record), inserts the `dnt_appointments` row with
`status:'Pending'`, `source:'self-scheduled'` through Task 2's
dedicated handler. A real `409` from the `EXCLUDE` constraint (someone
else booked this exact slot first) is mapped to a clean
`SLOT_TAKEN` response to the caller.

- [ ] **Step 4: Syntax-check + commit**

```
node --check api/sairndental/public-availability.js
node --check api/sairndental/public-book.js
```

```
git add api/sairndental/public-availability.js api/sairndental/public-book.js
git commit -m "feat: SAIRNdental -- public availability + booking endpoints (slug-scoped, rate-limited, never leak other patients' data)

..."
```

---

### Task 4: Internal app — Booking Settings + Pending Requests panels

**Files:** Modify `sairndental.html`

- [ ] **Step 1: Booking Settings panel**

Set/view `booking_slug` (validate uniqueness against a real
`check_slug` read before saving — a clean rejection if taken, not a
silent overwrite), `timezone`, and checkboxes over `procedureTypes()`
for "publicly bookable." Saves to `dnt_settings`.

- [ ] **Step 2: Pending Requests panel**

Lists every `dnt_appointments` entry with `status:'Pending'`, showing
patient/provider/procedure/time, Confirm/Reject buttons (write back
through Task 2's handler with `status` changed to `'Confirmed'` or
`'Cancelled'`). No outbound email here — deferred to the
automated-reminders follow-up plan (design spec §5, restated).

- [ ] **Step 3: Syntax-check + commit**

```
python tools/checkblocks.py sairndental.html
python tools/div_balance_check.py sairndental.html
```

```
git add sairndental.html
git commit -m "feat: SAIRNdental -- Booking Settings + Pending Requests panels

..."
```

---

### Task 5: `sairndental-book.html` — the real public page

**Files:** Create `sairndental-book.html`

- [ ] **Step 1: Write the page**

Minimal, no license gate, no PIN, no staff nav — reads `?slug=` from
the URL, calls `public-availability.js` for the selected provider/
procedure type, renders real open slots, calls `public-book.js` on
submission with the patient's entered contact info. Confirms success
with a real message ("Your request is pending confirmation — the
practice will reach out to confirm") — **never** implies the
appointment is confirmed, since it isn't yet (spec's firm
never-auto-confirm decision).

- [ ] **Step 2: `vercel.json` wiring — same commit**

`buildCommand`'s `cp` list gets `sairndental-book`, plus a
`{"src":"/sairndental-book$","dest":"/sairndental-book.html"}` route.

- [ ] **Step 3: Syntax-check + commit**

```
python tools/checkblocks.py sairndental-book.html
python tools/div_balance_check.py sairndental-book.html
node -e "JSON.parse(require('fs').readFileSync('vercel.json','utf8')); console.log('VALID_JSON')"
```

```
git add sairndental-book.html vercel.json
git commit -m "feat: SAIRNdental -- public self-scheduling page (sairndental-book.html)

..."
```

---

### Task 6: End-to-end verification, push, live-verify

- [ ] **Step 1:** Full local re-check of every changed file.
- [ ] **Step 2:** Push.
- [ ] **Step 3:** Live-verify `sairn.vercel.app/sairndental-book` returns
  200 and `sairn.vercel.app/sairndental`'s new panels load.
- [ ] **Step 4:** Real slug-resolution test: set a real slug via the
  internal app, confirm the public page resolves it correctly and an
  invalid slug is rejected cleanly.
- [ ] **Step 5:** Real conflict test (the actual regression test for
  §3): two near-simultaneous `public-book.js` requests for the same
  provider+time — confirm exactly one succeeds, the other gets a real
  `409 SLOT_TAKEN` from the `EXCLUDE` constraint itself firing.
- [ ] **Step 6:** Real rate-limit test: exceed the threshold from one
  source, confirm a real `429`.
- [ ] **Step 7:** Confirm `public-availability.js`'s live response
  contains only `{start_time, end_time, provider_id}` — inspect the
  actual response body, not just the code.
- [ ] **Step 8:** Confirm the real license key never appears anywhere
  in `sairndental-book.html`'s served source, JS, or any network
  request it makes — a real check (view source + inspect requests),
  not an assumption from the file being "separate."
- [ ] **Step 9:** Confirm a booking lands as `Pending`, appears in the
  internal app's Pending Requests panel, and Confirm/Reject actually
  updates its status.
- [ ] **Step 10:** Update
  `docs/superpowers/specs/2026-08-10-sairndental-availability-booking-design.md`'s
  status, with commit SHAs.

---

**Not started. Awaiting explicit go-ahead before any code in Tasks 1-6
is written**, per your instruction.
