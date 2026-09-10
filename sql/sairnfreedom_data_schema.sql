-- sql/sairnfreedom_data_schema.sql
-- SAIRNfreedom application data -- the post's records reach a server.
--
-- Run this once in the Supabase SQL editor. Every statement is idempotent
-- (create table if not exists), safe to re-run. Until it runs, every write
-- answers 503 NOT_PROVISIONED naming this file and every read answers
-- provisioned:false.
--
-- ALSO REQUIRES sql/sairnfreedom_license_seed.sql. SAIRNfreedom had NO
-- licence row of any kind before 2026-09-09 -- its only server call was
-- /api/claude, which takes no licence -- so without that seed every write
-- here answers 401 INVALID_LICENSE and the tables sit empty. Run both.
--
-- WHY THIS FILE EXISTS, MEASURED. tools/local_only_collection_check.py on
-- 2026-09-09 reported sairnfreedom.html as 35 of 35 collections with NO route
-- to a server. Membership, the ledger, gaming sessions, gaming expenses and
-- CHARITABLE DISBURSEMENTS -- the ORC 2915 reportable side of a fraternal
-- post's gaming -- lived in one browser and nowhere else.
--
-- THIRTY-FIVE TABLES. The seven keys this app writes that are NOT here are
-- device state or configuration, and each is named with its reason in
-- api/_resources/sairnfreedom.js rather than left as an absence.
--
-- ID COLUMN NAMING: mechanical singularisation of the resource name (strip
-- sf_, singularise, -ies -> -y), the same rule as every other app's schema.
--
-- ONE RECORD SHAPE NEEDED AN ID AND NOW MINTS ONE. sf_district_imports
-- pushed {entityId, year, fingerprint, ...} with no id. Its natural identity
-- is the district entity plus the report year, so the client now writes
-- `id: entityId + '-' + year`. That is deterministic: re-importing the same
-- district-year UPDATES its row rather than adding a duplicate, which is the
-- correct behaviour for a signed import record and is why a Date.now() id
-- would have been wrong here.
--
-- SECURITY MODEL: licence key only, RLS enabled with no anon policy,
-- api/sd-data.js the only door in. SAIRNfreedom has no per-employee
-- authentication. 64KB per row's data jsonb.
--
-- NO `delete` GRANT ANYWHERE IN THIS FILE. `revoke all` precedes each grant
-- because a bare grant cannot remove what the default ACL already handed over.

create extension if not exists pgcrypto;

-- Chart of accounts.
create table if not exists public.sf_accounts (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  account_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, account_id),
  constraint sf_accounts_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_accounts enable row level security;
drop policy if exists "svc only sf_accounts" on public.sf_accounts;
create policy "svc only sf_accounts" on public.sf_accounts
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_accounts from service_role;
grant select, insert, update on public.sf_accounts to service_role;

-- Automatic bottle-fill determinations.
create table if not exists public.sf_bottle_fills (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  bottle_fill_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, bottle_fill_id),
  constraint sf_bottle_fills_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_bottle_fills enable row level security;
drop policy if exists "svc only sf_bottle_fills" on public.sf_bottle_fills;
create policy "svc only sf_bottle_fills" on public.sf_bottle_fills
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_bottle_fills from service_role;
grant select, insert, update on public.sf_bottle_fills to service_role;

-- Ceremonial equipment.
create table if not exists public.sf_ceremonial_items (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  ceremonial_item_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, ceremonial_item_id),
  constraint sf_ceremonial_items_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_ceremonial_items enable row level security;
drop policy if exists "svc only sf_ceremonial_items" on public.sf_ceremonial_items;
create policy "svc only sf_ceremonial_items" on public.sf_ceremonial_items
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_ceremonial_items from service_role;
grant select, insert, update on public.sf_ceremonial_items to service_role;

-- Charitable disbursements -- the regulated side of gaming proceeds.
create table if not exists public.sf_disbursements (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  disbursement_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, disbursement_id),
  constraint sf_disbursements_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_disbursements enable row level security;
drop policy if exists "svc only sf_disbursements" on public.sf_disbursements;
create policy "svc only sf_disbursements" on public.sf_disbursements
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_disbursements from service_role;
grant select, insert, update on public.sf_disbursements to service_role;

