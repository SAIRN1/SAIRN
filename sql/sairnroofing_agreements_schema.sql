-- sql/sairnroofing_agreements_schema.sql
-- SAIRNroofing Phase 5 (final piece) -- the contingency agreement as a tracked
-- document with a signature state, plus the per-state rescission rules.
--
--   rf_contingency_rules  -- VERSIONED per-state rescission requirements as
--                            data, each carrying a required authority citation.
--                            Same shape and same reasoning as rf_cert_rules.
--   rf_claim_agreements   -- APPEND-ONLY signed-document record. An executed
--                            agreement and a later rescission are two ROWS, not
--                            one row edited twice.
--
-- ── THIS CORRECTS sql/sairnroofing_claims_schema.sql ─────────────────────
-- That file's comment on rf_claims.data reads "...waiting_on_carrier flag,
-- contingency sig", i.e. it anticipated the signature living inside the mutable
-- claim blob. That was the wrong call and this file supersedes it, for three
-- reasons that were already written down in that same file:
--   1. rf_claims is an UPSERT. An executed agreement is evidence, and that file
--      already argues, about rf_claim_photos, that "evidence that can be edited
--      after the fact is not evidence." The argument applies here verbatim.
--   2. rfclm_data_size caps rf_claims.data at 64KB. A captured signature is an
--      image; rf_claim_photos went to 1.5MB for exactly this reason.
--   3. Rescission needs a second, later record. A single mutable field cannot
--      hold "signed, then cancelled, and here is when each happened."
-- The comment in the 3b file is corrected in the same commit as this file, so
-- the two do not disagree on disk.
--
-- ── GRANTS: THE SOUND IDIOM ──────────────────────────────────────────────
-- REVOKE ALL from service_role FIRST, then grant exactly what is needed.
-- `grant select, insert` alone is NOT sufficient -- postgres's default ACL
-- confers TRUNCATE/REFERENCES/TRIGGER/MAINTAIN on every new table and GRANT
-- cannot subtract. See sql/append_only_grant_audit.sql. rf_contingency_rules
-- gets UPDATE (a rule is superseded in place, like rf_cert_rules);
-- rf_claim_agreements does NOT.
--
-- ── WHY THE RULE IS DATA AND NOT A CONSTANT ──────────────────────────────
-- Four jurisdictions were read directly before this table existed and they
-- disagree on the trigger event, the unit, the count, and the conditions:
--   OH  R.C. 1345.21-.28   3 business days from the transaction, ONLY for a
--                          sale solicited away from the seller's fixed place of
--                          business, and the right runs INDEFINITELY if the
--                          seller failed to give the notice plus the separate
--                          detachable cancellation form (R.C. 1345.23).
--   CO  C.R.S. 6-22-104    72 hours after the insurer's WRITTEN DENIAL. Does
--                          not extend to supplemental services whose damage
--                          could not reasonably have been foreseen at the
--                          initial inspection -- i.e. this app's `asserted`
--                          hidden-damage supplement class.
--   FL  Fla. Stat. 489.147 10 days after EXECUTION for contracts arising from a
--                          declared state of emergency; omitting the
--                          prohibited-practices notice lets the owner void.
--   TX  Bus.&Com. 27.02    no rescission right in that section at all; what it
--                          mandates is a 12-point boldface deductible notice.
-- Only Ohio is seeded (sql/sairnroofing_contingency_seed_ohio.json), matching
-- the state already seeded for licensing in Phase 3a. The other three are
-- researched and recorded here but NOT loaded -- a rule nobody has verified
-- against the current statute text should not render as a confident date.
--
-- ── WHAT IS DELIBERATELY NOT STORED HERE ─────────────────────────────────
-- The verbatim statutory NOTICE TEXT. The rule row carries the mechanical facts
-- and the citation; the wording a contractor actually prints is entered in-app
-- with a named source. Generated statutory language that is close but not
-- verbatim is worse than none.
--
-- Run this once in the Supabase SQL editor. Safe to re-run.

