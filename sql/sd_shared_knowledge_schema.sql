-- sql/sd_shared_knowledge_schema.sql
-- StoneDesk Shared Company-Knowledge Layer -- Supabase schema
--
-- Run this once in the Supabase SQL editor (same project as the other
-- sd_*_schema.sql files) before api/sd-data.js's 'shared_knowledge'
-- resource will work. Until this runs, it returns a clear empty/not-
-- provisioned result rather than a generic 500.
--
-- WHY THIS EXISTS: "Claude should learn and grow with the company" (Michael,
-- 2026-08-04/05) -- clarified in conversation that the model itself doesn't
-- retrain from usage; what's real and buildable is leveling up the existing
-- per-browser "SAIRN REAL PERSONALIZATION AI" module (stonedesk.html,
-- localStorage keys sairn_learned_stonedesk / sairn_learned_global) from
-- per-device to shared-per-shop, scoped by license_hash instead of one
-- browser's localStorage.
--
-- SCOPE, DELIBERATELY NARROWER THAN THE EXISTING PER-BROWSER MODULE: the
-- old module also tracks per-person communication style (expertSignals/
-- beginnerSignals word-matching, simple/medium/complex question-length
-- buckets, bullets/examples/numbers click-through counts, session counts,
-- and a cross-app "which other SAIRN products has this browser used" list).
-- NONE of that carries forward into this shared table -- aggregating one
-- specific person's phrasing/skill signals across "whoever happens to be
-- logged in on whatever device" doesn't produce a meaningful "company"
-- trait, and the cross-app usage list is specifically about one device's
-- browsing habits across products, not shop knowledge. Per the explicit
-- constraint ("NOT device/activity monitoring... no tracking what
-- individual employees are doing"), only aggregate TOPIC/TERM frequency
-- carries forward here -- word-frequency counts, never verbatim message
-- text, never tied to which employee or device asked.
--
-- "Recurring customer patterns" (the third thing asked for) is NOT stored
-- in this table at all -- it's computed live, on each context build, directly
-- from the real sdCustomers/sdJobs data already in the app (most common
-- project type, most common material, stage distribution). That's more
-- accurate than trying to persist a scraped/aggregated version of it, adds
-- zero extra storage, and avoids ever aggregating anything resembling
-- customer PII from chat text.
--
-- One row per license_hash (not per employee, not per device -- that's the
-- whole point of this table). data.topics is a word -> count map, pruned to
-- the top ~150 entries server-side on every write so the row can't grow
-- unbounded over the life of a shop's account.
--
-- Design note: no RLS policy defined, on purpose -- same reasoning as every
-- other StoneDesk-owned table: read/write exclusively via api/sd-data.js
-- using SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS regardless.

create table if not exists sd_shared_knowledge (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null unique,
  data jsonb not null default '{}'::jsonb,  -- {topics:{word:count}, totalQuestions:N}
  updated_at timestamptz not null default now()
);
create index if not exists idx_sd_shared_knowledge_license on sd_shared_knowledge (license_hash);
grant select, insert, update on public.sd_shared_knowledge to service_role;
