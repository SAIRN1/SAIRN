-- fourth b61 item 3: CONFIRM-ONLY. The live sweep drive re-sent one claim draft,
-- CLM-B61-LIVETEST, to sen_claims on SEN-AUDIT-2026. The API refused it with 413
-- PAYLOAD_TOO_LARGE before any store, so this must return 0. Nothing here deletes.
create extension if not exists pgcrypto;
select count(*) as must_be_zero
  from public.sen_claims
 where license_hash = encode(digest('SEN-AUDIT-2026', 'sha256'), 'hex')
   and claim_id = 'CLM-B61-LIVETEST';
