// tests/composite_context.js
//
// Run:  node tests/composite_context.js
//
// [0039] THE COMPOSITE INFERENCE CONTEXT.
//
// buildSDSystemPrompt() concatenated four blocks with `+` and returned a
// string. Memory selection was `_sdMemories.slice(0, 10)` -- insertion order,
// no relevance, no bound -- and the assembled system prompt had no budget at
// all, while the [0039] message budget shipped the same day measured itself
// against it.
//
// Most of what is asserted below is NOT the arithmetic. It is the three
// places this kind of change goes quietly wrong:
//
//   * A ranking that silently reorders the no-query case. If relevance
//     scoring changes what a shop sees when nothing was asked, the change is
//     invisible and untraceable. The old order is asserted as the floor.
//   * A date guard that treats a missing value as a number. new Date('') is
//     NaN but new Date(null) is 0, and 0 here means "January 1970" stated
//     confidently. This platform has been bitten by that shape repeatedly.
//   * A drop policy that cuts the wrong thing, or cuts silently. The order
//     is asserted explicitly, and so is the fact that the base prompt, the
//     shop's name and the declared style note are never droppable.
//
// The implementation is extracted from the real stonedesk.html rather than
// re-stated here, so this file fails if what ships changes.

'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'stonedesk.html'), 'utf8');

function grab(startMarker, endMarker) {
  const s = html.indexOf(startMarker);
  assert.ok(s > 0, 'not found in stonedesk.html: ' + startMarker);
  const e = html.indexOf(endMarker, s);
  assert.ok(e > s, 'unterminated: ' + startMarker);
  return html.slice(s, e);
}

const ctx = { console, Date, Math, JSON, String, Number, Array };
vm.createContext(ctx);
vm.runInContext(
  grab('var SD_CTX_TOK_CHARS = 4;', '// === SYSTEM PROMPT BUILDER'),
  ctx
);
const {
  sdCtxEstTokens, sdCtxTerms, sdCtxRelevance, sdCtxRecency,
  sdCtxScoreMemories, sdCtxProfileFields, sdBuildInferenceContext,
  SD_CTX_MAX_MEMORIES, SD_CONTEXT_BUDGET_TOKENS,
  SD_CTX_W_RELEVANCE, SD_CTX_W_RECENCY
} = ctx;

let n = 0;
function ok(cond, label) { assert.ok(cond, label); n++; }
// Values built inside the vm belong to the vm's realm, so an array it
// returns is not an instanceof the host's Array and deepStrictEqual rejects
// it on prototype identity alone. Normalise through JSON so the assertion is
// about the values, which is what it was ever meant to be about.
function eq(a, b, label) {
  const norm = (v) => (v !== null && typeof v === 'object') ? JSON.parse(JSON.stringify(v)) : v;
  assert.deepStrictEqual(norm(a), norm(b), label);
  n++;
}

const NOW = Date.parse('2026-09-02T12:00:00Z');
const DAY = 86400000;
function mem(text, ageDays, extra) {
  return Object.assign({
    memory_text: text,
    source: 'stonedesk',
    created_at: ageDays === null ? null : new Date(NOW - ageDays * DAY).toISOString()
  }, extra || {});
}

// ── 1. The extraction itself ────────────────────────────────────────────────
ok(typeof sdBuildInferenceContext === 'function', 'sdBuildInferenceContext extracted');
ok(SD_CTX_MAX_MEMORIES === 10,
   'the memory COUNT is unchanged from slice(0,10) -- this change is about which, not how many');

// ── 2. Term extraction ──────────────────────────────────────────────────────
eq(sdCtxTerms('The granite countertop AND the quartz'), ['granite', 'countertop', 'quartz'],
   'stopwords and sub-3-char tokens dropped, order preserved, deduped');
eq(sdCtxTerms(null), [], 'null text is not a crash and not a term');
eq(sdCtxTerms('a a a'), [], 'nothing but stopwords/short tokens yields nothing');

// ── 3. Relevance ────────────────────────────────────────────────────────────
ok(sdCtxRelevance(['granite'], []) === 0, 'no query terms means no relevance, never a divide-by-zero');
ok(sdCtxRelevance([], ['granite']) === 0, 'an empty memory scores 0');
ok(sdCtxRelevance(['granite'], ['granite']) === 1, 'a one-term query fully matched scores 1');
// The specific thing sqrt-normalisation buys: a 9-term question with 3 real
// hits is a strong match, not a 33% one.
ok(sdCtxRelevance(['granite', 'slab', 'waste'],
                  ['granite', 'slab', 'waste', 'kitchen', 'edge', 'profile', 'quartz', 'marble', 'seam']) === 1,
   '3-of-9 reaches 1.0 under sqrt normalisation rather than 0.33');
