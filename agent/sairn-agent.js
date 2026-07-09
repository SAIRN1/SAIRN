#!/usr/bin/env node
// agent/sairn-agent.js
// SAIRN On-Prem Agent — runs on the customer's machine, behind their firewall.
// Makes ONLY outbound HTTPS calls to SAIRN's cloud (sairn.vercel.app). Never
// listens on any port, never accepts inbound connections. IT can confirm this
// by checking the process's open sockets — there won't be any listening ones.
//
// WHAT THIS DOES: repeatedly long-polls the cloud for pending commands. When
// one arrives, it looks up the operation NAME in the local config.json
// whitelist (never in a cloud-supplied query/path/command) and only then runs
// the corresponding pre-approved local action.
//
// WHAT THIS DELIBERATELY DOES NOT DO: execute arbitrary SQL, shell commands, or
// file paths sent from the cloud. If an operation name isn't in this machine's
// own config.json, it is refused — full stop, regardless of what the cloud
// side asked for. That's the whole security model: the customer's own local
// config is the only source of truth for what's callable.
//
// SETUP: copy config.example.json to config.json, fill in the token you were
// given and your whitelisted operations, then `node sairn-agent.js`.
//
// v1 SCOPE (honest limitations, not hidden):
//  - Supports two operation kinds: sql_query (via a pg/mysql2/mssql client —
//    install whichever driver you need, see config.example.json) and file_read
//    (a whitelisted absolute path only, size-capped). http_call is stubbed but
//    not yet implemented — extend executeOperation() below when needed.
//  - No automatic retry/backoff tuning beyond a fixed interval — fine for a
//    single-agent pilot, worth revisiting before running many agents at once.
//  - Not yet packaged as a Windows/Linux service — run it under a process
//    supervisor (pm2, nssm, systemd) for production use so it restarts on crash
//    or reboot. That packaging step is not done here.

const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, 'config.json');
if (!fs.existsSync(CONFIG_PATH)) {
  console.error('config.json not found. Copy config.example.json to config.json and fill it in first.');
  process.exit(1);
}
const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));

const BASE_URL = config.base_url || 'https://sairn.vercel.app';
const TOKEN = config.token;
const OPERATIONS = config.operations || {};
const POLL_INTERVAL_MS = 500; // gap between poll calls; poll.js itself blocks up to ~8s per call

if (!TOKEN) {
  console.error('config.json is missing "token". Get this from whoever provisioned your agent.');
  process.exit(1);
}

function authHeaders(extra) {
  return Object.assign({ Authorization: 'Bearer ' + TOKEN, 'Content-Type': 'application/json' }, extra || {});
}

async function register() {
  const res = await fetch(BASE_URL + '/api/agent/register', { method: 'POST', headers: authHeaders() });
  const data = await res.json();
  if (!res.ok) {
    console.error('Registration failed:', data.error && data.error.message);
    process.exit(1);
  }
  console.log('Registered as agent "' + data.agent_name + '" for customer ' + data.customer_id);
}

async function poll() {
  const res = await fetch(BASE_URL + '/api/agent/poll', { method: 'POST', headers: authHeaders() });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    console.error('Poll error:', data.error && data.error.message);
    return null;
  }
  const data = await res.json();
  return data.command || null;
}

async function submitResult(commandId, ok, result, error) {
  await fetch(BASE_URL + '/api/agent/result', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ command_id: commandId, ok, result, error })
  });
}

// The ONLY place a command turns into a real local action. Operation names not
// present in this machine's own config.operations are refused — see the file
// header for why that's the entire security model here.
async function executeOperation(operation, params) {
  const opConfig = OPERATIONS[operation];
  if (!opConfig) {
    throw new Error('Operation "' + operation + '" is not in this agent\'s local whitelist — refused.');
  }

  if (opConfig.kind === 'sql_query') {
    // Bring your own driver: npm install pg  (or mysql2, or mssql) depending on
    // opConfig.driver. Left as an explicit require here so this file has zero
    // hard dependencies until a customer actually configures a sql_query op.
    const driver = require(opConfig.driver); // e.g. 'pg'
    const client = new driver.Client({ connectionString: opConfig.connection_string });
    await client.connect();
    try {
      const result = await client.query(opConfig.query_template, opConfig.param_order.map((k) => params[k]));
      return { rows: result.rows };
    } finally {
      await client.end();
    }
  }

  if (opConfig.kind === 'file_read') {
    const allowedPath = path.resolve(opConfig.path);
    const stat = fs.statSync(allowedPath);
    const maxBytes = opConfig.max_bytes || 1_000_000;
    if (stat.size > maxBytes) {
      throw new Error('File exceeds max_bytes (' + stat.size + ' > ' + maxBytes + ')');
    }
    return { content: fs.readFileSync(allowedPath, 'utf8') };
  }

  throw new Error('Operation kind "' + opConfig.kind + '" is not implemented in this agent version.');
}

async function mainLoop() {
  await register();
  console.log('SAIRN Agent running. Outbound-only, polling ' + BASE_URL + '. Ctrl+C to stop.');
  for (;;) {
    try {
      const command = await poll();
      if (command) {
        console.log('Received command:', command.operation);
        try {
          const result = await executeOperation(command.operation, command.params || {});
          await submitResult(command.id, true, result, null);
          console.log('Completed:', command.operation);
        } catch (opErr) {
          await submitResult(command.id, false, null, opErr.message);
          console.error('Operation failed:', opErr.message);
        }
      }
    } catch (loopErr) {
      console.error('Agent loop error (will retry):', loopErr.message);
    }
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
}

mainLoop();
