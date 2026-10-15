THE ONE LEGACY STEDI CIPHERTEXT -- THE EXACT STEP, AND IT IS NOT SQL
hank, batch b15, 2026-10-15.  Uploaded as SAIRN-backfill-stedi-step.txt.

WHERE THIS CAME FROM
Michael ran sql/legacy_ciphertext_census.sql against the live database:
  sc_credentials                        legacy_rows = 1   <- this file
  sairnlaw_employee_auth.mfa_secret...  clean
SD_AUTH_SECRET_PREVIOUS MUST NOT BE CLEARED until that row is v2. Step 4 of
sql/sd_encryption_key_revoke_2026-09-24.sql removes the only remaining route
to a legacy value, and the failure is SILENT: decryptSecret() returns null and
every caller reads null as "no secret stored" -- for Stedi, "eligibility is
not configured".

WHY THE ANSWER IS NOT SQL, AND THIS IS THE WHOLE POINT
The ciphertext cannot be re-encrypted in SQL. The key never leaves the Node
process: encryptSecret() in api/_lib/auth.js:874 derives AES-256-GCM from
sha256(SD_ENCRYPTION_KEY), and Postgres has neither the key nor the function.
An UPDATE that put anything into data->'stedi'->>'enc' would be putting a
value no reader can decrypt, which is worse than the legacy row -- it would
satisfy the census (no longer matching "not like 'v2.%'") while making the
credential permanently unreadable. THE CENSUS WOULD THEN REPORT ZERO AND
AUTHORISE CLEARING THE OLD KEY. Do not write SQL for this.

=========================================================================
THE STEP -- re-save the key through the app's own write path
=========================================================================
api/sc-credentials.js:200-205 is the only thing that writes this field, and it
calls encryptSecret() on every set. SD_ENCRYPTION_KEY is set in production
(created 2026-09-26), so dedicatedEncryptionKey() returns a key and the new
ciphertext is written with the v2. prefix. Re-saving the SAME key is therefore
a backfill, with no new code and no hand-edited ciphertext.

  0. BEFORE: note the fingerprint, so step 3 can prove you re-saved the same
     key and did not replace the credential.
       SAIRNcode -> sign in as a COMPLIANCE ADMIN -> the eligibility panel.
     The connection block there renders api/sc-credentials.js's `status`
     action, which returns last4 and updated_at -- never the value and never
     the ciphertext, for any role. WRITE DOWN last4 AND updated_at.

  1. Have the Stedi API key itself to hand. It is NOT readable from the app
     (by design, and that is not a gap -- publicStatus() returns a last-4
     fingerprint precisely so an admin can identify a key without reading it).
     Get it from Stedi's own dashboard or wherever it is held.
     IF YOU CANNOT GET THE PLAINTEXT, STOP AND READ "IF THE KEY IS NOT TO
     HAND" BELOW. Do not improvise.

  2. Paste it into the Stedi API key field and press Save.
     That is saveStediKey() in sairncode.html, which posts
       { action: 'set', service: 'stedi', value: <the key> }
     to /api/sc-credentials. Admin-only, server-side.

  3. AFTER: re-read the same connection block.
       last4       MUST be identical to step 0. If it changed you have saved a
                   DIFFERENT key -- the credential is now wrong and eligibility
                   will fail. Paste the right one.
       updated_at  MUST have moved. If it has not, the write did not land and
                   the row is still legacy.

  4. Re-run PART 1 of sql/legacy_ciphertext_census.sql.
       EXPECTED: legacy_rows = 0 on BOTH rows of the grid, v2_rows = 1 on the
       sc_credentials row.
     ONLY THEN is step 4 of the revoke file (clearing
     SD_AUTH_SECRET_PREVIOUS) authorised.

  5. If PART 1 still shows legacy_rows = 1 after a successful save, STOP.
     That means encryptSecret() did not take the dedicated key -- i.e.
     SD_ENCRYPTION_KEY is not reaching the function in the environment that
     served the write. Clearing SD_AUTH_SECRET_PREVIOUS at that point would
     destroy the credential. This is also exactly what PART 3 of the census
     warns about, and the distinguishing test is the one it names: a fresh
     write that stays legacy means the key is not reaching the writer.

=========================================================================
WHAT THIS DOES NOT DO
=========================================================================
* It does not touch the MFA surface. The census found that clean.
* It does not read, log or move the plaintext anywhere. The app never returns
  it and this step does not ask it to.
* It is not idempotent in the sense of being free: each save rotates the IV
  and rewrites updated_at/updated_by. Running it twice is harmless; running it
  with the WRONG key is not, which is why step 3 compares the fingerprint.
* IT DOES NOT PROVE THE KEY STILL WORKS. last4 and a v2 prefix say the write
  landed, not that Stedi accepts the key. If eligibility was working before
  this and fails after, the key you pasted is wrong -- that is what step 3 is
  for, and it is cheaper to catch there.

=========================================================================
IF THE KEY IS NOT TO HAND -- A DECISION, NOT A WORKAROUND
=========================================================================
The legacy ciphertext is still READABLE today: legacyDecryptionKeys() tries
sha256(SD_AUTH_SECRET) and SD_AUTH_SECRET_PREVIOUS, which is the only reason
eligibility works at all right now. So a server-side re-wrap is possible in
principle -- read the row, decryptSecret(), encryptSecret(), write it back,
reusing the same two functions and the same upsert.

THAT IS NEW CODE AND IT IS NOT IN THIS BATCH. It needs: an admin-only one-shot
action, a refusal if decryptSecret() returns null (otherwise it would write the
ciphertext of an empty string and the census would go green over a destroyed
credential), an audit row, and an independent review because it is a path that
handles a decrypted secret. A one-line "while I was in there" version of this
is precisely how a silent failure gets shipped.

ROUTED AS A DECISION: if the plaintext is not retrievable, say so and it gets
built properly in a batch of its own. Until then the window stays open and
SD_AUTH_SECRET_PREVIOUS stays set, which costs nothing except that the
rotation is unfinished.

VERIFIED WHILE WRITING THIS, not remembered:
  api/_lib/auth.js:823        const ENC_V2 = 'v2'
  api/_lib/auth.js:825-831    dedicatedEncryptionKey() reads SD_ENCRYPTION_KEY
  api/_lib/auth.js:874-883    encryptSecret() prefixes v2. only when it has one
  api/sc-credentials.js:200-205  the only writer of data->'<service>'->>'enc'
  api/sc-credentials.js:70-82    publicStatus() returns last4, never the value
  sairncode.html:6068            saveStediKey() posts action:'set' service:'stedi'
