-- sql/sairncare_payer_rules_schema.sql
-- SAIRNcare Phase 1: payer/billing-routing engine -- two tables.
--
--   alf_payer_rules  -- VERSIONED billing rules as data, per state, per program.
--   alf_claim_routes -- the per-claim routing decisions the engine produced.
--
-- WHY THE RULES ARE VERSIONED DATA AND NOT CODE, with a real example rather
-- than a principle: Indiana published IHCP Bulletin BT2025173 on 2025-12-04
-- MANDATING monthly billing at >=28 days present and daily below that,
-- effective 2026-01-01, with the wrong method denied in BOTH directions --
-- and then on 2025-12-31, 27 days later and one day before it took effect,
-- published BT2025190 PAUSING that mandate "until further notice" and
-- stating FSSA "will work with stakeholders to implement a new billing
-- policy later in 2026." A hardcoded implementation would have shipped a
-- rule that was obsolete before its own effective date. Every rule here
-- therefore carries effective_from/effective_to and a real authority
-- citation, the same shape SAIRNlaw's deadline engine already uses on this
-- platform, so a claim for a past month computes against the rule that was
-- actually in force that month rather than today's rule.
--
-- WHAT IS DELIBERATELY *NOT* STORED HERE: dollar rates. Rates live on the
-- facility rate card (alf_facility), entered by the facility, exactly as
-- they already did before this phase. Three reasons, all real: (1) Ohio's
-- rates live in appendix A to OAC 5160-1-06.5, which is republished on its
-- own schedule and which could not be retrieved from any primary source
-- during this build -- seeding a number nobody verified is precisely the
-- fabricated-data pattern sairn-guardian-v2 Check 0b exists to catch;
-- (2) Ohio's community transition service is explicitly a per-job bid rate
-- "negotiated and approved by ODA's designee" (OAC 5160-33-07(C)), so there
-- is no single correct number to seed at all; (3) rates are provider- and
-- year-specific in every state surveyed. The rules encode WHICH CODE AND
-- MODIFIERS apply and WHAT CONSTRAINTS bind -- never how much money.
--
-- COVERAGE IS HONEST AND EXPLICIT: only OH and IN are seeded. MI and PA are
-- NOT covered -- no primary-source codes or modifiers could be located for
-- either during this build, and the engine refuses with an explicit
-- NO_RULE_FOR_STATE naming the state rather than silently falling back to
-- another state's rules or returning an empty success.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.alf_payer_rules (
  id             uuid primary key default gen_random_uuid(),
  license_hash   text not null,
  app_id         text not null default 'sairncare',
  rule_id        text not null,                  -- client/seed-supplied stable id
  state          text not null,                  -- 2-letter USPS, uppercase
  program        text not null,                  -- 'medicaid_hcbs' | 'hospice_ma'
  effective_from date not null,
  effective_to   date,                            -- null = still in force
  -- 'active'            -- a real rule, selectable when the service month falls in its window
  -- 'never_in_force'    -- published but repealed/paused before it ever governed a claim.
  --                        Retained deliberately (Indiana's BT2025173 is exactly this) so the
  --                        history stays legible, but the engine must never select it. Modeled
  --                        as an explicit status rather than an inverted date range, because an
  --                        inverted range is indistinguishable from a data-entry error and the
  --                        date CHECK below correctly rejects it.
  status         text not null default 'active',
  data           jsonb not null default '{}'::jsonb,
  verified_by    text,   -- server-stamped from the session. SEE NOTE BELOW.
  -- WHAT THIS ACTUALLY RECORDS, corrected 2026-08-29: the employee_id of
  -- whoever was SIGNED IN when the row was written. Not who verified the
  -- content. The two coincide only by accident -- the Ohio HSSA contingency
  -- rules were written by a disposable verification account and carry its id.
  -- THE REAL PROVENANCE IS data.authority (citation, url, quote, read_on),
  -- which is required and is what a customer would have to defend.
  -- Kept as `verified_by` rather than renamed to `loaded_by`: the rename is
  -- correct and is deferred, because it is a migration across six live tables
  -- plus every write path plus two tools that subtract this field BY NAME
  -- (api/reference-fingerprint.js, sql/platform_reference_rules_divergence_
  -- 2026-08-28.sql). See SAIRN-BACKLOG.md.
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (license_hash, rule_id),
  constraint alfpr_program_check check (program in ('medicaid_hcbs','hospice_ma')),
  constraint alfpr_status_check check (status in ('active','never_in_force')),
  constraint alfpr_state_len check (char_length(state) = 2),
  constraint alfpr_date_order check (effective_to is null or effective_to >= effective_from),
  constraint alfpr_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfpr_license on public.alf_payer_rules(license_hash);
create index if not exists idx_alfpr_lookup on public.alf_payer_rules(license_hash, state, program);

-- Append-only record of what the engine actually decided for a given claim.
-- Append-only because a routing decision is an assertion about how a real
-- claim was billed -- if the determination changes, that is a NEW decision
-- with its own timestamp, not an edit erasing what was previously believed
-- and acted on. Same reasoning as alf_mar's administration entries.
create table if not exists public.alf_claim_routes (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairncare',
  entry_id      text not null,                   -- client-generated (ROUTE-<timestamp>)
  resident_id   text not null,
  service_month text not null,                    -- YYYY-MM
  data          jsonb not null default '{}'::jsonb,
  decided_by    text,                             -- server-stamped from the real session
  created_at    timestamptz not null default now(),
  unique (license_hash, entry_id),
  constraint alfcr_month_fmt check (service_month ~ '^[0-9]{4}-[0-9]{2}$'),
  constraint alfcr_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_alfcr_license on public.alf_claim_routes(license_hash);
create index if not exists idx_alfcr_resident on public.alf_claim_routes(license_hash, resident_id);

grant select, insert, update on public.alf_payer_rules to service_role;
grant select, insert on public.alf_claim_routes to service_role;
revoke all on public.alf_payer_rules from anon, authenticated;
revoke all on public.alf_claim_routes from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from alf_payer_rules;
--   select count(*) from alf_claim_routes;
