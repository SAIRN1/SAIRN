-- sql/field_scope_live_fixture_sen_branches_2026-10-28.sql
--
-- CONCEPT. One fixture row for the sen_branches.read live block (cc b64): the
-- branch row on SEN-AUDIT-0002 that `python tools/sairn_field_scope_check.py
-- --live` judges every sairnsenior role against.
--
-- WRITTEN AND RUN BY cc b64. Same shape and guards as
-- sql/field_scope_live_fixtures_2026-10-28.sql (b63). The values are generated
-- from tools/sairn_field_scope_check.py's own seed() over the rule in
-- tools/field_scope_rules.json; nothing here was typed by hand. If the rule
-- changes, regenerate this file or the live judge reports MISSING.
--
-- NO CREDENTIAL ROW. It writes one sen_branches row on an audit licence and
-- nothing else; SEN-AUDIT-0002's five accounts are the b62 file's.
--
-- IF RUN TWICE: the same row, the same values (on conflict do update). If the
-- guard fails, the transaction rolls back and nothing is committed.
-- ---------------------------------------------------------------------------

begin;

insert into public.sen_branches (license_hash, app_id, branch_id, data)
values ('f179514cf3acba9f6626ceb8f9e9b65c34eed3ec181b44dc4c27881b2417165c', 'sairnsenior', 'FSMK1bd0a09798caQ', '{"name": "FSMK3d90b81a44a2Q", "state": "FSMK67ae5414c6f3Q", "active": "FSMK06d07f438a1eQ", "address": "FSMK3db06ef0a777Q", "phone": "FSMK5f7b5e5ab523Q", "updatedBy": "FSMK73ee29427838Q", "updatedByRole": "FSMK9a27c67401adQ"}'::jsonb)
on conflict (license_hash, branch_id) do update set data = excluded.data, updated_at = now();

do $$
declare n int;
begin
  if encode(digest('SEN-AUDIT-0002', 'sha256'), 'hex') <> 'f179514cf3acba9f6626ceb8f9e9b65c34eed3ec181b44dc4c27881b2417165c' then
    raise exception 'ABORTED: license_hash literal for SEN-AUDIT-0002 is wrong. Nothing committed.';
  end if;
  select count(*) into n from public.sen_branches where license_hash = 'f179514cf3acba9f6626ceb8f9e9b65c34eed3ec181b44dc4c27881b2417165c';
  if n <> 1 then
    raise exception 'ABORTED: sen_branches on SEN-AUDIT-0002 has % row(s), not exactly the 1 fixture -- the live judge needs a fully known table. Nothing committed.', n;
  end if;
  raise notice 'sen_branches fixture: guard passed';
end $$;

commit;