-- Signed district report imports. district_import_id is entityId + report year -- see the id-column note.
create table if not exists public.sf_district_imports (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  district_import_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, district_import_id),
  constraint sf_district_imports_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_district_imports enable row level security;
drop policy if exists "svc only sf_district_imports" on public.sf_district_imports;
create policy "svc only sf_district_imports" on public.sf_district_imports
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_district_imports from service_role;
grant select, insert, update on public.sf_district_imports to service_role;

-- Post documents.
create table if not exists public.sf_documents (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  document_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, document_id),
  constraint sf_documents_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_documents enable row level security;
drop policy if exists "svc only sf_documents" on public.sf_documents;
create policy "svc only sf_documents" on public.sf_documents
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_documents from service_role;
grant select, insert, update on public.sf_documents to service_role;

-- Donations received.
create table if not exists public.sf_donations (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  donation_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, donation_id),
  constraint sf_donations_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_donations enable row level security;
drop policy if exists "svc only sf_donations" on public.sf_donations;
create policy "svc only sf_donations" on public.sf_donations
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_donations from service_role;
grant select, insert, update on public.sf_donations to service_role;

-- Donor awards.
create table if not exists public.sf_donor_awards (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  donor_award_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, donor_award_id),
  constraint sf_donor_awards_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_donor_awards enable row level security;
drop policy if exists "svc only sf_donor_awards" on public.sf_donor_awards;
create policy "svc only sf_donor_awards" on public.sf_donor_awards
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_donor_awards from service_role;
grant select, insert, update on public.sf_donor_awards to service_role;

-- Donor tier definitions.
create table if not exists public.sf_donor_tiers (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  donor_tier_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, donor_tier_id),
  constraint sf_donor_tiers_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_donor_tiers enable row level security;
drop policy if exists "svc only sf_donor_tiers" on public.sf_donor_tiers;
create policy "svc only sf_donor_tiers" on public.sf_donor_tiers
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_donor_tiers from service_role;
grant select, insert, update on public.sf_donor_tiers to service_role;

-- Hall events.
create table if not exists public.sf_events (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  event_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, event_id),
  constraint sf_events_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_events enable row level security;
drop policy if exists "svc only sf_events" on public.sf_events;
create policy "svc only sf_events" on public.sf_events
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_events from service_role;
grant select, insert, update on public.sf_events to service_role;

-- Gaming expenses -- ORC 2915 reportable.
create table if not exists public.sf_gaming_expenses (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  gaming_expense_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, gaming_expense_id),
  constraint sf_gaming_expenses_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_gaming_expenses enable row level security;
drop policy if exists "svc only sf_gaming_expenses" on public.sf_gaming_expenses;
create policy "svc only sf_gaming_expenses" on public.sf_gaming_expenses
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_gaming_expenses from service_role;
grant select, insert, update on public.sf_gaming_expenses to service_role;

-- Honour-guard details.
create table if not exists public.sf_honor_details (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  honor_detail_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, honor_detail_id),
  constraint sf_honor_details_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_honor_details enable row level security;
drop policy if exists "svc only sf_honor_details" on public.sf_honor_details;
create policy "svc only sf_honor_details" on public.sf_honor_details
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_honor_details from service_role;
grant select, insert, update on public.sf_honor_details to service_role;

-- Bar inventory counts.
create table if not exists public.sf_inventory_counts (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  inventory_count_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, inventory_count_id),
  constraint sf_inventory_counts_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_inventory_counts enable row level security;
drop policy if exists "svc only sf_inventory_counts" on public.sf_inventory_counts;
create policy "svc only sf_inventory_counts" on public.sf_inventory_counts
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_inventory_counts from service_role;
grant select, insert, update on public.sf_inventory_counts to service_role;

-- Ledger entries.
create table if not exists public.sf_ledger (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  ledger_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, ledger_id),
  constraint sf_ledger_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_ledger enable row level security;
drop policy if exists "svc only sf_ledger" on public.sf_ledger;
create policy "svc only sf_ledger" on public.sf_ledger
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_ledger from service_role;
grant select, insert, update on public.sf_ledger to service_role;

