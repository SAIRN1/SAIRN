// The grounded legal-term definition tool, driven verbatim from sairnlaw.html.
//
// WHAT THIS EXISTS TO PIN DOWN. The Legal Reference panel promises "Nothing on
// this screen is answered from the model's memory" and delivers it through a
// real Cornell LII retrieval. The AI Assistant one panel over had two tools,
// neither of them that one, and a system prompt that expressly permitted
// "explaining concepts" -- so a question about what a legal term means was
// answered from model memory, unsourced, inside the product that promises
// otherwise. The citation rule did not reach it: that rule forbids emitting a
// citation STRING and expressly ALLOWS narrative description.
//
// THE NEGATIVE CONTROL IS THE MOST IMPORTANT CASE IN THIS FILE and it is a
// real trap the file's own comment had already predicted. lawExecuteTool used
// to be synchronous. An async tool run through it returns a PENDING PROMISE as
// `result`, and JSON.stringify(pending promise) is "{}" -- so the model would
// have been handed an empty object with ok:true, with nothing throwing and
// nothing logging. That case is asserted directly against a reconstructed copy
// of the old dispatcher, so the async change is proven load-bearing rather
// than asserted to be.
//
// Nothing here talks to Cornell LII. referenceFetch is stubbed, because what
// is being tested is that the tool returns ONLY what it was handed and refuses
// loudly with the REASON when it is handed nothing.

const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', '..', 'sairnlaw.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

