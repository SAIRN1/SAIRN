-- sql/sd_progress_photos_qc_schema.sql
-- Adds QC-gate columns to sd_progress_photos -- StoneDesk hard-gate process
-- checklist, Phase 1 concrete example (task completion requires a QC'd
-- finished-product photo).
--
-- Run this AFTER sql/sd_progress_photos_schema.sql. Written as an additive
-- migration (add column if not exists) rather than editing that file in
-- place, specifically because that file may already have been run by the
-- time this one exists -- running both in sequence is safe either way,
-- idempotent regardless of order-of-operations on Michael's side.
--
-- is_final marks a photo as THE finished-product photo for a job (as
-- opposed to a general mid-work progress photo) -- this is what the
-- completion gate actually checks for.
--
-- qc_status is never settable by the person who uploaded the photo --
-- api/sd-sub-data.js's write branch forces it to 'pending' server-side
-- whenever is_final=true, regardless of what the client sends. Only the
-- separate 'qc-review' action (owner/admin, and never the original
-- uploader -- enforced server-side) can move it to 'approved'/'rejected'.
-- This is the actual "reviewed by someone else, not self-certification"
-- enforcement point.

alter table public.sd_progress_photos
  add column if not exists is_final       boolean not null default false,
  add column if not exists qc_status      text not null default 'pending' check (qc_status in ('pending','approved','rejected')),
  add column if not exists qc_reviewer_id text,
  add column if not exists qc_notes       text,
  add column if not exists qc_reviewed_at timestamptz;

create index if not exists idx_sdprogphoto_qc_gate
  on public.sd_progress_photos(license_hash, job_id, is_final, qc_status);