-- Post membership roster.
create table if not exists public.sf_members (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  member_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, member_id),
  constraint sf_members_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_members enable row level security;
drop policy if exists "svc only sf_members" on public.sf_members;
create policy "svc only sf_members" on public.sf_members
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_members from service_role;
grant select, insert, update on public.sf_members to service_role;

-- National service-hour categories.
create table if not exists public.sf_national_categories (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  national_category_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, national_category_id),
  constraint sf_national_categories_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_national_categories enable row level security;
drop policy if exists "svc only sf_national_categories" on public.sf_national_categories;
create policy "svc only sf_national_categories" on public.sf_national_categories
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_national_categories from service_role;
grant select, insert, update on public.sf_national_categories to service_role;

-- Post officers.
create table if not exists public.sf_officers (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  officer_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, officer_id),
  constraint sf_officers_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_officers enable row level security;
drop policy if exists "svc only sf_officers" on public.sf_officers;
create policy "svc only sf_officers" on public.sf_officers
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_officers from service_role;
grant select, insert, update on public.sf_officers to service_role;

-- Gaming operators.
create table if not exists public.sf_operators (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  operator_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, operator_id),
  constraint sf_operators_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_operators enable row level security;
drop policy if exists "svc only sf_operators" on public.sf_operators;
create policy "svc only sf_operators" on public.sf_operators
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_operators from service_role;
grant select, insert, update on public.sf_operators to service_role;

-- Permit compliance flags.
create table if not exists public.sf_permit_flags (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  permit_flag_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, permit_flag_id),
  constraint sf_permit_flags_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_permit_flags enable row level security;
drop policy if exists "svc only sf_permit_flags" on public.sf_permit_flags;
create policy "svc only sf_permit_flags" on public.sf_permit_flags
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_permit_flags from service_role;
grant select, insert, update on public.sf_permit_flags to service_role;

-- Bar products.
create table if not exists public.sf_products (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  product_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, product_id),
  constraint sf_products_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_products enable row level security;
drop policy if exists "svc only sf_products" on public.sf_products;
create policy "svc only sf_products" on public.sf_products
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_products from service_role;
grant select, insert, update on public.sf_products to service_role;

-- Hall rentals.
create table if not exists public.sf_rentals (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  rental_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, rental_id),
  constraint sf_rentals_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_rentals enable row level security;
drop policy if exists "svc only sf_rentals" on public.sf_rentals;
create policy "svc only sf_rentals" on public.sf_rentals
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_rentals from service_role;
grant select, insert, update on public.sf_rentals to service_role;

-- Veteran service appointments.
create table if not exists public.sf_service_appointments (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  service_appointment_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, service_appointment_id),
  constraint sf_service_appointments_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_service_appointments enable row level security;
drop policy if exists "svc only sf_service_appointments" on public.sf_service_appointments;
create policy "svc only sf_service_appointments" on public.sf_service_appointments
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_service_appointments from service_role;
grant select, insert, update on public.sf_service_appointments to service_role;

-- Recorded volunteer service hours.
create table if not exists public.sf_service_hours (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  service_hour_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, service_hour_id),
  constraint sf_service_hours_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_service_hours enable row level security;
drop policy if exists "svc only sf_service_hours" on public.sf_service_hours;
create policy "svc only sf_service_hours" on public.sf_service_hours
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_service_hours from service_role;
grant select, insert, update on public.sf_service_hours to service_role;

-- Veteran service referrals.
create table if not exists public.sf_service_referrals (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  service_referral_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, service_referral_id),
  constraint sf_service_referrals_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_service_referrals enable row level security;
drop policy if exists "svc only sf_service_referrals" on public.sf_service_referrals;
create policy "svc only sf_service_referrals" on public.sf_service_referrals
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_service_referrals from service_role;
grant select, insert, update on public.sf_service_referrals to service_role;

-- Gaming sessions.
create table if not exists public.sf_sessions (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  session_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, session_id),
  constraint sf_sessions_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_sessions enable row level security;
drop policy if exists "svc only sf_sessions" on public.sf_sessions;
create policy "svc only sf_sessions" on public.sf_sessions
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_sessions from service_role;
grant select, insert, update on public.sf_sessions to service_role;

