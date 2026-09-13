-- sql/ledger_balance_trigger.sql
-- Item 41, phase B. Makes "debits equal credits" a rule THE DATABASE enforces
-- on a posted entry, instead of a rule one endpoint happens to obey.
--
-- ══ NOT RUN. ═══════════════════════════════════════════════════════════════
-- Nothing has executed this against the live database as of 2026-09-13, and it
-- must not be run before the pre-flight in section 0 comes back with zero rows.
-- Idempotent and safe to re-run once it has been.
--
-- ══ WHAT IT BUYS, AND WHAT IT DOES NOT ═════════════════════════════════════
-- api/_lib/ledger.js's header already states the honest limit: a Postgres CHECK
-- cannot span rows, so the guarantee today is "no code path writes an
-- unbalanced entry", not "the database would refuse one". That holds because
-- api/ledger.js is the only writer. IT HOLDS BY COINCIDENCE OF STAFFING, NOT BY
-- CONSTRUCTION -- a future writer, another app, a migration, or a support
-- script inherits none of it. This closes that.
--
-- IT IS A CONTROL, NOT AN ELIMINATION. It cannot make an unbalanced entry
-- unrepresentable; it makes one unpostable. entryFromTransfers() in
-- api/_lib/ledger.js is the elimination half, and it only covers entries with a
-- single account on one side. See docs/2026-09-13-prevent-by-construction-review.md.
--
-- ══ WHY IT FIRES ON THE STATUS FLIP AND NOT ON THE LINES ═══════════════════
-- THIS IS THE PART THAT IS EASY TO GET WRONG. api/ledger.js writes in three
-- SEPARATE HTTP CALLS -- header as draft, then the lines, then PATCH status to
-- posted -- so there is no transaction for a DEFERRABLE constraint trigger to
-- sit inside. A deferred trigger on ledger_lines would fire at the end of the
-- LINES call, when the entry is still legitimately an unbalanced draft, and
-- would reject every ordinary post.
--
-- Firing on the entry's status instead also makes the rule exactly as narrow as
-- it should be: a draft is ALLOWED to be unbalanced, and a posted entry is not.
--
-- ══ WHAT IT STILL CANNOT SEE, said here rather than found later ════════════
-- ledger_lines has NO FOREIGN KEY to ledger_entries -- the schema's own comment
-- says so and gives the platform-convention reason. So a line naming an entry
-- that does not exist is still representable, and this trigger will not see it:
-- it sums the lines that claim the entry_id, and an orphan claims a different
-- one. Adding that FK is a separate decision with a separate migration, and it
-- is NOT bundled here. Nobody should read a passing trigger as closing it.

-- ---------------------------------------------------------------------------
-- 0. PRE-FLIGHT. Run this FIRST, on its own, and read the result.
-- ---------------------------------------------------------------------------
-- If any posted entry already fails the rule, creating the trigger will make
-- the NEXT ordinary update to that row fail -- including an updated_at touch --
-- and the failure would surface far from here. Expect ZERO rows. If it is not
-- zero, stop and fix the data first; do not create the trigger and do not
-- "temporarily" widen the rule.
--
--   select e.license_hash, e.entry_id, e.status,
--          coalesce(sum(l.debit), 0)  as debits,
--          coalesce(sum(l.credit), 0) as credits,
--          count(l.id)                as lines
--     from public.ledger_entries e
--     left join public.ledger_lines l
--       on l.license_hash = e.license_hash and l.entry_id = e.entry_id
--    where e.status = 'posted'
--    group by e.license_hash, e.entry_id, e.status
--   having coalesce(sum(l.debit), 0) <> coalesce(sum(l.credit), 0)
--       or count(l.id) < 2;

-- ---------------------------------------------------------------------------
-- 1. The function.
-- ---------------------------------------------------------------------------
create or replace function public.ledger_posted_must_balance()
returns trigger
language plpgsql
as $$
declare
  v_debits  numeric(14,2);
  v_credits numeric(14,2);
  v_lines   integer;
