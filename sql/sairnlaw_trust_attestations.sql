-- sql/sairnlaw_trust_attestations.sql
-- THE IOLTA RECONCILIATION ATTESTATION -- the record, and the one per-firm
-- setting that decides whether a solo attorney may sign it alone.
--
-- CONCEPT, stated before any of this existed
-- (docs/2026-10-19-hank-b23-notes.md, item 3):
--
--   A completed three-way reconciliation becomes an ATTESTED record only when a
--   bar-admitted person signs a hash of the exact comparison that was run; a
--   firm that has EXACTLY ONE active owner/attorney may switch on a per-firm
--   single-signer setting and attest alone, and every attestation taken that
--   way is stored as signer_mode 'single' -- so the record never claims two
--   people looked when one did.
--
-- Design: docs/2026-10-19-hank-b21-attestation-design.md (Alternative A,
-- MODE_ALWAYS, with §6 answered as a hybrid of its answers 2 and 3).
-- Policy and validation: api/_lib/law-attest.js. Route: api/law-attest.js.
--
-- ── WHAT THIS FILE DOES *NOT* CREATE, AND WHY THAT IS THE GOOD NEWS ───────
-- NO TOKEN TABLE. The two-signer path reuses `sairnlaw_countersign_tokens`
-- from sql/sairnlaw_countersign_schema.sql, which Michael has already run.
-- Measured rather than assumed: that table's `resource` column is
-- `text not null` with NO CHECK on its value (line 56 of that file), so a
-- `law_trust_attestation` token row is representable there today. A second
-- token table would have been a second copy of a lifecycle 59 arms already
-- prove.
--
-- SO: running THIS file is the only database step the attestation needs.
--
-- ── THE SELF-SIGNATURE CHECK IS CONDITIONAL, AND THAT IS THE WHOLE DESIGN ─
-- Every other countersignature table on this platform carries a flat
-- "the signer is not the preparer" CHECK. THIS ONE CANNOT, because a solo
-- attorney's attestation legitimately names one person twice. The answer is
-- not to drop the constraint -- it is to make the constraint depend on
-- `signer_mode`, so THE DATABASE REFUSES A SELF-SIGNATURE UNLESS THE ROW
-- SAYS, IN A STORED COLUMN, THAT IT IS A SINGLE-SIGNER ATTESTATION:
--
--   signer_mode = 'dual'    ->  prepared_by <> attested_by   (enforced)
--   signer_mode = 'single'  ->  prepared_by  = attested_by   (enforced)
--
-- Both directions, because 'single' must not become a label somebody puts on a
-- two-person record either. A row cannot be a self-signature without admitting
-- it, and it cannot claim to be solo while naming two people.
--
-- ── NO UPDATE, NO DELETE, AND THE LEADING REVOKE IS NOT BOILERPLATE ──────
-- An attestation is never amended; a correction is a NEW comparison with a NEW
-- attestation. That is stricter than the countersign token tables, which need
-- UPDATE to mark a token spent. Without the leading `revoke all` this table
-- inherits TRUNCATE from the platform default ACL, and TRUNCATE here would
-- erase every attestation a firm has ever recorded, silently, in one
-- statement -- leaving a firm that HAS reconciled and attested for years
-- indistinguishable from one that never did.
-- ---------------------------------------------------------------------------

-- ═══ 1. THE ATTESTATION RECORD ═════════════════════════════════════════════

