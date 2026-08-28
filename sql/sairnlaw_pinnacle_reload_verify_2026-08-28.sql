-- sql/sairnlaw_pinnacle_reload_verify_2026-08-28.sql
-- READ-ONLY. No insert, update, delete, grant, revoke, alter, drop, truncate.
-- Independent verification of Hank's LAW-PINNACLE-2026 reload, plus the
-- compute-diff that closes the ~84-row caveat left open by the triage file.
--
-- ── WHY A SECOND PAIR OF EYES NEEDS TO BE A DIFFERENT PAIR ──────────────
-- These expectations were derived from the SEED FILES in this repo, read
-- directly, not from Hank's reload script and not from his report. If the
-- reload loaded the wrong thing, a check written from the same script would
-- agree with it. This one can disagree.
--
-- ── THE EXPECTED STATE, read from the seeds on 2026-08-28 ───────────────
-- Note the three rows do NOT share an expectation. Two must have LOST their
-- extension; one must KEEP one. A check that assumes a single direction would
-- pass the federal rows and quietly mis-grade Florida.
--
--   frcp-12a1Ai-answer-after-service           count 21 cd fwd   ext ABSENT
--     (sql/sairnlaw_deadline_seed_us_federal.json -- Rule 4 service; 6(d) does
--      not reach it. Extension removed by e1aa3f8.)
--
--   frcp-12a2-united-states-official-capacity  count 60 cd fwd   ext ABSENT
--     (same seed -- service on the US attorney is Rule 4(i) process, not a
--      Rule 5 paper. Extension removed by e1aa3f8.)
--
--   fl-rcp-1140a1-answer-to-complaint          count 20 cd fwd   ext PRESENT
--     (sql/sairnlaw_deadline_seed_florida.json -- Florida genuinely HAS a mail
--      extension under Rule 2.514(b), so PRESENT is correct here. Full shape:
--      standard fl_rgpja_2514b, add 5, calendar_days, order after,
--      requires_exclusive TRUE, on_unknown_exclusivity assume_exclusive.)
--
-- ⚠ FOR FLORIDA, PRESENCE ALONE IS NOT THE TEST. The 2026-08-27 exclusivity fix
-- added `requires_exclusive` / `on_unknown_exclusivity`. A stale copy could
-- carry a service_extension that LOOKS right and still be wrong, because
-- without requires_exclusive it applies five days unconditionally instead of
-- only when service was by mail ALONE. Query 1 checks the fields, not the key.

