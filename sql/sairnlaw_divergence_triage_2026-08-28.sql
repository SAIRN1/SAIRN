-- sql/sairnlaw_divergence_triage_2026-08-28.sql
-- READ-ONLY. No insert, update, delete, grant, revoke, alter, drop, truncate.
-- No dynamic SQL either -- both tables and both licences are known, so this is
-- plain static SQL and none of the query_to_xml fragility applies.
--
-- ── WHY THIS FILE EXISTS ─────────────────────────────────────────────────
-- The platform divergence audit found law_deadline_rules with 87 diverged
-- entry_ids and law_holidays with 48, both between LAW-PINNACLE-2026 and
-- LAW-TEST-2026, and ZERO divergence in every other reference table on the
-- platform. That is a real signal, but 87 is not one finding -- it is a bucket
-- holding at least two different things:
--
--   (a) LEGITIMATE: LAW-TEST-2026 deliberately holds newer or experimental
--       content ahead of LAW-PINNACLE-2026. Divergence here is the system
--       working as intended.
--   (b) A LIVE DEFECT: one licence holds the PRE-FIX copy of a rule that was
--       corrected on 2026-08-27, and is therefore computing a wrong legal
--       deadline today while looking exactly as authoritative as the right one.
--
-- This file separates the two before anyone concludes anything.
--
-- ── THE DISCRIMINATOR IS MECHANICAL, NOT A JUDGMENT CALL ────────────────
-- Commit e1aa3f8 fixed federal answer deadlines that ran THREE DAYS LATE on
-- mailed service. Read from the diff, the fix REMOVED the `service_extension`
-- object (standard frcp_6d, add 3) from exactly two rows, and deliberately KEPT
-- it on a third neighbour. The corrected state, as it stands in
-- sql/sairnlaw_deadline_seed_us_federal.json today:
--
--   frcp-12a1Ai-answer-after-service            service_extension ABSENT   (fixed)
--   frcp-12a2-united-states-official-capacity   service_extension ABSENT   (fixed)
--   frcp-12a1B-counterclaim-crossclaim          service_extension PRESENT  (correct)
--
-- So for these three rows there is nothing to eyeball. A licence whose copy of
-- either fixed row still carries service_extension is running the pre-fix rule.
-- And a licence MISSING it on the counterclaim row has the opposite error --
-- someone applied the fix too broadly. Query 1 reports both directions.
--
-- Reasoning, quoted from the corrected seed so it is not re-derived: Rule 6(d)
-- adds three days only for service under Rule 5(b)(2)(C), (D) or (F). A summons
-- and complaint are served under RULE 4, a different rule for a different stage,
-- and 6(d) does not reach it. A counterclaim IS a paper served between parties
-- under Rule 5, so that row keeps its three days.

-- ── ONE NAMING TRAP, checked rather than assumed ─────────────────────────
-- The seed files call the identifier `rule_id`; the TABLE column is `entry_id`.
-- They are the same value under two names, mapped at load time. Every query
-- below reads the DB column `entry_id`. Mentioned because a reader comparing a
-- seed file against this SQL will otherwise think one of them is wrong.
--
-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 1 -- THE THREE ROWS THE FEDERAL FIX TOUCHED. Verdict, not a blob.
-- Run this first. It is the only part with a right answer known in advance.
-- ═════════════════════════════════════════════════════════════════════════
with lic as (
  select 'LAW-PINNACLE-2026' as key, encode(digest('LAW-PINNACLE-2026','sha256'),'hex') as h
  union all
  select 'LAW-TEST-2026',            encode(digest('LAW-TEST-2026','sha256'),'hex')
),
target(entry_id_like, expected_extension, why) as (values
  ('frcp-12a1Ai-answer-after-service%', false,
   'Rule 4 service -- 6(d) does not reach it; extension REMOVED by e1aa3f8'),
  ('frcp-12a2%',                        false,
   'service on the US attorney is Rule 4(i) process, not a Rule 5 paper; REMOVED by e1aa3f8'),
  ('frcp-12a1B-counterclaim%',          true,
   'a counterclaim IS served under Rule 5 -- this row KEEPS its three days')
)
select
  t.entry_id_like                                   as rule_pattern,
  l.key                                             as licence,
  r.entry_id,
  (r.data ? 'service_extension')                    as has_extension,
  t.expected_extension                              as should_have_extension,
  case
    when r.entry_id is null then 'ROW ABSENT on this licence'
    when (r.data ? 'service_extension') = t.expected_extension then 'CORRECT'
    when t.expected_extension = false then
      'STALE -- PRE-FIX COPY. This licence adds 3 days it should not: deadlines run LATE.'
    else
      'OVER-APPLIED -- the fix was taken too far; this row should keep its extension.'
  end                                               as verdict,
  r.data #>> '{service_extension,standard}'         as extension_standard,
  r.data #>> '{service_extension,add}'              as extension_days,
  -- The fix's reasoning lives in `computation`, NOT in a `note` key. Verified
  -- against the seed: these rows carry rule_id / jurisdiction / domain / label /
  -- trigger_event / count / computation / authority / effective_from /
  -- effective_to / version / supersedes, and `service_extension` only where it
  -- belongs. An earlier draft of this query read `note` and would have shown a
  -- blank column on every row while looking like it had checked something.
  left(coalesce(r.data ->> 'computation',''), 110)  as computation_prefix