create table if not exists public.sairnlaw_trust_attestations (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  attestation_id text not null,

  -- THE BINDING. sha256 over the canonical JSON of the comparison with the
  -- resource name inside it -- api/_lib/countersign.js's contentHash(). Stored
  -- so the two-signer path's token and this row can be shown to be about the
  -- same comparison years later, by recomputation rather than by trust.
  content_hash text not null,

  -- ── THE THREE LEGS, AS INTEGER CENTS. NEVER numeric, NEVER float. ───────
  -- api/_lib/law-trust-reconcile.js computes in cents and sairnlaw.html sends
  -- `client_total_cents`, so a float column here could manufacture the very
  -- discrepancy the reconciliation exists to settle. bigint because a firm's
  -- trust account in cents comfortably exceeds int4 and silently wrapping a
  -- trust balance is not a failure mode worth leaving open.
  bank_balance_cents bigint not null,
  ledger_balance_cents bigint not null,
  client_subledger_total_cents bigint not null,

  -- AND THEIR AS-OF DATES. A balance with no as-of date is not a leg of a
  -- reconciliation, it is a number; three legs compared across three different
  -- days is a legitimate situation that the record has to be able to show.
  bank_as_of date not null,
  ledger_as_of date not null,
  subledger_as_of date not null,

  -- THE VERDICT. CANNOT_RECONCILE is a real answer and not an error state: a
  -- firm whose bank statement has not arrived has not failed to reconcile.
  verdict text not null,

  -- The client sub-ledgers that were NEGATIVE. [] means none -- an absent key
  -- and a cannot-tell read the same to a consumer and only one is honest, so
  -- api/_lib/law-attest.js normalises absent to [] and this column is NOT NULL.
  negative_balances jsonb not null default '[]'::jsonb,

  -- ── WHO. The preparer ran the comparison; the attester signed it. ───────
  -- The ROLES are stored, not re-derived at read time, because it is the
  -- signer's standing AT THE MOMENT OF SIGNING that the record claims.
  prepared_by text not null,
  prepared_role text not null,
  attested_by text not null,
  attested_role text not null,
  attested_at timestamptz not null default now(),

  -- 'dual' or 'single'. SPELLED rather than a boolean: these two words are
  -- part of the record a bar auditor reads, and `single_signer: false` would
  -- read as the same claim with the opposite value.
  signer_mode text not null,

  created_at timestamptz not null default now(),

  -- ONE ATTESTATION ID PER FIRM. Not globally unique: two firms numbering
  -- their attestations from 1 is ordinary, and a global unique would make the
  -- second firm's first attestation fail for a reason nobody could diagnose.
  constraint sairnlaw_trust_attestations_firm_id unique (license_hash, attestation_id),

  constraint sairnlaw_trust_attestations_verdict_enum
    check (verdict in ('AGREES', 'DISAGREES', 'PARTIAL', 'CANNOT_RECONCILE')),

  constraint sairnlaw_trust_attestations_signer_mode_enum
    check (signer_mode in ('dual', 'single')),

  -- ── THE SELF-SIGNATURE CONSTRAINT, BOTH DIRECTIONS (see the header) ─────
  -- This is the third place the rule lives: api/_lib/countersign.js refuses a
  -- self-countersignature on the dual path, api/_lib/law-attest.js decides
  -- which path applies, and THIS refuses a row that disagrees with itself. The
  -- two application checks live in one process; a future write path that
  -- forgot them would leave no trace without this one.
  constraint sairnlaw_trust_attestations_signer_mode_agrees
    check ((signer_mode = 'dual'   and prepared_by <> attested_by)
        or (signer_mode = 'single' and prepared_by  = attested_by)),

  -- A SINGLE-SIGNER ATTESTATION IS BY A BAR-ADMITTED PERSON, AND SO IS A DUAL
  -- ONE. LAW_BAR_ADMITTED_ROLES is { owner, attorney } in
  -- api/_lib/law-roles.js. THIS IS A SECOND COPY OF THAT LIST and is declared
  -- as such: the cross-file check at the bottom of this file is how the two are
  -- kept honest. The preparer is deliberately NOT constrained -- a paralegal
  -- may run the comparison, which is the delegation this whole mechanism
  -- exists to make safe.
  constraint sairnlaw_trust_attestations_attester_bar_admitted
    check (attested_role in ('owner', 'attorney')),

  -- VERDICT CONSISTENCY, IN THE DATABASE AS WELL. AGREES means the three legs
  -- hold the same number. A row saying AGREES beside three different figures
  -- is a lie on its face and is the shape a fabricated verdict takes. This
  -- checks the record against ITSELF; nothing here says the figures are right.
  constraint sairnlaw_trust_attestations_agrees_is_consistent
    check (verdict <> 'AGREES'
           or (bank_balance_cents = ledger_balance_cents
               and ledger_balance_cents = client_subledger_total_cents))
);

