-- sql/sairndesign_qa_test_cleanup.sql
-- Removes two leftover QA click-through test rows found live on SDN-PINNACLE-2026
-- (2026-08-19) while investigating a separate sync-test cleanup task -- these are
-- NOT the rows sql/sairndesign_synctest_cleanup.sql already covers (different ids,
-- different origin: a manual QA client/vendor entry from 2026-08-08, not the
-- write-then-read round-trip verification test). That script's own target rows
-- were confirmed already absent before this file was written.
--
-- Confirmed live via:
--   curl -s -X POST https://sairn.vercel.app/api/sd-data \
--     -H 'Content-Type: application/json' -H 'Authorization: Bearer SDN-PINNACLE-2026' \
--     -d '{"action":"read","resource":"sdn_clients"}'
--   -> {"ok":true,"data":[{"id":"CL-1786203853037-53","name":"QA Test Client",...}],...}
--   (same call against sdn_vendors returned "id":"VN-1786203842089-145","name":"QA Test Fabrics")
--
-- No delete action exists in api/sd-data.js for sdn_* resources (checked -- only
-- SAIRNcode's sc_* resources have one), so this can't be run through the app's own
-- API; needs a direct Supabase SQL run, same as every other one-off cleanup script
-- in this directory.
--
-- Safe to run once; matches on the exact client_id/vendor_id only, nothing else
-- in either table is touched.

delete from public.sdn_clients where client_id = 'CL-1786203853037-53';
delete from public.sdn_vendors where vendor_id = 'VN-1786203842089-145';

-- Verify after running (expect 0 rows each):
--   select count(*) from public.sdn_clients where client_id = 'CL-1786203853037-53';
--   select count(*) from public.sdn_vendors where vendor_id = 'VN-1786203842089-145';
