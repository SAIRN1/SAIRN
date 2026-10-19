-- sql/sairnlegacy_settings_schema.sql
-- The PER-HOME POLICY ROW for SAIRNlegacy -- b18's two practitioner answers,
-- F2 and F3, given a place to live.
--
-- CONCEPT, stated before the file existed:
-- docs/2026-10-19-hank-b20-concepts.md item 4, carried forward unchanged from
-- docs/2026-10-19-hank-b19-concepts.md item 3. One row per home keyed by
-- `license_hash`, the two answers as NAMED columns, an invalid value refused at
-- the boundary rather than normalised away at read time, and AN ABSENT ROW
-- MEANS THE NARROW DEFAULT.
--
-- ── WHAT CONSUMES THIS, AND THE HONEST STATE OF THAT WIRING ───────────────
-- `api/_lib/leg-roles.js` has owned the policy since b18. Its `decide()` takes
-- an OPTIONAL fifth argument:
--
--     decide(resource, role, action, grants, home)
--     home = { livery_billing: <text>, apprentice: <jsonb object> }
--
-- which is exactly the shape of one row of this table.
--
-- **NOTHING READS THIS TABLE YET, AND THAT IS STATED HERE RATHER THAN LEFT TO
-- BE DISCOVERED.** `api/sd-data.js` passes no `home` argument, so every
-- apprentice currently gets the empty default and F3's countersign branch is
-- unreachable in production. b18's own comment at that call site says so. The
-- three steps, in order, are: (1) THIS FILE; (2) a `leg_settings` entry in
-- `LEG_RESOURCES` with id column `settings_id`; (3) the read of this row in the
-- `LEG_RESOURCES` prelude, passed as the fifth argument. Steps 2 and 3 are in
-- `api/sd-data.js`, which is cody's on Michael's explicit instruction, and are
-- ROUTED in docs/2026-10-19-hank-b19-routed-to-cody-and-fourth.md.
--
-- So: **running this file provisions storage that nothing writes to and
-- nothing reads.** It is not useless -- step 3 cannot be written against a
-- table that does not exist -- but it is not a working feature either, and a
-- provisioning file that reads as if it were would be the kind of claim this
-- platform's rules exist to stop.
--
-- ── WHY A DATABASE CHECK WHEN THE NORMALISER ALREADY FAILS NARROW ─────────
-- `liveryBilling()` returns `through_the_home` for anything it does not
-- recognise, and `apprenticePolicy()` drops any resource name that is not in
-- `LEG_ROLE_MATRIX`. That layer is the authority and must never be removed: a
-- stored row is untrusted input.
--
-- THE CHECK SOLVES THE OTHER DIRECTION. The normaliser SILENTLY REWRITES a bad
-- value to the default, so a home that stored `direct-to-family` with a hyphen
-- would be running `through_the_home` and nothing anywhere would say so --
-- they would set the policy, see no error, and get the other arrangement. The
-- CHECK turns that into a REFUSED WRITE at the boundary. Two layers, two
-- different failures: the constraint stops a wrong value being STORED, the
-- normaliser stops a wrong value being OBEYED if one ever is.
--
-- ── AND WHY THE ENUM IS A `check`, NOT A POSTGRES `type ... as enum` ──────
-- An enum type is a schema object shared by every table that references it and
-- `alter type ... add value` cannot run inside a transaction on older servers.
-- A CHECK is local to this table, is visible in `\d`, and a third arrangement
-- is a migration a reader can see in the diff. The two values are
-- `LEG_LIVERY_BILLING_VALUES` in api/_lib/leg-roles.js and that array is the
-- source; this constraint is the second copy, which is a real cost and is the
-- reason the verification block at the bottom asserts the two agree.