begin
  -- Matched on (license_hash, entry_id) because that is the entry's identity:
  -- ledger_entries is unique on exactly that pair, and app_id is not part of
  -- it. Summing on app_id too would silently exclude a line written under a
  -- different app_id and let the entry post half-counted.
  select coalesce(sum(l.debit), 0), coalesce(sum(l.credit), 0), count(*)
    into v_debits, v_credits, v_lines
    from public.ledger_lines l
   where l.license_hash = new.license_hash
     and l.entry_id     = new.entry_id;

  -- A single-sided post is the exact defect the old gl_entries writers shipped,
  -- so it is named separately rather than folded into "does not balance" -- an
  -- entry with one line balances against nothing and would otherwise pass the
  -- sum test whenever that line is zero.
  if v_lines < 2 then
    raise exception
      'ledger entry % has % line(s); a posted entry needs at least two',
      new.entry_id, v_lines
      using errcode = 'check_violation';
  end if;

  if v_debits <> v_credits then
    -- Both totals and the gap, for the reason the engine's own message gives
    -- them: "does not balance" without the numbers is something a human has to
    -- reproduce by hand before they can act on it.
    raise exception
      'ledger entry % does not balance: debits %, credits %, out by %',
      new.entry_id, v_debits, v_credits, abs(v_debits - v_credits)
      using errcode = 'check_violation';
  end if;

  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- 2. The trigger.
-- ---------------------------------------------------------------------------
-- AFTER, not BEFORE: the row's final state is what the rule is about, and a
-- raise here rolls the statement back either way.
--
-- INSERT is covered as well as UPDATE, deliberately. api/ledger.js never
-- inserts a row already marked posted -- it writes a draft and flips it -- so
-- covering INSERT costs the live path nothing and closes the one door a
-- DIFFERENT writer would come through, which is the entire reason this file
-- exists.
--
-- The WHEN clause is `new.status = 'posted'` and nothing more. A later
-- ordinary UPDATE to an already-posted row re-runs the check; that is cheap and
-- strictly more protective, since it also stops a posted entry being edited
-- into imbalance. Narrowing it with `old.status is distinct from 'posted'`
-- would buy a little work back and give that up.
drop trigger if exists ledger_posted_must_balance on public.ledger_entries;
create trigger ledger_posted_must_balance
  after insert or update on public.ledger_entries
  for each row
  when (new.status = 'posted')
  execute function public.ledger_posted_must_balance();

-- ---------------------------------------------------------------------------
-- 3. Verify it BITES, do not assume. Expect an ERROR from the third statement.
-- ---------------------------------------------------------------------------
-- A trigger nobody has seen refuse anything is not known to be a trigger --
-- five promoted checkers on this platform had no control proving they could
-- fire. Run all four, in order, in a transaction you roll back:
--
--   begin;
--   insert into public.ledger_entries
--     (license_hash, app_id, entry_id, entry_date, memo, status)
--   values ('trigtest','sairnbiz','JE-TRIG',current_date,'trigger control','draft');
--
--   insert into public.ledger_lines
--     (license_hash, app_id, entry_id, line_no, account_code, debit, credit)
--   values ('trigtest','sairnbiz','JE-TRIG',1,'1100',1200,0),
--          ('trigtest','sairnbiz','JE-TRIG',2,'4010',0,1100);
--
--   -- EXPECT: ERROR ... does not balance: debits 1200.00, credits 1100.00, out by 100.00
--   update public.ledger_entries set status = 'posted', posted_at = current_date
--    where license_hash = 'trigtest' and entry_id = 'JE-TRIG';
--
--   rollback;
--
-- Then the positive control, so a trigger that refuses EVERYTHING is not
-- mistaken for one that works -- same transaction shape, credit 1200 instead of
-- 1100, and the update must SUCCEED. Roll that back too.
--
-- Then re-run sql/schema_snapshot_query.sql so db/schema_snapshot.json carries
-- the trigger.
