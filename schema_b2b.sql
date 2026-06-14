-- ================================================================
-- SAIRN B2B Schema — Supabase
-- Covers: StoneDesk, SAIRNbuild, SAIRNtrade, SAIRNhr, SAIRNacc
-- Michael L. Dibert · SAIRN Technologies · 2026
-- Run in Supabase SQL Editor AFTER the existing schema.sql
-- ================================================================

-- ── SHOPS (one row per B2B subscriber) ─────────────────────────
create table if not exists public.shops (
  id            uuid primary key default uuid_generate_v4(),
  owner_id      uuid references public.profiles(id) on delete cascade,
  app_id        text not null,   -- 'stonedesk','sairnbuild','sairntrade','sairnscape'
  shop_name     text not null,
  plan          text not null default 'starter', -- starter|pro|enterprise
  stripe_customer_id     text,
  stripe_subscription_id text,
  stripe_payment_method  text,   -- default card on file
  status        text not null default 'active',
  trial_ends_at timestamptz,
  billing_email text,
  address       text,
  phone         text,
  timezone      text default 'America/New_York',
  settings      jsonb default '{}'::jsonb,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

alter table public.shops enable row level security;
create policy "Owner can manage shop"
  on public.shops for all using (auth.uid() = owner_id);
create policy "Service role full access to shops"
  on public.shops for all using (auth.role() = 'service_role');

create index idx_shops_owner    on public.shops(owner_id);
create index idx_shops_app      on public.shops(app_id);
create index idx_shops_stripe   on public.shops(stripe_customer_id);

-- ── SHOP USERS (team members per shop) ──────────────────────────
create table if not exists public.shop_users (
  id         uuid primary key default uuid_generate_v4(),
  shop_id    uuid not null references public.shops(id) on delete cascade,
  user_id    uuid references public.profiles(id) on delete set null,
  role       text not null default 'tech', -- owner|admin|manager|office|tech|installer|viewer
  pin        text,                          -- 4-digit PIN (hashed)
  full_name  text not null,
  email      text,
  phone      text,
  trade      text,                          -- HVAC|Plumbing|Electrical|All
  certs      jsonb default '[]'::jsonb,
  hourly_rate numeric(10,2),
  status     text default 'active',
  created_at timestamptz default now()
);

alter table public.shop_users enable row level security;
create policy "Shop owner can manage users"
  on public.shop_users for all using (
    exists (select 1 from public.shops where id = shop_id and owner_id = auth.uid())
  );
create policy "Service role full access to shop_users"
  on public.shop_users for all using (auth.role() = 'service_role');

create index idx_shop_users_shop on public.shop_users(shop_id);
create index idx_shop_users_user on public.shop_users(user_id);

-- ── CUSTOMERS ───────────────────────────────────────────────────
create table if not exists public.customers (
  id           uuid primary key default uuid_generate_v4(),
  shop_id      uuid not null references public.shops(id) on delete cascade,
  first_name   text,
  last_name    text,
  company_name text,
  email        text,
  phone        text,
  address      text,
  city         text,
  state        text,
  zip          text,
  customer_type text default 'residential', -- residential|commercial|industrial
  stripe_customer_id text,
  stripe_payment_method text,     -- card on file
  notes        text,
  tags         jsonb default '[]'::jsonb,
  total_jobs   integer default 0,
  total_revenue numeric(12,2) default 0,
  created_at   timestamptz default now(),
  updated_at   timestamptz default now()
);

alter table public.customers enable row level security;
create policy "Shop can manage customers"
  on public.customers for all using (
    exists (select 1 from public.shops where id = shop_id and owner_id = auth.uid())
  );
create policy "Service role full access to customers"
  on public.customers for all using (auth.role() = 'service_role');

create index idx_customers_shop  on public.customers(shop_id);
create index idx_customers_email on public.customers(email);
create index idx_customers_stripe on public.customers(stripe_customer_id);

-- ── JOBS (universal across all trade apps) ──────────────────────
create table if not exists public.jobs (
  id             uuid primary key default uuid_generate_v4(),
  shop_id        uuid not null references public.shops(id) on delete cascade,
  customer_id    uuid references public.customers(id) on delete set null,
  app_id         text not null,  -- which app created it
  job_number     text,           -- WO-1042, SD-0099 etc
  title          text not null,
  description    text,
  trade          text,           -- HVAC|Plumbing|Electrical|StoneDesk|Construction
  service_type   text,           -- repair|install|maintenance|inspection|emergency
  status         text default 'scheduled', -- lead|scheduled|en_route|in_progress|complete|invoiced|paid|cancelled
  priority       text default 'normal',    -- normal|urgent|emergency
  assigned_to    uuid references public.shop_users(id),
  scheduled_date date,
  scheduled_time time,
  started_at     timestamptz,
  completed_at   timestamptz,
  address        text,
  notes          text,
  internal_notes text,
  equipment      jsonb default '{}'::jsonb,
  checklist      jsonb default '[]'::jsonb,
  photos         jsonb default '[]'::jsonb,
  ai_diagnostic  text,
  estimated_revenue numeric(12,2),
  actual_revenue    numeric(12,2),
  parts_cost        numeric(12,2) default 0,
  labor_hours       numeric(8,2)  default 0,
  labor_cost        numeric(12,2) default 0,
  margin_pct        numeric(6,2),
  created_at     timestamptz default now(),
  updated_at     timestamptz default now()
);

alter table public.jobs enable row level security;
create policy "Shop can manage jobs"
  on public.jobs for all using (
    exists (select 1 from public.shops where id = shop_id and owner_id = auth.uid())
  );
create policy "Service role full access to jobs"
  on public.jobs for all using (auth.role() = 'service_role');

create index idx_jobs_shop      on public.jobs(shop_id);
create index idx_jobs_customer  on public.jobs(customer_id);
create index idx_jobs_status    on public.jobs(status);
create index idx_jobs_scheduled on public.jobs(scheduled_date);
create index idx_jobs_assigned  on public.jobs(assigned_to);

-- ── INVOICES ────────────────────────────────────────────────────
create table if not exists public.invoices (
  id              uuid primary key default uuid_generate_v4(),
  shop_id         uuid not null references public.shops(id) on delete cascade,
  job_id          uuid references public.jobs(id) on delete set null,
  customer_id     uuid references public.customers(id) on delete set null,
  invoice_number  text not null,
  status          text default 'draft', -- draft|sent|viewed|paid|overdue|cancelled
  subtotal        numeric(12,2) not null default 0,
  tax_rate        numeric(6,4) default 0,
  tax_amount      numeric(12,2) default 0,
  total           numeric(12,2) not null default 0,
  amount_paid     numeric(12,2) default 0,
  balance_due     numeric(12,2) generated always as (total - amount_paid) stored,
  payment_terms   text default 'net30',
  due_date        date,
  sent_at         timestamptz,
  paid_at         timestamptz,
  stripe_payment_intent_id text,
  line_items      jsonb default '[]'::jsonb,
  notes           text,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

alter table public.invoices enable row level security;
create policy "Shop can manage invoices"
  on public.invoices for all using (
    exists (select 1 from public.shops where id = shop_id and owner_id = auth.uid())
  );
create policy "Service role full access to invoices"
  on public.invoices for all using (auth.role() = 'service_role');

create index idx_invoices_shop     on public.invoices(shop_id);
create index idx_invoices_customer on public.invoices(customer_id);
create index idx_invoices_status   on public.invoices(status);
create index idx_invoices_due      on public.invoices(due_date);

-- ── PAYMENTS ────────────────────────────────────────────────────
create table if not exists public.payments (
  id               uuid primary key default uuid_generate_v4(),
  shop_id          uuid not null references public.shops(id) on delete cascade,
  invoice_id       uuid references public.invoices(id),
  customer_id      uuid references public.customers(id),
  amount           numeric(12,2) not null,
  method           text,  -- card|ach|check|cash
  stripe_payment_intent_id text,
  stripe_charge_id text,
  status           text default 'pending', -- pending|succeeded|failed|refunded
  notes            text,
  created_at       timestamptz default now()
);

alter table public.payments enable row level security;
create policy "Shop can manage payments"
  on public.payments for all using (
    exists (select 1 from public.shops where id = shop_id and owner_id = auth.uid())
  );
create policy "Service role full access to payments"
  on public.payments for all using (auth.role() = 'service_role');

create index idx_payments_shop    on public.payments(shop_id);
create index idx_payments_invoice on public.payments(invoice_id);
create index idx_payments_stripe  on public.payments(stripe_payment_intent_id);

-- ── PARTS / INVENTORY ───────────────────────────────────────────
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
create policy "Shop can manage parts"
  on public.parts for all using (
    exists (select 1 from public.shops where id = shop_id and owner_id = auth.uid())
  );

create index idx_parts_shop on public.parts(shop_id);
create index idx_parts_sku  on public.parts(shop_id, sku);

-- ── STONEDESK SPECIFIC: SLABS ───────────────────────────────────
create table if not exists public.slabs (
  id           uuid primary key default uuid_generate_v4(),
  shop_id      uuid not null references public.shops(id) on delete cascade,
  material     text not null,
  color        text,
  supplier     text,
  bundle       text,
  thickness    text default '3cm',
  length_in    numeric(8,2),
  width_in     numeric(8,2),
  sqft         numeric(8,2) generated always as (
    round((length_in * width_in / 144.0)::numeric, 2)
  ) stored,
  cost_per_sqft numeric(8,2),
  total_cost    numeric(10,2),
  status        text default 'available', -- available|reserved|used|sold
  location      text,
  notes         text,
  photos        jsonb default '[]'::jsonb,
  created_at    timestamptz default now()
);

alter table public.slabs enable row level security;
create policy "Shop can manage slabs"
  on public.slabs for all using (
    exists (select 1 from public.shops where id = shop_id and owner_id = auth.uid())
  );
create index idx_slabs_shop on public.slabs(shop_id);

-- ── SAIRNBUILD SPECIFIC: PROJECTS ───────────────────────────────
create table if not exists public.projects (
  id            uuid primary key default uuid_generate_v4(),
  shop_id       uuid not null references public.shops(id) on delete cascade,
  customer_id   uuid references public.customers(id),
  project_name  text not null,
  project_type  text,  -- residential|commercial|renovation|new_build
  address       text,
  permit_number text,
  contract_value numeric(12,2),
  status        text default 'planning',
  start_date    date,
  target_end    date,
  actual_end    date,
  milestones    jsonb default '[]'::jsonb,
  subcontractors jsonb default '[]'::jsonb,
  documents     jsonb default '[]'::jsonb,
  weather_holds integer default 0,
  notes         text,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

alter table public.projects enable row level security;
create policy "Shop can manage projects"
  on public.projects for all using (
    exists (select 1 from public.shops where id = shop_id and owner_id = auth.uid())
  );
create index idx_projects_shop on public.projects(shop_id);

-- ── GL ENTRIES (bridges to SAIRNacc) ────────────────────────────
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
create policy "Shop can manage GL"
  on public.gl_entries for all using (
    exists (select 1 from public.shops where id = shop_id and owner_id = auth.uid())
  );
create index idx_gl_shop on public.gl_entries(shop_id, date);

-- ── WEBHOOK EVENTS (for Stripe idempotency) ─────────────────────
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

-- ── USEFUL FUNCTIONS ────────────────────────────────────────────

-- Get shop dashboard summary
create or replace function public.shop_dashboard(p_shop_id uuid)
returns jsonb language plpgsql security definer as $$
declare
  result jsonb;
begin
  select jsonb_build_object(
    'jobs_today',        (select count(*) from public.jobs where shop_id = p_shop_id and scheduled_date = current_date),
    'jobs_open',         (select count(*) from public.jobs where shop_id = p_shop_id and status not in ('complete','invoiced','paid','cancelled')),
    'revenue_today',     (select coalesce(sum(actual_revenue),0) from public.jobs where shop_id = p_shop_id and completed_at::date = current_date),
    'revenue_mtd',       (select coalesce(sum(actual_revenue),0) from public.jobs where shop_id = p_shop_id and date_trunc('month', completed_at) = date_trunc('month', now())),
    'invoices_overdue',  (select count(*) from public.invoices where shop_id = p_shop_id and status = 'overdue'),
    'outstanding_ar',    (select coalesce(sum(balance_due),0) from public.invoices where shop_id = p_shop_id and balance_due > 0),
    'customers_total',   (select count(*) from public.customers where shop_id = p_shop_id),
    'techs_active',      (select count(*) from public.shop_users where shop_id = p_shop_id and status = 'active')
  ) into result;
  return result;
end;
$$;

-- Auto-update updated_at
create trigger jobs_updated_at      before update on public.jobs      for each row execute procedure public.update_updated_at();
create trigger customers_updated_at before update on public.customers for each row execute procedure public.update_updated_at();
create trigger invoices_updated_at  before update on public.invoices  for each row execute procedure public.update_updated_at();
create trigger parts_updated_at     before update on public.parts     for each row execute procedure public.update_updated_at();
create trigger shops_updated_at     before update on public.shops     for each row execute procedure public.update_updated_at();
create trigger projects_updated_at  before update on public.projects  for each row execute procedure public.update_updated_at();

-- ================================================================
-- DONE. Run schema.sql first, then this file.
-- Tables: shops, shop_users, customers, jobs, invoices, payments,
--         parts, slabs, projects, gl_entries, webhook_events
-- ================================================================
