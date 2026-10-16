-- sql/sairnsenior_period_closings_schema.sql
-- SAIRNsenior: the APPEND-ONLY record of pay periods closed and reopened.
-- Written 2026-10-16 (hank, b17). NOT YET RUN -- see the verification block at
-- the bottom and the b17 Michael SQL package.
--
-- ══ WHY THIS TABLE EXISTS, AND WHY A SETTINGS KEY WAS NOT ENOUGH ══════════
-- b16 built the paid-period freeze. b17's first attempt stored the closed-period
-- list as ONE `sen_settings` row under the key `payroll_closed_periods`, with an
-- append-only check in the handler. fourth's b26 review (FINDING H3, HIGH, on
-- money) drove the hole through the real endpoint with a real signed session:
--
--     stored before : {"periods":[{"period_start":"2026-09-01", ...}]}
--     as billing    -> HTTP 200
--     as owner      -> HTTP 200
--     stored after  : {"periods":[]}
--     rows carrying the key: 1   (an APPEND would leave 2+; a REPLACE leaves 1)
--
-- and then the consequence, the same pay run twice:
--
--     closed_periods = the real one -> period_closed={...} minutes=240 gross=8000
--     closed_periods = EMPTIED      -> period_closed=null  minutes=300 gross=10000
--
-- A billing session POSTs one settings row, gets a 200, and the next pay run
-- reports $100.00 for a period already paid at $80.00 -- with `period_closed:
-- null` stating that nothing is frozen, and NO RECORD ANYWHERE that the list
-- ever contained anything. `sen_settings` upserts with
-- `resolution=merge-duplicates`, so the prior value is simply gone.
--
-- fourth's verdict, carried here rather than re-argued: "A control erasable by
-- the same role that runs payroll, through an endpoint whose own comment
-- disclaims validating it, with the prior value overwritten, is not a control
-- -- it is a convention."
--
-- ══ THE SHAPE: ONE ROW PER EVENT, NEVER UPDATED, NEVER DELETED ════════════
-- The same shape `leg_custodylog` already has, for the same reason: a record
-- that can be edited is not a record of what happened. A closing is an event;
-- so is a reopening. The effective set of closed periods is DERIVED by replaying
-- them, which means the derivation can be re-run and audited, and no write can
-- make a past closing cease to have existed.
--
--   kind = 'close'   period_start, period_end, paid_at, reason
--   kind = 'reopen'  reverses -> the closing_id it reverses, reason REQUIRED
--
-- A REOPEN IS AN APPENDED ROW AND NEVER A SILENT REPLACE. That is fourth's rule
-- in one sentence. Reopening a period is a legitimate act -- a payroll error
-- found after the run has to be fixable -- and it is a *loud* one: it names the
-- closing it reverses, it carries a reason, and both rows survive forever.
--
-- ══ NO DELETE AND NO UPDATE IN THE GRANTS, WHICH IS THE ENFORCEMENT ═══════
-- The handler refuses an edit by an existence lookup before the insert. That is
-- the FIRST defence and it is the one that produces a good error message. THIS
-- is the second: with no UPDATE and no DELETE privilege, a handler bug cannot
-- rewrite history even if the lookup is wrong. `revoke all` first strips the
-- default-ACL TRUNCATE/REFERENCES/TRIGGER -- TRUNCATE on this table would erase
-- every agency's freeze record at once, which is the exact harm H3 named.
--
-- The cost is stated rather than hidden: a row written here cannot be removed
-- by the API, by any tool, or by this file. Only a human in the SQL editor, and
-- only by first granting themselves a privilege this file revokes. That is the
-- append-only rule working as designed.

create table if not exists public.sen_period_closings (
  id            uuid primary key default gen_random_uuid(),
  license_hash  text not null,
  app_id        text not null default 'sairnsenior',
  closing_id    text not null,                      -- client-supplied, unique per licence
  data          jsonb not null default '{}'::jsonb, -- kind/period_start/period_end/paid_at/reason/reverses
  created_by    text,                               -- employee_id, SERVER-side from the verified
                                                    -- session, never from the client payload
  created_role  text,                               -- the role that did it, same provenance
  created_at    timestamptz not null default now(),
  unique (license_hash, closing_id),
  constraint senpc_data_size check (octet_length(data::text) <= 65536),
  -- THE KIND IS CONSTRAINED IN THE DATABASE AND NOT ONLY IN THE HANDLER.
  -- A third kind added in code without a migration is refused here rather than
  -- stored as a row the replay does not understand -- and a row the replay
  -- does not understand is a freeze state nobody can reproduce.
  constraint senpc_kind check (data->>'kind' in ('close', 'reopen'))
);

