-- sql/sairnsenior_verify_cleanup_2026-08-25.sql
-- Scoped cleanup for the SAIRNsenior end-to-end verification run on
-- 2026-08-25/26. NOT RUN by this session (no DB access). Every row below was
-- created by that run and nothing else; each is targeted by exact id, never by
-- license_hash alone.
--
-- WHY THIS FILE HAS TO EXIST: none of the six SAIRNsenior tables has a delete
-- path through the API. sd-data.js's sen_clients / sen_caregivers / sen_visits
-- / sen_claims branches handle read and write only, sen-portal.js revokes a
-- link by PATCHing active=false rather than deleting the row, and every
-- schema file grants `select, insert, update` with no delete
-- (sql/sairnsenior_*_schema.sql). That is the correct design for
-- care-record data -- it is also why verification debris here can only be
-- removed as owner, in the SQL editor. Same 14-cleanup-files-across-10-apps
-- pattern docs/SAIRN-OPEN-WORK-INDEX.md already tracks.
--
-- ALL DATA BELOW IS SYNTHETIC. The client rows are shaped like PHI because
-- the gates being tested are HIPAA minimum-necessary gates, but every value
-- was invented for the test: names are literally "SYNTHETIC TEST CLIENT A/B",
-- the diagnosis field says "SYNTHETIC - not real PHI", addresses are
-- "1 Test Way" / "2 Test Way". No real person's information was written.
--
-- license_hash below is sha256('SEN-PINNACLE-2026'), derived the same way as
-- every other seed in this directory and validated by the fact that all 30
-- checks in the run authenticated against it successfully.
--
-- ── WHAT WAS VERIFIED, so the value of this run is not lost with the rows ──
-- 30/30 checks passed against production. First time SAIRNsenior has been
-- exercised end to end since its 2026-08-20 build:
--   bootstrap -> first owner created; login round-trip for owner + 2 caregivers
--   owner wrote 2 clients, 1 caregiver record, scheduled 2 visits
--   caregiver A clocked in and out on their OWN visit; EVV write preserved the
--     scheduling fields untouched
--   assignment gates, all refused correctly:
--     caregiver A sees only client A / visit A; caregiver B only client B
--     403 on EVV against B's visit, on write to B's client, on creating a
--         visit, on reassigning their own client, on reading claims
--     owner (scheduler tier) CANNOT forge an EVV clock-in -- the field is
--         dropped, not merged, which is the stronger of the two possible
--         behaviours and the one the code comments claim
--   portal links: created, public view works with NO licence and NO session,
--     returns only client_name + visit times (no diagnosis, address or GPS --
--     minimum-necessary holds on the public leg too), bogus token 404s, and a
--     revoked token stops working immediately

-- ── 1. billing ───────────────────────────────────────────────────────────
delete from public.sen_claims
 where license_hash = '75bdc179a257a6688febcd88df11ab0efed12542eea6a8db29a3053ee817ac8f'
   and claim_id = 'SENV-CLAIM-A';

-- ── 2. portal link (revoked during the run; the ROW still exists) ─────────
delete from public.sen_portal_links
 where license_hash = '75bdc179a257a6688febcd88df11ab0efed12542eea6a8db29a3053ee817ac8f'
   and id = 'f8f4fa91-87d4-4d57-9a76-2a07094c4553';

-- ── 3. visits (carry the EVV clock-in/out records) ───────────────────────
delete from public.sen_visits
 where license_hash = '75bdc179a257a6688febcd88df11ab0efed12542eea6a8db29a3053ee817ac8f'
   and visit_id in ('SENV-VISIT-A', 'SENV-VISIT-B');

-- ── 4. caregiver employment record ───────────────────────────────────────
delete from public.sen_caregivers
 where license_hash = '75bdc179a257a6688febcd88df11ab0efed12542eea6a8db29a3053ee817ac8f'
   and caregiver_id = 'SENV-CG-A';

-- ── 5. clients (delete AFTER visits/claims, which reference them) ────────
delete from public.sen_clients
 where license_hash = '75bdc179a257a6688febcd88df11ab0efed12542eea6a8db29a3053ee817ac8f'
   and client_id in ('SENV-CLIENT-A', 'SENV-CLIENT-B');

-- ── 6. the three credentials ─────────────────────────────────────────────
-- RECOMMENDED, but read the note first -- this one is a judgment call, not
-- mechanical like the five above.
--
-- Removing ALL THREE re-arms action:bootstrap for this licence, because
-- bootstrap refuses only when the licence already has at least one row
-- (api/sen-auth.js:182). That is the right end state: SEN-PINNACLE-2026 is a
-- demo licence nobody has used yet, and the first REAL user should get to
-- create their own owner account rather than inherit a throwaway named
-- "sen-verify-owner" whose PIN is written in a public repo.
--
-- Keeping sen-verify-owner instead is defensible if you want the demo
-- immediately loggable-in -- but then change its PIN, because 604318 is in
-- this file, in sql/sairnsenior_license_seed.sql's sibling commit, and in the
-- session transcript.
delete from public.sairnsenior_employee_auth
 where license_hash = '75bdc179a257a6688febcd88df11ab0efed12542eea6a8db29a3053ee817ac8f'
   and employee_id in ('sen-verify-owner', 'sen-verify-cg-a', 'sen-verify-cg-b');

-- ── NOT deleted, deliberately ────────────────────────────────────────────
-- public.license_keys row 'SEN-PINNACLE-2026' STAYS. It is a real demo
-- licence in the same class as SB-PINNACLE-2026 / GRD-DEMO-2026 /
-- SCP-DEMO-2026, provisioned to close a genuine gap, not test debris.

-- ── Confirm afterwards (expect 0 from each) ──────────────────────────────
--   select count(*) from public.sen_claims        where claim_id = 'SENV-CLAIM-A';
--   select count(*) from public.sen_portal_links  where id = 'f8f4fa91-87d4-4d57-9a76-2a07094c4553';
--   select count(*) from public.sen_visits        where visit_id like 'SENV-%';
--   select count(*) from public.sen_caregivers    where caregiver_id like 'SENV-%';
--   select count(*) from public.sen_clients       where client_id like 'SENV-%';
--   select count(*) from public.sairnsenior_employee_auth where employee_id like 'sen-verify-%';
-- And confirm the licence survived (expect 1):
--   select count(*) from public.license_keys where key = 'SEN-PINNACLE-2026';
