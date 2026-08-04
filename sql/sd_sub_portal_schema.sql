-- sql/sd_sub_portal_schema.sql
-- StoneDesk Subcontractor Portal (Phase 1) -- Supabase schema
--
-- Run this once in the Supabase SQL editor (same project as
-- sql/sd_employee_auth_schema.sql) before api/sd-sub-auth.js or
-- api/sd-sub-data.js will work. Until this runs, both return a clear 503
-- NOT_PROVISIONED rather than a generic 500.
--
-- WHY THIS EXISTS: subs (installers, templaters, etc.) are not staff -- they
-- need their own login, scoped to see ONLY their own assigned job(s), never
-- other subs' data, shop financials, other jobs, pricing/margins, or
-- customer info. Deliberately a SEPARATE credential tier from
-- sd_employee_auth, not a new role bolted onto it -- api/_lib/auth.js's
-- ROLES_BY_APP now has a distinct 'stonedesk_sub' app namespace (role: 'sub')
-- specifically so a sub token can never be confused with or pass as an
-- employee token, the same cross-app-collision discipline that already
-- separates StoneDesk's own roles from SAIRNbiz's.
--
-- Replaces panel-subcontractor's old localStorage-only demo roster (name/
-- trade/phone/rate/ytd/ins_exp/status, seeded with 5 fictional subs, no
-- login, no job assignment, no cross-device sync) -- confirmed via grep
-- before touching it that nothing else in the app referenced its functions
-- or 'sd_subs' localStorage key except the demo-data-clear utility's key
-- list, which still works unchanged (the roster below still mirrors to
-- localStorage under the same key, Supabase is just now the source of
-- truth for cross-device/sub-portal access).
--
-- THREE TABLES:
--   sd_subs      -- roster: name/contact/trade/active-inactive
--   sd_sub_auth  -- login credentials (hashed PIN), separate from roster
--                   data on purpose -- same reasoning as sd_employee_auth
--                   being separate from `employees`: auth material and
--                   profile data are different concerns with different
--                   write paths.
--   sd_sub_jobs  -- job assignments: address/details/photos/pay, one row
--                   per assignment (a sub can have multiple).
--
-- SECURITY: pin_hash is scrypt(pin, pin_salt), never the raw PIN -- same
-- api/_lib/auth.js primitives sd_employee_auth already uses. license_hash
-- scopes every row to a shop. No RLS policy defined on purpose, same
-- reasoning as every other StoneDesk-owned table: read/write exclusively
-- via the api/*.js endpoints below using SUPABASE_SERVICE_ROLE_KEY, which
-- bypasses RLS regardless.
--
-- SIZE CAP NOTE (lesson from sql/sd_render_usage_schema.sql and the bulk
-- slab upload incident): NOT adding a DB-level CHECK constraint on
-- sd_sub_jobs.data here on purpose -- that earlier incident was caused by
-- an API-level cap (sd-data.js) that didn't match an existing DB-level cap
-- (sd_slabs' sdslabs_data_size CHECK) it wasn't aware of. Rather than adding
-- a second constraint that api/sd-sub-data.js's own cap would then need to
-- stay in lockstep with forever, the ONE enforced limit lives at the API
-- layer (see api/sd-sub-data.js's SUB_JOB_PAYLOAD cap) and this table has
-- no DB-level ceiling of its own to drift out of sync with it.

create table if not exists sd_subs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  sub_id text not null,           -- login identifier, same role employee_id plays for staff
  name text not null,
  phone text,
  email text,
  trade text,                     -- e.g. 'Installer', 'Templater', 'Fabricator'
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, sub_id)
);
create index if not exists idx_sd_subs_license on sd_subs (license_hash);
grant select, insert, update on public.sd_subs to service_role;

create table if not exists sd_sub_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  sub_id text not null,
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, sub_id)
);
create index if not exists idx_sd_sub_auth_license on sd_sub_auth (license_hash);
grant select, insert, update on public.sd_sub_auth to service_role;

create table if not exists sd_sub_jobs (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  sub_id text not null,
  data jsonb not null,            -- {address, details, photos:[base64,...], payRate, payAmount, paid, paidDate, createdAt}
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_sd_sub_jobs_license on sd_sub_jobs (license_hash);
create index if not exists idx_sd_sub_jobs_sub on sd_sub_jobs (license_hash, sub_id);
grant select, insert, update on public.sd_sub_jobs to service_role;