create index if not exists idx_senpc_license on public.sen_period_closings(license_hash);
-- The replay reads every row for a licence in creation order. A reopen must be
-- applied after the closing it reverses, and `created_at` is what orders them.
create index if not exists idx_senpc_license_created
  on public.sen_period_closings(license_hash, created_at);

alter table public.sen_period_closings enable row level security;
drop policy if exists "svc only sen_period_closings" on public.sen_period_closings;
create policy "svc only sen_period_closings" on public.sen_period_closings
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

revoke all on public.sen_period_closings from service_role;
-- SELECT AND INSERT ONLY. No update, no delete, no truncate. Do NOT add either
-- when fixing a missing grant: the absence is the control, not an oversight.
grant select, insert on public.sen_period_closings to service_role;
revoke all on public.sen_period_closings from anon, authenticated;

-- ══ VERIFY AFTER RUNNING ══════════════════════════════════════════════════
-- 1. The table exists and is empty:
--      select count(*) from public.sen_period_closings;          -- expect 0
--
-- 2. THE GRANTS ARE EXACTLY INSERT AND SELECT. This is the arm that matters --
--    an UPDATE or DELETE here reopens H3 by the door this table was built to
--    close:
--      select string_agg(privilege_type, ', ' order by privilege_type)
--        from information_schema.role_table_grants
--       where grantee = 'service_role' and table_schema = 'public'
--         and table_name = 'sen_period_closings';
--      -- expect exactly: INSERT, SELECT
--
-- 3. anon and authenticated hold NOTHING (expect zero rows). The publishable
--    key is public by design and this table decides whether a wage is frozen:
--      select grantee, privilege_type
--        from information_schema.role_table_grants
--       where table_schema = 'public' and table_name = 'sen_period_closings'
--         and grantee in ('anon','authenticated');
--
-- 4. THE KIND CONSTRAINT REALLY REFUSES. A constraint nobody has seen refuse
--    is a constraint that might be spelled wrong:
--      insert into public.sen_period_closings (license_hash, closing_id, data)
--      values ('verify-probe', 'ZZ-VERIFY-BAD-KIND', '{"kind":"delete"}'::jsonb);
--      -- EXPECT: ERROR, new row violates check constraint "senpc_kind"
--      -- If this SUCCEEDS, stop: delete the row (you will need a DELETE grant
--      -- to do it, which is itself the point) and re-read this file.
--
-- 5. AND THE APPEND-ONLY GRANT REALLY REFUSES. Same argument:
--      insert into public.sen_period_closings (license_hash, closing_id, data)
--      values ('verify-probe', 'ZZ-VERIFY-APPEND', '{"kind":"close"}'::jsonb);
--      update public.sen_period_closings set created_by = 'x'
--       where closing_id = 'ZZ-VERIFY-APPEND';
--      -- EXPECT: ERROR, permission denied for table sen_period_closings
--      --
--      -- THE ROW FROM THE FIRST STATEMENT IS REAL RESIDUE AND STAYS. It is on
--      -- the fake licence_hash 'verify-probe', so it is invisible to every
--      -- agency and to every replay (which filters on license_hash), and it
--      -- CANNOT BE REMOVED without granting a DELETE this file revokes. If you
--      -- would rather not carry it, skip step 5 -- api/b17-freeze-reopen.test.js
--      -- arm P7 drives the handler's half of the same refusal, and step 2 is
--      -- the grant itself. Recorded in docs/live-residue/ if you do run it.
--
-- 6. THEN CONFIRM LIVE, which is the real proof -- a clean SQL run is not
--    evidence the app can reach it:
--      POST /api/sd-data {"action":"read","resource":"sen_period_closings"}
--      with a valid SEN- licence and an owner session.
--      Before this file is run:  503 NOT_PROVISIONED
--      After:                    200 {"ok":true,"data":[],"provisioned":true}
--      The FLIP is the evidence, not the absence of an error.
--
-- ══ AND ONE MORE THING THIS FILE DOES NOT DO ═════════════════════════════
-- It does not migrate an existing `sen_settings.payroll_closed_periods` row.
-- Measured rather than assumed: as of 2026-10-16 NO AGENCY HAS ONE -- the
-- mechanism has never fired in production, which the b16 handoff also says.
-- api/sd-data.js's read UNIONS the legacy settings row with this table anyway,
-- so an agency that somehow has one keeps its freeze; the union is the
-- migration, and it is in code where it can be tested.
