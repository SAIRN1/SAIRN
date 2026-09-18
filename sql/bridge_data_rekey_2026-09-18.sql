-- sql/bridge_data_rekey_2026-09-18.sql
-- Removes CUSTOMER LICENCE KEYS from public.bridge_data's primary key, and
-- renames the column so it stops lying about what it holds.
--
-- ── WHAT IS ACTUALLY SITTING THERE ──────────────────────────────────────
-- `bridge_data.shop_id` was written from `sdShopId()`, whose implementation is
-- `return sdLicenseKey()` -- so every row created before 2026-09-17 has a
-- CUSTOMER'S RAW LICENCE KEY as its primary key. A licence key is the bearer
-- credential every `/api/sd-data` call presents as `Authorization: Bearer`; the
-- NHI register states the rule for exactly this in its `tenant_key` comment:
-- "NEVER the raw licence key -- that is a bearer secret and must not sit in a
-- log table."
--
-- Found independently by two sessions on 2026-09-17, hank (who wrote the auth
-- fix and flagged the rows as "orphaned") and fourth (reviewing it, who
-- objected that "orphaned" understates a bearer secret in a primary key).
-- Neither could act on it: no clone holds database access. This is the action.
--
-- ── WHY IT IS NOT UNREACHABLE-THEREFORE-HARMLESS ────────────────────────
-- Nothing reads the table -- api/bridge.js:22 says so in terms, and the
-- `?action=pull` read path was deleted on 2026-09-17. That makes the rows
-- harmless to the PRODUCT and says nothing about the credential. A secret at
-- rest is exposed to every route that reaches the database, not to the routes
-- the application happens to offer: a `service_role` key, a `pg_dump`, a
-- support export, the backup this platform is currently trying to make work.
-- "Nothing reads it" is an argument about the app; the risk is about the row.
--
-- ── THE FIX IS A REKEY, NOT A DELETE, AND THAT IS A DELIBERATE CHOICE ───
-- Deleting the legacy rows would also remove the secret and would be simpler.
-- It is refused here for one reason: THERE IS NO WORKING BACKUP. The nightly
-- job exists and has failed on every run it has ever had, so an irreversible
-- delete is the one operation this platform currently cannot undo. Hashing the
-- key in place destroys the SECRET and keeps the ROW, which is the strictly
-- smaller action and reaches the same security end state.
--
-- THE HASH MATCHES api/_lib/license.js's `hashLicense` EXACTLY -- sha256 of the
-- key, hex, lower case:
--     crypto.createHash('sha256').update(key).digest('hex')
--     encode(digest(shop_id, 'sha256'), 'hex')
-- so a rekeyed legacy row lands on the SAME id the handler writes today. That
-- is not cosmetic: if a shop still has its old row and pushes again, the upsert
-- updates that row instead of creating a second one beside it.
--
-- ── DISCRIMINATING A KEY FROM A HASH, AND WHY IT IS SAFE ────────────────
-- A hashLicense output is exactly 64 lower-case hex characters. A SAIRN licence
-- key is not -- they are of the shape `SD-PINNACLE-2026`. So
-- `shop_id ~ '^[0-9a-f]{64}$'` identifies an already-hashed row and everything
-- else is legacy. RE-RUNNING THIS FILE IS A NO-OP: a row hashed by a previous
-- run matches the pattern and is skipped, so the hash is never applied twice.
--
-- ⚠ IF A LICENCE KEY WERE EVER 64 LOWER-CASE HEX CHARACTERS it would be
-- mistaken for a hash and left in place. Verify 1 below prints the shop_id
-- LENGTHS and a redacted prefix precisely so that case is visible rather than
-- assumed away; no key on this platform has that shape today, and the query
-- says so rather than the comment claiming it.
--
-- ── AND THE COLUMN NAME IS RENAMED, WHICH IS HALF THE DEFECT ───────────
-- After hank's fix the handler writes `shop_id = lic.license_hash`. The column
-- then holds a hash under a name that says it holds a shop id, and the next
-- reader has to read the handler to find out. Every other tenant-scoped table
-- on this platform names that column `license_hash`. Renaming it is what stops
-- this being rediscovered.
--
-- api/bridge.js MUST BE DEPLOYED WITH THIS FILE. It is a one-word change in the
-- insert body. Order does not matter for safety -- the endpoint's only write is
-- an upsert and a failed one loses a row nothing reads -- but a gap between
-- them is a window where the push 400s, so ship them together.

