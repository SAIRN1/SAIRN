-- SAIRN Technologies — Complete Supabase Schema (Fixed)
-- Michael L. Dibert · SAIRN Technologies · 2026
-- Run this entire file in Supabase SQL Editor

-- EXTENSIONS
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- PROFILES
create table if not exists public.profiles (
  id                  uuid primary key references auth.users(id) on delete cascade,
  email               text,
  full_name           text,
  avatar_url          text,
  created_at          timestamptz default now(),
  updated_at          timestamptz default now(),
  style_data          jsonb default '{}'::jsonb,
  preferred_language  text default 'en',
  timezone            text default 'UTC'
);

alter table public.profiles enable row level security;

create policy "profiles_select" on public.profiles
  for select using (auth.uid() = id);

create policy "profiles_update" on public.profiles
  for update using (auth.uid() = id)
  with check (auth.uid() = id);

create policy "profiles_insert" on public.profiles
  for insert with check (auth.uid() = id);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, full_name, avatar_url)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data->>'full_name',
    new.raw_user_meta_data->>'avatar_url'
  );
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- SUBSCRIPTIONS
create table if not exists public.subscriptions (
  id                      uuid primary key default uuid_generate_v4(),
  user_id                 uuid not null references public.profiles(id) on delete cascade,
  app_id                  text not null,
  stripe_customer_id      text,
  stripe_subscription_id  text,
  stripe_price_id         text,
  status                  text not null default 'inactive',
  current_period_start    timestamptz,
  current_period_end      timestamptz,
  cancel_at_period_end    boolean default false,
  created_at              timestamptz default now(),
  updated_at              timestamptz default now(),
  unique(user_id, app_id)
);

alter table public.subscriptions enable row level security;

create policy "subscriptions_select" on public.subscriptions
  for select using (auth.uid() = user_id);

create policy "subscriptions_service_all" on public.subscriptions
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create index if not exists idx_subscriptions_user_app on public.subscriptions(user_id, app_id);
create index if not exists idx_subscriptions_stripe on public.subscriptions(stripe_subscription_id);
create index if not exists idx_subscriptions_status on public.subscriptions(status);

-- CONVERSATIONS
create table if not exists public.conversations (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  app_id      text not null,
  mode        text not null default 'default',
  title       text,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now(),
  is_archived boolean default false
);

alter table public.conversations enable row level security;

create policy "conversations_all" on public.conversations
  for all using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create index if not exists idx_conversations_user_app on public.conversations(user_id, app_id);
create index if not exists idx_conversations_updated on public.conversations(updated_at desc);