from target t
cross join lic l
left join public.law_deadline_rules r
       on r.license_hash = l.h and r.entry_id like t.entry_id_like
order by t.entry_id_like, l.key;

-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 2 -- BUCKET ALL 87 (and the 48 holidays) BY *SHAPE* OF DIFFERENCE.
-- This is what turns one undifferentiated number into triage.
--
--   NEWER_CONTENT     one licence's blob is a strict SUPERSET of the other's --
--                     same values wherever both have a key, plus extra keys on
--                     one side. That is the signature of LAW-TEST holding newer
--                     content, and is almost certainly legitimate.
--   VALUE_CONFLICT    both licences have the SAME key with DIFFERENT values.
--                     This is where a stale-vs-corrected rule hides. Read these.
--   ONE_SIDED         the entry exists on only one licence. Not a conflict; it
--                     is content one licence never received.
-- ═════════════════════════════════════════════════════════════════════════
with p as (select encode(digest('LAW-PINNACLE-2026','sha256'),'hex') as h),
     t as (select encode(digest('LAW-TEST-2026','sha256'),'hex')      as h),
pairs as (
  select
    coalesce(a.entry_id, b.entry_id) as entry_id,
    a.data as pin_data,
    b.data as test_data
  from (select entry_id, data from public.law_deadline_rules, p where license_hash = p.h) a
  full outer join
       (select entry_id, data from public.law_deadline_rules, t where license_hash = t.h) b
    on a.entry_id = b.entry_id
),
classified as (
  select
    entry_id,
    case
      when pin_data is null or test_data is null then 'ONE_SIDED'
      when exists (
        select 1
        from jsonb_each(pin_data) pk
        join jsonb_each(test_data) tk on tk.key = pk.key
        where pk.value is distinct from tk.value
      ) then 'VALUE_CONFLICT'
      when pin_data <> test_data then 'NEWER_CONTENT'
      else 'identical'
    end as diff_shape,
    (select string_agg(pk.key, ', ' order by pk.key)
       from jsonb_each(pin_data) pk
       join jsonb_each(test_data) tk on tk.key = pk.key
      where pk.value is distinct from tk.value) as conflicting_keys
  from pairs
)
select diff_shape, count(*) as entries, string_agg(entry_id, ', ' order by entry_id) as ids
from classified
where diff_shape <> 'identical'
group by diff_shape
order by case diff_shape when 'VALUE_CONFLICT' then 1 when 'ONE_SIDED' then 2 else 3 end;

-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 3 -- THE VALUE CONFLICTS, KEY BY KEY. Only the rows query 2 bucketed as
-- VALUE_CONFLICT, showing exactly which field disagrees and both values.
-- This is the "diff a handful of the highest-stakes ones directly" step, done
-- for all of them at once because the field-level view is small enough to read.
-- ═════════════════════════════════════════════════════════════════════════
with p as (select encode(digest('LAW-PINNACLE-2026','sha256'),'hex') as h),
     t as (select encode(digest('LAW-TEST-2026','sha256'),'hex')      as h)