-- Closed bar shifts with cash variance.
create table if not exists public.sf_shifts (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  shift_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, shift_id),
  constraint sf_shifts_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_shifts enable row level security;
drop policy if exists "svc only sf_shifts" on public.sf_shifts;
create policy "svc only sf_shifts" on public.sf_shifts
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_shifts from service_role;
grant select, insert, update on public.sf_shifts to service_role;

-- Typed document signatures.
create table if not exists public.sf_signatures (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  signature_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, signature_id),
  constraint sf_signatures_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_signatures enable row level security;
drop policy if exists "svc only sf_signatures" on public.sf_signatures;
create policy "svc only sf_signatures" on public.sf_signatures
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_signatures from service_role;
grant select, insert, update on public.sf_signatures to service_role;

-- Post staff.
create table if not exists public.sf_staff (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  staff_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, staff_id),
  constraint sf_staff_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_staff enable row level security;
drop policy if exists "svc only sf_staff" on public.sf_staff;
create policy "svc only sf_staff" on public.sf_staff
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_staff from service_role;
grant select, insert, update on public.sf_staff to service_role;

-- Ticket sales.
create table if not exists public.sf_tickets (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  ticket_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, ticket_id),
  constraint sf_tickets_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_tickets enable row level security;
drop policy if exists "svc only sf_tickets" on public.sf_tickets;
create policy "svc only sf_tickets" on public.sf_tickets
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_tickets from service_role;
grant select, insert, update on public.sf_tickets to service_role;

-- Vehicle service records.
create table if not exists public.sf_vehicle_service (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  vehicle_service_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, vehicle_service_id),
  constraint sf_vehicle_service_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_vehicle_service enable row level security;
drop policy if exists "svc only sf_vehicle_service" on public.sf_vehicle_service;
create policy "svc only sf_vehicle_service" on public.sf_vehicle_service
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_vehicle_service from service_role;
grant select, insert, update on public.sf_vehicle_service to service_role;

-- Post vehicles.
create table if not exists public.sf_vehicles (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  vehicle_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, vehicle_id),
  constraint sf_vehicles_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_vehicles enable row level security;
drop policy if exists "svc only sf_vehicles" on public.sf_vehicles;
create policy "svc only sf_vehicles" on public.sf_vehicles
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_vehicles from service_role;
grant select, insert, update on public.sf_vehicles to service_role;

-- Vendor price list.
create table if not exists public.sf_vendor_prices (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  vendor_price_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, vendor_price_id),
  constraint sf_vendor_prices_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_vendor_prices enable row level security;
drop policy if exists "svc only sf_vendor_prices" on public.sf_vendor_prices;
create policy "svc only sf_vendor_prices" on public.sf_vendor_prices
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_vendor_prices from service_role;
grant select, insert, update on public.sf_vendor_prices to service_role;

-- Vendors.
create table if not exists public.sf_vendors (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  vendor_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, vendor_id),
  constraint sf_vendors_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_vendors enable row level security;
drop policy if exists "svc only sf_vendors" on public.sf_vendors;
create policy "svc only sf_vendors" on public.sf_vendors
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_vendors from service_role;
grant select, insert, update on public.sf_vendors to service_role;

-- Signed waivers.
create table if not exists public.sf_waivers (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  waiver_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, waiver_id),
  constraint sf_waivers_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_waivers enable row level security;
drop policy if exists "svc only sf_waivers" on public.sf_waivers;
create policy "svc only sf_waivers" on public.sf_waivers
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_waivers from service_role;
grant select, insert, update on public.sf_waivers to service_role;

-- Youth-programme participants.
create table if not exists public.sf_youth_participants (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  app_id text not null default 'sairnfreedom',
  youth_participant_id text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, youth_participant_id),
  constraint sf_youth_participants_data_size check (octet_length(data::text) <= 65536)
);
alter table public.sf_youth_participants enable row level security;
drop policy if exists "svc only sf_youth_participants" on public.sf_youth_participants;
create policy "svc only sf_youth_participants" on public.sf_youth_participants
  for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
revoke all on public.sf_youth_participants from service_role;
grant select, insert, update on public.sf_youth_participants to service_role;

grant usage on schema public to service_role;
