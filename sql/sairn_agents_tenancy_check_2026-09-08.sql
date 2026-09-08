-- sql/sairn_agents_tenancy_check_2026-09-08.sql
-- ---------------------------------------------------------------------------
-- READ-ONLY. Selects only. Nothing here writes, alters or drops anything.
--
-- ONE QUESTION: does more than one customer rely on api/agent/enqueue.js in
-- parallel today?
--
-- WHY IT MATTERS. That endpoint takes an agent_id and an arbitrary operation
-- and queues it for a customer's on-prem agent to execute, with NO credential
-- of any kind. Its only gates are that the agent row exists, its status is
-- 'active', and its plan has not expired. The file's own header sets the
-- condition under which that is acceptable:
--
--   "fine for a single-customer pilot where the agent_id isn't guessable/
--    shared, but it must NOT be treated as secure multi-tenant isolation.
--    Before more than one customer relies on this in parallel, add real
--    per-customer auth."
--
-- That is a sound judgement with an expiry date, and nothing was watching it.
-- The answer lives in this table and nowhere else: no session can read it, and
-- no deployed endpoint exposes a count -- every api/agent/*.js path is keyed by
-- a specific id or token_hash, checked 2026-09-08.
--
-- HOW TO READ THE RESULT (the branches Michael set):
--   0 or 1 distinct customer with an active, in-plan agent
--       -> the pilot precondition still holds. Log the row confirmed-safe-for-
--          now and move on. It is still worth re-asking whenever a second
--          customer is onboarded, which is the whole point of writing it down.
--   2 or more
--       -> the precondition has LAPSED. api/agent/enqueue.js needs real
--          per-customer auth before anything else ships against it: today any
--          party holding one customer's agent_id can queue an operation to it,
--          and agent_id travels in the app's own client-side calls.
--
-- Run in the Supabase SQL editor. Paste the whole file; each block prints a
-- labelled result.
-- ---------------------------------------------------------------------------

-- 1. THE HEADLINE. Distinct customers whose agent could accept a command right
--    now: exactly the population api/agent/enqueue.js will serve, using that
--    handler's own three gates (status active, and either paid or a trial that
--    has not expired) rather than a looser definition.
select
  count(distinct customer_id)                             as customers_enqueueable_now,
  count(*)                                                as agent_rows_enqueueable_now
from public.sairn_agents
where status = 'active'
  and plan_status <> 'canceled'
  and (plan_status <> 'trial' or trial_ends_at > now());

-- 2. THE WHOLE TABLE, one row per customer, so a borderline answer can be read
--    rather than inferred from a single number. customer_id is NOT masked here
--    because this output is for the schema owner in their own SQL editor; do
--    not paste it into a chat or a commit.
select
  customer_id,
  count(*)                                                as agents,
  count(*) filter (where status = 'active')               as active,
  count(*) filter (where status = 'pending')              as pending,
  count(*) filter (where status = 'revoked')              as revoked,
  count(*) filter (where plan_status = 'paid')            as paid,
  count(*) filter (where plan_status = 'trial'
                     and trial_ends_at > now())           as trial_live,
  count(*) filter (where plan_status = 'trial'
                     and trial_ends_at <= now())          as trial_expired,
  count(*) filter (where plan_status = 'canceled')        as canceled,
  max(last_seen_at)                                       as last_seen,
  min(created_at)                                         as first_registered
from public.sairn_agents
group by customer_id
order by last_seen desc nulls last;

-- 3. RECENCY, because "has a row" and "is actually being used" are different
--    claims and the row this answers asks about RELIANCE, not registration.
--    An agent polls to receive work, so last_seen_at is the honest signal.
select
  count(distinct customer_id) filter (where last_seen_at > now() - interval '7 days')  as customers_seen_7d,
  count(distinct customer_id) filter (where last_seen_at > now() - interval '30 days') as customers_seen_30d,
  count(distinct customer_id) filter (where last_seen_at is null)                      as customers_never_seen,
  count(distinct customer_id)                                                          as customers_total
from public.sairn_agents;

-- 4. HAS ANYTHING EVER BEEN QUEUED. A table of registered agents that has
--    never carried a command means the feature is provisioned but unused --
--    a different answer again, and the safest one.
select
  count(*)                                                as commands_total,
  count(*) filter (where created_at > now() - interval '30 days') as commands_30d,
  count(distinct agent_id)                                as agents_ever_commanded,
  min(created_at)                                         as first_command,
  max(created_at)                                         as last_command
from public.sairn_agent_commands;

-- 5. CONTROL, so an empty result above is read as "no rows" and never as
--    "wrong table" or "no permission" -- the distinction this platform has
--    been caught by before.
select
  to_regclass('public.sairn_agents')          as sairn_agents_exists,
  to_regclass('public.sairn_agent_commands')  as sairn_agent_commands_exists;
