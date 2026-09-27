-- sql/legacy_ciphertext_census.sql
--
-- WHICH ROWS ARE STILL ENCRYPTED UNDER THE SIGNING SECRET.
-- Run in the Supabase SQL editor. READ ONLY -- every statement is a SELECT and
-- there is no write, no ALTER and no DELETE in this file.
--
-- ── THE SELECT NOBODY HAD RUN ───────────────────────────────────────────────
-- docs/2026-09-24-sd-encryption-key-revoke.md §3 lists two things it could not
-- settle. The first is measured now (SD_ENCRYPTION_KEY exists in Vercel,
-- production only, created 2026-09-26). The second is this file:
--
--   "Legacy ciphertexts. Anything written before the split decrypts with
--    sha256(SD_AUTH_SECRET), so rotating SD_ENCRYPTION_KEY does not revoke
--    them. ... WHICH ROWS ARE STILL LEGACY IS NOT MEASURED HERE and needs a
--    select nobody has run."
--
-- ── WHY THE ANSWER IS A PRECONDITION AND NOT A CURIOSITY ────────────────────
-- api/_lib/auth.js publishes a four-step SD_AUTH_SECRET rotation. Steps 1-3 are
-- safe for legacy ciphertexts as of 2026-09-27 -- `legacyDecryptionKeys()` tries
-- SD_AUTH_SECRET_PREVIOUS the way `signingKeys()` already did. **STEP 4,
-- clearing SD_AUTH_SECRET_PREVIOUS, is the point of no return**: it removes the
-- only remaining route to a legacy value, and the failure is silent because
-- `decryptSecret()` returns null and every caller reads null as "no secret
-- stored" -- for MFA, "MFA is not set up".
--
-- So step 4 has a precondition the other three do not: **this census must return
-- ZERO legacy rows.** A count is the only thing that turns "probably backfilled"
-- into a fact, and the stored format carries a `v2.` prefix for exactly that.
--
-- ── THE DISCRIMINATOR IS THE FORMAT ITSELF, NOT A GUESS ────────────────────
--   legacy   iv.tag.ciphertext         -> sha256(SD_AUTH_SECRET)
--   v2       v2.iv.tag.ciphertext      -> sha256(SD_ENCRYPTION_KEY)
-- api/sc-eligibility.js already reads it the same way in production code:
-- `String(rec.enc || '').startsWith('v2.') ? 'v2' : 'legacy'`. One rule, two
-- places, and this file uses the one the app uses rather than a second spelling.
--
-- ── THE TWO SURFACES, read out of the code rather than remembered ──────────
--   sairnlaw_employee_auth.mfa_secret_encrypted  attorney TOTP secrets
--                                            (api/law-auth.js, loadEmployee)
--   sc_credentials.data->>'enc'              the Stedi API key
--                                            (api/sc-eligibility.js)
-- If a third surface is ever added, it belongs here -- and NOTHING ENFORCES
-- THAT, which is stated rather than hidden: this file is a hand-kept list of
-- encrypted columns and will go stale the day somebody adds one without reading
-- it. `grep -rn "encryptSecret(" api/` is the check.
--
-- ── AND THE FIRST DRAFT OF THIS FILE NAMED THE WRONG TABLE ─────────────────
-- It said `law_employee_auth`. The real table is `sairnlaw_employee_auth` --
-- api/law-auth.js:127, `const TABLE = 'sairnlaw_employee_auth'`. Caught by
-- `tools/sairn_sql_preflight.py` as UNDECLARED_TABLE before it reached anybody,
-- which is the argument for running the preflight on a file whose only
-- statements are SELECTs: a census against a table that does not exist answers
-- with an ERROR, and an operator reading an error at step 4a has no count --
-- which is indistinguishable from not having checked.
--
-- ── WHAT A NULL MEANS, AND WHY IT IS COUNTED SEPARATELY ────────────────────
-- A row with no ciphertext at all is not a legacy row. For MFA it means the
-- attorney has not enrolled. Folding "never set" into "legacy" would inflate the
-- number that gates step 4 and make the precondition impossible to satisfy,
-- which is how a safety check gets skipped.

-- ── 1. THE ONE NUMBER STEP 4 DEPENDS ON ────────────────────────────────────
-- Expect legacy_rows = 0 before clearing SD_AUTH_SECRET_PREVIOUS.
select
  'sairnlaw_employee_auth.mfa_secret_encrypted' as surface,
  count(*) filter (where mfa_secret_encrypted is not null
                     and mfa_secret_encrypted not like 'v2.%')        as legacy_rows,
  count(*) filter (where mfa_secret_encrypted like 'v2.%')            as v2_rows,
  count(*) filter (where mfa_secret_encrypted is null)                as never_set_rows,
  count(*)                                                            as total_rows
from public.sairnlaw_employee_auth
union all
select
  'sc_credentials.data->>enc' as surface,
  count(*) filter (where data->>'enc' is not null
                     and data->>'enc' not like 'v2.%')                as legacy_rows,
  count(*) filter (where data->>'enc' like 'v2.%')                    as v2_rows,
  count(*) filter (where data->>'enc' is null)                        as never_set_rows,
  count(*)                                                            as total_rows
from public.sc_credentials;

-- ── 2. WHICH LICENCES ARE AFFECTED, so a backfill can be scoped ────────────
-- No plaintext, no ciphertext, and no employee identity beyond the id the app
-- already uses as a key: a census does not need the secret to count it.
select license_hash, employee_id, 'legacy' as format
  from public.sairnlaw_employee_auth
 where mfa_secret_encrypted is not null
   and mfa_secret_encrypted not like 'v2.%'
 order by license_hash, employee_id;

select license_hash, credential_id, 'legacy' as format
  from public.sc_credentials
 where data->>'enc' is not null
   and data->>'enc' not like 'v2.%'
 order by license_hash, credential_id;

-- ── 3. AND THE ONE THAT WOULD MEAN THE SPLIT NEVER REACHED PRODUCTION ─────
-- If v2_rows is 0 across BOTH surfaces while SD_ENCRYPTION_KEY is set, then
-- either nothing has been written since the key landed -- plausible, it landed
-- 2026-09-26 -- or writes are not taking the dedicated key. The two are
-- distinguishable only by a fresh write, so this is a prompt to check rather
-- than a verdict:
select
  (select count(*) from public.sairnlaw_employee_auth where mfa_secret_encrypted like 'v2.%')
  + (select count(*) from public.sc_credentials where data->>'enc' like 'v2.%')
  as v2_rows_total;
-- v2_rows_total = 0 with the key set is NOT proof of a fault. Enrol one test MFA
-- secret and re-run part 1; if it is still 0, the key is not reaching the
-- function that writes.
