-- sql/stonedesk_intake_photos_2026-09-03.sql
-- Photo storage for public quote requests, so StoneDesk's Project Intake form
-- can be built on the public surface that already exists (2026-09-03).
--
-- ── READ THIS BEFORE RUNNING: THE PLAN THIS FILE IMPLEMENTS IS NOT THE ONE
--    THAT WAS ASKED FOR, AND THE DIFFERENCE IS THE POINT ──────────────────────
--
-- The task was: migrate `intake_submissions` to carry license_hash/app_id and a
-- public slug, and add a rate-limit table, so a public intake form could be
-- built on the SAIRNdental template.
--
-- NONE OF THAT IS NEEDED, because StoneDesk already has all of it. Checked
-- before writing rather than after:
--
--   sql/stonedesk_public_surface_schema.sql  (2026-09-02)  ships
--       sd_public_shop        shop_slug, published, license_hash -- the slug
--       sd_quote_requests     inbound leads from a public form, land `pending`
--       sd_public_rate_limits per-IP-hash counters
--   api/_lib/stonedesk-public.js   resolveShopSlug + checkAndIncrementRateLimit
--   api/stonedesk-public.js        LIVE and answering: probed 2026-09-03,
--                                  {"action":"catalog","slug":"..."} -> 404
--                                  NOT_FOUND, {} -> 400 naming both actions
--
-- Adding a second slug column, a second rate-limit table and a second public
-- endpoint would have duplicated a day-old subsystem. `sd_quote_requests` IS
-- the intake table; the quote-request form on the public catalog IS a customer
-- intake form.
--
-- ── SO WHY THIS FILE EXISTS AT ALL ─────────────────────────────────────────
-- One real gap, and it is a hard constraint rather than a preference:
--
--     constraint sdqr_data_size check (octet_length(data::text) <= 65536)
--
-- 64 KB. StoneDesk's intake is not a text form -- its whole value is that the
-- customer photographs their kitchen, Claude estimates the run lengths and the
-- shape, and the result loads straight into the Drawing Tool. The legacy
-- `intake_submissions` table carries photo_base64, photo_base64_2 and
-- photo_base64_3. A single phone photo base64-encodes well past 64 KB, so
-- putting it in sd_quote_requests.data would fail the check constraint on the
-- first real submission -- a 400 from PostgREST, which api/stonedesk-public.js
-- maps to NOT_PROVISIONED: "This shop is not set up to take requests yet."
-- A customer would be told the shop cannot take requests because their photo
-- was too big. That is exactly the misleading-error class this app has been
-- fixing all week, so the photo gets its own row and its own limit.
--
-- Photos therefore live in a sibling table keyed by request_id, mirroring
-- sd_progress_photos -- which is the house pattern for image bytes and already
-- carries the 1.5 MB per-row cap used here.
--
-- ── WHAT THIS FILE DOES *NOT* DO, DELIBERATELY ─────────────────────────────
-- It does not touch `intake_submissions`. That table is live, has 22 columns,
-- keys rows by a PLAINTEXT `license_key`, and is declared in no schema file.
-- Migrating it was the original plan and is now unnecessary: nothing should be
-- built on it, and it holds an unknown number of real rows that are unreadable
-- through the anon key anyway (42501, verified live 2026-08-26). Retiring it is
-- a separate decision with a separate question attached -- whether anything in
-- it needs to be carried across -- and that question needs a person who can
-- read the table. Leaving it alone is not an oversight.
--
-- ADDITIVE AND IDEMPOTENT. Safe to re-run. Run after
-- sql/stonedesk_public_surface_schema.sql, which creates sd_quote_requests.
--
-- Verify after running:
--   select column_name from information_schema.columns
--    where table_name = 'sd_quote_request_photos';
--   -- expect: id, license_hash, request_id, data, created_at
--   select grantee, privilege_type from information_schema.role_table_grants
--    where table_name = 'sd_quote_request_photos';
--   -- expect service_role with SELECT, INSERT, UPDATE and NOTHING ELSE.

set search_path to public, extensions;

-- ── sd_quote_request_photos ────────────────────────────────────────────────
-- One row per photo, not an array column: a request can carry up to three, and
-- a per-ROW size cap is the only shape where the second photo cannot push the
-- first one over a limit. Same reasoning as sd_progress_photos, whose 1.5 MB
-- cap is reused verbatim here so the two paths cannot diverge on what "a photo
-- that is too large" means.
--
-- request_id is the sd_quote_requests.request_id text key, NOT its uuid. That
-- is what api/stonedesk-public.js generates (newId('QR')) and returns to the
-- caller, and it is unique per licence by the constraint on that table. No
-- foreign key: the public endpoint writes the request and the photos in two
-- statements without a transaction, and an FK would make a slow photo write
-- orphan-check against a row that is definitely there. Orphan rows here are
-- harmless and readable; a failed insert on a customer's only photo is not.
create table if not exists public.sd_quote_request_photos (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  request_id   text not null,
  data         jsonb not null default '{}'::jsonb,  -- photo_base64, slot, ai_analysis, analyzed_at
  created_at   timestamptz not null default now(),
  constraint sdqrp_data_size check (octet_length(data::text) <= 1572864)
);
create index if not exists idx_sdqrp_license_request
  on public.sd_quote_request_photos(license_hash, request_id);

alter table public.sd_quote_request_photos enable row level security;
drop policy if exists "svc only sd_quote_request_photos" on public.sd_quote_request_photos;
create policy "svc only sd_quote_request_photos" on public.sd_quote_request_photos
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

-- NO DELETE GRANT, AND NO ANON GRANT.
--
-- delete: sql/unused_delete_grant_revoke_2026-08-24.sql revoked it across 134
-- tables (134 LOST / 0 GAINED, verified). This file is idempotent and meant to
-- be re-run, so granting delete here would silently restore what that sweep
-- removed. The platform's only reachable delete path is api/sd-data.js's
-- SC_RESOURCES branch.
--
-- anon: the whole reason the intake panel was broken is that it read
-- intake_submissions through the anon key and got 42501, then swallowed it.
-- The fix is to route the panel through api/sd-data.js on the service role --
-- NOT to grant anon a read. The publishable key is public by design, so an
-- anon SELECT here would make every customer's kitchen photo world-readable.
grant select, insert, update on public.sd_quote_request_photos to service_role;