-- ── THE ROW ───────────────────────────────────────────────────────────────
-- ONE PER HOME. `license_hash` is UNIQUE and not merely indexed: two policy
-- rows for one home is a question with two answers, and whichever one a
-- `limit 1` happened to return would be the policy. The constraint makes that
-- unrepresentable rather than making the reader careful.
create table if not exists public.sairnlegacy_settings (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null unique,

  -- ── F2: IS LIVERY INVOICED THROUGH THE HOME? ──────────────────────────
  -- Michael's answer to practitioner question F2 is that it is a PER-HOME
  -- SETTING, because both arrangements are real and neither is the platform's
  -- answer. What it decides is whether `leg_liverybookings` is GRANTABLE:
  --
  --   through_the_home  the booking is a purchase order the home owes money
  --                     on -- the home's commercial record, not the driver's,
  --                     and NOT grantable. The shipped behaviour and the
  --                     DEFAULT.
  --   direct_to_family  the booking is the livery company's own contract with
  --                     the family and the home is a referrer, so a driver
  --                     reading THEIR OWN booking becomes the operational
  --                     case -- grantable, still per-employee, still READ
  --                     only, still only by owner or director, and still
  --                     nothing by default.
  --
  -- NOTHING WIDENS BY DEFAULT AND NOTHING WIDENS AUTOMATICALLY. Setting
  -- `direct_to_family` grants no driver anything; it makes a grant POSSIBLE,
  -- which personnel above them still have to perform.
  --
  -- NOT NULL WITH THE NARROW DEFAULT, deliberately, rather than nullable.
  -- A null would be a third state meaning "unanswered" that every reader
  -- would have to coalesce, and one reader eventually would not. An ABSENT
  -- ROW is already the way to say "unanswered", and it means the same thing
  -- this default means -- so there is one unanswered state, not two.
  livery_billing text not null default 'through_the_home'
    constraint sairnlegacy_settings_livery_billing_enum
    check (livery_billing in ('through_the_home', 'direct_to_family')),

  -- ── F3: WHAT AN APPRENTICE MAY NOT SIGN ───────────────────────────────
  -- Michael's answer to F3 is that it is a CONFIG, because the licensing
  -- board's wording is PER-STATE and a per-state legal constraint modelled as
  -- one platform rule is F3's own named failure: "a supervision rule modelled
  -- wrongly is worse than one left unmodelled with a note, because the wrong
  -- model LOOKS like compliance."
  --
  -- `jsonb` AND NOT NAMED COLUMNS, and this is the one place in this file
  -- where the b19 concept's "named columns rather than a free JSON blob" does
  -- not apply -- so it is argued rather than assumed. Two of the three fields
  -- are LISTS OF RESOURCE NAMES. A resource name is not an enum this database
  -- can hold in sync: `LEG_ROLE_MATRIX` has ~36 rows and gains them in
  -- application commits, so a CHECK on membership would go stale against the
  -- code and start refusing valid configuration. `apprenticePolicy()` filters
  -- both lists against the live table at read time, which is the only place
  -- that can be correct.
  --
  -- SO THE CONSTRAINT ASSERTS THE SHAPE AND STOPS THERE, which is exactly as
  -- much as a database can know here:
  --   * it is a JSON OBJECT, not an array, string or number -- a string where
  --     an object belongs is the shape `apprenticePolicy()` coerces to `{}`,
  --     and coercing silently is how a home's whole F3 answer disappears
  --   * `countersign` and `forbidden`, IF PRESENT, are JSON ARRAYS
  --   * `presence_disclosure`, IF PRESENT, is a JSON BOOLEAN
  -- Membership, typos and the countersign/forbidden overlap are the
  -- normaliser's, and it resolves the overlap to FORBIDDEN because "may not
  -- touch it at all" and "may prepare it" cannot both be true and the narrower
  -- reading is the only safe one to guess.
  --
  -- THE DEFAULT GRANTS NOTHING NEW AND TURNS THE DISCLOSURE ON. Empty
  -- countersign, empty forbidden, `presence_disclosure: true` -- so a home
  -- that has not answered F3 keeps exactly today's policy (an apprentice reads
  -- the regulated band and writes none of it) and IS TOLD the app cannot
  -- enforce supervision. An empty default is also the only honest one: we do
  -- not know any particular home's board. It matches
  -- `LEG_APPRENTICE_POLICY_DEFAULT` in api/_lib/leg-roles.js and the
  -- verification block below asserts that rather than trusting it.
  apprentice jsonb not null
    default '{"countersign": [], "forbidden": [], "presence_disclosure": true}'::jsonb
    constraint sairnlegacy_settings_apprentice_shape
    check (
      jsonb_typeof(apprentice) = 'object'
      and (not apprentice ? 'countersign'
           or jsonb_typeof(apprentice -> 'countersign') = 'array')
      and (not apprentice ? 'forbidden'
           or jsonb_typeof(apprentice -> 'forbidden') = 'array')
      and (not apprentice ? 'presence_disclosure'
           or jsonb_typeof(apprentice -> 'presence_disclosure') = 'boolean')
    ),

  -- ── WHO CHANGED IT AND WHEN ───────────────────────────────────────────
  -- The same minimum sql/sairnvet_witness_schema.sql's policy table carries,
  -- and for the same reason: A POLICY THAT CAN BE RELAXED SILENTLY IS NOT A
  -- POLICY. `direct_to_family` makes a resource grantable and an apprentice
  -- `countersign` list makes a `prepare` route exist, so both directions of
  -- this row change who can reach what. These two columns are the least that
  -- makes such a change reconstructable afterwards.
  --
  -- NOT AN AUDIT LOG AND NOT PRESENTED AS ONE. It records the LAST writer
  -- only; the previous value is gone. SAIRNlegacy already has
  -- sql/sairnlegacy_audit_log_schema.sql and a settings write belongs there
  -- too -- that is application work, it is NOT done, and claiming this column
  -- is the audit trail would be the gap-wearing-compliance shape again.
  updated_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- NO ADDITIONAL INDEX. `license_hash text not null unique` already builds the
