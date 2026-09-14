/**
 * api/claude-guardrail-metamorphic.test.js
 *
 *   node api/claude-guardrail-metamorphic.test.js
 *
 * Item 8's OTHER half: the attack-generation side, applied to SAIRN's own
 * request envelope. ZERO ANTHROPIC CALLS BY CONSTRUCTION -- global.fetch is
 * stubbed before the handler is required, and an arm asserts the stub was never
 * reached where it must not be.
 *
 * ── WHAT THIS ADDS THAT claude-guardrail-probes.test.js DOES NOT ────────────
 * That suite (27 arms, Hank, 2026-09-13) asserts EXACT VALUES: this app_id is
 * accepted, that tool type is refused, `max_tokens: true` lands on 1000. Every
 * one of those is a point measurement, and a guard can be right at every point
 * an author thought to write down and wrong on the variant nobody typed.
 *
 * A METAMORPHIC RELATION asks the other question, and needs no oracle: take an
 * input, transform it in a way that CANNOT legitimately change the verdict, and
 * assert the verdict did not change. That is item 18's mechanism
 * (tools/metamorphic_check.py, which applies it to CHECKERS) pointed at the AI
 * guardrails instead. It finds the class where a guard is right by accident --
 * matching a shape that happens to correlate with the attack rather than the
 * attack itself.
 *
 * ── WHY THIS IS THE DETERMINISTIC HALF, AND WHAT IT IS NOT ──────────────────
 * The natural-language version of this -- "the model refuses P, so it must also
 * refuse a rephrasing of P" -- REQUIRES A MODEL CALL, and that half is deferred
 * by Michael's recorded garak decision (separate approval, dry-run cost first,
 * never against production). So the rephrasing families here are over the
 * REQUEST ENVELOPE, which is SAIRN's own code and answers for free:
 *
 *   - the same app_id padded, cased, or unicode-confused
 *   - the same number as an integer, a string, a float, a boxed value
 *   - the same tool type with different casing or whitespace
 *   - the same guard applied twice instead of once
 *
 * A clean run here means THE ENVELOPE GUARDS ARE INVARIANT UNDER THESE
 * FAMILIES. It says nothing whatever about whether Claude honours a system
 * prompt, and this file will not be read as if it did.
 *
 * ── THE RELATIONS, AND THE REAL TRAP EACH ONE COMES FROM ────────────────────
 * R1  EXACT-MATCH ALLOWLIST. Every near-miss of a real app_id must be REFUSED.
 *     The allowlist has silently 400'd live apps three times (2026-07-26 nine
 *     apps, SAIRNsenior, two more at build time), which means the failure this
 *     platform has actually suffered is over-strictness -- so the risk when
 *     somebody "fixes" that is a loosened comparison, and a padded or recased
 *     id sliding through is a bypass of the only auth this endpoint has.
 *
 * R2  NUMERICALLY-EQUAL REPRESENTATIONS AGREE. `4096`, `'4096'`, `4096.0` and
 *     `'4096.0'` are the same number, so cappedMaxTokens must return the same
 *     value for all four. If it does not, a client changing how it serialises
 *     JSON changes its own spend cap. This is the exact trap that already
 *     produced a real bug here: `max_tokens: true` and `[5]` were accepted.
 *
 * R3  CLAMP IDEMPOTENCE. Applying a clamp to its own output must change
 *     nothing. A non-idempotent clamp means the answer depends on how many
 *     times the value passed through, which is how a value gets capped twice in
 *     one path and once in another and the two disagree.
 *
 * R4  ORDER AND MULTIPLICITY INVARIANCE. sanitizeTools must treat a tool the
 *     same wherever it sits in the array, and the SAME tool twice must sanitize
 *     to two identical entries. A filter that is position-sensitive is one that
 *     can be walked past by reordering.
 *
 * R5  ENVELOPE-SIZE INVARIANCE. A guard's verdict must not depend on how many
 *     messages ride with it. A refusal that holds for one message and not for
 *     fifty is bypassable by padding, which is the cheapest attack there is.
 *
 * ── AND THE CONTROLS ARE THE POINT ─────────────────────────────────────────
 * Section Z sabotages each guard IN A COPY OF THE MODULE, asserts the sabotage
 * APPLIED (the anchor matched and the bytes changed), asserts the mutant
 * actually RAN rather than dying on require, and only then believes that the
 * relation went red. Measured on this platform 2026-09-13: 23 of 39 negative
 * controls never verified their own sabotage applied, and a mutation control
 * that crashes on import exits non-zero exactly like one that worked -- which
 * made four of five controls vacuous in a suite written earlier today.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const run = [];
let pass = 0;
const fails = [];
function t(name, fn) { run.push([name, fn]); }
function section(s) { run.push([s, null]); }

// ── STUBS, BEFORE THE HANDLER IS REQUIRED ──────────────────────────────────
// Same reason claude-guardrail-probes.test.js records: on a machine with no
// SUPABASE_URL the real limiter and licence store throw, every state collapses
// to `error`, and a suite written against that passes whether the logic is
// right or wrong.
const LIMITER = require.resolve('./_lib/ai-rate-limit');
require.cache[LIMITER] = {
  id: LIMITER, filename: LIMITER, loaded: true,
  exports: {
    checkAiRateLimit: async () => ({ allowed: true, rowId: 'r', degraded: false }),
    recordAiUsage: async () => {},
  },
};
const LICENCE = require.resolve('./_lib/license');
require.cache[LICENCE] = {
  id: LICENCE, filename: LICENCE, loaded: true,
  exports: { validateLicenseKey: async () => ({ valid: true, active: true, license_hash: 'h' }) },
};

process.env.ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY || 'test-key';
process.env.SAIRN_CLAUDE_AUTH_MODE = 'observe';

let anthropicCalls = 0;
let sentBody = null;
global.fetch = async function (url, opts) {
  anthropicCalls += 1;
  sentBody = JSON.parse(opts.body);
  return {
    ok: true, status: 200,
    json: async () => ({ content: [{ type: 'text', text: 'ok' }], usage: { input_tokens: 1, output_tokens: 1 } }),
  };
};

delete require.cache[require.resolve('./claude.js')];
const handler = require('./claude.js');
const {
  sanitizeTools, cappedMaxTokens, KNOWN_APP_IDS,
  ALLOWED_SERVER_TOOL_TYPES, MAX_TOOL_USES_CEILING, MAX_TOKENS_CEILING,
} = handler;

const MSG = [{ role: 'user', content: 'hi' }];
const SERVER_TOOL = ALLOWED_SERVER_TOOL_TYPES[0];
const REAL_APP = KNOWN_APP_IDS[0];

function mockRes() {
  const res = { _s: 0, _j: null };
  res.status = function (c) { res._s = c; return res; };
  res.json = function (o) { res._j = o; return res; };
  res.setHeader = function () { return res; };
  return res;
}

async function call(body) {
  anthropicCalls = 0; sentBody = null;
  const res = mockRes();
  await handler({ method: 'POST', headers: {}, body }, res);
  return { status: res._s, body: res._j, sent: sentBody, calls: anthropicCalls };
}

// ── THE BLIND LOCK ─────────────────────────────────────────────────────────
// The relations are asserted against HAND-BUILT functions first, before any
// real guard is touched -- convention 1, and convention 5's isolated
// validation: a lock that rides beside the live subject can be satisfied by
// the subject. A deliberately BROKEN clamp must fail R2 and R3, and a correct
// one must pass, or these relations prove nothing about the real guards.
function goodClamp(v) {
  if (typeof v !== 'number' && typeof v !== 'string') return 1000;
  const n = Number(v);
  if (!Number.isFinite(n) || n <= 0) return 1000;
  return Math.min(Math.floor(n), 4096);
}
// Wrong in the one direction that matters: string and number disagree.
function stringBlindClamp(v) {
  if (typeof v === 'string') return 4096;
  return goodClamp(v);
}
// Wrong differently: not idempotent, because it scales rather than clamps.
function nonIdempotentClamp(v) {
  const n = Number(v);
  if (!Number.isFinite(n) || n <= 0) return 1000;
  return Math.min(Math.floor(n * 2), 4096);
}

function relEqualRepresentations(fn) {
  // 4096 is deliberately AT the ceiling and 100 well below it, so the relation
  // is exercised on both sides of the clamp rather than only where it saturates
  // -- a saturating clamp makes every representation agree for free.
  const families = [[100, '100', 100.0, '100.0'], [4096, '4096', 4096.0, '4096.0']];
  return families.every((fam) => {
    const outs = fam.map(fn);
    return outs.every((o) => o === outs[0]);
  });
}

function relIdempotent(fn) {
  return [1, 100, 4095, 4096, 99999].every((v) => fn(fn(v)) === fn(v));
}

const LOCK = [
  ['a correct clamp satisfies EQUAL-REPRESENTATIONS', relEqualRepresentations(goodClamp), true],
  ['a string-blind clamp VIOLATES it', relEqualRepresentations(stringBlindClamp), false],
  ['a correct clamp satisfies IDEMPOTENCE', relIdempotent(goodClamp), true],
  ['a scaling clamp VIOLATES idempotence', relIdempotent(nonIdempotentClamp), false],
];

section('A. THE BLIND LOCK -- relations judged on hand-built functions first');
LOCK.forEach(([name, got, want]) => {
  t(name, () => {
    if (got !== want) throw new Error('relation returned ' + got + ', expected ' + want);
  });
});

// ── R1: EXACT-MATCH ALLOWLIST ──────────────────────────────────────────────
section('B. R1 -- every near-miss of a real app_id is REFUSED');

// The families are generated FROM the real allowlist rather than typed, so a
// renamed app cannot leave this suite testing a name nobody uses -- the
// instrument-drift shape from disciplines item 8.
function nearMisses(id) {
  return [
    [' ' + id, 'leading space'],
    [id + ' ', 'trailing space'],
    [id.toUpperCase(), 'upper case'],
    [id.charAt(0).toUpperCase() + id.slice(1), 'capitalised'],
    [id + '\u0000', 'trailing NUL'],
    [id + '\n', 'trailing newline'],
    [id.replace('a', 'а') !== id ? id.replace('a', 'а') : id + '​',
      'unicode confusable or zero-width'],
    ['\t' + id, 'leading tab'],
  ];
}

nearMisses(REAL_APP).forEach(([variant, label]) => {
  t('R1 ' + label + ' is refused, not treated as ' + REAL_APP, async () => {
    const r = await call({ app_id: variant, is_demo: true, messages: MSG });
    if (r.status === 200) {
      throw new Error('ACCEPTED a near-miss app_id (' + JSON.stringify(variant) +
        ') -- the allowlist is not an exact match, so it is bypassable by padding');
    }
    if (r.calls !== 0) {
      throw new Error('a refused app_id still reached Anthropic');
    }
  });
});

t('R1 CONTROL: the unmodified app_id really is accepted', async () => {
  const r = await call({ app_id: REAL_APP, is_demo: true, messages: MSG });
  if (r.status !== 200) {
    throw new Error('the real app_id ' + REAL_APP + ' was refused (status ' + r.status +
      ') -- without this the refusals above are satisfied by a guard that refuses everything');
  }
});

// ── R2: NUMERICALLY-EQUAL REPRESENTATIONS AGREE ────────────────────────────
section('C. R2 -- the same number in different clothes gets the same cap');

t('R2 cappedMaxTokens agrees across int / string / float / string-float', () => {
  if (!relEqualRepresentations(cappedMaxTokens)) {
    throw new Error('representations of one number produced different caps');
  }
});

t('R2 ...and the agreed value is inside the documented ceiling', () => {
  [100, '100', 4096, '4096', 99999, '99999'].forEach((v) => {
    const out = cappedMaxTokens(v);
    if (!(out > 0 && out <= MAX_TOKENS_CEILING)) {
      throw new Error(JSON.stringify(v) + ' -> ' + out + ', outside (0, ' + MAX_TOKENS_CEILING + ']');
    }
  });
});

t('R2 the non-numeric family all falls to the DEFAULT, never to the ceiling', () => {
  // Garbage in must not buy the largest generation available -- the file's own
  // stated rule, asserted here as a family rather than one value at a time.
  [true, false, [5], [], {}, null, undefined, NaN, 'abc', '', '  '].forEach((v) => {
    const out = cappedMaxTokens(v);
    if (out === MAX_TOKENS_CEILING) {
      throw new Error(JSON.stringify(v) + ' bought the CEILING (' + out + ')');
    }
    if (!(out > 0 && out <= MAX_TOKENS_CEILING)) {
      throw new Error(JSON.stringify(v) + ' -> ' + out + ', outside the range');
    }
  });
});

// ── R3: IDEMPOTENCE ────────────────────────────────────────────────────────
section('D. R3 -- applying a clamp to its own output changes nothing');

t('R3 cappedMaxTokens is idempotent', () => {
  if (!relIdempotent(cappedMaxTokens)) {
    throw new Error('cappedMaxTokens(cappedMaxTokens(v)) !== cappedMaxTokens(v)');
  }
});

t('R3 sanitizeTools is idempotent on its own output', () => {
  const once = sanitizeTools([{ type: SERVER_TOOL, max_uses: 99999 },
    { name: 'local', input_schema: {} }]);
  const twice = sanitizeTools(once);
  if (JSON.stringify(once) !== JSON.stringify(twice)) {
    throw new Error('sanitizing twice differed from once:\n  once=' +
      JSON.stringify(once) + '\n  twice=' + JSON.stringify(twice));
  }
});

// ── R4: ORDER AND MULTIPLICITY ─────────────────────────────────────────────
section('E. R4 -- position and repetition do not change a tool\'s treatment');

t('R4 an allowed tool is treated the same at every position', () => {
  const filler = { name: 'local_a', input_schema: {} };
  const target = { type: SERVER_TOOL, max_uses: 99999 };
  const first = sanitizeTools([target, filler, filler]);
  const middle = sanitizeTools([filler, target, filler]);
  const last = sanitizeTools([filler, filler, target]);
  const pick = (a) => JSON.stringify(a.filter((x) => x.type === SERVER_TOOL));
  if (pick(first) !== pick(middle) || pick(middle) !== pick(last)) {
    throw new Error('the same tool sanitized differently by position:\n  ' +
      pick(first) + '\n  ' + pick(middle) + '\n  ' + pick(last));
  }
});

t('R4 a REFUSED tool is refused at every position', () => {
  const bad = { type: 'definitely_not_allowed_' + Date.now() };
  [[bad], [bad, { name: 'x', input_schema: {} }], [{ name: 'x', input_schema: {} }, bad]]
    .forEach((arr, i) => {
      const out = sanitizeTools(arr) || [];
      if (out.some((x) => x.type === bad.type)) {
        throw new Error('a non-whitelisted tool type survived at position set ' + i);
      }
    });
});

t('R4 the same tool twice yields two IDENTICAL sanitized entries', () => {
  const out = sanitizeTools([{ type: SERVER_TOOL, max_uses: 99999 },
    { type: SERVER_TOOL, max_uses: 99999 }]);
  if (!out || out.length !== 2) throw new Error('expected 2 entries, got ' + JSON.stringify(out));
  if (JSON.stringify(out[0]) !== JSON.stringify(out[1])) {
    throw new Error('duplicates sanitized differently: ' + JSON.stringify(out));
  }
  if (out[0].max_uses > MAX_TOOL_USES_CEILING) {
    throw new Error('max_uses above the ceiling survived: ' + out[0].max_uses);
  }
});

t('R4 a near-miss of an ALLOWED tool type is refused (exact whitelist)', () => {
  [SERVER_TOOL.toUpperCase(), ' ' + SERVER_TOOL, SERVER_TOOL + ' ', SERVER_TOOL + '​']
    .forEach((ty) => {
      if (ty === SERVER_TOOL) return;
      const out = sanitizeTools([{ type: ty }]) || [];
      if (out.some((x) => x.type === ty)) {
        throw new Error('a recased/padded tool type was accepted: ' + JSON.stringify(ty));
      }
    });
});

// ── R5: ENVELOPE SIZE ──────────────────────────────────────────────────────
section('F. R5 -- a verdict must not depend on how much rides with it');

t('R5 a refused app_id stays refused with a 50-message envelope', async () => {
  const many = Array.from({ length: 50 }, () => ({ role: 'user', content: 'x'.repeat(200) }));
  const small = await call({ app_id: 'not_a_real_sairn_app', is_demo: true, messages: MSG });
  const big = await call({ app_id: 'not_a_real_sairn_app', is_demo: true, messages: many });
  if (small.status !== big.status) {
    throw new Error('verdict changed with envelope size: ' + small.status + ' vs ' + big.status);
  }
  if (big.calls !== 0) throw new Error('the padded refusal still reached Anthropic');
});

t('R5 the max_tokens cap does not move with envelope size', async () => {
  const many = Array.from({ length: 50 }, () => ({ role: 'user', content: 'x'.repeat(200) }));
  const a = await call({ app_id: REAL_APP, is_demo: true, messages: MSG, max_tokens: 99999 });
  const b = await call({ app_id: REAL_APP, is_demo: true, messages: many, max_tokens: 99999 });
  if (!a.sent || !b.sent) throw new Error('the stub captured no body');
  if (a.sent.max_tokens !== b.sent.max_tokens) {
    throw new Error('cap moved with envelope size: ' + a.sent.max_tokens + ' vs ' + b.sent.max_tokens);
  }
  if (a.sent.max_tokens > MAX_TOKENS_CEILING) {
    throw new Error('the cap sent upstream exceeds the ceiling: ' + a.sent.max_tokens);
  }
});

t('F CONTROL: no arm in this file has made a real Anthropic call', () => {
  // The stub counts. If the real fetch were ever restored this would be the arm
  // that noticed, which matters because the whole premise of the SAIRN-owned
  // half is that it costs nothing.
  if (typeof global.fetch !== 'function') throw new Error('fetch stub was removed');
  if (String(global.fetch).indexOf('anthropicCalls') === -1) {
    throw new Error('global.fetch is no longer this file\'s stub -- a real paid ' +
      'call may have been made');
  }
});

// ── Z. MUTATION CONTROLS ───────────────────────────────────────────────────
section('Z. CONTROLS -- break each guard, prove the sabotage landed, watch it go red');

const SRC_PATH = require.resolve('./claude.js');
const ORIGINAL = fs.readFileSync(SRC_PATH, 'utf8');

function withMutant(anchor, replacement, fn) {
  if (ORIGINAL.indexOf(anchor) === -1) {
    throw new Error('SABOTAGE ANCHOR NO LONGER MATCHES, so this control cannot ' +
      'fail and is worthless: ' + JSON.stringify(anchor.slice(0, 90)));
  }
  const patched = ORIGINAL.split(anchor).join(replacement);
  if (patched === ORIGINAL) throw new Error('the replacement changed nothing');

  // WRITTEN BESIDE THE ORIGINAL, NOT OVER IT. A mutant in os.tmpdir() cannot
  // resolve `./_lib/...`, and a require failure exits non-zero exactly like a
  // sabotage that worked -- which is how four of five controls in another
  // suite today passed while measuring an import crash. Same directory, unique
  // name, removed in the finally.
  const mutPath = path.join(path.dirname(SRC_PATH),
    '_mutant_' + process.pid + '_' + Math.abs(anchor.length) + '.js');
  fs.writeFileSync(mutPath, patched);
  try {
    const back = fs.readFileSync(mutPath, 'utf8');
    if (back !== patched) throw new Error('the mutant did not land on disk');
    delete require.cache[mutPath];
    const mod = require(mutPath);
    if (typeof mod !== 'function') {
      throw new Error('the mutant did not export a handler -- it did not run, so ' +
        'any red result below would be measuring a load failure');
    }
    return fn(mod);
  } finally {
    delete require.cache[mutPath];
    try { fs.unlinkSync(mutPath); } catch (e) { /* best effort */ }
  }
}