// ── verbatim extraction ──────────────────────────────────────────────────
function balanced(start, open, close) {
  let i = src.indexOf(open, start), depth = 0;
  if (i < 0) throw new Error('no ' + open + ' after ' + start);
  for (; i < src.length; i++) {
    if (src[i] === open) depth++;
    else if (src[i] === close) { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced from ' + start);
}
function extractFn(sig) {
  const start = src.indexOf(sig);
  if (start < 0) throw new Error('not found: ' + sig);
  return balanced(start, '{', '}');
}
function extractCall(marker) {
  const start = src.indexOf(marker);
  if (start < 0) throw new Error('not found: ' + marker);
  return balanced(start, '(', ')') + ';';
}
const REGISTER = extractFn('function lawRegisterTool(');
const EXECUTE = extractFn('async function lawExecuteTool(');
const DEFINE_TOOL = extractCall("lawRegisterTool(\r\n  'define_legal_term'");

check('lawExecuteTool is async in the real file', /^async function/.test(EXECUTE), true);
check('and its call site in sendAI awaits it',
  src.indexOf('var outcome=await lawExecuteTool(') !== -1, true);
check('the define tool is registered NOT sensitive -- a dictionary is not firm data',
  /\n  false,\r?\n/.test(DEFINE_TOOL), true);

// ── the world the extracted code runs in ────────────────────────────────
function build(referenceFetch, executeSrc) {
  const factory = new Function('referenceFetch',
    'var LAW_TOOLS = {};\n' + REGISTER + '\n' + (executeSrc || EXECUTE) + '\n' + DEFINE_TOOL +
    '\nreturn { LAW_TOOLS: LAW_TOOLS, lawExecuteTool: lawExecuteTool, lawRegisterTool: lawRegisterTool };');
  return factory(referenceFetch);
}

const WEX_OK = {
  ok: true,
  term: 'Res Judicata',
  paragraphs: ['Res judicata is a Latin phrase meaning a matter judged.', 'It bars relitigation.', 'Third.', 'Fourth.', 'FIFTH SHOULD BE DROPPED.'],
  crossReferences: [{ term: 'collateral estoppel', url: 'https://www.law.cornell.edu/wex/collateral_estoppel' }],
  source_name: 'Cornell LII Wex',
  source_url: 'https://www.law.cornell.edu/wex/res_judicata',
  retrieved_at: '2026-09-02T00:00:00.000Z'
};

async function run(stub, input, role) {
  const w = build(stub);
  return w.lawExecuteTool('define_legal_term', role || 'owner', input);
}

(async () => {
  // ── the grounded path returns ONLY retrieved fields ────────────────────
  let seen = null;
  const good = await run(async (action, payload) => { seen = { action, payload }; return WEX_OK; }, { term: ' res judicata ' });
  check('the tool calls the define action with the trimmed term',
    seen, { action: 'define', payload: { term: 'res judicata' } });
  check('a grounded lookup succeeds', good.ok, true);
  check('and returns the REAL source url it was handed, not one it composed',
    good.result.source_url, 'https://www.law.cornell.edu/wex/res_judicata');
  check('the definition text is the retrieved text, capped at four paragraphs',
    good.result.definition_paragraphs, WEX_OK.paragraphs.slice(0, 4));
  check('the fifth paragraph is dropped rather than summarised',
    good.result.definition_paragraphs.indexOf('FIFTH SHOULD BE DROPPED.'), -1);
  check('related terms come across as names only', good.result.related_terms, ['collateral estoppel']);
  check('and the result is marked grounded', good.result.grounded, true);
  // COMPOSES NOTHING: every key must trace to a field the stub supplied.
  check('the result invents no field of its own',
    Object.keys(good.result).sort(),
    ['definition_paragraphs', 'grounded', 'related_terms', 'retrieved_at', 'source_name', 'source_url', 'term']);

  // ── every failure refuses, and each one says WHICH ────────────────────
  const notFound = await run(async () => ({ ok: false, code: 'NOT_FOUND', message: 'no entry' }), { term: 'zzz' });
  check('a term Wex does not hold is a refusal, not an empty definition', notFound.ok, false);
  check('and it says Wex has no entry rather than "could not retrieve"',
    /has no entry/.test(notFound.error), true);

  const limited = await run(async () => ({ ok: false, code: 'RATE_LIMITED', message: 'wait' }), { term: 'estoppel' });
  check('a rate-limited lookup is a refusal', limited.ok, false);
  check('and it is distinguishable from NOT_FOUND, because only one is worth retrying',
    [/10 seconds/.test(limited.error), /has no entry/.test(limited.error)], [true, false]);

  const netErr = await run(async () => ({ error: { message: 'Network error: boom' } }), { term: 'laches' });
  check('a transport failure is a refusal that names the transport failure',
    [netErr.ok, /Network error: boom/.test(netErr.error)], [false, true]);

  const empty = await run(async () => { throw new Error('should not be called'); }, { term: '   ' });
  check('a blank term never reaches the network and refuses',
    [empty.ok, /No term was supplied/.test(empty.error)], [false, true]);

  // A REAL CRASH IS STILL FLATTENED. userSafe is opt-in precisely so an
  // unexpected throw cannot leak internals into a user-visible turn.
  const crash = await run(async () => { throw new Error('SUPABASE_SERVICE_ROLE_KEY missing'); }, { term: 'tort' });
  check('an unmarked internal error keeps the generic message',
    [crash.ok, crash.error], [false, 'Could not retrieve that data right now.']);
  check('and does not leak what actually failed',
    /SUPABASE/.test(crash.error), false);

  // ── the async dispatcher did not break the synchronous tools ──────────
  {
    const w = build(async () => WEX_OK);
    w.lawRegisterTool('sync_tool', 'd', { type: 'object', properties: {}, required: [] }, false, function () { return { n: 7 }; });
    const r = await w.lawExecuteTool('sync_tool', 'owner', {});
    check('a synchronous tool still returns its value unchanged through the async dispatcher',
      [r.ok, r.result], [true, { n: 7 }]);
    w.lawRegisterTool('secret', 'd', { type: 'object', properties: {}, required: [] }, true, function () { return 1; });
    const denied = await w.lawExecuteTool('secret', 'paralegal', {});
    check('the role gate on a sensitive tool still refuses before running it',
      [denied.ok, denied.error], [false, 'This data is restricted to the owner role.']);
    const missing = await w.lawExecuteTool('nope', 'owner', {});
    check('an unknown tool name still refuses', missing.ok, false);
  }

  // ── NEGATIVE CONTROL: the OLD synchronous dispatcher ──────────────────
  // Reconstructed from the constraint the file used to document, to prove the
  // async change is load-bearing. This is the failure the old comment warned
  // about, measured rather than described.
  const OLD_SYNC = `function lawExecuteTool(name, role, input) {
    var tool = LAW_TOOLS[name];
    if (!tool) return { ok: false, error: 'No tool named "' + name + '" exists.' };
    if (tool.sensitive && role !== 'owner') return { ok: false, error: 'This data is restricted to the owner role.' };
    try { return { ok: true, result: tool.run(input || {}) }; }
    catch (e) { return { ok: false, error: 'Could not retrieve that data right now.' }; }
  }`;
  {
    const w = build(async () => WEX_OK, OLD_SYNC);
    const bad = w.lawExecuteTool('define_legal_term', 'owner', { term: 'res judicata' });
    check('under the OLD sync dispatcher the tool reports SUCCESS', bad.ok, true);
    check('...with a pending Promise as the result', bad.result instanceof Promise, true);
    // This is the exact string sendAI() would have put in tool_result.
    check('...which serialises to an EMPTY OBJECT for the model, silently',
      JSON.stringify(bad.result), '{}');
    const badErr = w.lawExecuteTool('define_legal_term', 'owner', { term: '   ' });
    check('...and even the blank-term refusal is swallowed into a fake success',
      [badErr.ok, JSON.stringify(badErr.result)], [true, '{}']);
    if (bad.result && bad.result.catch) bad.result.catch(() => {});
    if (badErr.result && badErr.result.catch) badErr.result.catch(() => {});
  }

  // ── the instruction and the mechanism have to agree ───────────────────
  check('LAW_DEFINITION_RULE exists', src.indexOf('var LAW_DEFINITION_RULE=') !== -1, true);
  check('and it is actually spliced into the system prompt, not merely declared',
    src.indexOf("+LAW_DEFINITION_RULE+") !== -1, true);
  check('it names the tool the assistant must call',
    /LAW_DEFINITION_RULE='[^']*define_legal_term/.test(src), true);
  check('it forbids the fallback in the words the model would otherwise reach for',
    ['general sense', 'roughly speaking', 'own knowledge'].map(s => src.indexOf(s) !== -1),
    [true, true, true]);
  check('the firm-data rule no longer grants a blanket "explaining concepts" permission',
    /help with general drafting, explaining concepts/.test(src), false);
  check('and it hands term questions to the definition rule explicitly',
    /governed by the definition rule/.test(src), true);

  console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
  if (fail) process.exit(1);
})();
