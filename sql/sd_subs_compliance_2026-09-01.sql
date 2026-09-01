-- sql/sd_subs_compliance_2026-09-01.sql
--
-- Adds the subcontractor COMPLIANCE LAYER to StoneDesk's sub roster.
--
-- WHY. `docs/superpowers/specs/2026-08-27-sairnmechanical-shared-platform-competitive-research.md`
-- §5 Row 1 is the one StoneDesk finding in that worldwide competitive pass:
-- the entire sd_subs payload was `sub_id, name, phone, email, trade, active`
-- and a grep of the whole app for insurance / COI / W-9 / licence / expiry on
-- the subcontractor record returned nothing. Re-verified against sd_subs and
-- api/sd-sub-data.js on 2026-09-01 before writing this, not taken on trust from
-- the 08-27 doc: the columns were still absent.
--
-- Real-time expiry monitoring and renewal alerts are table stakes in a mature
-- category (Certificial, MyCOI, TrustLayer, Jones, Billy, SmartCompliance,
-- CertFocus, BCS, Constrafor). The honest nuance recorded in that doc still
-- holds: this is a category-wide gap among FIELD-SERVICE products, and
-- StoneDesk is behind the CONSTRUCTION field, which is where its subs come
-- from.
--
-- THE REFERENCE IMPLEMENTATION IS SAIRNbuild, IN THIS SAME REPO. Its sub
-- records already carry w9_on_file / coi_expiry / licence_no / licence_expiry
-- and, crucially, it ENFORCES: award is hard-blocked for a non-compliant sub.
-- Tracking without a gate is a report nobody reads, so the gate here lives in
-- api/sd-sub-data.js's jobs-write path, not only in the UI.
--
-- ── SHAPE ──────────────────────────────────────────────────────────────────
-- Six nullable columns plus one defaulted boolean. Nullable on purpose: an
-- existing roster must not become "non-compliant" the moment this runs, or the
-- gate blocks every assignment on every shop the day it deploys. NULL means
-- NOT TRACKED and is reported as exactly that -- never as "compliant". The
-- API and the UI both distinguish the three states (tracked-and-valid,
-- tracked-and-expired, not-tracked); collapsing not-tracked into compliant is
-- the silent-failure shape this platform keeps getting bitten by.
--
-- DATE, not timestamptz: a certificate expires on a calendar day in the
-- issuer's jurisdiction, and storing an instant would invent a timezone the
-- source document does not have.
--
-- No CHECK constraint on the dates, deliberately, for the same reason
-- sd_sub_portal_schema.sql declines a size CHECK: the ONE enforced rule lives
-- at the API layer, and a second copy here would have to stay in lockstep with
-- it forever.
--
-- ── RUNNING IT ─────────────────────────────────────────────────────────────
-- Run once in the Supabase SQL editor, same project as
-- sql/sd_sub_portal_schema.sql. Idempotent -- every statement is
-- `add column if not exists`, so re-running is a no-op rather than an error.
--
-- UNTIL IT RUNS, the app does not silently degrade: api/sd-sub-data.js's
-- roster read falls back to the base column list on a PostgREST 400 and
-- returns `compliance_provisioned: false`, and the panel shows a banner saying
-- compliance is not provisioned. It does NOT show a roster of green ticks.

alter table public.sd_subs
  add column if not exists coi_carrier     text,
  add column if not exists coi_policy_no   text,
  add column if not exists coi_expiry      date,
  add column if not exists licence_no      text,
  add column if not exists licence_expiry  date,
  add column if not exists w9_on_file      boolean not null default false;

-- Expiry is the only thing ever filtered on, and only within one licence.
create index if not exists idx_sd_subs_coi_expiry
  on public.sd_subs (license_hash, coi_expiry);
create index if not exists idx_sd_subs_licence_expiry
  on public.sd_subs (license_hash, licence_expiry);

-- Unchanged from sd_sub_portal_schema.sql -- restated because a reader of this
-- file alone should not have to go looking for whether the new columns are
-- reachable. No new grant is needed; the table-level grant already covers them.
-- grant select, insert, update on public.sd_subs to service_role;

-- ── VERIFY ─────────────────────────────────────────────────────────────────
-- Expect six rows.
select column_name, data_type, is_nullable, column_default
  from information_schema.columns
 where table_schema = 'public'
   and table_name   = 'sd_subs'
   and column_name in ('coi_carrier','coi_policy_no','coi_expiry',
                       'licence_no','licence_expiry','w9_on_file')
 order by column_name;
