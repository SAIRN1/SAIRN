-- sql/sairnroofing_employee_auth_certifications_migration.sql
-- Adds a certifications column to the EXISTING sairnroofing_employee_auth
-- table (sql/sairnroofing_employee_auth_schema.sql, already live -- this is
-- an ALTER, not a fresh CREATE).
--
-- Phase 2, Tesla Solar Roof capability gate. Per the scope doc (sec.3):
-- Tesla Solar Roof is "installable only by Tesla Energy crews or Tesla
-- Certified Installers -- a capability gate, not merely a price line."
-- Deliberately narrow for now: only tesla_certified is read or written by
-- any code path today. The column is a small jsonb bag rather than a
-- dedicated boolean column so a later manufacturer credential (GAF Master
-- Elite, Owens Corning Platinum Preferred, CertainTeed SELECT -- all
-- COMPANY-level programmes per the scope doc, not per-employee, and
-- unbuilt Phase 4 work) can be added as another key without another
-- migration -- not because those are being built now.
--
-- Owner-only to set (api/rf-auth.js's new set_certifications action,
-- gated the same as set_active). Read by api/sd-data.js's rf_jobs write
-- gate to enforce the Tesla capability check.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

alter table public.sairnroofing_employee_auth
  add column if not exists certifications jsonb not null default '{}'::jsonb;