t('Z1 a string-blind max_tokens clamp violates R2', () => {
  const broke = withMutant(
    '  const n = Number(requested);\n  if (!Number.isFinite(n) || n <= 0) return DEFAULT_MAX_TOKENS;\n  return Math.min(Math.floor(n), MAX_TOKENS_CEILING);',
    '  if (typeof requested === \'string\') return MAX_TOKENS_CEILING;\n  const n = Number(requested);\n  if (!Number.isFinite(n) || n <= 0) return DEFAULT_MAX_TOKENS;\n  return Math.min(Math.floor(n), MAX_TOKENS_CEILING);',
    (mod) => !relEqualRepresentations(mod.cappedMaxTokens));
  if (!broke) throw new Error('R2 stayed green against a string-blind clamp, so it ' +
    'is not actually testing the relation');
});

t('Z2 a substring app_id match makes R1 go red', () => {
  const red = withMutant(
    // The anchor is the WHOLE condition including the falsy-app_id guard. The
    // first attempt anchored on `if (!KNOWN_APP_IDS.includes(app_id))` alone
    // and did not match, because the real line is
    // `if (!app_id || !KNOWN_APP_IDS.includes(app_id))`. The control REFUSED
    // rather than silently replacing nothing -- which is the whole reason
    // withMutant() throws on a missed anchor instead of proceeding.
    'if (!app_id || !KNOWN_APP_IDS.includes(app_id))',
    'if (!app_id || !KNOWN_APP_IDS.some(function (k) { return String(app_id || \'\').indexOf(k) !== -1; }))',
    (mod) => {
      // Drive the mutant directly rather than through `call`, which is bound to
      // the real module.
      let calls = 0;
      const prev = global.fetch;
      global.fetch = async function (u, o) {
        calls += 1; return { ok: true, status: 200,
          json: async () => ({ content: [{ type: 'text', text: 'ok' }], usage: {} }) };
      };
      const res = mockRes();
      return mod({ method: 'POST', headers: {}, body: { app_id: ' ' + REAL_APP, is_demo: true, messages: MSG } }, res)
        .then(() => { global.fetch = prev; return res._s === 200; })
        .catch((e) => { global.fetch = prev; throw e; });
    });
  return red.then((accepted) => {
    if (!accepted) {
      throw new Error('a SUBSTRING allowlist did not accept a padded app_id, so R1 ' +
        'is not proven to be testing exactness');
    }
  });
});

