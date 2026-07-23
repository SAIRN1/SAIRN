// api/sd-agent.js
// ---------------------------------------------------------------------------
// StoneDesk Agent SDK — a tool-calling Claude agent scoped to one license's
// StoneDesk data. Separate, new endpoint: does NOT touch or replace
// api/claude.js (the plain chat proxy) or api/sd-data.js (the direct
// read/write sync endpoint the StoneDesk client already calls). Tool
// execution is a thin wrapper around api/_lib/sd-store.js, which mirrors
// sd-data.js's own Supabase logic.
//
// IMPLEMENTATION: a manual fetch() loop against the Anthropic Messages API —
// no @anthropic-ai/sdk dependency, consistent with api/claude.js and
// api/sd-data.js already calling out to their respective APIs via bare
// fetch(). Model: claude-sonnet-5. Effort: medium (output_config.effort),
// adaptive thinking left on (the model's own default).
//
// TOOLS (5): read_profile, read_slabs, read_memories, write_memory all
// auto-execute inline in the loop. write_slab is confirm-first: the loop
// stops the moment Claude requests it and returns the pending call to the
// caller instead of running it. tool_choice disables parallel tool use, so
// each assistant turn requests at most one tool — this keeps the
// confirm-first branch simple (never a mix of an auto tool and write_slab
// in the same turn).
//
// SESSION MODEL: intentionally stateless, same as the rest of this API layer
// — there is no server-side session store. The caller carries the
// conversation forward turn-to-turn via the opaque `conversation` array this
// endpoint returns, and resumes a pending write_slab by resubmitting that
// array plus `confirm_tool_use_id`. Bearer license_key is the only auth
// boundary (Authorization header, same as sd-data.js) — a caller who already
// holds the license key could construct a conversation array that "confirms"
// a write_slab call the model never actually made. That's an accepted
// consequence of the existing bearer-token trust model (see sd-data.js's own
// header comment), not a gap specific to this endpoint; confirm-first here
// is a human-in-the-loop UX guard against the *agent* writing unreviewed
// data, not a cryptographic barrier against a caller who already has full
// access to that shop's data.
//
// REQUIRES env: ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
// ---------------------------------------------------------------------------

const store = require('./_lib/sd-store');

const MODEL = 'claude-sonnet-5';
const MAX_TOKENS = 4096;
const MAX_ITERATIONS = 10; // guards against a runaway tool-call loop

const SYSTEM_PROMPT =
  'You are the StoneDesk Agent, a data assistant scoped to one shop\'s StoneDesk ' +
  'account. Use read_profile, read_slabs, and read_memories to look up existing ' +
  'data before answering. Use write_memory freely to record useful notes. ' +
  'write_slab requires the user\'s explicit approval before it takes effect — ' +
  'call it whenever a slab record should be created or updated, but do not ' +
  'assume it already ran until you see its result.';

const TOOLS = [
  {
    name: 'read_profile',
    description: 'Read this shop\'s StoneDesk business profile (shop_id and profile fields). No input required.',
    input_schema: { type: 'object', properties: {}, additionalProperties: false }
  },
  {
    name: 'read_slabs',
    description: 'Read every slab record on file for this shop. No input required.',
    input_schema: { type: 'object', properties: {}, additionalProperties: false }
  },
  {
    name: 'write_slab',
    description:
      'Create or update one slab record. Requires explicit user approval before it runs — ' +
      'call this when the user asks to add, change, or log a slab, then wait for the result ' +
      'before telling the user it is saved.',
    input_schema: {
      type: 'object',
      properties: {
        slab: {
          type: 'object',
          description: 'Full slab record to store. Must include an "id" field; all other fields are shop-defined.'
        }
      },
      required: ['slab'],
      additionalProperties: false
    }
  },
  {
    name: 'read_memories',
    description: 'Read the 10 most recent notes/memories saved for this shop.',
    input_schema: { type: 'object', properties: {}, additionalProperties: false }
  },
  {
    name: 'write_memory',
    description: 'Save a note or piece of context for future reference. Runs immediately, no approval needed.',
    input_schema: {
      type: 'object',
      properties: {
        memory: { type: 'object', description: 'Structured content to remember, e.g. {"note": "..."}.' }
      },
      required: ['memory'],
      additionalProperties: false
    }
  }
];

async function callClaude(messages) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error('ANTHROPIC_API_KEY is not set in environment variables');
    const e = new Error('Server configuration error — contact support');
    e.code = 'CONFIG';
    throw e;
  }

  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01'
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: MAX_TOKENS,
      system: SYSTEM_PROMPT,
      messages: messages,
      tools: TOOLS,
      tool_choice: { type: 'auto', disable_parallel_tool_use: true },
      output_config: { effort: 'medium' }
    })
  });

  const data = await r.json();
  if (!r.ok) {
    const message = (data && data.error && data.error.message) ? data.error.message : ('Anthropic API error ' + r.status);
    const e = new Error(message);
    e.code = 'UPSTREAM';
    e.status = r.status;
    throw e;
  }
  return data;
}

