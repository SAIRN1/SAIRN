-- sql/ai_memories_schema.sql
-- The migration file for public.ai_memories, written 2026-08-26.
--
-- ══ THIS TABLE HAS BEEN LIVE IN PRODUCTION SINCE LONG BEFORE THIS FILE ═════
-- Not a new table. `ai_memories` backs StoneDesk's `memory` resource and has
-- had no migration file anywhere in the repo. Found 2026-08-25 from two
-- directions: from the code side (registered resource `memory` with no
-- same-named table, and no `create table` for its real target anywhere in
-- sql/), and as one of the 25 `live_but_not_declared` rows returned by
-- sql/provisioning_gap_check_2026-08-25.sql.
--
-- EVERY COLUMN, CONSTRAINT AND INDEX BELOW WAS READ OUT OF THE LIVE DATABASE
-- via sql/introspect_undeclared_tables_2026-08-26.sql on 2026-08-26, not
-- inferred. The code-side prediction was right that a surrogate key was likely
-- and that `created_at` had to default server-side -- the writer never sends
-- it (api/sd-data.js:320) while the reader orders by it (:303) -- but it could
-- not see `id`, the defaults, the size CHECK, or the composite index.
--
-- Safe to re-run. See DISCLOSED FINDINGS for the two things this file
-- deliberately does NOT change.
--
-- ══ DISCLOSED FINDING 1 -- there is NO unique constraint, and this file does ══
-- ══ not add one ═══════════════════════════════════════════════════════════
-- Confirmed by introspection, not assumed: `ai_memories` has a primary key on
-- `id` and NOTHING else. Nothing prevents duplicate (license_hash, app_id)
-- rows, and the write path does not try to prevent them either -- it is a
-- plain INSERT with no `on_conflict` (api/sd-data.js:320), and the read takes
-- `order=created_at.desc&limit=10` (:303). So duplicates are not a bug being
-- worked around; append-and-take-the-latest-10 is what the code does.
--
-- THIS FILE DOES NOT ADD A UNIQUE CONSTRAINT. That is a real design decision
-- with consequences in both directions, and it is not this migration's call:
--   * Adding one would CHANGE BEHAVIOUR -- the plain INSERT would begin
--     failing on conflict rather than appending, so api/sd-data.js:320 would
--     have to change in the same breath.
--   * It could also fail outright on existing data, since duplicate rows may
--     already be present -- by design, per the above.
--   * And there is a real question underneath it that nobody has answered:
--     whether this table is meant to be an append-only log (it behaves like
--     one) or a per-licence record (its name suggests one). Decide that first;
--     the constraint follows from the answer, not the reverse.
-- Recorded here rather than silently fixed. If the append-only reading is
-- confirmed, say so in this header and the question stops being reopened.
--
-- ══ DISCLOSED FINDING 2 -- anon/authenticated hold TRUNCATE, and the revoke ══
-- ══ line below is the ONLY statement in this file that changes live state ══
-- Live grants as introspected 2026-08-26:
--     service_role   INSERT, SELECT, UPDATE          <- correct, no DELETE
--     anon           TRUNCATE, REFERENCES, TRIGGER   <- default-ACL baseline
--     authenticated  TRUNCATE, REFERENCES, TRIGGER   <- default-ACL baseline
--
-- service_role is already correct -- no DELETE -- so this table was NOT missed
-- by the 2026-08-25 DELETE sweep. The anon/authenticated verbs are the
-- Supabase default-ACL baseline removed elsewhere by
-- sql/append_only_grant_audit.sql and the 2026-08-24 TRUNCATE sweep. This
-- table was never in scope for either, because neither could see a table with
-- no schema file -- the same blind spot this file exists to close.
--
-- The `revoke all ... from anon, authenticated` line is written in because it
-- is the house idiom (sql/sairnroofing_billing_schema.sql) and a table
-- re-provisioned from this file should not inherit the problem. On the
-- EXISTING live table it is not inert. Whether to run it belongs to the
-- platform-wide privilege work, not to this migration.

--
-- ══ TWO SMALL THINGS THAT ARE INFERRED, NOT REPORTED -- stated so they can be ══
-- ══ checked rather than trusted ════════════════════════════════════════════
-- 1. `default gen_random_uuid()` on the primary key. The introspection summary
--    gave the column as `id uuid pk` without quoting its default. The default
--    is inferred, and inferred on solid ground: no writer on any path sends
--    `id`, and every insert succeeds, which cannot both be true unless the
--    column defaults server-side. Confirm against section 1's `column_default`
--    and correct this line if it differs -- the database wins.
-- 2. The CHECK constraint NAME below is this file's own, since the summary
--    reported the constraint's definition rather than its identifier. That is
--    harmless by construction: the guard around it matches on the definition,
--    not the name, so re-running cannot duplicate an existing differently-named
--    constraint. A fresh provision simply gets this name.

