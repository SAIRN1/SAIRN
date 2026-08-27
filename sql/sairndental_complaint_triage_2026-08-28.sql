-- sql/sairndental_complaint_triage_2026-08-28.sql
-- READ-ONLY. Reads one row so it can be classified. Deletes nothing.
--
-- WHY THIS IS SQL AND NOT A CURL. Both read paths to dnt_complaints are closed
-- to this session, and neither should be forced open:
--   * api/sd-data.js's dnt_complaints read is session-gated (:5775, dntGate) and
--     every SAIRNdental credential was deleted in the cleanup. Getting a session
--     means bootstrapping a new owner -- which is armed right now precisely
--     BECAUSE the licence is clean, and is the exact mistake this session
--     already made once tonight. Not doing it twice.
--   * api/sairndental/public-complaint-thread.js reads by `access_token`, which
--     only the complainant ever received. There is no legitimate way for me to
--     have one.
--
-- ── HANDLE THE OUTPUT AS PHI ─────────────────────────────────────────────
-- This row came in through the PUBLIC complaint form. It may be a real patient
-- writing about real care. The query below is deliberately shaped so the first
-- pass can classify it WITHOUT anyone pasting its contents anywhere: it returns
-- timestamps, status, presence-of-contact-details as booleans, message length,
-- and only a 120-character prefix.
--
-- If that prefix makes it obvious this is scanner or spam traffic, that is the
-- answer and nothing further needs reading.
-- If it looks like a real person with a real complaint, DO NOT paste the text
-- back into a chat transcript. Say only that it is real -- that is enough for me
-- to act on, and it keeps patient words out of a log that did not need them.

select
  complaint_id,
  created_at,
  updated_at,
  data->>'status'                                   as status,
  data->>'source'                                   as source,
  (data->>'patient_name'  is not null
     and data->>'patient_name'  <> '')              as has_name,
  (data->>'patient_email' is not null
     and data->>'patient_email' <> '')              as has_email,
  (data->>'patient_phone' is not null
     and data->>'patient_phone' <> '')              as has_phone,
  jsonb_array_length(coalesce(data->'messages', '[]'::jsonb)) as message_count,
  length(coalesce(data->>'message',
                  data->'messages'->0->>'body', ''))          as first_message_len,
  left(coalesce(data->>'message',
                data->'messages'->0->>'body', ''), 120)       as first_120_chars
from public.dnt_complaints
where license_hash = encode(digest('DNT-PINNACLE-2026', 'sha256'), 'hex')
order by created_at desc;

-- ── HOW TO CLASSIFY WHAT COMES BACK ─────────────────────────────────────
-- SCANNER / ABUSE, the likely case for an unauthenticated form on a public URL:
--   * first_120_chars contains markup, a payload, a URL, or template syntax
--     ({{, <script, ${, ../, ' or 1=1) -- probing, not complaining;
--   * has_name/has_email/has_phone all false, or filled with obvious junk;
--   * first_message_len at or near a boundary (0, 1, or exactly the 4000-char
--     MAX_MESSAGE_LEN) -- a person does not write exactly the maximum.
--   -> Note it, leave the row or delete it, and treat the real question as
--      whether a rate-limited public form is enough. It is currently 20 replies
--      per hour per IP on the reply path (public-complaint-thread.js) with the
--      submit path rate-limited separately.
--
-- A REAL COMPLAINT:
--   * plausible contact details present, prose that reads like a person.
--   -> This is not a cleanup item. Somebody has written to a dental practice
--      and nobody has read it. Flag it to Michael directly and leave it alone.
--
-- EITHER WAY, one thing is already established regardless of which it is: the
-- public complaint endpoint is live, reachable, and receiving unsolicited
-- traffic. That was not known before the provenance audit surfaced this row.
