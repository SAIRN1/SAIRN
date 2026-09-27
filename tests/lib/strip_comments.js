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
//   * It is not a JS parser. A `/` that begins a REGEX literal containing a
//     quote -- `/["']/` -- flips the string state and can desynchronise the rest
//     of a script block. No SAIRN app has tripped this and a suite that goes
//     inexplicably red should suspect it first.
//   * Template-literal `${ ... }` interpolation is treated as ordinary string
//     content, so a comment inside an interpolation is not removed.
//   * It does not remove CSS comments inside `<style>`, deliberately: those are
//     outside `<script>`, so the `/*` rule does not apply there and a CSS comment
//     survives. No arm has needed them gone; if one does, that is a new rule and
//     not a tweak to this one.
'use strict';

function stripComments(html) {
  const out = [];
  let i = 0;
  let inScript = false;     // between <script...> and </script>
  let htmlC = false;        // inside <!-- -->
  let blockC = false;       // inside /* */  (script only)
  let quote = null;         // ' " or ` while inside a string literal (script only)

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
        if (ch === quote) quote = null;
        keep(ch); i++; continue;
      }
      if (ch === '"' || ch === "'" || ch === '`') { quote = ch; keep(ch); i++; continue; }
      if (html.startsWith('//', i)) {
        const nl = html.indexOf('\n', i);
        i = nl === -1 ? html.length : nl;   // the \n itself is kept next pass
        continue;
      }
      if (html.startsWith('/*', i)) { blockC = true; i += 2; continue; }
      keep(ch); i++; continue;
    }

    // Outside a script: HTML comments only.
    if (html.startsWith('<!--', i)) { htmlC = true; i += 4; continue; }
    keep(ch); i++;
  }
  return out.join('');
}

module.exports = { stripComments };