-- ---------------------------------------------------------------------------
-- 1. Table
-- ---------------------------------------------------------------------------
create table if not exists public.ai_memories (
  id           uuid        primary key default gen_random_uuid(),
  license_hash text        not null,
  app_id       text        not null default 'stonedesk',
  -- Nullable on purpose, and the code depends on it: the writer stamps
  -- shop_id from the profile inside a try/catch and comments the failure path
  -- "non-fatal -- memory still saves unlinked" (api/sd-data.js:311-317,
  -- api/_lib/sd-store.js:145). Making this NOT NULL would turn a tolerated
  -- unlinked write into a hard failure.
  shop_id      text,
  data         jsonb       not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 2. Constraints
-- ---------------------------------------------------------------------------
-- Primary key only. NO unique constraint -- see DISCLOSED FINDING 1. Do not
-- "fix" this without answering the append-only-vs-per-licence question first.

-- 64 KB ceiling on the JSON payload, matching MAX_PAYLOAD_BYTES in
-- api/_lib/sd-store.js. That app-side check and this one must move together:
-- writeMemory() rejects at 64 KB with PAYLOAD_TOO_LARGE before the request is
-- ever sent, so if this bound is raised without raising that one, the app
-- keeps refusing payloads the database would now accept.
do $$
begin
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'public.ai_memories'::regclass
       and contype  = 'c'
       and pg_get_constraintdef(oid) like '%65536%'
  ) then
    alter table public.ai_memories
      add constraint ai_memories_data_size
      check (octet_length(data::text) <= 65536);
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- 3. Indexes
-- ---------------------------------------------------------------------------
-- The pkey brings its own. This composite is the one that exists live and
-- would be lost in a rebuild, and it is shaped exactly like the only read the
-- code performs: `license_hash=eq.<hash>&order=created_at.desc&limit=10`
-- (api/sd-data.js:303, api/_lib/sd-store.js:126). The DESC matters -- drop it
-- and the ordering becomes a sort instead of an index walk.
create index if not exists idx_mem_scope
  on public.ai_memories (license_hash, created_at desc);

-- ---------------------------------------------------------------------------
-- 4. RLS -- service-role only
-- ---------------------------------------------------------------------------
alter table public.ai_memories enable row level security;
drop policy if exists "svc only ai_memories" on public.ai_memories;
create policy "svc only ai_memories" on public.ai_memories
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

-- ---------------------------------------------------------------------------
-- 5. Grants -- revoke first, then grant only the verbs the code uses
-- ---------------------------------------------------------------------------
-- `revoke all` before `grant`: ALTER DEFAULT PRIVILEGES in this project grants
-- service_role a baseline on every new relation in public, so a bare grant
-- never describes the real end state. See sql/append_only_grant_audit.sql.
--
-- Verbs: SELECT, INSERT, UPDATE. No DELETE -- the memory branch implements
-- read and write only. Do NOT re-add `delete` here when fixing a missing
-- grant; that is the 2026-08-06 overcorrection this platform already undid
-- once across 68 lines in 16 files.
--
-- UPDATE is granted although the code only ever inserts. That matches the live
-- state as introspected and is left alone deliberately -- narrowing it to
-- `select, insert` would be a real tightening, and tightening a live grant is
-- the platform-privilege work's call, not this file's.
revoke all on public.ai_memories from service_role;
grant select, insert, update on public.ai_memories to service_role;

-- THE ONE NON-INERT STATEMENT IN THIS FILE. See DISCLOSED FINDING 2.
-- No-op on a fresh provision; on the existing live table it removes
-- TRUNCATE/REFERENCES/TRIGGER that anon and authenticated hold right now.
-- Comment it out to declare without changing.
revoke all on public.ai_memories from anon, authenticated;

-- ---------------------------------------------------------------------------
-- 6. Verify after running
-- ---------------------------------------------------------------------------
--   select count(*) from public.ai_memories;
--     -- expect the real row count, NOT 0. Live data.
--
--   select conname, pg_get_constraintdef(oid) from pg_constraint
--    where conrelid = 'public.ai_memories'::regclass order by contype;
--     -- expect a PRIMARY KEY and a CHECK, and NO unique constraint.
--     -- A unique constraint appearing here means someone "fixed" finding 1
--     -- without answering it -- check api/sd-data.js:320 still inserts.
--
--   select indexname from pg_indexes
--    where schemaname = 'public' and tablename = 'ai_memories' order by 1;
--     -- expect 2: the pkey and idx_mem_scope
