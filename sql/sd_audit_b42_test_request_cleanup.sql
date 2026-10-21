-- sql/sd_audit_b42_test_request_cleanup.sql
--
-- PERMANENTLY removes the test data hank b42 created on the dedicated test
-- licence SD-AUDIT-2026 (not a customer licence), on Michael's instruction
-- (2026-10-21): one quote request, its one photo, and the unpublished test
-- shop row that the public form needed.
--
-- The request was already SOFT-deleted through the app (hank b43): hidden from
-- the inbox, listed in tombstones. Soft delete keeps the row and does not touch
-- sd_quote_request_photos, so this file is what actually removes them.
--
-- license_hash = sha256('SD-AUDIT-2026'), the same hashLicense() the API uses:
--   python -c "import hashlib;print(hashlib.sha256(b'SD-AUDIT-2026').hexdigest())"
--
-- Every statement is scoped to that licence AND the exact test identifier, so
-- it cannot touch another row. Run the BEFORE counts first; expected 1 / 1 / 1.

-- BEFORE
select 'photos'   as what, count(*) from public.sd_quote_request_photos
 where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea'
   and request_id   = 'QR-1792602627030-534'
union all
select 'request',  count(*) from public.sd_quote_requests
 where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea'
   and request_id   = 'QR-1792602627030-534'
union all
select 'shop',     count(*) from public.sd_public_shop
 where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea'
   and shop_slug    = 'sd-audit-b42-test'
   and published    = false;

delete from public.sd_quote_request_photos
 where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea'
   and request_id   = 'QR-1792602627030-534';

delete from public.sd_quote_requests
 where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea'
   and request_id   = 'QR-1792602627030-534';

delete from public.sd_public_shop
 where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea'
   and shop_slug    = 'sd-audit-b42-test'
   and published    = false;

-- AFTER -- expected 0 / 0 / 0. Send these three counts back; "it ran" is not
-- a result.
select 'photos'   as what, count(*) from public.sd_quote_request_photos
 where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea'
   and request_id   = 'QR-1792602627030-534'
union all
select 'request',  count(*) from public.sd_quote_requests
 where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea'
   and request_id   = 'QR-1792602627030-534'
union all
select 'shop',     count(*) from public.sd_public_shop
 where license_hash = '8f1610119858d53f7deee8f975adf501b0ed1ee6dd57c674399743da7d6b76ea'
   and shop_slug    = 'sd-audit-b42-test';
