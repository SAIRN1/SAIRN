-- sql/stonedesk_verify_admin_seed.sql
-- One disposable StoneDesk sign-in credential, for live verification only.
-- 2026-08-28. NOT RUN by the session that wrote this file (no DB access).
--
-- ── WHY THIS EXISTS ──────────────────────────────────────────────────────
-- The Revoke Sign-In Access panel shipped 2026-08-28 and could not be
-- live-verified, because ALL THREE StoneDesk licences answer `bootstrap` with
-- 409 ALREADY_PROVISIONED and NO PIN for any of them is recorded anywhere in
-- this repository. Verified by probe, not assumed:
--
--     SD-PINNACLE-2026   409   SD-AUDIT-2026   409   SD-PARTNER-2026   409
--
-- That is precisely the state api/sd-auth.js:304-308 records as how three
-- StoneDesk licences were lost: "SD-PINNACLE-2026's PIN is still undocumented,
-- SD-AUDIT-2026 needed a hand-written DELETE run directly in Supabase, and
-- SD-PARTNER-2026 was provisioned purely to route around both." The app that
-- lost three licences to untracked credential state is the same one that could
-- not be verified tonight for exactly that reason.
--
-- ── WHY SD-PINNACLE-2026 ─────────────────────────────────────────────────
-- Chosen deliberately, not by default. It is StoneDesk's primary demo licence
-- and the one every other StoneDesk verification file references. The other two
-- are worse choices for specific reasons: SD-AUDIT-2026 exists because its
-- credential had to be deleted by hand once already
-- (stonedesk_audit_license_credential_reset.sql documents that incident), and
-- SD-PARTNER-2026 was created solely as a workaround for the other two — adding
-- a fourth credential to a licence that is itself a workaround compounds the
-- problem this file is trying to end.
--
-- ── LICENSE_HASH DERIVATION, VALIDATED NOT TRUSTED ───────────────────────
-- license_hash is sha256(license_key) hex per api/_lib/license.js:38-40, which
-- applies no trim or case normalisation — the raw string is hashed.
--
-- The derivation was VALIDATED against a known-good production value before
-- being used for a new licence: sha256('RF-PINNACLE-2026') reproduces
--   47540a2aeaa094a99cf6d7ecf3bed062568bc07b62f60fd15f7616f97d5ff32b
-- exactly — the hash already living in sairnroofing_verify_admin_seed.sql and
-- already proven to work against the live login endpoint. Same method, same
-- run, so the value below rests on a check rather than on confidence.
--
--   sha256('SD-PINNACLE-2026')
--     = 194a52b14a2f732335f538c7814acb7aca99bdcb015f283741d7ee86b4f36d77
--
-- ── THE CREDENTIAL ───────────────────────────────────────────────────────
--   employee_id : sd-verify-admin
--   role        : admin
--   PIN         : 74679792
--
-- The pin_hash/pin_salt below were produced by the app's OWN hashPin() from
-- api/_lib/auth.js (scrypt, 64-byte, per-credential random salt), so this row
-- is indistinguishable from one the API created and needs no code change to be
-- accepted. The PIN is written here on purpose — the account is useless
-- otherwise — which is also the reason the cleanup exists and should be run
-- promptly. A PIN in a public repo is a reason to DELETE the account, never to
-- keep it.
--
-- ── ROLE: admin, NOT owner. DELIBERATE. ──────────────────────────────────
-- StoneDesk is the only app with TWO provisioning roles —
-- PROVISIONING_ROLES = ['owner','admin'] (api/sd-auth.js) — so an `admin` can
-- exercise roster and set_active fully, which is all the verification needs.
-- It CANNOT mint an Owner: api/sd-auth.js:243-247 refuses that specifically
-- ("Only an existing Owner can grant Owner access"). Seeding the lower of the
-- two capable roles keeps the blast radius smaller at zero cost to the test.
--
-- ── SCOPED SO NOTHING EXISTING IS TOUCHED ────────────────────────────────
-- The unique key is (license_hash, employee_id) and 'sd-verify-admin' is a NEW
-- id — confirmed absent from every StoneDesk SQL file in this repo. Whatever
-- credentials already exist on SD-PINNACLE-2026 are untouched by an insert on a
-- different id, and the ON CONFLICT clause can only ever affect this one row.
--
-- Adding a SECOND provisioning-role account is also safe with respect to
-- set_active's last-admin refusal (api/sd-auth.js:384): that guard blocks
-- removing the last one, and this only ever adds. It in fact makes the licence
-- SAFER — see the Platform lockout row in docs/SAIRN-OPEN-WORK-INDEX.md, where
-- RF-PINNACLE-2026 was found with zero active owners and no API route back.

insert into public.sd_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values (
  '194a52b14a2f732335f538c7814acb7aca99bdcb015f283741d7ee86b4f36d77',
  'sd-verify-admin',
  'SD Verify Admin (disposable)',
  'admin',
  '2e0c67c3b5a8e1b6ee46749123a62d6cf8980a6c0cae6eb67fd50e3a6011c847f90ae907c1f1953fb374deca0ec9ea5ff6ee524f3e366a6466424864f465d6d1',
  '082b5d8fa073910eb20aeef9a5ea53b2',
  true
)
on conflict (license_hash, employee_id) do update
  set pin_hash = excluded.pin_hash,
      pin_salt = excluded.pin_salt,
      role     = excluded.role,
      active   = true;

-- ── CONFIRM IT LANDED ────────────────────────────────────────────────────
-- Expect exactly one row for this id, role = admin, active = t — AND every
-- pre-existing row on this licence still present and unchanged:
--   select employee_id, role, active
--     from public.sd_employee_auth
--    where license_hash = '194a52b14a2f732335f538c7814acb7aca99bdcb015f283741d7ee86b4f36d77'
--    order by employee_id;
--
-- Then confirm through the API, which is the real proof — a clean insert is not
-- evidence the app accepts it:
--   POST /api/sd-auth
--   {"action":"login","employee_id":"sd-verify-admin","pin":"74679792"}
--   with Authorization: Bearer SD-PINNACLE-2026. Expect 200 and role "admin".
--
-- ── TEARDOWN ─────────────────────────────────────────────────────────────
-- Run sql/stonedesk_access_panel_verify_cleanup_2026-08-28.sql when the
-- verification is done. DELETE the row, never deactivate it: StoneDesk needs at
-- least one active owner/admin, and deactivating your way to zero is the
-- lockout found live on another licence the same day.