-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 1 -- THE THREE ROWS, FIELD BY FIELD, AGAINST THE SEED VALUES.
-- Every column ending _ok must be true. Run this first.
-- ═════════════════════════════════════════════════════════════════════════
with lic as (
  select 'LAW-PINNACLE-2026' as key, encode(digest('LAW-PINNACLE-2026','sha256'),'hex') as h
  union all
  select 'LAW-TEST-2026',            encode(digest('LAW-TEST-2026','sha256'),'hex')
),
expected(entry_id, want_count, want_ext, want_standard, want_add, want_req_excl) as (values
  ('frcp-12a1Ai-answer-after-service',          21, false, null,              null,      null),
  ('frcp-12a2-united-states-official-capacity', 60, false, null,              null,      null),
  ('fl-rcp-1140a1-answer-to-complaint',         20, true,  'fl_rgpja_2514b',  '5',       true)
)
select
  l.key                                                as licence,
  e.entry_id,
  (r.entry_id is not null)                             as row_present,
  (r.data #>> '{count,value}')::int                    as actual_count,
  e.want_count,
  ((r.data #>> '{count,value}')::int = e.want_count)   as count_ok,
  (r.data ? 'service_extension')                       as actual_has_ext,
  e.want_ext,
  ((r.data ? 'service_extension') = e.want_ext)        as ext_presence_ok,
  r.data #>> '{service_extension,standard}'            as actual_standard,
  r.data #>> '{service_extension,add}'                 as actual_add,
  r.data #>> '{service_extension,requires_exclusive}'  as actual_requires_exclusive,
  -- full shape check: for the two federal rows this is trivially true because
  -- there should be no extension at all; for Florida it is the real test.
  (coalesce(r.data #>> '{service_extension,standard}','')            = coalesce(e.want_standard,'')
   and coalesce(r.data #>> '{service_extension,add}','')             = coalesce(e.want_add,'')
   and coalesce(r.data #>> '{service_extension,requires_exclusive}','')
       = coalesce(e.want_req_excl::text,''))           as ext_shape_ok,
  case
    when r.entry_id is null then 'ROW MISSING -- the reload did not land this rule'
    when (r.data ? 'service_extension') <> e.want_ext and e.want_ext = false
      then 'STALE -- still carries the pre-fix extension; deadlines run LATE'
    when (r.data ? 'service_extension') <> e.want_ext and e.want_ext = true
      then 'STALE -- extension missing; Florida mail allowance not applied'
    when coalesce(r.data #>> '{service_extension,requires_exclusive}','')
         <> coalesce(e.want_req_excl::text,'')
      then 'PARTIAL -- extension present but PRE-EXCLUSIVITY shape; 5 days applied unconditionally'
    when (r.data #>> '{count,value}')::int <> e.want_count
      then 'WRONG BASE PERIOD'
    else 'MATCHES SEED'
  end                                                  as verdict
from expected e
cross join lic l
left join public.law_deadline_rules r
       on r.license_hash = l.h and r.entry_id = e.entry_id
order by e.entry_id, l.key;

-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 2 -- CLOSE THE ~84-ROW CAVEAT. Compute-diff only.
--
-- The earlier triage bucketed by "any field differs", which is why the count
-- came out at 87 and why most of it turned out to be metadata noise. This
-- compares ONLY the fields that can move a date, so a residual conflict here is
-- a real one. Metadata (verified_by, version, supersedes, authority, label,
-- computation prose) is excluded deliberately and listed so the exclusion is
-- auditable rather than hidden.
-- ═════════════════════════════════════════════════════════════════════════
with p as (select encode(digest('LAW-PINNACLE-2026','sha256'),'hex') as h),
     t as (select encode(digest('LAW-TEST-2026','sha256'),'hex')      as h),
compute_fields(f) as (values ('count'),('trigger_event'),('service_extension'),
                             ('effective_from'),('effective_to'),('jurisdiction'),('domain')),
pairs as (
  select coalesce(a.entry_id,b.entry_id) as entry_id, a.data as pin, b.data as tst
  from (select entry_id,data from public.law_deadline_rules, p where license_hash=p.h) a
  full outer join
       (select entry_id,data from public.law_deadline_rules, t where license_hash=t.h) b
    on a.entry_id=b.entry_id
)
select
  pr.entry_id,
  cf.f                                as compute_field,
  left(pr.pin -> cf.f #>> '{}', 100)  as law_pinnacle,
  left(pr.tst -> cf.f #>> '{}', 100)  as law_test,
  case when pr.pin is null then 'MISSING on PINNACLE'
       when pr.tst is null then 'MISSING on TEST'
       else 'VALUE DIFFERS' end       as shape
from pairs pr
cross join compute_fields cf
where pr.pin is null or pr.tst is null
   or (pr.pin -> cf.f) is distinct from (pr.tst -> cf.f)
order by pr.entry_id, cf.f;

-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 3 -- THE HEADLINE NUMBER, so the caveat can be closed with a figure.
-- ═════════════════════════════════════════════════════════════════════════
with p as (select encode(digest('LAW-PINNACLE-2026','sha256'),'hex') as h),
     t as (select encode(digest('LAW-TEST-2026','sha256'),'hex')      as h),
pairs as (
  select coalesce(a.entry_id,b.entry_id) as entry_id, a.data as pin, b.data as tst
  from (select entry_id,data from public.law_deadline_rules, p where license_hash=p.h) a
  full outer join
       (select entry_id,data from public.law_deadline_rules, t where license_hash=t.h) b
    on a.entry_id=b.entry_id
)
select
  count(*) filter (where pin is not null and tst is not null
                     and (pin->'count')            is distinct from (tst->'count')
                      or (pin->'trigger_event')    is distinct from (tst->'trigger_event')
                      or (pin->'service_extension')is distinct from (tst->'service_extension'))
    as rows_that_compute_a_different_date,
  count(*) filter (where pin is null or tst is null)          as rows_on_only_one_licence,
  count(*) filter (where pin is distinct from tst)            as rows_differing_at_all,
  count(*)                                                    as rows_total
from pairs;

-- ═════════════════════════════════════════════════════════════════════════
-- READING IT
-- ═════════════════════════════════════════════════════════════════════════
-- QUERY 1: every *_ok column true and verdict 'MATCHES SEED' on
--   LAW-PINNACLE-2026 means the reload landed correctly for the rules that
--   matter. LAW-TEST-2026 is expected to still differ -- it is a stale internal
--   test tenant and is NOT authoritative; seeds are. Do not "fix" TEST to match.
--
-- QUERY 3's `rows_that_compute_a_different_date` is the number that closes the
--   caveat. If it is 0, the remaining divergence is metadata and the ~84 are
--   noise, confirmed rather than assumed. If it is not 0, query 2 names exactly
--   which rows and which field, and those resolve AGAINST THE SEED FILES.
--
-- ⚠ WHAT THIS FILE CANNOT DO: it cannot tell you the reload ran. It can only
--   tell you what the licence holds NOW. If query 1 says MATCHES SEED, that is
--   consistent with a successful reload but also with the rows having been
--   correct already -- the distinction only matters if someone needs to prove
--   the reload itself executed, which is a different question from whether the
--   data is right.