-- MESSAGES
create table if not exists public.messages (
  id              uuid primary key default uuid_generate_v4(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id         uuid not null references public.profiles(id) on delete cascade,
  role            text not null check (role in ('user','assistant','system')),
  content         text not null,
  tokens_used     integer default 0,
  created_at      timestamptz default now()
);

alter table public.messages enable row level security;

create policy "messages_all" on public.messages
  for all using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create index if not exists idx_messages_conversation on public.messages(conversation_id, created_at);
create index if not exists idx_messages_user on public.messages(user_id);

-- USER STORAGE
create table if not exists public.user_storage (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  app_id      text not null,
  key         text not null,
  value       jsonb not null default '{}'::jsonb,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now(),
  unique(user_id, app_id, key)
);

alter table public.user_storage enable row level security;

create policy "storage_all" on public.user_storage
  for all using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create index if not exists idx_storage_user_app on public.user_storage(user_id, app_id);
create index if not exists idx_storage_key on public.user_storage(user_id, app_id, key);

-- USAGE LOGS
create table if not exists public.usage_logs (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid references public.profiles(id) on delete cascade,
  app_id      text not null,
  tokens_in   integer not null default 0,
  tokens_out  integer not null default 0,
  cost_usd    numeric(10,6) default 0,
  created_at  timestamptz default now()
);

alter table public.usage_logs enable row level security;

create policy "usage_select" on public.usage_logs
  for select using (auth.uid() = user_id);

create policy "usage_insert_service" on public.usage_logs
  for insert with check (auth.role() = 'service_role');

create index if not exists idx_usage_user_app on public.usage_logs(user_id, app_id);
create index if not exists idx_usage_created on public.usage_logs(created_at desc);

-- DEMO RATE LIMITING
create table if not exists public.demo_calls (
  id          uuid primary key default uuid_generate_v4(),
  ip_hash     text not null,
  app_id      text not null,
  created_at  timestamptz default now()
);

create index if not exists idx_demo_ip_day on public.demo_calls(ip_hash, app_id, created_at);

-- WEBHOOK EVENTS
create table if not exists public.webhook_events (
  id               uuid primary key default uuid_generate_v4(),
  stripe_event_id  text unique,
  event_type       text,
  status           text default 'processing',
  payload          text,
  error_message    text,
  processed_at     timestamptz,
  created_at       timestamptz default now()
);

-- HELPER FUNCTIONS
create or replace function public.has_active_subscription(p_user_id uuid, p_app_id text)
returns boolean language sql security definer as $$
  select exists (
    select 1 from public.subscriptions
    where user_id = p_user_id
      and app_id = p_app_id
      and status in ('active','trialing')
      and (current_period_end is null or current_period_end > now())
  );
$$;

create or replace function public.update_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

drop trigger if exists profiles_updated_at on public.profiles;
create trigger profiles_updated_at before update on public.profiles
  for each row execute procedure public.update_updated_at();

drop trigger if exists subscriptions_updated_at on public.subscriptions;
create trigger subscriptions_updated_at before update on public.subscriptions
  for each row execute procedure public.update_updated_at();

drop trigger if exists storage_updated_at on public.user_storage;
create trigger storage_updated_at before update on public.user_storage
  for each row execute procedure public.update_updated_at();

-- SHOPS
create table if not exists public.shops (
  id                      uuid primary key default uuid_generate_v4(),
  owner_id                uuid references public.profiles(id) on delete cascade,
  app_id                  text not null,
  shop_name               text not null,
  plan                    text not null default 'starter',
  stripe_customer_id      text,
  stripe_subscription_id  text,
  stripe_payment_method   text,
  status                  text not null default 'active',
  trial_ends_at           timestamptz,
  billing_email           text,
  address                 text,
  phone                   text,
  timezone                text default 'America/New_York',
  settings                jsonb default '{}'::jsonb,
  created_at              timestamptz default now(),
  updated_at              timestamptz default now()
);

alter table public.shops enable row level security;

create policy "shops_owner" on public.shops
  for all using (auth.uid() = owner_id)
  with check (auth.uid() = owner_id);

create policy "shops_service" on public.shops
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create index if not exists idx_shops_owner  on public.shops(owner_id);
create index if not exists idx_shops_app    on public.shops(app_id);
create index if not exists idx_shops_stripe on public.shops(stripe_customer_id);

-- SHOP USERS
create table if not exists public.shop_users (
  id          uuid primary key default uuid_generate_v4(),
  shop_id     uuid not null references public.shops(id) on delete cascade,
  user_id     uuid references public.profiles(id) on delete set null,
  role        text not null default 'tech',
  pin         text,
  full_name   text not null,
  email       text,
  phone       text,
  trade       text,
  certs       jsonb default '[]'::jsonb,
  hourly_rate numeric(10,2),
  status      text default 'active',
  created_at  timestamptz default now()
);

alter table public.shop_users enable row level security;

create policy "shop_users_service" on public.shop_users
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create index if not exists idx_shop_users_shop on public.shop_users(shop_id);

-- CUSTOMERS
create table if not exists public.customers (
  id                      uuid primary key default uuid_generate_v4(),
  shop_id                 uuid not null references public.shops(id) on delete cascade,
  first_name              text,
  last_name               text,
  company_name            text,
  email                   text,
  phone                   text,
  address                 text,
  city                    text,
  state                   text,
  zip                     text,
  customer_type           text default 'residential',
  stripe_customer_id      text,
  stripe_payment_method   text,
  notes                   text,
  tags                    jsonb default '[]'::jsonb,
  total_jobs              integer default 0,
  total_revenue           numeric(12,2) default 0,
  created_at              timestamptz default now(),
  updated_at              timestamptz default now()
);

alter table public.customers enable row level security;

create policy "customers_service" on public.customers
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create index if not exists idx_customers_shop   on public.customers(shop_id);
create index if not exists idx_customers_email  on public.customers(email);
create index if not exists idx_customers_stripe on public.customers(stripe_customer_id);

-- JOBS
create table if not exists public.jobs (
  id                  uuid primary key default uuid_generate_v4(),
  shop_id             uuid not null references public.shops(id) on delete cascade,
  customer_id         uuid references public.customers(id) on delete set null,
  app_id              text not null,
  job_number          text,
  title               text not null,
  description         text,
  trade               text,
  service_type        text,
  status              text default 'scheduled',
  priority            text default 'normal',
  assigned_to         uuid references public.shop_users(id),
  scheduled_date      date,
  scheduled_time      time,
  started_at          timestamptz,
  completed_at        timestamptz,
  address             text,
  notes               text,
  internal_notes      text,
  equipment           jsonb default '{}'::jsonb,
  checklist           jsonb default '[]'::jsonb,
  photos              jsonb default '[]'::jsonb,
  ai_diagnostic       text,
  estimated_revenue   numeric(12,2),
  actual_revenue      numeric(12,2),
  parts_cost          numeric(12,2) default 0,
  labor_hours         numeric(8,2)  default 0,
  labor_cost          numeric(12,2) default 0,
  margin_pct          numeric(6,2),
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);

alter table public.jobs enable row level security;

create policy "jobs_service" on public.jobs
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create index if not exists idx_jobs_shop      on public.jobs(shop_id);
create index if not exists idx_jobs_customer  on public.jobs(customer_id);
create index if not exists idx_jobs_status    on public.jobs(status);
create index if not exists idx_jobs_scheduled on public.jobs(scheduled_date);
create index if not exists idx_jobs_assigned  on public.jobs(assigned_to);

-- INVOICES
create table if not exists public.invoices (
  id                        uuid primary key default uuid_generate_v4(),
  shop_id                   uuid not null references public.shops(id) on delete cascade,
  job_id                    uuid references public.jobs(id) on delete set null,
  customer_id               uuid references public.customers(id) on delete set null,
  invoice_number            text not null,
  status                    text default 'draft',
  subtotal                  numeric(12,2) not null default 0,
  tax_rate                  numeric(6,4) default 0,
  tax_amount                numeric(12,2) default 0,
  total                     numeric(12,2) not null default 0,
  amount_paid               numeric(12,2) default 0,
  payment_terms             text default 'net30',
  due_date                  date,
  sent_at                   timestamptz,
  paid_at                   timestamptz,
  stripe_payment_intent_id  text,
  line_items                jsonb default '[]'::jsonb,
  notes                     text,
  created_at                timestamptz default now(),
  updated_at                timestamptz default now()
);

alter table public.invoices enable row level security;

create policy "invoices_service" on public.invoices
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create index if not exists idx_invoices_shop     on public.invoices(shop_id);
create index if not exists idx_invoices_customer on public.invoices(customer_id);
create index if not exists idx_invoices_status   on public.invoices(status);
create index if not exists idx_invoices_due      on public.invoices(due_date);

-- PAYMENTS
create table if not exists public.payments (
  id                        uuid primary key default uuid_generate_v4(),
  shop_id                   uuid not null references public.shops(id) on delete cascade,
  invoice_id                uuid references public.invoices(id),
  customer_id               uuid references public.customers(id),
  amount                    numeric(12,2) not null,
  method                    text,
  stripe_payment_intent_id  text,
  stripe_charge_id          text,
  status                    text default 'pending',
  notes                     text,
  created_at                timestamptz default now()
);

alter table public.payments enable row level security;

create policy "payments_service" on public.payments
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create index if not exists idx_payments_shop    on public.payments(shop_id);
create index if not exists idx_payments_invoice on public.payments(invoice_id);

-- PARTS
create table if not exists public.parts (
  id           uuid primary key default uuid_generate_v4(),
  shop_id      uuid not null references public.shops(id) on delete cascade,
  sku          text,
  name         text not null,
  trade        text,
  category     text,
  unit_cost    numeric(10,2) default 0,
  unit_price   numeric(10,2) default 0,
  quantity     integer default 0,
  reorder_at   integer default 0,
  supplier     text,
  supplier_sku text,
  location     text,
  created_at   timestamptz default now(),
  updated_at   timestamptz default now()
);

alter table public.parts enable row level security;

create policy "parts_service" on public.parts
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create index if not exists idx_parts_shop on public.parts(shop_id);

-- SLABS (StoneDesk)
create table if not exists public.slabs (
  id            uuid primary key default uuid_generate_v4(),
  shop_id       uuid not null references public.shops(id) on delete cascade,
  material      text not null,
  color         text,
  supplier      text,
  bundle        text,
  thickness     text default '3cm',
  length_in     numeric(8,2),
  width_in      numeric(8,2),
  cost_per_sqft numeric(8,2),
  total_cost    numeric(10,2),
  status        text default 'available',
  location      text,
  notes         text,
  photos        jsonb default '[]'::jsonb,
  created_at    timestamptz default now()
);

alter table public.slabs enable row level security;

create policy "slabs_service" on public.slabs
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create index if not exists idx_slabs_shop on public.slabs(shop_id);

-- PROJECTS (SAIRNbuild)
create table if not exists public.projects (
  id              uuid primary key default uuid_generate_v4(),
  shop_id         uuid not null references public.shops(id) on delete cascade,
  customer_id     uuid references public.customers(id),
  project_name    text not null,
  project_type    text,
  address         text,
  permit_number   text,
  contract_value  numeric(12,2),
  status          text default 'planning',
  start_date      date,
  target_end      date,
  actual_end      date,
  milestones      jsonb default '[]'::jsonb,
  subcontractors  jsonb default '[]'::jsonb,
  documents       jsonb default '[]'::jsonb,
  weather_holds   integer default 0,
  notes           text,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

alter table public.projects enable row level security;

create policy "projects_service" on public.projects
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create index if not exists idx_projects_shop on public.projects(shop_id);

-- GL ENTRIES
create table if not exists public.gl_entries (
  id           uuid primary key default uuid_generate_v4(),
  shop_id      uuid not null references public.shops(id) on delete cascade,
  date         date not null default current_date,
  account_code text not null,
  description  text not null,
  debit        numeric(12,2) default 0,
  credit       numeric(12,2) default 0,
  reference    text,
  source_app   text,
  source_id    uuid,
  posted       boolean default false,
  created_at   timestamptz default now()
);

alter table public.gl_entries enable row level security;

create policy "gl_service" on public.gl_entries
  for all using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create index if not exists idx_gl_shop on public.gl_entries(shop_id, date);

-- SHOP DASHBOARD FUNCTION
create or replace function public.shop_dashboard(p_shop_id uuid)
returns jsonb language plpgsql security definer as $$
declare result jsonb;
begin
  select jsonb_build_object(
    'jobs_today',       (select count(*) from public.jobs where shop_id = p_shop_id and scheduled_date = current_date),
    'jobs_open',        (select count(*) from public.jobs where shop_id = p_shop_id and status not in ('complete','invoiced','paid','cancelled')),
    'revenue_today',    (select coalesce(sum(actual_revenue),0) from public.jobs where shop_id = p_shop_id and completed_at::date = current_date),
    'revenue_mtd',      (select coalesce(sum(actual_revenue),0) from public.jobs where shop_id = p_shop_id and date_trunc('month', completed_at) = date_trunc('month', now())),
    'invoices_overdue', (select count(*) from public.invoices where shop_id = p_shop_id and status = 'overdue'),
    'outstanding_ar',   (select coalesce(sum(total - amount_paid),0) from public.invoices where shop_id = p_shop_id and total > amount_paid),
    'customers_total',  (select count(*) from public.customers where shop_id = p_shop_id),
    'techs_active',     (select count(*) from public.shop_users where shop_id = p_shop_id and status = 'active')
  ) into result;
  return result;
end;
$$;

-- DONE
