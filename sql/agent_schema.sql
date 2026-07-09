-- sql/agent_schema.sql
-- SAIRN On-Prem Agent — Supabase schema
--
-- Run this once in the Supabase SQL editor (project ejrlrrkvhtllxbbypdjb) before
-- the api/agent/*.js endpoints will function. They read/write these two tables
-- via the Supabase REST API using SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY,
-- the same pair of env vars used elsewhere in SAIRN's Supabase-backed apps.
--
-- Design note: the agent NEVER receives raw commands (SQL text, shell commands,
-- arbitrary file paths). It only receives an operation NAME + params. The agent's
-- own local config.json is the only place operation names are mapped to actual
-- queries/paths/endpoints — so a compromised or malicious cloud-side caller can
-- only invoke what that specific customer's IT already pre-approved locally.
--
-- Trial/paywall design: every agent gets full, unrestricted access to every
-- whitelisted operation for 30 days from creation (plan_status='trial',
-- trial_ends_at = created_at + 30 days). There is no feature-gating during the
-- trial — it's a time gate only, not a capability gate. Once trial_ends_at
-- passes and plan_status is still 'trial' (not flipped to 'paid'), poll.js and
-- enqueue.js both refuse all further activity until plan_status = 'paid'. See
-- scripts/mark-agent-paid.js to flip it manually; there is no automatic Stripe
-- webhook wired up yet — that's a documented next step, not something claimed
-- to exist here.

create extension if not exists pgcrypto;

create table if not exists sairn_agents (
  id uuid primary key default gen_random_uuid(),
  customer_id text not null,
  agent_name text not null,
  token_hash text not null,              -- sha256 of the agent's bearer token — never store the raw token
  status text not null default 'pending', -- pending | active | revoked
  plan_status text not null default 'trial', -- trial | paid | canceled
  trial_ends_at timestamptz not null default (now() + interval '30 days'),
  last_seen_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_sairn_agents_token_hash on sairn_agents (token_hash);
create index if not exists idx_sairn_agents_customer_id on sairn_agents (customer_id);

create table if not exists sairn_agent_commands (
  id uuid primary key default gen_random_uuid(),
  agent_id uuid not null references sairn_agents(id) on delete cascade,
  operation text not null,               -- name only, e.g. "get_customer_balance" — never raw SQL/commands
  params jsonb not null default '{}',
  status text not null default 'pending', -- pending | delivered | completed | failed | expired
  result jsonb,
  error text,
  created_at timestamptz not null default now(),
  delivered_at timestamptz,
  completed_at timestamptz,
  expires_at timestamptz not null default (now() + interval '2 minutes')
);

create index if not exists idx_sairn_agent_commands_poll on sairn_agent_commands (agent_id, status, created_at);