-- only lookup this table has -- one row by licence -- and a second index on the
-- same column would be dead weight the planner never chooses. Said explicitly
-- because the other SAIRNlegacy schemas in this directory all declare indexes
-- and their absence here should read as a decision, not an omission.

alter table public.sairnlegacy_settings enable row level security;
drop policy if exists "svc only sairnlegacy_settings"
  on public.sairnlegacy_settings;
create policy "svc only sairnlegacy_settings"
  on public.sairnlegacy_settings
  for all using (false) with check (false);

-- ── GRANTS ────────────────────────────────────────────────────────────────
-- REVOKE ALL FIRST, then grant only what the code calls. Without the leading
-- revoke this inherits TRUNCATE/REFERENCES/TRIGGER from the platform default
-- ACL. TRUNCATE here would drop every home's policy row at once -- and because
-- AN ABSENT ROW MEANS THE NARROW DEFAULT, that failure is SILENT AND SAFE-
-- LOOKING: every home would revert to `through_the_home` with an empty
-- apprentice config, no error would be raised anywhere, and the only visible
-- symptom would be grants quietly ceasing to be possible. A failure that
-- presents as the safe default is the hardest kind to notice, which is why the
-- revoke is not boilerplate on this particular table.
--
-- NO DELETE. Clearing a home's policy is `update` back to the defaults, which
-- leaves `updated_by` and `updated_at` saying who did it. A `delete` would
-- return the home to the narrow default WITH NO RECORD THAT ANYONE CHOSE IT --
-- indistinguishable from a home that never configured anything.
revoke all on public.sairnlegacy_settings from service_role;
grant select, insert, update on public.sairnlegacy_settings to service_role;
revoke all on public.sairnlegacy_settings from anon, authenticated;

