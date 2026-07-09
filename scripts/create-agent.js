#!/usr/bin/env node
// scripts/create-agent.js
// Run this locally (not deployed to Vercel) to provision a new agent for a
// customer. Prints a one-time bearer token — copy it into that customer's
// agent/config.json as "token" and it will never be shown again (only its
// sha256 hash is stored).
//
// Usage:
//   SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... node scripts/create-agent.js "customer_id" "Agent display name"
//
// REQUIRES: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY set in your shell
// environment when you run this — the same pair used by the Vercel-deployed
// api/agent/*.js endpoints. Never hardcode either value in this file.

const crypto = require('crypto');

async function main() {
  const [, , customerId, agentName] = process.argv;
  if (!customerId || !agentName) {
    console.error('Usage: node scripts/create-agent.js "customer_id" "Agent display name"');
    process.exit(1);
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!SUPABASE_URL || !SERVICE_KEY) {
    console.error('Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your environment first.');
    process.exit(1);
  }

  const token = crypto.randomBytes(32).toString('hex');
  const tokenHash = crypto.createHash('sha256').update(token).digest('hex');

  const res = await fetch(SUPABASE_URL + '/rest/v1/sairn_agents', {
    method: 'POST',
    headers: {
      apikey: SERVICE_KEY,
      Authorization: 'Bearer ' + SERVICE_KEY,
      'Content-Type': 'application/json',
      Prefer: 'return=representation'
    },
    body: JSON.stringify({ customer_id: customerId, agent_name: agentName, token_hash: tokenHash, status: 'pending' })
  });
  const data = await res.json();
  if (!res.ok) {
    console.error('Failed to create agent:', data);
    process.exit(1);
  }

  console.log('Agent created:', data[0].id);
  console.log('');
  console.log('Give this token to the customer for their agent/config.json — it will not be shown again:');
  console.log('');
  console.log('  ' + token);
  console.log('');
}

main();
