# SAIRN On-Prem Agent

Lets a SAIRN app reach data that lives behind a customer's firewall, without
ever opening an inbound port on their network.

## How it works (and why it's safe to install)

The agent runs on the customer's machine and only ever makes **outbound**
HTTPS calls to `sairn.vercel.app`, asking "anything for me?" every few
seconds. It never listens on a port and never accepts an inbound connection —
this is the same pattern used by tools like Okta's on-prem provisioning
agents, Fivetran/Segment reverse-ETL connectors, and GitHub Actions
self-hosted runners.

The cloud side can only ever say "run the operation named X with these
parameters." It can **never** send raw SQL, a shell command, or a file path.
Every operation name has to already exist in that specific customer's own
`config.json` — a file only their IT controls, sitting on their own machine.
If the cloud asks for an operation name that isn't in the local whitelist, the
agent refuses, full stop. A compromised or malicious caller on the cloud side
can only ever trigger what that customer's IT already pre-approved locally —
it cannot invent a new capability remotely.

## Setup

1. `cp config.example.json config.json`
2. Fill in the `token` you were given (see `scripts/create-agent.js`) and your
   whitelisted `operations`.
3. `node sairn-agent.js`

For production use, run it under a process supervisor (pm2, nssm on Windows,
systemd on Linux) so it restarts automatically on crash or reboot — this
repo does not include that packaging step yet.

## Provisioning a new agent (SAIRN ops side)

```
SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... node scripts/create-agent.js "customer_id" "Agent display name"
```

Prints a one-time token. Give it to the customer for their `config.json`. Only
its SHA-256 hash is ever stored — if it's lost, provision a new agent record.

## 30-day trial and paywall

Every agent gets **full, unrestricted access to every whitelisted operation
for 30 days** from the moment it's created — there is no feature-gating
during the trial, only a time gate. `trial_ends_at` is set automatically in
the database when the row is created.

Once the trial ends and the plan hasn't been marked paid, `api/agent/poll.js`
and `api/agent/enqueue.js` both refuse all further activity (HTTP 402, code
`TRIAL_EXPIRED`) until you run:

```
SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... node scripts/mark-agent-paid.js <agent_id> paid
```

Access resumes on the agent's very next poll — no restart needed on the
customer's end. The agent script itself detects the expired state and backs
off to checking once an hour instead of failing loudly on every poll.

**Not wired up yet:** there's no Stripe webhook that calls
`mark-agent-paid.js` automatically when a subscription is actually paid —
that's a documented next step, not something built here. Today, someone on
the SAIRN side has to run it manually after confirming payment.

## Known v1 limitations (said plainly, not hidden)

- Only two operation kinds exist so far: `sql_query` and `file_read`.
  `http_call` is not implemented yet — extend `executeOperation()` in
  `sairn-agent.js` when a customer integration needs it.
- Delivery latency is roughly 8–10 seconds (bounded by Vercel's serverless
  function execution limits), not instant push. Fine for background sync,
  not for anything needing sub-second response.
- `api/agent/enqueue.js` (the endpoint SAIRN apps call to request something
  from an agent) currently has no per-customer session authorization beyond
  knowing a valid `agent_id`. That's acceptable for a single-customer pilot
  but must be hardened with real per-customer auth before more than one
  customer relies on this in parallel — see the security note at the top of
  that file.
- Not yet packaged as an installable Windows/Linux service.

## Requires (Vercel env vars)

`SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` — same pair used by SAIRN's
other Supabase-backed apps. Run `sql/agent_schema.sql` in the Supabase SQL
editor once before any of this will function.