ok(sdCtxRelevance(['granite'],
                  ['granite', 'slab', 'waste', 'kitchen', 'edge', 'profile', 'quartz', 'marble', 'seam']) < 0.4,
   '1-of-9 is a weak match and scores like one');
// A long memory is not punished for saying more than was asked.
const longMem = sdCtxTerms('granite slab waste kitchen edge profile seam install template fabrication');
ok(sdCtxRelevance(longMem, ['granite']) === 1,
   'a long memory containing the query term still scores 1 -- Jaccard would penalise it');

// ── 4. Recency, and the empty-value-becomes-a-number trap ───────────────────
ok(sdCtxRecency(null, NOW) === null, 'null created_at is undated, not 1970');
ok(sdCtxRecency('', NOW) === null, 'empty string is undated, not 1970');
ok(sdCtxRecency(undefined, NOW) === null, 'undefined is undated');
ok(sdCtxRecency('not a date', NOW) === null, 'unparseable is undated, not NaN leaking into a score');
// This is the assertion that matters: new Date(null).getTime() === 0, which
// Number.isFinite accepts. If the guard were `if (!t) return null` it would
// pass by accident; if it were a plain isFinite on an unchecked value it
// would return a 1970 recency of ~0 and rank the memory dead last as though
// that were measured. The null check in front is what makes it correct.
ok(new Date(null).getTime() === 0, 'precondition: new Date(null) is epoch 0, not NaN');
ok(sdCtxRecency(new Date(NOW).toISOString(), NOW) === 1, 'a memory written now scores 1');
ok(Math.abs(sdCtxRecency(new Date(NOW - 30 * DAY).toISOString(), NOW) - 0.5) < 1e-9,
   'the 30-day half-life is actually a half-life');
ok(sdCtxRecency(new Date(NOW + 90 * DAY).toISOString(), NOW) === 1,
   'a clock-skewed future stamp is clamped to now, never to better-than-now');

// ── 5. Ranking with NO query degenerates to the old order ───────────────────
// The floor. If this fails, the change is invisible to anyone who did not
// know to look for it.
const hist = [mem('newest note', 1), mem('middle note', 10), mem('oldest note', 100)];
const noQuery = sdCtxScoreMemories(hist, undefined, NOW);
eq(noQuery.map(m => m.text), ['newest note', 'middle note', 'oldest note'],
   'with no query the ranking is pure recency -- the same order slice(0,10) produced');
eq(sdCtxScoreMemories(hist, '', NOW).map(m => m.text),
   ['newest note', 'middle note', 'oldest note'],
   'an empty query behaves the same as no query');

// ── 6. Relevance actually beats recency ─────────────────────────────────────
const mixed = [mem('shop bought a new forklift', 0), mem('quartzite pricing runs 30% over granite', 120)];
const ranked = sdCtxScoreMemories(mixed, 'what should I charge for quartzite', NOW);
eq(ranked[0].text, 'quartzite pricing runs 30% over granite',
   'a four-month-old memory about the exact subject outranks a same-day unrelated one');
ok(ranked[0].relevance > 0 && ranked[1].relevance === 0, 'and it wins on relevance, not on a tie-break');

// An undated memory stays eligible on relevance alone.
const undated = sdCtxScoreMemories(
  [mem('shop bought a new forklift', 0), mem('quartzite pricing runs 30% over granite', null)],
  'quartzite pricing', NOW);
eq(undated[0].text, 'quartzite pricing runs 30% over granite',
   'an undated memory can still win on relevance');
ok(undated[0].recency === null && undated[0].dated === false,
   'and its missing date is recorded as null, not imputed');
ok(Math.abs(undated[0].score - SD_CTX_W_RELEVANCE * undated[0].relevance) < 1e-9,
   'an undated memory contributes exactly zero on the recency axis');

// Stable tie-break: equal scores keep insertion order.
const ties = sdCtxScoreMemories([mem('alpha', null), mem('beta', null), mem('gamma', null)], '', NOW);
eq(ties.map(m => m.text), ['alpha', 'beta', 'gamma'], 'equal scores keep insertion order');

// Empty / whitespace memory text is excluded rather than rendered as a blank row.
eq(sdCtxScoreMemories([mem('', 1), mem('   ', 1), mem('real', 1)], '', NOW).map(m => m.text),
   ['real'], 'blank memory text is dropped, not numbered into the prompt');

