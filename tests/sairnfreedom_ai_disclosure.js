// tests/sairnfreedom_ai_disclosure.js
//
// Run:  node tests/sairnfreedom_ai_disclosure.js
//
// REQUIREMENT: every AI surface in SAIRNfreedom says it is AI on its output,
//   the one AI-written record carries `ai_source`, and the one-time notice is
//   acknowledged once per employee against the server rather than per device.
//
// ── WHY THE FOUR SITES ARE DERIVED AND NOT LISTED ─────────────────────────
// A suite that named four line numbers would pass forever after a fifth AI
// feature was added. This one finds every `callClaude(` call site in the file,
// walks out to its enclosing function, and requires `sfAiLabel(` inside it. Add
// a fifth AI feature with no disclosure and this goes red on that commit; move
// the existing ones anywhere and it does not.
//
// THE COUNT IS ASSERTED AS A FLOOR AND THE NAMES ARE ASSERTED EXACTLY, which is
// the shape that survives both directions: four today, and if that becomes
// three because a feature was removed, the name list says which one went.

'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const HTML = fs.readFileSync(process.env.SF_HTML
  || path.join(ROOT, 'sairnfreedom.html'), 'utf8').replace(/\r\n/g, '\n');

// Assembled rather than written as escapes -- this file has been through a
// generator once already and a lone backslash in a char literal is what it
// mangled.
const BS = String.fromCharCode(92);
const NL = String.fromCharCode(10);

let n = 0, bad = 0;
function ok(cond, label) {
  if (cond) { console.log('  ok   ' + label); n++; }
  else { console.log('  FAIL ' + label); bad++; }
}
function section(s) { console.log('\n' + s); }

// ── COMMENTS ARE BLANKED BEFORE ANYTHING IS COUNTED, AND THAT IS NOT ──────
// ── TIDINESS -- THE FIRST DRAFT OF THIS SUITE WAS FOOLED BY ONE ───────────
// It found FIVE `callClaude(` call sites and then crashed looking for the
// enclosing function of the fifth, which is this sentence inside a comment at
// sairnfreedom.html:
//
//     "most of them hardcode the URL rather than going through their app's own
//      callClaude(). Editing them all to ship a security fix is the..."
//
// PR 1.2 exactly: grep cannot tell code from text that describes code. Had the
// walker not crashed it would have reported a naked AI surface that does not
// exist, and the fix for a false finding is usually to loosen the check --
// which is how a real one gets lost later.
//
// The blanked copy is the SAME LENGTH as the original, so every index found in
// it points at the same byte of the real file. Shortening the string instead
// would shift every offset and silently misattribute each site.
function blankComments(src) {
  const out = src.split('');
  // ONLY INSIDE <script> SPANS. The markup above them is prose, and prose has
  // apostrophes in it ("don't"), which this walker would read as an unbalanced
  // string delimiter and then swallow whatever came next.
  const spans = [];
  let p = 0;
  while ((p = src.indexOf('<script', p)) !== -1) {
    const open = src.indexOf('>', p);
    const close = src.indexOf('</script', open);
    if (open === -1 || close === -1) break;
    spans.push([open + 1, close]);
    p = close + 1;
  }
  for (const [from, to] of spans) {
    let i = from, q = null;
    while (i < to) {
      const c = src[i];
      if (q) {
        if (c === BS) { i += 2; continue; }
        if (c === q) q = null;
        i++; continue;
      }
      // COMMENTS ARE TESTED BEFORE QUOTES, and the first draft had it the
      // other way round. An apostrophe inside a block comment -- "their app's
      // own callClaude()" -- opened a fake string, the walker ran to the next
      // apostrophe, and the comment it was supposed to blank survived intact.
      // The symptom was a FIFTH AI call site with no enclosing function.
      if (c === '/' && src[i + 1] === '/') {
        while (i < to && src[i] !== NL) { out[i] = ' '; i++; }
        continue;
      }
      if (c === '/' && src[i + 1] === '*') {
        while (i < to && !(src[i] === '*' && src[i + 1] === '/')) {
          if (src[i] !== NL) out[i] = ' ';
          i++;
        }
        if (i < to) { out[i] = ' '; out[i + 1] = ' '; i += 2; }
        continue;
      }
      if (c === '"' || c === "'" || c === '`') { q = c; i++; continue; }
      i++;
    }
  }
  return out.join('');
}
const CODE = blankComments(HTML);

// Brace-matched extraction, quote- and comment-aware. Same walker
// tests/sairnlegacy_reservation_lock.js uses, for the same reason: a regex that
// stops at the first `}` grabs a fragment and asserts against it happily.
function grab(sig) {
  const start = HTML.indexOf(sig);
  assert.ok(start > 0, 'not found in sairnfreedom.html: ' + sig);
  let i = HTML.indexOf('{', start + sig.length - 1), depth = 0, q = null;
  for (; i < HTML.length; i++) {
    const c = HTML[i], p = HTML[i - 1];
    if (q) { if (c === q && p !== '\\') q = null; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '/' && HTML[i + 1] === '/') { i = HTML.indexOf('\n', i); continue; }
    if (c === '/' && HTML[i + 1] === '*') { i = HTML.indexOf('*/', i) + 1; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (!depth) return HTML.slice(start, i + 1); }
  }
  throw new Error('unterminated: ' + sig);
}

