-- sql/sairnlegacy_settings_livery_grants.sql
-- OWNER: cody, batch b29, 2026-10-20
--
-- ONE COLUMN. It is the storage F2's widening half has never had.
--
-- ══ WHY THIS FILE EXISTS ═══════════════════════════════════════════════════
-- `api/_lib/leg-roles.js`'s policy function takes five arguments:
--
--     decide(resource, role, action, grants, home)
--
-- `home` was wired in b27 and reads one row of `public.sairnlegacy_settings`.
-- `grants` -- the PER-EMPLOYEE half, which is the only thing that can widen
-- anything under F2 -- has been passed as a literal `null` at the call site
-- since the argument existed, for the plainest possible reason: NOTHING STORES
-- IT. So branch 4 of `decide()` is unreachable in production, and b27's own
-- handoff §6.5 recorded exactly that: "decide()'s branch 4 needs a
-- per-employee grant and api/sd-data.js passes null."
--
-- The policy is correct, tested and inert. This column is the missing noun.
--
-- ══ WHAT IT CHANGES, AND WHAT IT DELIBERATELY DOES NOT ═════════════════════
-- RUNNING THIS FILE GRANTS NOBODY ANYTHING. The default is `'{}'::jsonb` --
-- an empty map -- so every existing home and every existing employee is in
-- exactly the state they are in today. Two separate things have to be true
-- before one driver can read one booking:
--
--   1. the home sets `livery_billing = 'direct_to_family'` (F2's per-home
--      answer -- under `through_the_home` the booking is the HOME's commercial
--      record and no grant can reach it), AND
--   2. somebody with personnel authority writes this employee's id into this
--      map for that resource.
--
-- Neither alone does anything. That pairing is F2's whole answer and arm B4 of
-- api/b22-funeral-f1-f2-f3-wiring.test.js already asserts it at the module;
-- api/b29-funeral-f2-f3.test.js asserts it at the endpoint.
--
-- AND `leg_liveryvendors` IS NOT GRANTABLE AT ALL, under any setting, with any
-- entry in this map. It carries the pricing an invoice is built from. The
-- policy module denies it before the grant is consulted (arm B2), so an
-- operator who writes `{"leg_liveryvendors": true}` into this column has
-- written something that does nothing -- which is the right direction for a
-- mistake, and is asserted rather than trusted.
--
-- ══ THE SHAPE ══════════════════════════════════════════════════════════════
--     {
--       "<employee_id>": { "<resource>": true },
--       ...
--     }
--
-- Keyed by employee id FIRST, resource second, because the question the
-- handler asks is "what may THIS caller see" -- one lookup, no scan. And
-- because the alternative (resource first) makes removing one leaver a sweep
-- across every resource instead of deleting one key.
--
-- `true` AND NOTHING ELSE IS A GRANT. `decide()` tests `grants[resource] ===
-- true`, so `1`, `"yes"` and `{}` are all refusals. That is the same
-- convention tests/role_maps_have_no_prototype.js holds every role map to, for
-- the same reason: two spellings of one check that disagree on truthiness is a
-- gate that is open on one line and shut on the next.
--
-- ══ THE HANDLER WORKS BEFORE THIS FILE IS RUN, AND THAT IS THE POINT ═══════
-- `api/sd-data.js` selects this column and FALLS BACK TO THE NARROW DEFAULT if
-- PostgREST answers 400 undefined_column -- it re-reads without it rather than
-- treating the whole settings row as unreadable. So:
--
--   before this file  every livery grant is absent, every driver is denied,
--                     and one `console.error` line says the column is missing
--                     rather than failing the request
--   after this file   the map is read and F2's widening becomes reachable
--
-- A migration whose absence breaks the app is a migration somebody has to run
-- at 2am. This one can wait.
--
-- ══ RUN ════════════════════════════════════════════════════════════════════
-- Idempotent. `add column if not exists` skips an existing column, and the
-- default is applied to existing rows by Postgres 11+ without a table rewrite.

alter table public.sairnlegacy_settings
  add column if not exists livery_grants jsonb not null default '{}'::jsonb;

-- A map, never an array or a scalar. Without this a single `true` written at
-- the top level would be read as a grants object by the handler's `[resource]`
-- lookup and would resolve to `undefined` -- a refusal, so it is not a hole,
-- but it is a silently ignored configuration and those come back as support
-- tickets.
alter table public.sairnlegacy_settings
  drop constraint if exists sairnlegacy_settings_livery_grants_is_object;

alter table public.sairnlegacy_settings
  add constraint sairnlegacy_settings_livery_grants_is_object
  check (jsonb_typeof(livery_grants) = 'object') not valid;

alter table public.sairnlegacy_settings
  validate constraint sairnlegacy_settings_livery_grants_is_object;

-- ══ VERIFY, DO NOT ASSUME ══════════════════════════════════════════════════
-- A clean statement result is not evidence the column is what you think.
--
--   select column_name, data_type, is_nullable, column_default
--     from information_schema.columns
--    where table_schema = 'public'
--      and table_name   = 'sairnlegacy_settings'
--      and column_name  = 'livery_grants';
--
-- Expect: jsonb, NO, '{}'::jsonb.
--
--   select conname, pg_get_constraintdef(oid), convalidated
--     from pg_constraint
--    where conrelid = 'public.sairnlegacy_settings'::regclass
--      and conname  = 'sairnlegacy_settings_livery_grants_is_object';
--
-- Expect: one row, convalidated = true.
--
-- THEN CONFIRM THE PATH END TO END rather than trusting the DDL. With the home
-- set to `direct_to_family` and one driver's id in the map, that driver's read
-- of `leg_liverybookings` must answer 200; with the map empty it must answer
-- 403 FORBIDDEN. A 403 in both cases means the handler is still falling back
-- (check the server log for the undefined-column line); a 200 in both means
-- the grant is not being consulted at all, which is a worse finding than
-- either.
--
-- ══ NO GRANT LINE ══════════════════════════════════════════════════════════
-- `public.sairnlegacy_settings` already carries its privileges from
-- sql/sairnlegacy_settings_schema.sql and adding a column does not change
-- them. Said explicitly because a missing `grant` line in a SAIRN SQL file is
-- normally a defect, and here its absence is correct.
