#!/usr/bin/env node
// scripts/mark-agent-paid.js
// Run this locally after a customer converts from trial to a paid plan. Flips
// plan_status so api/agent/poll.js and api/agent/enqueue.js resume allowing
// access. Can also cancel a plan.
//
// NOT WIRED UP: this is a manual step for now. There is no Stripe webhook
// listener that calls this automatically when a subscription is paid — that's
// a clear, documented next step, not something claimed to exist here.
//
// Usage:
//   SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... node scripts/mark-agent-paid.js <agent_id> paid
//   SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... node scripts/mark-agent-paid.js <agent_id> canceled

async function main() {
  const [, , agentId, newStatus] = process.argv;
  const allowed = ['paid', 'trial', 'canceled'];
  if (!agentId || !allowed.includes(newStatus)) {
    console.error('Usage: node scripts/mark-agent-paid.js <agent_id> <paid|trial|canceled>');
    process.exit(1);
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your environment first.');
    process.exit(1);
  }

  const res = await fetch(SUPABASE_URL + '/rest/v1/sairn_agents?id=eq.' + agentId, {
    method: 'PATCH',
    headers: {
      apikey: SERVICE_KEY,
      Authorization: 'Bearer ' + SERVICE_KEY,
      'Content-Type': 'application/json',
      Prefer: 'return=representation'
    },
    body: JSON.stringify({ plan_status: newStatus })
  });
  const data = await res.json();
  if (!res.ok || !Array.isArray(data) || data.length === 0) {
    console.error('Failed to update agent:', data);
    process.exit(1);
  }

  console.log('Agent ' + agentId + ' plan_status set to "' + newStatus + '".');
  if (newStatus === 'paid') {
    console.log('Access resumes on this agent\'s next poll — no restart needed.');
  }
}

main();