t('Z3 a non-idempotent clamp makes R3 go red', () => {
  const broke = withMutant(
    '  return Math.min(Math.floor(n), MAX_TOKENS_CEILING);\n}',
    '  return Math.min(Math.floor(n) + 1, MAX_TOKENS_CEILING);\n}',
    (mod) => !relIdempotent(mod.cappedMaxTokens));
  if (!broke) throw new Error('R3 stayed green against an off-by-one clamp');
});

t('Z4 a case-insensitive tool whitelist makes R4 go red', () => {
  const broke = withMutant(
    'ALLOWED_SERVER_TOOL_TYPES.includes(t.type)',
    'ALLOWED_SERVER_TOOL_TYPES.some(function (a) { return String(a).toLowerCase() === String(t.type).toLowerCase(); })',
    (mod) => {
      const out = mod.sanitizeTools([{ type: SERVER_TOOL.toUpperCase() }]) || [];
      return out.length > 0;
    });
  if (!broke) throw new Error('a case-insensitive whitelist accepted nothing new, so ' +
    'R4\'s exactness arm is not proven');
});

t('Z5 the real module is byte-identical after every mutant', () => {
  const now = fs.readFileSync(SRC_PATH, 'utf8');
  if (now !== ORIGINAL) throw new Error('api/claude.js was modified by this suite');
  const leftovers = fs.readdirSync(path.dirname(SRC_PATH))
    .filter((f) => f.indexOf('_mutant_') === 0);
  if (leftovers.length) throw new Error('mutant files left behind: ' + leftovers.join(', '));
});

// ── RUNNER ─────────────────────────────────────────────────────────────────
(async function main() {
  for (const [name, fn] of run) {
    if (!fn) { console.log('\n' + name); continue; }
    try {
      await fn();
      console.log('  ok   ' + name);
      pass += 1;
    } catch (e) {
      console.log('  FAIL ' + name + '\n         ' + (e && e.message ? e.message : e));
      fails.push(name);
    }
  }
  console.log('');
  if (fails.length) {
    console.log('claude-guardrail-metamorphic: ' + pass + ' passed, ' +
      fails.length + ' FAILED -- ' + fails.join('; '));
    process.exit(1);
  }
  console.log('claude-guardrail-metamorphic: all ' + pass +
    ' arms pass, 5 relations hold, 4 mutation controls bite, 0 Anthropic calls.');
})();