-- The query an auditor's "show me this firm's attestations, newest first" is
-- built from, and the one the route's `list` action runs.
create index if not exists idx_sairnlaw_trust_attestations_firm
  on public.sairnlaw_trust_attestations (license_hash, attested_at desc);

-- The query that answers "has THIS comparison been attested?" without
-- scanning. The route uses it to refuse a duplicate attestation of one
-- comparison, which is not the same thing as refusing a re-reconciliation.
create index if not exists idx_sairnlaw_trust_attestations_content
  on public.sairnlaw_trust_attestations (license_hash, content_hash);

alter table public.sairnlaw_trust_attestations enable row level security;
drop policy if exists "svc only sairnlaw_trust_attestations"
  on public.sairnlaw_trust_attestations;
create policy "svc only sairnlaw_trust_attestations"
  on public.sairnlaw_trust_attestations
  for all using (false) with check (false);

revoke all on public.sairnlaw_trust_attestations from service_role;
grant select, insert on public.sairnlaw_trust_attestations to service_role;
revoke all on public.sairnlaw_trust_attestations from anon, authenticated;


-- ═══ 2. THE PER-FIRM SETTING ═══════════════════════════════════════════════
--
-- ONE KEYED-ROW TABLE rather than a column per setting, which is the shape
-- sen_settings and rf_settings already use. Today it holds exactly one key --
-- `trust_attestation_single_signer` -- and that is said out loud so the table
-- does not read as a general configuration surface somebody may add to without
-- a decision.
--
-- AN ABSENT ROW MEANS OFF, which is the narrow default: a firm that has never
-- touched this gets the two-signer requirement. That direction matters --
-- absent-means-on would hand every firm on the platform the weaker control the
-- day this file ran.
--
-- UPDATE IS GRANTED HERE AND NOT ON THE TABLE ABOVE, and the difference is the
-- point: a setting is a current statement about the firm and must be
-- changeable (a firm that hires a second attorney turns it off); an
-- attestation is a historical record and must not be.

create table if not exists public.sairnlaw_firm_settings (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  setting_key text not null,
  -- jsonb rather than boolean: the next setting this table holds will not be a
  -- boolean, and a `value_bool` column would have to be joined by a second one
  -- the day that happens. api/_lib/law-attest.js reads `=== true` and treats
  -- everything else as off, so a non-boolean in this column is OFF rather than
  -- truthy -- which is the safe direction and is asserted by an arm.
  value jsonb not null,
  -- WHO SET IT AND WHEN. A setting that weakens a control and does not say who
  -- chose it is an audit gap, and this one is read during a bar examination.
  updated_by text not null,
  updated_role text not null,
  updated_at timestamptz not null default now(),
  -- THE ROSTER COUNT AT THE MOMENT IT WAS SET. Recorded because the setting is
  -- a claim about staffing and this is the evidence the claim was true when
  -- accepted. It is NOT the authority: the count is re-derived on every
  -- single-signer attestation, because a stale count is exactly what this
  -- column must not be allowed to become.
  bar_admitted_count_at_set integer,

  constraint sairnlaw_firm_settings_key unique (license_hash, setting_key),
  constraint sairnlaw_firm_settings_known_key
    check (setting_key in ('trust_attestation_single_signer'))
);

alter table public.sairnlaw_firm_settings enable row level security;
drop policy if exists "svc only sairnlaw_firm_settings"
  on public.sairnlaw_firm_settings;
create policy "svc only sairnlaw_firm_settings"
  on public.sairnlaw_firm_settings
  for all using (false) with check (false);

-- NO DELETE. Turning the setting off is an `update` to `false`, which leaves
-- `updated_by` saying who did it. A delete would return the firm to the narrow
-- default WITH NO RECORD THAT ANYONE CHOSE IT -- indistinguishable from a firm
-- that never configured anything, on a setting whose whole purpose is to be
-- explainable to an examiner.
revoke all on public.sairnlaw_firm_settings from service_role;
grant select, insert, update on public.sairnlaw_firm_settings to service_role;
revoke all on public.sairnlaw_firm_settings from anon, authenticated;