console.log('SAIRNfreedom -- every AI surface says it is AI\n');

(async () => {
  // ══ 1. EVERY AI CALL SITE IS INSIDE A FUNCTION THAT LABELS ITS OUTPUT ═══
  section('1. the AI surfaces, DERIVED from the call sites rather than listed');
  const DEF = 'function callClaude(payload){';
  const defAt = CODE.indexOf(DEF);
  ok(defAt > 0, 'callClaude() is the single AI transport in this file');

  // Every call that is not the definition.
  const sites = [];
  let at = 0;
  while ((at = CODE.indexOf('callClaude(', at + 1)) !== -1) {
    if (at === defAt + 'function '.length) continue;   // the declaration
    sites.push(at);
  }
  ok(sites.length >= 4,
     'found ' + sites.length + ' AI call site(s) in CODE -- a floor of four, '
     + 'so a suite that found one would not quietly pass');
  ok(HTML.split('callClaude(').length - 1 > sites.length + 1,
     '...and the raw file mentions callClaude( MORE times than that, which is '
     + 'the comment-blanking doing its job rather than being decorative: '
     + (HTML.split('callClaude(').length - 1) + ' raw vs ' + (sites.length + 1)
     + ' in code including the declaration');

  // Walk out to the enclosing function for each, then require the label.
  const enclosing = (idx) => {
    const head = HTML.lastIndexOf('\nfunction ', idx);
    assert.ok(head > 0, 'no enclosing function for the call site at ' + idx);
    const name = (HTML.slice(head + 10, HTML.indexOf('(', head)) || '').trim();
    return { name: name, body: grab(HTML.slice(head + 1, HTML.indexOf('{', head) + 1)) };
  };

  const covered = [];
  const naked = [];
  for (const idx of sites) {
    const fn = enclosing(idx);
    if (!fn) { naked.push('<no enclosing function at offset ' + idx + '>'); continue; }
    if (fn.body.indexOf('sfAiLabel(') !== -1) covered.push(fn.name);
    else naked.push(fn.name);
  }
  ok(naked.length === 0,
     'EVERY function that calls the model labels its output'
     + (naked.length ? ' -- NOT: ' + naked.join(', ') : ''));
  ok(covered.length === sites.length,
     'all ' + sites.length + ' labelled: ' + covered.join(', '));

  // AND THE NAMES, so a REMOVED feature is as visible as an added one.
  // READ OUT OF THE FILE, NOT REMEMBERED. The first draft of this list said
  // `sfMerchSearch`, which has never existed in this file -- the market search
  // is `sfMarketSearch`. That is exactly the propagation this app's own
  // comments record for `sfBottleFill`: a name that appeared in two comments
  // and no function, and was then cited by a register cell and a routed fix
  // before anybody checked. Caught here by the suite failing, not by review.
  const EXPECTED = ['sfEstimateFill', 'sfMarketSearch', 'sfOutreachIdeas',
                    'sfDraftNewsletter'];
  const found = covered.slice().sort();
  const missing = EXPECTED.filter((f) => found.indexOf(f) === -1);
  ok(missing.length === 0,
     'the four known surfaces are all present by name'
     + (missing.length ? ' -- MISSING: ' + missing.join(', ')
          + ' (found: ' + found.join(', ') + ')' : ''));

  // ══ 2. THE LABEL ITSELF ═════════════════════════════════════════════════
  section('2. the label says the thing, in ONE place');
  {
    const ctx = { H: (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;') };
    vm.createContext(ctx);
    vm.runInContext(HTML.slice(HTML.indexOf("var AI_SURFACE_LABEL"),
      HTML.indexOf('\n}', HTML.indexOf('function sfAiLabel(')) + 2), ctx);
    const out = ctx.sfAiLabel();
    ok(/Written by AI/.test(out),
       'the default label says "Written by AI" in plain words -- not '
       + '"AI-assisted", not "powered by", which is what a reader skims past');
    ok(/Claude/.test(out), '...and names the model');
    ok(out.indexOf('<div') === 0 && /<\/div>$/.test(out.trim()),
       '...and it is one element, so it can be prepended anywhere');
    const custom = ctx.sfAiLabel('A specific sentence for this surface.');
    ok(/A specific sentence for this surface\./.test(custom)
       && /Written by AI/.test(custom),
       'a per-surface sentence is allowed and the headline still appears -- so '
       + 'four different explanations cannot produce four different headlines');
    ok(/<script/i.test(ctx.sfAiLabel('<script>x</script>')) === false,
       'the per-surface sentence is ESCAPED. It is author-supplied today, but '
       + 'an unescaped sink in a disclosure is the one place nobody looks');
  }

  // ══ 3. THE RECORD ═══════════════════════════════════════════════════════
  section('3. the one AI-written RECORD carries ai_source');
  {
    const fill = grab('function sfEstimateFill(){');
    ok(/ai_source\s*:\s*'claude:bottle-fill'/.test(fill),
       'sfEstimateFill stores ai_source on the fill record');
    ok(/method\s*:\s*'Automatic, from photograph'/.test(fill),
       '...alongside the method field that was already there, not instead of '
       + 'it -- the two say different things and both are evidence');
    const ai = require(path.join(ROOT, 'api/_lib/ai-safeguards'));
    ok(Object.prototype.hasOwnProperty.call(ai.NOT_HIGH_RISK_AI, 'sf_bottle_fills'),
       'and the platform policy has an explicit NOT-high-risk decision for '
       + 'sf_bottle_fills, so the absence of an approval gate is a recorded '
       + 'argument rather than a gap');
    ok(!ai.isHighRisk('sf_bottle_fills'),
       '...which means this write is not refused for having no approval');
    ok(/no slider|adjustable guess/.test(ai.NOT_HIGH_RISK_AI.sf_bottle_fills),
       '...and that decision cites the app\'s own binding product decision '
       + 'rather than asserting the row is harmless');
  }
  {
    // THE OTHER THREE STORE NOTHING, and that is asserted rather than assumed
    // -- if one of them starts writing a record, it needs ai_source too and
    // this arm is where that gets noticed.
    for (const f of EXPECTED.filter((x) => x !== 'sfEstimateFill')) {
      const body = grab('function ' + f + '(){');
      const writes = /\bst\(\s*K_/.test(body) || /sfData\(\s*'write'/.test(body);
      ok(!writes,
         f + ' stores nothing, so it needs no ai_source -- the day it saves a '
         + 'record this arm goes red and asks for one');
    }
  }

  // ══ 4. THE ONE-TIME NOTICE ══════════════════════════════════════════════
  section('4. the notice is asked once, against the SERVER');
  {
    const check = grab('function sfAiNoticeCheck(){');
    const ack = grab('function sfAckAiNotice(){');
    const call = grab('function sfAiNoticeCall(action, extra){');

    ok(/sfSession && sfSession\.token/.test(call) && /X-SD-Auth/.test(call),
       'the notice calls carry the SESSION token -- the ack is recorded against '
       + 'an employee, so a licence key alone cannot place one');
    ok(/app_id:'sairnfreedom'/.test(call),
       '...and name the app, which is what picks the credential table server '
       + 'side and is re-verified against the token there');
    ok(/data\.required/.test(check),
       'the banner is shown only when the SERVER says the notice is owed');
    ok(/current_version/.test(check),
       '...and the version comes from the server rather than being written '
       + 'here, so a client cannot ack a string the server will never match');
    ok(/localStorage/.test(check) === false && /localStorage/.test(ack) === false,
       'NEITHER path touches localStorage. A per-device flag would re-ask the '
       + 'same person on the post\'s second computer and would be cleared by '
       + 'clearing a browser -- which is why the state is on the server');
    ok(/catch/.test(check) && /style\.display = 'none'/.test(check),
       'every failure path leaves the banner HIDDEN and unacknowledged, so a '
       + 'network blip neither records an ack nor wedges the app');
    ok(/you will be asked again/.test(ack),
       'a FAILED ack tells the user they will be asked again rather than '
       + 'silently appearing to have worked');
    ok(/!res\.d\.ok/.test(ack) || /!res\.ok/.test(ack),
       '...and it checks the server actually said ok before hiding the banner');
  }
  {
    // IT HANGS OFF THE ONE PLACE A SIGN-IN LANDS.
    const enter = grab('function sfEnterApp(d){');
    ok(/sfAiNoticeCheck\(\)/.test(enter),
       'sfEnterApp -- the single sign-in landing point -- runs the check');
    ok(enter.indexOf('sfRenderAll();') < enter.indexOf('sfAiNoticeCheck()'),
       '...AFTER sfRenderAll(), so a slow or failed notice check cannot delay '
       + 'the app rendering');
    ok(/try \{ sfAiNoticeCheck\(\); \} catch/.test(enter),
       '...and inside a try, so a throw in the notice path cannot break a '
       + 'sign-in that has otherwise already succeeded');
  }
  {
    const html = HTML.indexOf('id="ai-notice"');
    ok(html > 0, 'the banner element exists in the markup');
    ok(/id="ai-notice" style="display:none"/.test(HTML),
       '...and starts hidden, so it cannot flash on a page load that does not '
       + 'need it');
  }

  console.log('\n' + n + ' passed, ' + bad + ' failed  ('
              + sites.length + ' AI call site(s) derived)');
  console.log('\nWHAT A GREEN RUN DOES NOT SAY: that the notice has ever been shown to a\n'
              + 'real employee. That needs sql/2026-10-14-hank-b9-ai-safeguards.sql run\n'
              + 'against the live database; until then api/ai-notice.js answers 503 and\n'
              + 'this client correctly leaves the banner hidden.');
  process.exit(bad ? 1 : 0);
})();