begin;

-- ── 1. THE SECRET, DESTROYED IN PLACE ──────────────────────────────────
-- pgcrypto is already relied on by sql/agent_schema.sql and three other files
-- on this deployment, so `digest` is available. `create extension if not
-- exists` is here anyway, because a migration that assumes an extension is a
-- migration that fails at 3am on a restored database.
create extension if not exists pgcrypto;

update public.bridge_data
   set shop_id = encode(digest(shop_id, 'sha256'), 'hex')
 where shop_id !~ '^[0-9a-f]{64}$';

-- ── 2. THE NAME ────────────────────────────────────────────────────────
-- Guarded so the file is re-runnable: a second run finds no `shop_id` column
-- and does nothing, rather than erroring out half way and leaving step 1
-- applied and step 2 not.
do $$
begin
  if exists (select 1 from information_schema.columns
              where table_schema = 'public' and table_name = 'bridge_data'
                and column_name = 'shop_id') then
    alter table public.bridge_data rename column shop_id to license_hash;
  end if;
end
$$;

comment on column public.bridge_data.license_hash is
  'sha256 hex of the customer licence key, matching api/_lib/license.js '
  'hashLicense(). NEVER the raw key -- that is a bearer secret. Rows written '
  'before 2026-09-17 held the raw key and were rehashed in place by '
  'sql/bridge_data_rekey_2026-09-18.sql.';

commit;

-- ── VERIFY, one query per statement with the answer it must give ────────

-- 1. NO ROW HOLDS ANYTHING BUT A 64-HEX HASH. Expect: not_hashed = 0.
--    `lengths` and `sample_prefix` are printed even on a pass, because the one
--    way this migration can be wrong is a licence key that happens to look like
--    a hash -- and a query that only prints a zero cannot show you that.
select count(*) filter (where license_hash !~ '^[0-9a-f]{64}$') as not_hashed,
       count(*)                                                 as rows_total,
       array_agg(distinct length(license_hash))                 as lengths,
       array_agg(distinct left(license_hash, 8))                as sample_prefix
  from public.bridge_data;

-- 2. THE COLUMN IS RENAMED AND THE OLD NAME IS GONE. Expect exactly one row:
--    license_hash. A result with BOTH names means step 2 did not run; a result
--    with neither means you are looking at the wrong table.
select column_name, data_type
  from information_schema.columns
 where table_schema = 'public' and table_name = 'bridge_data'
   and column_name in ('shop_id', 'license_hash');

-- 3. A REKEYED LEGACY ROW LANDS ON THE ID THE HANDLER WRITES TODAY.
--    Run this with a licence key you hold, in the SQL editor, and confirm the
--    two agree. Expect: matches = true when that shop has a row.
--    (Substitute the key; it is not committed here for the obvious reason.)
-- select encode(digest('<A-REAL-LICENCE-KEY>', 'sha256'), 'hex') = license_hash
--          as matches, updated_at
--   from public.bridge_data
--  where license_hash = encode(digest('<A-REAL-LICENCE-KEY>', 'sha256'), 'hex');

-- 4. THE GRANTS ARE UNCHANGED BY THIS FILE, and that is stated rather than
--    assumed: a rename does not alter privileges, and nothing here grants or
--    revokes. Expect the same rows as before the migration.
select grantee, privilege_type
  from information_schema.role_table_grants
 where table_schema = 'public' and table_name = 'bridge_data'
 order by grantee, privilege_type;

-- ── WHAT THIS FILE DOES NOT DO ─────────────────────────────────────────
--   * It does not add a foreign key to license_keys. bridge_data has no
--     tracked CREATE TABLE anywhere in sql/, so its real constraints are
--     unknown from this repo, and adding one blind could refuse a legitimate
--     row for a licence that has since been rotated.
--   * It does not enable RLS or narrow any grant. Both are real questions for
--     a table nothing reads, and both are separable from removing a secret --
--     bundling them would make this migration hard to reason about and harder
--     to roll back.
--   * It does not delete anything. See the header: no working backup exists.