select
  a.entry_id,
  pk.key                                as conflicting_field,
  left(pk.value::text, 120)             as law_pinnacle_value,
  left(tk.value::text, 120)             as law_test_value
from (select entry_id, data from public.law_deadline_rules, p where license_hash = p.h) a
join (select entry_id, data from public.law_deadline_rules, t where license_hash = t.h) b
  on a.entry_id = b.entry_id
join jsonb_each(a.data) pk on true
join jsonb_each(b.data) tk on tk.key = pk.key
where pk.value is distinct from tk.value
order by
  -- Field names taken from the real seed, not guessed: a rule row carries
  -- rule_id / jurisdiction / domain / label / trigger_event / count /
  -- computation / service_extension / authority / effective_from /
  -- effective_to / version / supersedes.
  -- Tier 0 CHANGES THE DATE. Tier 1 changes what the row claims about itself.
  -- Tier 2 is prose that diverges without moving any deadline.
  case
    when pk.key in ('count','trigger_event','service_extension',
                    'effective_from','effective_to') then 0
    when pk.key in ('jurisdiction','domain','version','supersedes') then 1
    else 2
  end,
  a.entry_id, pk.key;

-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 4 -- the same bucketing for law_holidays (48 diverged).
-- Holidays are lower stakes per row but feed EVERY deadline calculation, so a
-- calendar that disagrees between licences moves dates on rules that are
-- otherwise identical.
-- ═════════════════════════════════════════════════════════════════════════
with p as (select encode(digest('LAW-PINNACLE-2026','sha256'),'hex') as h),
     t as (select encode(digest('LAW-TEST-2026','sha256'),'hex')      as h),
pairs as (
  select coalesce(a.entry_id,b.entry_id) as entry_id, a.data as pin_data, b.data as test_data
  from (select entry_id, data from public.law_holidays, p where license_hash = p.h) a
  full outer join
       (select entry_id, data from public.law_holidays, t where license_hash = t.h) b
    on a.entry_id = b.entry_id
)
select
  case
    when pin_data is null or test_data is null then 'ONE_SIDED'
    when exists (select 1 from jsonb_each(pin_data) pk
                 join jsonb_each(test_data) tk on tk.key = pk.key
                 where pk.value is distinct from tk.value) then 'VALUE_CONFLICT'
    else 'NEWER_CONTENT'
  end as diff_shape,
  count(*) as entries,
  string_agg(entry_id, ', ' order by entry_id) as ids
from pairs
where pin_data is distinct from test_data
group by 1
order by 1;

-- ═════════════════════════════════════════════════════════════════════════
-- HOW TO READ THE RESULT, and what NOT to conclude
-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 1 is the one with a known right answer. Any 'STALE -- PRE-FIX COPY' row
--   is a live defect on that licence today: it adds three days to a federal
--   answer deadline that Rule 6(d) does not reach, in the direction that loses a
--   filing. 'OVER-APPLIED' is the mirror error and is equally wrong.
--
-- QUERY 2/4 turn 87 and 48 into buckets. NEWER_CONTENT and ONE_SIDED are the
--   expected shape if LAW-TEST is simply ahead -- that is a provisioning gap,
--   not a correctness bug, and it argues for the shared-rules redesign rather
--   than for an urgent data fix.
--
-- QUERY 3 is where a real defect would show as something other than prose:
--   a differing `period`, `unit`, `trigger`, `service_extension` or
--   `holiday_calendar` on the SAME entry_id means the two licences compute
--   different dates from identical inputs. `note` differences are excluded
--   deliberately -- they are commentary and diverge without changing behaviour.
--
-- ⚠ WHAT THIS FILE CANNOT TELL YOU: which licence is RIGHT. It can prove the two
--   disagree and, for the three federal rows, which side matches the corrected
--   seed in the repo. For everything else, the seed files under sql/ are the
--   authority, and a conflict should be resolved against the seed rather than by
--   preferring whichever licence looks newer.
--
-- ⚠ AND THE OBVIOUS ONE, worth saying because 87 is a frightening number: none
--   of this is evidence that any CUSTOMER has a wrong deadline. Both of these
--   are internal licences. The finding is about the mechanism -- rules are
--   copied per licence and drift silently -- which is exactly what the
--   platform-wide scoping problem predicts, now with a measurement attached.