// Executes the four auto tools. write_slab is deliberately absent here — it
// only ever runs via the explicit confirm-resume path below, never inline.
async function executeAutoTool(lic, toolUse) {
  try {
    switch (toolUse.name) {
      case 'read_profile':
        return { ok: true, data: await store.readProfile(lic) };
      case 'read_slabs':
        return { ok: true, data: await store.readSlabs(lic) };
      case 'read_memories':
        return { ok: true, data: await store.readMemories(lic) };
      case 'write_memory':
        return { ok: true, data: await store.writeMemory(lic, toolUse.input && toolUse.input.memory) };
      default:
        return { ok: false, error: 'Unknown or non-auto tool: ' + toolUse.name };
    }
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

function toolResultMessage(toolUseId, result) {
  const block = {
    type: 'tool_result',
    tool_use_id: toolUseId,
    content: JSON.stringify(result.ok ? result.data : { error: result.error })
  };
  if (!result.ok) block.is_error = true;
  return { role: 'user', content: [block] };
}

// Drives the loop forward until Claude stops calling tools, hits the
// iteration cap, or requests write_slab (which pauses for confirmation).
async function runLoop(lic, messages) {
  for (let i = 0; i < MAX_ITERATIONS; i++) {
    const response = await callClaude(messages);

    if (response.stop_reason === 'tool_use') {
      const toolUse = response.content.find((b) => b.type === 'tool_use');
      messages.push({ role: 'assistant', content: response.content });

      if (!toolUse) {
        // Shouldn't happen given stop_reason === 'tool_use', but don't loop forever on it.
        return { status: 'done', reply: '', conversation: messages };
      }

      if (toolUse.name === 'write_slab') {
        return { status: 'confirmation_required', tool_use: toolUse, conversation: messages };
      }

      const result = await executeAutoTool(lic, toolUse);
      messages.push(toolResultMessage(toolUse.id, result));
      continue;
    }

    // end_turn (or any other terminal stop_reason) — done.
    messages.push({ role: 'assistant', content: response.content });
    const textBlock = response.content.find((b) => b.type === 'text');
    return { status: 'done', reply: textBlock ? textBlock.text : '', conversation: messages };
  }

  const e = new Error('Agent exceeded ' + MAX_ITERATIONS + ' tool-call iterations without finishing');
  e.code = 'MAX_ITERATIONS';
  e.conversation = messages;
  throw e;
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: { message: 'Method not allowed — POST only' } });
    return;
  }

  const authz = req.headers['authorization'] || '';
  const licenseKey = authz.startsWith('Bearer ') ? authz.slice(7).trim() : null;

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) {
      res.status(400).json({ error: { message: 'Invalid JSON body' } });
      return;
    }
  }
  body = body || {};

  let lic;
  try {
    lic = await store.validateAndGate(licenseKey);
  } catch (err) {
    if (err.code === 'NO_LICENSE') return void res.status(401).json({ error: { code: 'NO_LICENSE', message: err.message } });
    if (err.code === 'INVALID_LICENSE') return void res.status(401).json({ error: { code: 'INVALID_LICENSE', message: err.message } });
    if (err.code === 'LICENSE_INACTIVE') return void res.status(403).json({ error: { code: 'LICENSE_INACTIVE', message: err.message } });
    if (err.code === 'TRIAL_EXPIRED') return void res.status(402).json({ error: { code: 'TRIAL_EXPIRED', message: err.message } });
    if (err.code === 'CONFIG') {
      console.error('sd-agent config error:', err.message);
      return void res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
    }
    console.error('sd-agent license validation error:', err);
    return void res.status(502).json({ error: { message: 'Upstream connection error — try again' } });
  }

  try {
    let messages;

    if (body.confirm_tool_use_id) {
      // Resuming a previously paused write_slab call. The pending tool_use
      // lives at the end of the last assistant message in the conversation
      // the caller resubmits — not in anything the caller supplies directly.
      if (!Array.isArray(body.conversation) || body.conversation.length === 0) {
        res.status(400).json({ error: { message: 'conversation is required alongside confirm_tool_use_id' } });
        return;
      }
      messages = body.conversation;
      const lastMessage = messages[messages.length - 1];
      const pendingToolUse = lastMessage && Array.isArray(lastMessage.content)
        ? lastMessage.content.find((b) => b.type === 'tool_use' && b.id === body.confirm_tool_use_id)
        : null;

      if (!pendingToolUse || pendingToolUse.name !== 'write_slab') {
        res.status(400).json({ error: { message: 'No pending write_slab call matches confirm_tool_use_id' } });
        return;
      }

      let result;
      try {
        const slab = await store.writeSlab(lic, pendingToolUse.input && pendingToolUse.input.slab);
        result = { ok: true, data: slab };
      } catch (err) {
        result = { ok: false, error: err.message };
      }
      messages.push(toolResultMessage(pendingToolUse.id, result));
    } else if (Array.isArray(body.conversation) && body.conversation.length > 0) {
      messages = body.conversation;
      if (body.message) messages.push({ role: 'user', content: body.message });
    } else if (body.message) {
      messages = [{ role: 'user', content: body.message }];
    } else {
      res.status(400).json({ error: { message: 'message (or conversation) is required' } });
      return;
    }

    const outcome = await runLoop(lic, messages);

    if (outcome.status === 'confirmation_required') {
      res.status(200).json({
        ok: true,
        status: 'confirmation_required',
        tool_use: { id: outcome.tool_use.id, name: outcome.tool_use.name, input: outcome.tool_use.input },
        conversation: outcome.conversation
      });
      return;
    }

    res.status(200).json({ ok: true, status: 'done', reply: outcome.reply, conversation: outcome.conversation });
  } catch (err) {
    if (err.code === 'MAX_ITERATIONS') {
      res.status(500).json({ error: { code: 'MAX_ITERATIONS', message: err.message }, conversation: err.conversation });
      return;
    }
    if (err.code === 'CONFIG') {
      console.error('sd-agent config error:', err.message);
      res.status(500).json({ error: { message: 'Server configuration error — contact support' } });
      return;
    }
    console.error('sd-agent error:', err);
    res.status(err.status || 502).json({ error: { message: err.message || 'Upstream connection error — try again' } });
  }
};