-- ── VERIFY AFTER RUNNING, one query per statement with its expected answer ──
-- A single count at the end cannot tell a full apply from a partial one. This
-- file's two CHECK constraints are the whole point of it, and a paste that
-- applied the table without them would look identical to a reader and accept
-- every value this file exists to refuse.
--
--   select count(*) from public.sairnlegacy_settings;
--     -- expect 0. Any other number means this was not a fresh provision.
--
--   select conname from pg_constraint
--    where conrelid = 'public.sairnlegacy_settings'::regclass
--      and contype = 'c';
--     -- expect BOTH sairnlegacy_settings_livery_billing_enum AND
--     -- sairnlegacy_settings_apprentice_shape. If only one is listed the
--     -- paste applied partway. If NEITHER is listed you have a table that
--     -- accepts any text and any json, which is strictly worse than no table:
--     -- the normaliser would hide it and the home would run an arrangement it
--     -- did not choose.
--
--   select count(*) from pg_constraint
--    where conrelid = 'public.sairnlegacy_settings'::regclass
--      and contype = 'u';
--     -- expect 1 -- the UNIQUE on license_hash. Zero means two policy rows
--     -- for one home are representable and the policy is whichever one a
--     -- `limit 1` returns.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name = 'sairnlegacy_settings' and grantee = 'service_role';
--     -- expect EXACTLY 3 (SELECT, INSERT, UPDATE). A 4th is a DELETE or
--     -- TRUNCATE that must not be there; 0 is the 42501 that looks like
--     -- nothing else.
--
--   select count(*) from information_schema.role_table_grants
--    where table_name = 'sairnlegacy_settings'
--      and grantee in ('anon','authenticated');
--     -- expect 0.
--
-- ── AND TWO NEGATIVE CHECKS, because a constraint nobody tried is a
-- ── constraint nobody has evidence of. Run these in a transaction and roll
-- ── back; each must ERROR, and an INSERT that SUCCEEDS is the finding.
--
--   begin;
--     insert into public.sairnlegacy_settings (license_hash, livery_billing)
--     values ('__verify__', 'direct-to-family');
--     -- expect ERROR 23514, violates sairnlegacy_settings_livery_billing_enum.
--     -- THE HYPHEN IS THE POINT: api/_lib/leg-roles.js's liveryBilling() would
--     -- accept this row and silently run `through_the_home`, so if this insert
--     -- succeeds the home gets the other arrangement and is never told.
--   rollback;
--
--   begin;
--     insert into public.sairnlegacy_settings (license_hash, apprentice)
--     values ('__verify__', '"countersign"'::jsonb);
--     -- expect ERROR 23514, violates sairnlegacy_settings_apprentice_shape.
--     -- A JSON STRING WHERE THE OBJECT BELONGS: apprenticePolicy() coerces
--     -- this to `{}`, so the home's entire F3 answer would vanish with no
--     -- error on write and no error on read.
--   rollback;
--
-- ── THE CROSS-FILE CHECK, which is the one most worth doing and the one a
-- ── reader is least likely to think of. The enum above is a SECOND COPY of
-- ── LEG_LIVERY_BILLING_VALUES and the apprentice default is a second copy of
-- ── LEG_APPRENTICE_POLICY_DEFAULT. Two copies drift. Run from the repo root:
--
--   node -e "const r=require('./api/_lib/leg-roles');
--     console.log(JSON.stringify(r.LEG_LIVERY_BILLING_VALUES));
--     console.log(JSON.stringify(r.LEG_APPRENTICE_POLICY_DEFAULT));"
--
--     -- expect ["through_the_home","direct_to_family"] -- the same two values,
--     -- the same spellings, in the CHECK above.
--     -- expect countersign [] / forbidden [] / presence_disclosure true -- the
--     -- same three fields as the `apprentice` column default. (The module's
--     -- object also carries `recorded`, which is provenance for a reader and
--     -- is deliberately NOT a stored column: it describes the decision, not
--     -- the home.)
--
-- NOT A GATE AND NOT PRETENDING TO BE ONE. A comment block does not run, so
-- this is a check a person performs, and the drift it guards against will not
-- announce itself -- the app would simply start refusing a value the code
-- considers valid, at a write, in production. The durable fix is a probe in
-- tests/ that parses this file's CHECK and compares it to the module's array;
-- it is NOT written, and it is named in the b20 handoff as open work rather
-- than left as an intention inside a comment.
