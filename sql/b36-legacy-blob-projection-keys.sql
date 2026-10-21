-- b36 (cody) -- READ-ONLY. Does any LIVE row carry a projection key inside its `data` blob?
--
-- WHY: api/b36-projection-runtime-differential.test.js proves at runtime that every
-- current WRITE strips these keys out of `data`. It also measured that on 21 of the 22
-- resources the READ is still Object.assign(columns, data) -- so a blob that DOES carry
-- the key (a row written before its strip list existed) overrides the column on read.
-- Whether any such row exists is a data question only the live database answers.
--
-- SAFE TO RUN: every statement is a SELECT. Nothing is written. Run each statement on its
-- own -- a table that does not exist on this project errors alone and the rest still answer.
-- EXPECTED ANSWER for every row: 0. Any non-zero count names a table and key whose read
-- can show the blob's value instead of the column's -- send the numbers back to cody.

select 'sd_customers' as tbl,
  count(*) filter (where data ? 'id') as has_id
from public.sd_customers;  -- expect every count 0

select 'sd_crm' as tbl,
  count(*) filter (where data ? 'id') as has_id,
  count(*) filter (where data ? 'assigned_employee_id') as has_assigned_employee_id
from public.sd_crm;  -- expect every count 0

select 'sdn_clients' as tbl,
  count(*) filter (where data ? 'id') as has_id,
  count(*) filter (where data ? 'assigned_employee_id') as has_assigned_employee_id
from public.sdn_clients;  -- expect every count 0

select 'bld_bids' as tbl,
  count(*) filter (where data ? 'id') as has_id,
  count(*) filter (where data ? 'assigned_employee_id') as has_assigned_employee_id
from public.bld_bids;  -- expect every count 0

select 'sen_clients' as tbl,
  count(*) filter (where data ? 'id') as has_id,
  count(*) filter (where data ? 'assigned_employee_id') as has_assigned_employee_id
from public.sen_clients;  -- expect every count 0

select 'sen_caregivers' as tbl,
  count(*) filter (where data ? 'id') as has_id
from public.sen_caregivers;  -- expect every count 0

select 'sen_claims' as tbl,
  count(*) filter (where data ? 'id') as has_id
from public.sen_claims;  -- expect every count 0

select 'sen_branches' as tbl,
  count(*) filter (where data ? 'id') as has_id
from public.sen_branches;  -- expect every count 0

select 'sen_payer_contracts' as tbl,
  count(*) filter (where data ? 'id') as has_id
from public.sen_payer_contracts;  -- expect every count 0

select 'sen_authorizations' as tbl,
  count(*) filter (where data ? 'id') as has_id
from public.sen_authorizations;  -- expect every count 0

select 'sen_pay_rates' as tbl,
  count(*) filter (where data ? 'id') as has_id
from public.sen_pay_rates;  -- expect every count 0

select 'sen_franchise_agreements' as tbl,
  count(*) filter (where data ? 'id') as has_id
from public.sen_franchise_agreements;  -- expect every count 0

select 'alf_clients' as tbl,
  count(*) filter (where data ? 'id') as has_id,
  count(*) filter (where data ? 'assigned_employee_id') as has_assigned_employee_id
from public.alf_clients;  -- expect every count 0

select 'alf_staff' as tbl,
  count(*) filter (where data ? 'id') as has_id
from public.alf_staff;  -- expect every count 0

select 'alf_mar' as tbl,
  count(*) filter (where data ? 'id') as has_id,
  count(*) filter (where data ? 'resident_id') as has_resident_id,
  count(*) filter (where data ? 'entry_type') as has_entry_type,
  count(*) filter (where data ? 'assigned_employee_id') as has_assigned_employee_id,
  count(*) filter (where data ? 'created_at') as has_created_at
from public.alf_mar;  -- expect every count 0

select 'alf_billing' as tbl,
  count(*) filter (where data ? 'id') as has_id,
  count(*) filter (where data ? 'resident_id') as has_resident_id
from public.alf_billing;  -- expect every count 0

select 'alf_activities' as tbl,
  count(*) filter (where data ? 'id') as has_id
from public.alf_activities;  -- expect every count 0

select 'alf_facility' as tbl,
  count(*) filter (where data ? 'id') as has_id
from public.alf_facility;  -- expect every count 0

select 'alf_signals' as tbl,
  count(*) filter (where data ? 'id') as has_id,
  count(*) filter (where data ? 'resident_id') as has_resident_id,
  count(*) filter (where data ? 'signal_type') as has_signal_type,
  count(*) filter (where data ? 'recorded_at') as has_recorded_at
from public.alf_signals;  -- expect every count 0

select 'alf_claim_routes' as tbl,
  count(*) filter (where data ? 'id') as has_id,
  count(*) filter (where data ? 'resident_id') as has_resident_id,
  count(*) filter (where data ? 'service_month') as has_service_month,
  count(*) filter (where data ? 'decided_by') as has_decided_by,
  count(*) filter (where data ? 'created_at') as has_created_at
from public.alf_claim_routes;  -- expect every count 0

select 'alf_staff_credentials' as tbl,
  count(*) filter (where data ? 'id') as has_id,
  count(*) filter (where data ? 'staff_id') as has_staff_id,
  count(*) filter (where data ? 'record_type') as has_record_type,
  count(*) filter (where data ? 'recorded_by') as has_recorded_by,
  count(*) filter (where data ? 'created_at') as has_created_at
from public.alf_staff_credentials;  -- expect every count 0
