-- sql/sairnbuild_tna_schema.sql
-- SAIRNbuild Training Needs Assessment -- Supabase schema
--
-- WHY THIS EXISTS: employee training-needs tool, built on the Hennessy-
-- Hicks Training Needs Analysis (TNA) methodology -- a WHO-endorsed, free,
-- validated importance/performance-gap instrument (30 items, dual 7-point
-- rating scales: how important is this to the job, how well is it
-- currently performed; the gap between the two = the training need).
-- Structure verified via live web research (WHO/Birmingham eprints
-- toolkit + academic sources) before building -- NOT reconstructed from
-- memory alone. The verbatim original 30 healthcare item texts could not
-- be retrieved (5 source PDFs attempted, all failed to extract readable
-- text) -- the item BANK shipped in sairnbuild.html is therefore original
-- wording, adapted for construction operations, built on the verified
-- real domain structure and scale methodology, not a reproduction of the
-- original healthcare item set. The instrument's own documented
-- customization rules explicitly permit up to 8 of 30 items replaced plus
-- up to 10 additional items "in accordance with basic principles of
-- questionnaire design" -- this build goes further than that (all 30
-- reworded for a non-healthcare industry) precisely because the original
-- wording was never actually obtained, so calling it verbatim would be a
-- false provenance claim. Labelled "Hennessy-Hicks-style" throughout the
-- app copy for exactly this reason -- never claimed as the literal
-- original instrument.
--
-- Two-perspective structure (Michael's spec, 2026-08-20): the employee
-- rates themselves ('self' perspective, soft/positive-reinforcement
-- framing) and, separately, their manager rates them ('management'
-- perspective, analytical framing) -- same 30 items, same dual scale,
-- two independent raters. This is a real, common extension of the base
-- single-rater instrument (triangulating self-perception against a
-- supervisor's observation), not part of the original WHO methodology
-- itself.
--
-- Deliberately NOT a personality or cognitive-ability test, and the
-- optional DISC-style module (disc_responses/disc_profile below) is a
-- generic, non-branded communication/work-style questionnaire, not a
-- licensed commercial DISC product (those are trademarked -- see
-- sairnbuild.html's own DISC section header for the same disclosure).
-- Framing throughout stays "training and communication style," never
-- clinical or diagnostic language, specifically to avoid the tool being
-- read as an ADA-covered medical inquiry. This is a design/framing
-- choice, not a legal opinion -- Michael should have real employment
-- counsel review the live copy before this is used for actual personnel
-- decisions.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.bld_tna_assessments (
  id           uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id       text not null default 'sairnbuild',
  subject_employee_id   text not null,             -- who this assessment is ABOUT
  perspective            text not null check (perspective in ('self','management')),
  assessor_employee_id   text not null,             -- who filled it out (== subject for 'self')
  responses    jsonb not null default '{}'::jsonb,  -- { "item_1": {"importance":1-7,"performance":1-7}, ... }
  disc_responses jsonb,                             -- optional, self-perspective only -- { "d1":1-5, ... }
  disc_profile   jsonb,                             -- computed { "D":n,"I":n,"S":n,"C":n,"primary":"D","secondary":"I" }
  submitted_at timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (license_hash, subject_employee_id, perspective),
  constraint bldtna_data_size check (
    octet_length(responses::text) <= 65536
    and octet_length(coalesce(disc_responses::text,'')) <= 16384
    and octet_length(coalesce(disc_profile::text,'')) <= 4096
  )
);

create index if not exists idx_bldtna_license on public.bld_tna_assessments(license_hash);
create index if not exists idx_bldtna_subject on public.bld_tna_assessments(license_hash, subject_employee_id);

-- ---------------------------------------------------------------------------
-- GRANTS -- explicit up front, same reasoning as every other data table's
-- own header this session.
grant select, insert, update on public.bld_tna_assessments to service_role;
revoke all on public.bld_tna_assessments from anon, authenticated;