// ── 7. Named profile fields, and the two fabricated facts that are gone ─────
const fullProfile = {
  company_name: 'Pinnacle Stone', ein: '12-3456789', city: 'Dallas', state: 'Texas',
  headcount: 14, revenue_range: '1m_5m',
  preferences: { owner_name: 'A. Ruiz', ai_notes: 'Two saws, one CNC.' }
};
const fields = sdCtxProfileFields(fullProfile);
eq(fields.map(f => f.key).sort(),
   ['ai_notes', 'city', 'company_name', 'ein', 'headcount', 'owner_name', 'revenue_range', 'state'].sort(),
   'every populated field is named');
eq(fields.filter(f => f.drop === null).map(f => f.key), ['company_name'],
   'the shop name is the only profile field that can never be dropped');

// The corrections. A sparse profile must not acquire facts it never had.
const sparse = sdCtxProfileFields({ company_name: 'Pinnacle Stone' });
eq(sparse.map(f => f.key), ['company_name'], 'a name-only profile yields exactly one field');
const sparseCtx = sdBuildInferenceContext({ base: 'BASE', profile: { company_name: 'Pinnacle Stone' }, nowMs: NOW });
ok(!/Ohio/.test(sparseCtx.system),
   'the hardcoded ", Ohio" is gone -- it used to be stamped on every shop in the country');
ok(!/Westlake/.test(sparseCtx.system),
   'the hardcoded "Westlake" city default is gone');
ok(!/Headcount/.test(sparseCtx.system),
   'headcount is absent when unknown, instead of asserting a one-person shop');
// And a real Texas shop is described as a Texas shop.
const txCtx = sdBuildInferenceContext({ base: 'BASE', profile: fullProfile, nowMs: NOW });
ok(/City: Dallas/.test(txCtx.system) && /State: Texas/.test(txCtx.system),
   'a shop that filled in its location gets its own location');
eq(sdCtxProfileFields(null), [], 'no profile is no fields');
eq(sdCtxProfileFields({ city: 'Dallas' }), [],
   'a profile with no company_name yields nothing, same gate as before');

// ── 8. The budget bounds the system prompt ──────────────────────────────────
const many = [];
for (let i = 0; i < 20; i++) many.push(mem('note ' + i + ' ' + 'x'.repeat(400), i));
const bounded = sdBuildInferenceContext({
  base: 'BASE', profile: fullProfile, memories: many,
  styleNote: '\n\nResponse style: Be direct and concise.',
  budgetTokens: 400, nowMs: NOW
});
ok(bounded.tokens <= bounded.budget, 'the assembled prompt is actually inside its budget');
ok(bounded.over === false, 'and it did not have to report itself over');
ok(bounded.dropped.length > 0, 'getting there required drops, and they are reported');
// The reported total is measured off the rendered string, not summed from
// parts -- a total assembled from per-part estimates disagrees with what is
// actually sent, which is the failure this whole file is about.
eq(bounded.tokens, sdCtxEstTokens(bounded.system) + bounded.reserved,
   'the reported token count is the rendered string, not a sum of estimates');

// ── 9. The drop policy, in order ────────────────────────────────────────────
// Memories go first, lowest-scored first.
const dropOrder = sdBuildInferenceContext({
  base: 'B', profile: fullProfile,
  memories: [mem('granite ' + 'a'.repeat(200), 1), mem('unrelated ' + 'b'.repeat(200), 2)],
  styleNote: '\n\nResponse style: Be direct and concise.',
  styleDirectives: '\n\nWrite in short sentences.',
  query: 'granite', budgetTokens: 130, nowMs: NOW
});
eq(dropOrder.dropped[0].kind, 'memory', 'memories are cut before anything else');
ok(dropOrder.fields.memories.selected.every(m => !/unrelated/.test(m.text)),
   'and the lowest-scored memory is the one that goes');

// Then style directives, then profile fields by rank.
function cutSequence(budget) {
  return sdBuildInferenceContext({
    base: 'B', profile: fullProfile, memories: [mem('note', 1)],
    styleNote: '\n\nResponse style: Be direct and concise.',
    styleDirectives: '\n\nWrite in short sentences.',
    budgetTokens: budget, nowMs: NOW
  }).dropped.map(d => d.key || d.kind);
}
const seq = cutSequence(1);
eq(seq.slice(0, 2), ['memory', 'style_directives'],
   'after memories, the inferred style directives go before any declared fact');
eq(seq.slice(2), ['ai_notes', 'revenue_range', 'ein', 'owner_name', 'headcount', 'city', 'state'],
   'profile fields are cut in the declared drop order, free text first and location last');

