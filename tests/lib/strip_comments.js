// tests/lib/strip_comments.js
//
// Remove comments from a single-file SAIRN app, so a suite asserting that a
// string is GONE cannot be satisfied by the comment that records removing it.
//
// ── WHY THIS IS A SHARED MODULE AND NOT THREE COPIES ──────────────────────
// Three suites needed this in one day and each grew its own version. The
// versions were wrong in three DIFFERENT ways, and every one of them produced a
// green run against a file that should have gone red, or red against one that
// should have been green:
//
//   1. A LINE FILTER -- drop lines starting `//` or `<!--`. Kept every
//      CONTINUATION line of a multi-line `<!-- ... -->` block, which is exactly
//      where the removed strings are quoted. Six of fourteen arms failed on prose
//      in tests/sairnbiz_benefits_and_overtime.js.
//   2. A REGEX -- `/\/\*[\s\S]*?\*\//`. Recorded in
//      tests/stonedesk_field_quote_wiring.js as deleted for matching across an
//      unintended span and eating a real statement, taking a count from two to
//      ZERO. A false PASS in the other direction.
//   3. A NAIVE STATE MACHINE that treated `/*` as a block-comment start
//      ANYWHERE. `accept="image/*"` at sairnsenior.html:336 opened a comment that
//      never closed until the next `*/` thousands of lines later, so
//      `id="cg-employee"` at :565 was invisible and arm E1 failed against correct
//      markup. THIS IS THE ONE THAT MATTERS MOST: the same bug in the other
//      direction would swallow the code an arm is trying to find absent, and pass.
//
// ── THE RULE, WHICH IS THE FIX FOR ALL THREE ──────────────────────────────
// Comment syntax is CONTEXT-DEPENDENT, so the context is tracked:
//   * outside `<script>`: only `<!-- ... -->` is a comment. `/*` is not.
//   * inside  `<script>`: only `//` to end-of-line and `/* ... */` are comments,
//     and neither counts inside a string literal.
// Newlines are preserved wherever a comment is removed, so a caller can still
// slice by line and report a position that means something.
//
// ── WHAT IT STILL CANNOT DO, stated rather than discovered later ───────────
//   * It is not a JS parser. REGEX LITERALS ARE HANDLED AS OF 2026-09-27 --
//     including one containing a quote (`/["']/`) and one containing `//`, which
//     used to be read as a line comment and HID THE REST OF THE LINE. That was a
//     real failing finding, in the direction that makes an absence assertion pass
//     on code that is present, and it was found by borrowing the five attacks in
//     tests/sairnvet_scribe_review_probe.js section A2 into this library's own
//     control (arms A1-A6). Whether a `/` starts a regex is decided from the
//     previous significant character, which is a heuristic and not a grammar:
//     anything it does not recognise stays DIVISION, so it can only ever
//     under-strip. Under-stripping leaves a comment in; over-stripping hides code.
//   * Template-literal `${ ... }` interpolation is treated as ordinary string
//     content, so a comment inside an interpolation is not removed.
//   * It does not remove CSS comments inside `<style>`, deliberately: those are
//     outside `<script>`, so the `/*` rule does not apply there and a CSS comment
//     survives. No arm has needed them gone; if one does, that is a new rule and
//     not a tweak to this one.
'use strict';

