-- ═══════════════════════════════════════════════════════════════════
--  SAIRN Technologies — Complete Supabase Schema
--  Michael L. Dibert · SAIRN NEXUS Platform · 2026
--
--  Run this entire file in Supabase SQL Editor once.
--  It creates every table, policy, index, and function needed
--  for all 8 SAIRN apps with full auth + storage + scalability.
-- ═══════════════════════════════════════════════════════════════════

-- ── EXTENSIONS ────────────────────────────────────────────────────
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- ── USERS (extends Supabase auth.users) ───────────────────────────
create table public.profiles (
  id            uuid primary key references auth.users(id) on delete cascade,
  email         text,
  full_name     text,
  avatar_url    text,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now(),

  -- Style learning (SAIRN NEXUS core)
  style_data    jsonb default '{}'::jsonb,

  -- Preferences
  preferred_language  text default 'en',
  timezone            text default 'UTC'
);

alter table public.profiles enable row level security;
create policy "Users can view own profile"
  on public.profiles for select using (auth.uid() = id);
create policy "Users can update own profile"
  on public.profiles for update using (auth.uid() = id);

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

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- ── SUBSCRIPTIONS ─────────────────────────────────────────────────
-- One row per user per app. Synced from Stripe webhooks.
create table public.subscriptions (
  id                  uuid primary key default uuid_generate_v4(),
  user_id             uuid not null references public.profiles(id) on delete cascade,
  app_id              text not null,   -- 'sairntype','lingual','health','money','legal','study','roam','senior'
  stripe_customer_id  text,
  stripe_subscription_id text,
  stripe_price_id     text,
  status              text not null default 'inactive',
  -- status values: 'active' | 'inactive' | 'trialing' | 'past_due' | 'canceled'
  current_period_start timestamptz,
  current_period_end   timestamptz,
  cancel_at_period_end boolean default false,
  created_at          timestamptz default now(),
  updated_at          timestamptz default now(),

  unique(user_id, app_id)
);

alter table public.subscriptions enable row level security;
create policy "Users can view own subscriptions"
  on public.subscriptions for select using (auth.uid() = user_id);

-- Service role can write (for Stripe webhook handler)
create policy "Service role can manage subscriptions"
  on public.subscriptions for all using (auth.role() = 'service_role');

create index idx_subscriptions_user_app on public.subscriptions(user_id, app_id);
create index idx_subscriptions_stripe on public.subscriptions(stripe_subscription_id);
create index idx_subscriptions_status on public.subscriptions(status);

-- ── CONVERSATIONS ─────────────────────────────────────────────────
-- Every Claude exchange stored per user per app per mode
create table public.conversations (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  app_id      text not null,
  mode        text not null default 'default',
  title       text,                        -- auto-generated from first message
  created_at  timestamptz default now(),
  updated_at  timestamptz default now(),
  is_archived boolean default false
);

alter table public.conversations enable row level security;
create policy "Users can manage own conversations"
  on public.conversations for all using (auth.uid() = user_id);

create index idx_conversations_user_app on public.conversations(user_id, app_id);
create index idx_conversations_updated on public.conversations(updated_at desc);

-- ── MESSAGES ──────────────────────────────────────────────────────
create table public.messages (
  id              uuid primary key default uuid_generate_v4(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id         uuid not null references public.profiles(id) on delete cascade,
  role            text not null check (role in ('user','assistant','system')),
  content         text not null,
  tokens_used     integer default 0,
  created_at      timestamptz default now()
);

alter table public.messages enable row level security;
create policy "Users can manage own messages"
  on public.messages for all using (auth.uid() = user_id);

create index idx_messages_conversation on public.messages(conversation_id, created_at);
create index idx_messages_user on public.messages(user_id);

-- ── USER STORAGE (app-specific key-value) ─────────────────────────
-- Generic storage for each app: saved docs, notes, preferences, etc.
create table public.user_storage (
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
create policy "Users can manage own storage"
  on public.user_storage for all using (auth.uid() = user_id);

create index idx_storage_user_app on public.user_storage(user_id, app_id);
create index idx_storage_key on public.user_storage(user_id, app_id, key);

-- ── USAGE TRACKING ────────────────────────────────────────────────
-- Per-user API usage for rate limiting + cost monitoring
create table public.usage_logs (
  id            uuid primary key default uuid_generate_v4(),
  user_id       uuid references public.profiles(id) on delete cascade,
  app_id        text not null,
  tokens_in     integer not null default 0,
  tokens_out    integer not null default 0,
  cost_usd      numeric(10,6) default 0,
  created_at    timestamptz default now()
);

alter table public.usage_logs enable row level security;
create policy "Users can view own usage"
  on public.usage_logs for select using (auth.uid() = user_id);
create policy "Service role manages usage"
  on public.usage_logs for insert using (auth.role() = 'service_role');

create index idx_usage_user_app on public.usage_logs(user_id, app_id);
create index idx_usage_created on public.usage_logs(created_at desc);

-- ── DEMO RATE LIMITING ────────────────────────────────────────────
-- Tracks anonymous demo usage to protect API credits
create table public.demo_calls (
  id          uuid primary key default uuid_generate_v4(),
  ip_hash     text not null,
  app_id      text not null,
  created_at  timestamptz default now()
);

create index idx_demo_ip_day on public.demo_calls(ip_hash, app_id, created_at);

-- ── HELPER FUNCTIONS ──────────────────────────────────────────────

-- Check if user has active subscription to an app
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

-- Get all active subscriptions for a user
create or replace function public.get_user_subscriptions(p_user_id uuid)
returns table(app_id text, status text, current_period_end timestamptz) 
language sql security definer as $$
  select app_id, status, current_period_end
  from public.subscriptions
  where user_id = p_user_id
    and status in ('active','trialing');
$$;

-- Upsert user storage value
create or replace function public.upsert_storage(
  p_user_id uuid, p_app_id text, p_key text, p_value jsonb
) returns void language plpgsql security definer as $$
begin
  insert into public.user_storage(user_id, app_id, key, value, updated_at)
  values (p_user_id, p_app_id, p_key, p_value, now())
  on conflict(user_id, app_id, key)
  do update set value = p_value, updated_at = now();
end;
$$;

-- Auto-update updated_at on profiles
create or replace function public.update_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;
create trigger profiles_updated_at before update on public.profiles
  for each row execute procedure public.update_updated_at();
create trigger subscriptions_updated_at before update on public.subscriptions
  for each row execute procedure public.update_updated_at();
create trigger storage_updated_at before update on public.user_storage
  for each row execute procedure public.update_updated_at();

-- ── VIEWS ─────────────────────────────────────────────────────────

-- Dashboard view: user + all their subscriptions
create or replace view public.user_dashboard as
  select
    p.id,
    p.email,
    p.full_name,
    p.created_at,
    p.style_data,
    coalesce(
      json_agg(
        json_build_object(
          'app_id', s.app_id,
          'status', s.status,
          'current_period_end', s.current_period_end
        ) order by s.app_id
      ) filter (where s.id is not null),
      '[]'::json
    ) as subscriptions
  from public.profiles p
  left join public.subscriptions s on s.user_id = p.id and s.status in ('active','trialing')
  group by p.id;

-- ═══════════════════════════════════════════════════════════════════
--  DONE. Schema complete.
--  Next: set SUPABASE_URL and SUPABASE_ANON_KEY in Vercel env vars.
-- ═══════════════════════════════════════════════════════════════════
