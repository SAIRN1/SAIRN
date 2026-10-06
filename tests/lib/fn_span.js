// tests/lib/fn_span.js
//
// Give a suite the EXACT bytes of one function, bounded by that function's own
// balanced closing brace -- and refuse rather than guess.
//
// ── WHY THIS EXISTS: THE SPAN WAS THE DEFECT, NOT THE APP ─────────────────
// On 2026-10-05 tests/sairnlegacy_write_failure_voice.js reported
// `confirmReserve -> leg_merch_units (writes: )` -- a call site naming a
// resource its own function never writes. The app was RIGHT. Its spanOf()
// defined a function body as "from its start to the start of the next
// `function` ANYWHERE in the file", and confirmReserve declares
// `function undoLocalReservation(){...}` inside itself, so the span stopped at
// the nested declaration and never reached the write.
//
// A sweep for that class on 2026-10-06 measured 24 span sites against the
// function's true balanced end and found 15 that disagreed. Four of the
// disagreements were real and in the SILENT direction; the rest were a single
// trailing newline, or an artefact of the measuring script's own cheaper
// brace walk. The four fixed here are the ones this module is called from.
//
// ── THE DIRECTION THAT MATTERS, because it decides which ones are defects ──
// A span that is wrong is only dangerous in two of the four combinations:
//
//   positive assertion (the span CONTAINS x)  + span TOO LONG  -> FALSE GREEN
//   negative assertion (the span LACKS x)     + span TOO SHORT -> FALSE GREEN
//   positive assertion                        + span too short -> loud red
//   negative assertion                        + span too long  -> loud red
//
// So "the span is approximately right" is not a defence: a fixed `+ 1200`
// window over a 923-byte function hands 277 bytes of the NEXT function to a
// positive assertion, and nothing says so.
//
// ── IT REFUSES, AND THAT IS THE WHOLE POINT ───────────────────────────────
// Three failure modes, all of which previously produced a span rather than an
// error:
//   1. the signature is NOT PRESENT          -> throw, naming it
//   2. the signature appears MORE THAN ONCE  -> throw, naming the count
//   3. no balanced close can be found        -> throw, naming the start offset
// There is deliberately NO fallback bound. A fallback is what turned the
// sairnlegacy case into a silent wrong answer: spanOf() fell back to the next
// function and reported a span it had no basis for. "Could not bound it" is a
// third state and it is not folded into a span.
//
// ── WHAT IT IS NOT ────────────────────────────────────────────────────────
// Not a JS parser. It is a brace counter that skips string literals, line and
// block comments, and regex literals -- the three places a brace is not a
// brace. The division-vs-regex decision is IMPORTED from
// tests/lib/strip_comments.js rather than copied, because that character set
// is the part this platform has got wrong before and a second copy is a second
// thing to drift. Template-literal `${...}` interpolation is treated as string
// content, so a brace inside an interpolation is not counted -- which is the
// under-counting direction and would make the span run LONG, so a caller whose
// target function interpolates must say so. None of the four call sites does;
// that was checked, not assumed.
'use strict';

const { REGEX_OK } = require('./strip_comments.js');

// Walk from `open` (which must be the function's `{`) to its matching `}`.
// Returns the index ONE PAST the closing brace, or -1 when the braces never
// balance before end-of-input.
function balancedEnd(src, open) {
  let depth = 0;
  let i = open;
  let quote = null;
  let line = false;
  let block = false;
  let prev = '';
  const n = src.length;
  while (i < n) {
    const c = src[i];
    const d = i + 1 < n ? src[i + 1] : '';
    if (line) { if (c === '\n') line = false; i++; continue; }
    if (block) { if (c === '*' && d === '/') { block = false; i++; } i++; continue; }
    if (quote) {
      if (c === '\\') { i += 2; continue; }
      if (c === quote) { quote = null; prev = c; }
      i++; continue;
    }
    if (c === '/' && d === '/') { line = true; i += 2; continue; }
    if (c === '/' && d === '*') { block = true; i += 2; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; prev = c; i++; continue; }
    // A regex literal can carry a brace -- /[{]/ is one character, not a block.
    // `//` and `/*` are tested above, so an empty regex still reads as a
    // comment, which is what JavaScript itself does.
    if (c === '/' && REGEX_OK.test(prev || '^')) {
      i++;
      let inClass = false;
      while (i < n) {
        const r = src[i];
        if (r === '\\') { i += 2; continue; }
        if (r === '[') inClass = true;
        else if (r === ']') inClass = false;
        if (r === '\n') break;            // unterminated: do not run away
        i++;
        if (r === '/' && !inClass) break;
      }
      prev = '/';
      continue;
    }
    if (c === '{') depth++;
    else if (c === '}') {
      depth--;
      if (depth === 0) return i + 1;
    }
    if (!/\s/.test(c)) prev = c;
    i++;
  }
  return -1;
}

// fnSpan(src, signature) -> { start, end, body }
//
// `signature` is matched as a LITERAL SUBSTRING and must occur exactly once.
// Pass enough of the declaration to be unique -- `'function st(key,data){'`,
// not `'function st('`. The uniqueness requirement is the anchor discipline
// this repo already applies to its checkers: an anchor that matches twice is
// an anchor pointing at whichever one happens to come first.
function fnSpan(src, signature) {
  let count = 0;
  for (let at = src.indexOf(signature); at !== -1; at = src.indexOf(signature, at + 1)) count++;
  if (count === 0) {
    throw new Error('fnSpan: signature not found: ' + JSON.stringify(signature)
      + ' -- the function was renamed or its declaration was reformatted. '
      + 'This is a REFUSAL, not a span.');
  }
  if (count > 1) {
    throw new Error('fnSpan: signature occurs ' + count + ' times: '
      + JSON.stringify(signature) + ' -- pass more of the declaration. An '
      + 'anchor that matches twice points at whichever comes first.');
  }
  const start = src.indexOf(signature);
  const open = src.indexOf('{', start);
  if (open === -1) {
    throw new Error('fnSpan: no opening brace after ' + JSON.stringify(signature));
  }
  const end = balancedEnd(src, open);
  if (end === -1) {
    throw new Error('fnSpan: braces never balance from offset ' + open + ' for '
      + JSON.stringify(signature) + ' -- refusing to return a span rather than '
      + 'falling back to a bound with no basis.');
  }
  return { start, end, body: src.slice(start, end) };
}

// The body alone, for the common case.
function fnBody(src, signature) {
  return fnSpan(src, signature).body;
}

module.exports = { fnSpan, fnBody, balancedEnd };