-- ═══ VERIFY AFTER RUNNING ══════════════════════════════════════════════════
-- One query per statement with its expected answer. A single count at the end
-- cannot tell a full apply from a partial one, and the CHECK constraints are
-- most of what this file IS -- a paste that created the tables without them
-- would look identical to a reader and would accept every row this file exists
-- to refuse.
--
--   select count(*) from public.sairnlaw_trust_attestations;
--     -- expect 0. Any other number means this was not a fresh provision.
--
--   select conname from pg_constraint
--    where conrelid = 'public.sairnlaw_trust_attestations'::regclass
--      and contype = 'c' order by conname;
--     -- expect ALL FOUR:
--     --   sairnlaw_trust_attestations_agrees_is_consistent
--     --   sairnlaw_trust_attestations_attester_bar_admitted
--     --   sairnlaw_trust_attestations_signer_mode_agrees
--     --   sairnlaw_trust_attestations_signer_mode_enum
--     --   (and sairnlaw_trust_attestations_verdict_enum -- five in total)
--     -- Fewer means the paste applied partway. NONE means a table that
--     -- accepts a self-signed 'dual' attestation, which is the one row this
--     -- entire mechanism exists to make unrepresentable.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name = 'sairnlaw_trust_attestations' and grantee = 'service_role';
--     -- expect EXACTLY 2 (SELECT, INSERT). A 3rd is an UPDATE or DELETE that
--     -- must not be there -- an attestation is never amended. 0 is the 42501
--     -- that looks like nothing else.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name in ('sairnlaw_trust_attestations','sairnlaw_firm_settings')
--      and grantee in ('anon','authenticated');
--     -- expect 0.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name = 'sairnlaw_firm_settings' and grantee = 'service_role';
--     -- expect EXACTLY 3 (SELECT, INSERT, UPDATE).
--
-- ── FOUR NEGATIVE INSERTS AND ONE POSITIVE CONTROL. Run each in its own
-- ── transaction and roll back. Each negative must ERROR; AN INSERT THAT
-- ── SUCCEEDS IS THE FINDING. The positive control must SUCCEED -- four
-- ── erroring inserts are equally consistent with "the constraints work" and
-- ── with "this table rejects everything", and only the fifth tells them
-- ── apart.
--
--   -- N1. A SELF-SIGNED 'dual' ATTESTATION. THE ONE THAT MATTERS.
--   begin;
--     insert into public.sairnlaw_trust_attestations
--       (license_hash, attestation_id, content_hash,
--        bank_balance_cents, ledger_balance_cents, client_subledger_total_cents,
--        bank_as_of, ledger_as_of, subledger_as_of, verdict,
--        prepared_by, prepared_role, attested_by, attested_role, signer_mode)
--     values ('__verify__', 'N1', 'x',
--             100, 100, 100, '2026-10-01', '2026-10-01', '2026-10-01', 'AGREES',
--             'alice', 'attorney', 'alice', 'attorney', 'dual');
--     -- expect ERROR 23514, violates
--     -- sairnlaw_trust_attestations_signer_mode_agrees. One person, signing
--     -- twice, with the row claiming two looked.
--   rollback;
--
--   -- N2. A 'single' ATTESTATION NAMING TWO PEOPLE. The same constraint, the
--   -- other direction -- 'single' must not become a label on a dual record.
--   begin;
--     insert into public.sairnlaw_trust_attestations
--       (license_hash, attestation_id, content_hash,
--        bank_balance_cents, ledger_balance_cents, client_subledger_total_cents,
--        bank_as_of, ledger_as_of, subledger_as_of, verdict,
--        prepared_by, prepared_role, attested_by, attested_role, signer_mode)
--     values ('__verify__', 'N2', 'x',
--             100, 100, 100, '2026-10-01', '2026-10-01', '2026-10-01', 'AGREES',
--             'bob', 'paralegal', 'alice', 'attorney', 'single');
--     -- expect ERROR 23514, violates
--     -- sairnlaw_trust_attestations_signer_mode_agrees.
--   rollback;
--
--   -- N3. AGREES WITH LEGS THAT DO NOT AGREE.
--   begin;
--     insert into public.sairnlaw_trust_attestations
--       (license_hash, attestation_id, content_hash,
--        bank_balance_cents, ledger_balance_cents, client_subledger_total_cents,
--        bank_as_of, ledger_as_of, subledger_as_of, verdict,
--        prepared_by, prepared_role, attested_by, attested_role, signer_mode)
--     values ('__verify__', 'N3', 'x',
--             100, 101, 100, '2026-10-01', '2026-10-01', '2026-10-01', 'AGREES',
--             'bob', 'paralegal', 'alice', 'attorney', 'dual');
--     -- expect ERROR 23514, violates
--     -- sairnlaw_trust_attestations_agrees_is_consistent. ONE CENT APART, on
--     -- purpose: the interesting failure is never a big one.
--   rollback;
--
--   -- N4. A PARALEGAL AS THE ATTESTER.
--   begin;
--     insert into public.sairnlaw_trust_attestations
--       (license_hash, attestation_id, content_hash,
--        bank_balance_cents, ledger_balance_cents, client_subledger_total_cents,
--        bank_as_of, ledger_as_of, subledger_as_of, verdict,
--        prepared_by, prepared_role, attested_by, attested_role, signer_mode)
--     values ('__verify__', 'N4', 'x',
--             100, 100, 100, '2026-10-01', '2026-10-01', '2026-10-01', 'AGREES',
--             'alice', 'attorney', 'bob', 'paralegal', 'dual');
--     -- expect ERROR 23514, violates
--     -- sairnlaw_trust_attestations_attester_bar_admitted.
--   rollback;
--
--   -- P1. THE POSITIVE CONTROL. A legitimate solo attestation.
--   begin;
--     insert into public.sairnlaw_trust_attestations
--       (license_hash, attestation_id, content_hash,
--        bank_balance_cents, ledger_balance_cents, client_subledger_total_cents,
--        bank_as_of, ledger_as_of, subledger_as_of, verdict,
--        prepared_by, prepared_role, attested_by, attested_role, signer_mode)
--     values ('__verify__', 'P1', 'x',
--             250000, 250000, 250000, '2026-10-01', '2026-10-01', '2026-10-01',
--             'AGREES', 'alice', 'attorney', 'alice', 'attorney', 'single');
--     -- expect 1 row inserted. If this ERRORS, the four above prove nothing.
--   rollback;
--
--   -- P2. The setting's own positive control and its one negative.
--   begin;
--     insert into public.sairnlaw_firm_settings
--       (license_hash, setting_key, value, updated_by, updated_role)
--     values ('__verify__', 'trust_attestation_single_signer', 'true'::jsonb,
--             'alice', 'owner');
--     -- expect 1 row.
--     insert into public.sairnlaw_firm_settings
--       (license_hash, setting_key, value, updated_by, updated_role)
--     values ('__verify__', 'require_two_person', 'false'::jsonb,
--             'alice', 'owner');
--     -- expect ERROR 23514, violates sairnlaw_firm_settings_known_key. An
--     -- unknown key would be stored, read by nothing, and look configured.
--   rollback;
--
-- ── THE CROSS-FILE CHECK, which is the one a reader is least likely to think
-- ── of. `attested_role in ('owner','attorney')` above is a SECOND COPY of
-- ── LAW_BAR_ADMITTED_ROLES, and `setting_key in (...)` is a second copy of
-- ── SETTING_KEY. Two copies drift. From the repo root:
--
--   node -e "const r=require('./api/_lib/law-roles');const a=require('./api/_lib/law-attest');console.log(Object.keys(r.LAW_BAR_ADMITTED_ROLES).sort().join(','), a.SETTING_KEY)"
--     -- expect: attorney,owner trust_attestation_single_signer
--     -- If either differs from the literals in this file, THIS FILE IS THE
--     -- STALE COPY and the constraint is refusing a role the app now allows
--     -- (or allowing one it does not). Arm C3 of
--     -- api/b23-iolta-attestation.test.js asserts exactly this pairing by
--     -- reading both files, so it fails in CI rather than in Supabase.
