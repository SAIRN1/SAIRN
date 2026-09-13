-- sql/sairndental_complaint_idempotency_2026-09-13.sql
-- Adds the submission key that makes api/sairndental/public-complaint-submit.js
-- idempotent on a retried public form submission.
--
-- ── WHY ─────────────────────────────────────────────────────────────────
-- A public form is retried by a double-click, by a browser resubmitting on a
-- slow response, and by a patient who saw no confirmation. Every one of those
-- filed a SECOND complaint carrying the same first message, so the practice had
-- two records of one grievance -- which reads as two unhappy patients and gets
-- two replies.
--
-- Found by tools/idempotency_check.py, which classifies every mutating write in
-- api/ by whether it can be retried and whether it checks a key against DURABLE
-- storage. 41 unguarded writes were triaged; this is one of the two genuinely
-- retryable CREATES.
--
-- ── WHAT THE KEY IS, AND WHAT IT IS NOT ─────────────────────────────────
-- sha256 of license_hash + NUL + patient_name + NUL + message. The BUSINESS
-- EVENT, the same choice api/ledger.js makes with source_kind + source_id --
-- NOT a caller-supplied header. A public form has no client code to send one,
-- and a key the caller invents is a key the caller can vary on a retry, which
-- is exactly the case this exists for.
--
-- NUL as the delimiter, not a space: a space occurs in names and messages, and
-- 'ab'+'c' would hash the same as 'a'+'bc'. A delimiter that cannot appear in
-- the input cannot collide.
--
-- ── NO UNIQUE CONSTRAINT, DELIBERATELY ──────────────────────────────────
-- The handler bounds duplicate detection to a TEN-MINUTE window: a patient who
-- writes the same sentence a week later has a NEW complaint and must not be
-- silently folded into the old one. A unique index on (license_hash,
-- submission_key) would refuse that second, legitimate complaint forever --
-- a data-loss bug wearing an integrity constraint's clothes. The window is the
-- rule; the index below exists only to make the lookup fast.
--
-- ADDITIVE AND IDEMPOTENT. `add column if not exists` and `create index if not
-- exists`, so re-running changes nothing. Existing rows get NULL, which the
-- handler's `submission_key=eq.<hash>` filter simply never matches -- so every
-- complaint filed before today is untouched and invisible to the new check,
-- which is correct: it was not a duplicate of anything.
--
-- NO GRANT LINE. The table already carries `select, insert, update` for
-- service_role and a column does not need its own. Adding one here would risk
-- restoring the `delete` that sql/unused_delete_grant_revoke_2026-08-24.sql
-- removed platform-wide, exactly as the warning in
-- sql/sairndental_complaints_schema.sql says.

alter table public.dnt_complaints
  add column if not exists submission_key text;

comment on column public.dnt_complaints.submission_key is
  'sha256(license_hash || NUL || patient_name || NUL || message). Retry key for '
  'the public submit endpoint, checked within a 10-minute window. NOT unique: '
  'the same message a week later is a new complaint.';

-- Partial index: only rows that HAVE a key are ever looked up by one, and every
-- row written before 2026-09-13 has NULL.
create index if not exists idx_dntcp_submission_key
  on public.dnt_complaints(license_hash, submission_key, updated_at)
  where submission_key is not null;

-- ── VERIFY: run this after, and read it rather than assuming the DDL took ──
-- Expect one row: submission_key | text | YES (nullable).
select column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public'
  and table_name = 'dnt_complaints'
  and column_name = 'submission_key';