// What is never cut, even at a budget of 1.
const stripped = sdBuildInferenceContext({
  base: 'BASEPROMPT', profile: fullProfile, memories: [mem('note', 1)],
  styleNote: '\n\nResponse style: Be direct and concise.',
  styleDirectives: '\n\nWrite in short sentences.',
  budgetTokens: 1, nowMs: NOW
});
ok(/BASEPROMPT/.test(stripped.system), 'the base prompt is never dropped');
ok(/Pinnacle Stone/.test(stripped.system), 'the shop name is never dropped');
ok(/Response style/.test(stripped.system), 'the declared style note is never dropped');
ok(stripped.over === true,
   'and when the undroppable core still will not fit, that is REPORTED rather than sent quietly');

// ── 10. Withholding is disclosed, which slice(0,10) never did ───────────────
const twenty = [];
for (let i = 0; i < 20; i++) twenty.push(mem('note number ' + i, i));
const capped = sdBuildInferenceContext({ base: 'B', memories: twenty, nowMs: NOW });
eq(capped.fields.memories.selected.length, 10, 'ten memories are selected out of twenty');
eq(capped.fields.memories.considered, 20, 'and all twenty are recorded as considered');
eq(capped.fields.memories.capped_out, 10, 'the ten held back are counted');
ok(/10 further notes about this shop exist/.test(capped.system),
   'the model is TOLD it is not seeing everything -- the old slice(0,10) said nothing');
ok(/Do not treat the list above as everything/.test(capped.system),
   'and is told not to treat the partial list as complete, same discipline as a truncated tool result');
const nine = sdBuildInferenceContext({ base: 'B', memories: twenty.slice(0, 9), nowMs: NOW });
ok(!/further note/.test(nine.system), 'no disclosure when nothing was withheld');
const one = sdBuildInferenceContext({ base: 'B', memories: twenty.slice(0, 11), nowMs: NOW });
ok(/1 further note about this shop exists/.test(one.system), 'singular is singular');

// ── 11. Degenerate inputs do not throw ──────────────────────────────────────
ok(typeof sdBuildInferenceContext().system === 'string', 'no arguments at all still returns a prompt');
ok(sdBuildInferenceContext({ base: 'B', memories: null, profile: null }).system === 'B',
   'null memories and null profile render the base alone, byte for byte');
ok(sdBuildInferenceContext({ base: 'B', memories: [], profile: undefined }).dropped.length === 0,
   'nothing to drop means nothing reported dropped');
ok(sdBuildInferenceContext({ base: 'B', memories: [{}, { memory_text: null }], nowMs: NOW })
     .fields.memories.selected.length === 0,
   'malformed memory rows are skipped, not rendered as "1. undefined"');
eq(sdBuildInferenceContext({ base: 'B', memories: [mem('a', null), mem('b', 1)], nowMs: NOW })
     .fields.memories.undated, 1,
   'undated memories are counted so the reason a ranking looks odd is inspectable');

// ── 12. The reserved allowance is real ──────────────────────────────────────
// sendMsg appends a 383-char guardrail AFTER this returns. A budget that
// ignores it is wrong by construction.
const noReserve = sdBuildInferenceContext({ base: 'x'.repeat(1200), budgetTokens: 300, nowMs: NOW });
const withReserve = sdBuildInferenceContext({ base: 'x'.repeat(1200), budgetTokens: 300, reservedTokens: 96, nowMs: NOW });
ok(withReserve.tokens === noReserve.tokens + 96,
   'the reserved guardrail is counted against the budget, not added behind its back');

// ── 13. Mutation check, stated rather than assumed ──────────────────────────
// Re-run the ranking with the relevance weight zeroed. If assertion 6 still
// passed under that mutation, it was testing nothing.
(function mutationProbe() {
  const mutated = vm.createContext({ console, Date, Math, JSON, String, Number, Array });
  vm.runInContext(
    grab('var SD_CTX_TOK_CHARS = 4;', '// === SYSTEM PROMPT BUILDER')
      .replace('var SD_CTX_W_RELEVANCE = 0.65;', 'var SD_CTX_W_RELEVANCE = 0;'),
    mutated
  );
  const r = mutated.sdCtxScoreMemories(mixed, 'what should I charge for quartzite', NOW);
  ok(r[0].text === 'shop bought a new forklift',
     'MUTATION PROBE: with the relevance weight zeroed the ranking reverts to recency, so the relevance assertion above is load-bearing');
})();

console.log('composite_context: ' + n + '/' + n + ' assertions passed');
