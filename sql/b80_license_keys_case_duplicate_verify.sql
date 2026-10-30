-- cc b80: NOT RUN. Read-only. Proves no two license_keys rows differ only in case.
-- EXPECT: case_only_duplicate_groups = 0. keys_not_upper_case is context (expected 0).
select
  (select count(*)
     from (select upper(key)
             from public.license_keys
            group by upper(key)
           having count(*) > 1) g)                                 as case_only_duplicate_groups,
  (select count(*) from public.license_keys where key <> upper(key)) as keys_not_upper_case,
  (select count(*) from public.license_keys where key <> btrim(key)) as keys_with_edge_whitespace;