create table if not exists public.rf_contingency_rules (
  id               uuid primary key default gen_random_uuid(),
  license_hash     text not null,
  app_id           text not null default 'sairnroofing',
  rule_id          text not null,
  state            text not null,                 -- 'OH', 'CO', ...
  trigger_event    text not null,                 -- execution | insurer_denial
  count            numeric not null,
  unit             text not null,                 -- business_days | calendar_days | hours
  -- "Business day" is NOT a universal term and assuming it was produced a real
  -- bug in the first draft of api/_lib/roofing-agreements.js. R.C. 1345.21
  -- defines it for Ohio's Act as any day except SUNDAY plus eleven named
  -- holidays -- Saturday counts. 'mon_fri' is the ordinary meaning, used only
  -- for a state whose definitions section has not been read, and every result
  -- computed on it discloses that no holiday calendar was applied.
  business_day_basis text,                         -- oh_hssa | mon_fri | null
  effective_from   date not null,
  effective_to     date,
  status           text not null default 'active',
  data             jsonb not null default '{}'::jsonb,  -- authority (REQUIRED), notice_required,
                                                          -- form_required, indefinite_if_noncompliant,
                                                          -- applies_only_when_solicited, notes
  verified_by      text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (license_hash, rule_id),
  constraint rfcon_trigger_check check (trigger_event in ('execution','insurer_denial')),
  constraint rfcon_unit_check check (unit in ('business_days','calendar_days','hours')),
  constraint rfcon_basis_check check (business_day_basis is null or business_day_basis in ('oh_hssa','mon_fri')),
  constraint rfcon_count_check check (count > 0),
  constraint rfcon_status_check check (status in ('active','superseded')),
  -- A rule with no citation cannot be relied on, and the engine refuses to
  -- compute from one. Enforced here too so a bad row cannot be inserted at all.
  constraint rfcon_authority_check check (data ? 'authority'),
  constraint rfcon_data_size check (octet_length(data::text) <= 65536)
);

create index if not exists idx_rfcon_license on public.rf_contingency_rules(license_hash);
create index if not exists idx_rfcon_state on public.rf_contingency_rules(license_hash, state);

create table if not exists public.rf_claim_agreements (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairnroofing',
  agreement_id  text not null,                    -- client-generated (RFAGR-<timestamp>)
  claim_id      text not null,                    -- references rf_claims.claim_id
  event_type    text not null,                    -- executed | rescinded
  -- On a 'rescinded' row, the agreement_id of the executed row it cancels. The
  -- engine will not apply a rescission that does not name its target, so a
  -- stray row can never silently void a live agreement.
  supersedes    text,
  recorded_by   text not null,                    -- server-stamped from the session
  data          jsonb not null default '{}'::jsonb,  -- signer_name, signature_data (base64),
                                                       -- signing_venue, executed_at, state,
                                                       -- notice_given, cancellation_form_given,
                                                       -- notice_text_shown + notice_source,
                                                       -- rescinded_at, rescission_reason
  created_at    timestamptz not null default now(),
  unique (license_hash, agreement_id),
  constraint rfagr_event_check check (event_type in ('executed','rescinded')),
  -- A rescission with nothing to supersede is meaningless; refuse it at the row.
  constraint rfagr_supersedes_check check (event_type <> 'rescinded' or supersedes is not null),
  -- 1.5MB, matching rf_claim_photos -- a captured signature is an image, not
  -- app data, and must not be squeezed into the 64KB ceiling.
  constraint rfagr_data_size check (octet_length(data::text) <= 1572864)
);

create index if not exists idx_rfagr_license_claim on public.rf_claim_agreements(license_hash, claim_id);

alter table public.rf_contingency_rules enable row level security;
alter table public.rf_claim_agreements enable row level security;

drop policy if exists "svc only rf_contingency_rules" on public.rf_contingency_rules;
create policy "svc only rf_contingency_rules" on public.rf_contingency_rules
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

drop policy if exists "svc only rf_claim_agreements" on public.rf_claim_agreements;
create policy "svc only rf_claim_agreements" on public.rf_claim_agreements
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

-- Rules are superseded in place, so they keep UPDATE. Agreements are
-- append-only evidence and do NOT.
revoke all on public.rf_contingency_rules from service_role;
grant select, insert, update on public.rf_contingency_rules to service_role;
revoke all on public.rf_claim_agreements from service_role;
grant select, insert on public.rf_claim_agreements to service_role;
revoke all on public.rf_contingency_rules from anon, authenticated;
revoke all on public.rf_claim_agreements from anon, authenticated;

-- Verify after running (expect 0 rows, no error):
--   select count(*) from rf_contingency_rules;
--   select count(*) from rf_claim_agreements;
--
-- Confirm the grants (expect rf_contingency_rules = INSERT,SELECT,UPDATE ;
-- rf_claim_agreements = INSERT,SELECT ; no TRUNCATE or DELETE on either):
--   select table_name, string_agg(privilege_type, ', ' order by privilege_type)
--     from information_schema.role_table_grants
--    where grantee = 'service_role' and table_schema = 'public'
--      and table_name in ('rf_contingency_rules','rf_claim_agreements')
--    group by table_name;