// A `/` starts a REGEX LITERAL only when the previous significant character
// cannot end an expression. `^` stands for start-of-input. Deliberately a small
// closed set rather than a JS grammar: everything it does not match is treated as
// DIVISION, which keeps the character and can only ever under-strip. Over-
// stripping is the direction that hides real code.
const REGEX_OK = /[(,=:[!&|?{};^]|\^/;

function stripComments(html, opts) {
  const out = [];
  let i = 0;
  // `bareJs` starts the machine INSIDE script context. See stripJs() below for
  // why that option exists and why it is not the default.
  let inScript = !!(opts && opts.bareJs);   // between <script...> and </script>
  let htmlC = false;        // inside <!-- -->
  let blockC = false;       // inside /* */  (script only)
  let quote = null;         // ' " or ` while inside a string literal (script only)
  // Last emitted NON-WHITESPACE character inside a script. It is the only way to
  // tell `a / b` (division) from `/re/` (a regex literal), and without that
  // distinction a regex containing `//` is read as a line comment. See REGEX_OK.
  let prev = '';

  const keep = (ch) => out.push(ch);
  const keepNewlines = (ch) => { if (ch === '\n') out.push('\n'); };

  while (i < html.length) {
    const ch = html[i];

    // ── comment terminators first, so a region always gets a chance to close
    if (htmlC) {
      if (html.startsWith('-->', i)) { htmlC = false; i += 3; continue; }
      keepNewlines(ch); i++; continue;
    }
    if (blockC) {
      if (html.startsWith('*/', i)) { blockC = false; i += 2; continue; }
      keepNewlines(ch); i++; continue;
    }

    // ── script boundaries. Checked before comment starts so a </script> inside
    // a string cannot be missed in the common case, and so `/*` stops being a
    // comment the moment the block ends.
    if (!quote) {
      if (!inScript && /^<script\b/i.test(html.slice(i, i + 8))) {
        const gt = html.indexOf('>', i);
        const end = gt === -1 ? html.length : gt + 1;
        for (let k = i; k < end; k++) keep(html[k]);
        i = end; inScript = true; continue;
      }
      if (inScript && /^<\/script\s*>/i.test(html.slice(i, i + 10))) {
        const end = html.indexOf('>', i) + 1;
        for (let k = i; k < end; k++) keep(html[k]);
        i = end; inScript = false; continue;
      }
    }

    if (inScript) {
      // String state, so `//` in 'https://' and `/*` in "image/*" are literal.
      if (quote) {
        if (ch === '\\') { keep(ch); if (i + 1 < html.length) keep(html[i + 1]); i += 2; continue; }
        if (ch === quote) { quote = null; prev = ch; }
        keep(ch); i++; continue;
      }
      if (ch === '"' || ch === "'" || ch === '`') { quote = ch; prev = ch; keep(ch); i++; continue; }
      if (html.startsWith('//', i)) {
        const nl = html.indexOf('\n', i);
        i = nl === -1 ? html.length : nl;   // the \n itself is kept next pass
        continue;
      }
      if (html.startsWith('/*', i)) { blockC = true; i += 2; continue; }
      // ── REGEX LITERALS, ADDED 2026-09-27 AFTER A REAL FAILING FINDING ─────
      // `var re = /\/\//;` was being read as a LINE COMMENT, so everything after
      // it on that line vanished. That is the FAILING direction: real code
      // hidden, which makes an absence assertion pass on code that is present --
      // and five suites already depended on this library when it was found.
      //
      // FOUND BY BORROWING AN ATTACK, not by reading the code.
      // tests/sairnvet_scribe_review_probe.js section A2 exists to attack a
      // comment stripper with five shapes; those five are now arms A1-A6 of this
      // library's own control, and the regex one went red immediately. The
      // library had never faced them.
      //
      // THE HEURISTIC IS THE ONE THE PLATFORM ALREADY HAD RIGHT, in
      // api/sairnvet-transcribe.test.js: a `/` starts a regex only when the last
      // significant character cannot end an expression. After an identifier, a
      // number, `)` or `]` a `/` is division. This is not a full JS lexer and
      // does not need to be -- `//` and `/*` are checked BEFORE it, so an empty
      // regex `//` still reads as a comment, which is what JavaScript itself
      // does.
      //
      // An UNTERMINATED regex stops at the newline rather than running away,
      // because a runaway here deletes the rest of the file.
      if (ch === '/' && REGEX_OK.test(prev || '^')) {
        keep(ch); i++;
        let inClass = false;
        while (i < html.length) {
          const r = html[i];
          if (r === '\\') { keep(r); if (i + 1 < html.length) keep(html[i + 1]); i += 2; continue; }
          if (r === '[') inClass = true;
          else if (r === ']') inClass = false;
          if (r === '\n') break;            // unterminated: do not run away
          keep(r); i++;
          if (r === '/' && !inClass) break;
        }
        prev = '/'; continue;
      }
      keep(ch);
      if (!/\s/.test(ch)) prev = ch;
      i++; continue;
    }

    // Outside a script: HTML comments only.
    if (html.startsWith('<!--', i)) { htmlC = true; i += 4; continue; }
    keep(ch); i++;
  }
  return out.join('');
}

// ── stripJs: THE SAME MACHINE, FOR A FRAGMENT THAT IS ALREADY JAVASCRIPT ────
// ADDED 2026-09-27 during the sweep that migrated the ad-hoc copies, because the
// sweep could not be done safely without it, and the reason is a fail-open:
//
//   MOST CALL SITES DO NOT PASS A WHOLE FILE. They locate a function in the HTML
//   by index, slice it, and strip the slice. Handing that slice to
//   stripComments() means inScript is FALSE for the whole fragment -- so `//` and
//   `/* */` are NOT comments, NOTHING IS STRIPPED, and the call returns the input
//   unchanged. A suite asserting a string is absent from the code would then be
//   satisfied by the comment recording its removal, silently, with a call to the
//   shared library sitting right there looking correct.
//
//   That is a WORSE failure than any of the three ad-hoc versions this library
//   replaced, because it looks like the fix.
//
// SO THE FRAGMENT CASE GETS ITS OWN NAMED ENTRY POINT rather than an options bag
// somebody has to remember: `stripJs(src)` says what it takes.
//
// WHAT IT STILL CANNOT DO, stated rather than discovered later, and MEASURED by
// tests/lib/strip_comments.test.js rather than asserted here:
//   * an UNQUOTED `</script>` in the fragment ends script context, and nothing
//     after it is stripped (arm X4). A QUOTED one is handled correctly -- the
//     boundary check below is guarded on quote state -- and arm X3 pins that as a
//     strength so a refactor cannot lose it quietly. The first draft of this
//     paragraph had those two the wrong way round; the control corrected it.
//   * everything the whole-file path cannot do (regex literals containing a
//     quote, `${}` interpolation) it cannot do either -- it is the same machine.
//
// OFFSETS ARE NOT PRESERVED BY EITHER ENTRY POINT. Comment spans collapse to
// their newlines, so the output is SHORTER than the input and an index computed
// against the raw text does not point at the same place in the stripped text.
// A caller that needs both must strip first and locate in the stripped text --
// never locate in raw and slice out of stripped.
function stripJs(src) {
  return stripComments(src, { bareJs: true });
}

module.exports = { stripComments, stripJs };
