// tests/lib/strip_comments.test.js
//
//     node tests/lib/strip_comments.test.js
//
// THE CONTROL FOR tests/lib/strip_comments.js, WHICH HAD NONE. Exit 0 / 1.
//
// ── WHY THIS FILE EXISTS, AND WHY ITS ABSENCE WAS THE REAL DEFECT ──────────
// The library was created because three suites each grew their own comment
// stripper in one day and all three were wrong in DIFFERENT ways. It was then
// depended on by five suites and had no test of its own -- so the shared
// implementation had become a single point of failure with less coverage than
// the three copies it replaced. A shared helper with no control is not a fix, it
// is the same bug with a smaller blast radius on the day it lands and a larger
// one every day after.
//
// ── EVERY ONE OF THE THREE HISTORICAL BUGS IS A FIXTURE, IN BOTH DIRECTIONS ─
// Each of the three is pinned by a pair: the input that broke the old version,
// and an input the old version handled that must KEEP working. A fixture set
// that only proves the bug is gone cannot tell a fix from an over-correction,
// and two of the three original bugs WERE over-corrections.
//
//   1. THE LINE FILTER kept every continuation line of a multi-line
//      `<!-- ... -->` block. Fixtures H2/H3.
//   2. THE GREEDY REGEX `/\/\*[\s\S]*?\*\//` matched across an unintended span
//      and ate a real statement. Fixtures J3/J4.
//   3. THE NAIVE STATE MACHINE treated `/*` as a block start ANYWHERE, so
//      `accept="image/*"` opened a comment that swallowed thousands of lines.
//      Fixtures S1/S2 -- and S1 is the one that matters most, because the same
//      bug in the other direction would swallow the code an arm is trying to
//      find absent and PASS.
//
// ── AND THE FAIL-OPEN THE NEW stripJs() EXISTS TO CLOSE ────────────────────
// Section B drives the shape that made this sweep unsafe without it: handing a
// bare JavaScript FRAGMENT to stripComments() strips nothing at all, because
// outside `<script>` the `/*` rule does not apply. B1 asserts that is still
// true -- it is correct behaviour for the whole-file entry point -- and B2
// asserts stripJs() does strip it. An arm that only tested stripJs would not
// record why the trap exists.
'use strict';
const assert = require('assert');
const path = require('path');
const { stripComments, stripJs } = require(path.join(__dirname, 'strip_comments.js'));

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); console.log('  ok   ' + name); pass++; }
  catch (e) { console.log('  FAIL ' + name + '\n       ' + e.message); fail++; }
}
function section(t) { console.log('\n' + t); }

const wrap = (js) => '<html><body>\n<script>\n' + js + '\n</script>\n</body></html>';
// Lines, so an assertion can say WHICH line changed rather than diffing blobs.
const lines = (s) => s.split('\n');

console.log('tests/lib/strip_comments.js -- its first control');

// ── H. HTML COMMENTS, THE LINE-FILTER BUG ───────────────────────────────────
section('H. an HTML comment, including every continuation line (bug 1)');

test('H1. a single-line HTML comment goes, and the markup around it stays',
  () => {
    const out = stripComments('<p>keep</p><!-- drop --><p>also keep</p>');
    assert.ok(/keep/.test(out) && /also keep/.test(out), out);
    assert.ok(!/drop/.test(out), out);
  });

test('H2. THE BUG: a MULTI-LINE HTML comment goes ENTIRELY -- a line filter kept '
  + 'every line after the first, which is exactly where removed strings are quoted',
  () => {
    const out = stripComments(
      '<p>before</p>\n<!-- this used to say\n     sdOldFunction()\n     and that is gone -->\n<p>after</p>');
    assert.ok(!/sdOldFunction/.test(out),
      'the continuation line survived, so an arm asserting sdOldFunction is '
      + 'ABSENT would be satisfied by the comment saying it was removed: ' + out);
    assert.ok(/before/.test(out) && /after/.test(out), out);
  });

test('H3. ...and the LINE COUNT is unchanged, so a caller can still report a '
  + 'position that means something',
  () => {
    const src = '<p>a</p>\n<!-- one\ntwo\nthree -->\n<p>b</p>';
    assert.strictEqual(lines(stripComments(src)).length, lines(src).length);
  });

test('H4. an UNTERMINATED HTML comment eats the rest, which is what a browser '
  + 'does too -- so a suite cannot get a verdict the browser would not',
  () => {
    const out = stripComments('<p>a</p>\n<!-- never closed\n<p>b</p>');
    assert.ok(!/<p>b<\/p>/.test(out), out);
  });

// ── J. BLOCK COMMENTS, THE GREEDY-REGEX BUG ─────────────────────────────────
section('J. /* */ inside a script, without eating a real statement (bug 2)');

test('J1. a block comment inside <script> goes',
  () => {
    const out = stripComments(wrap('var a=1; /* gone */ var b=2;'));
    assert.ok(/var a=1/.test(out) && /var b=2/.test(out), out);
    assert.ok(!/gone/.test(out), out);
  });

test('J2. a `//` comment goes to end of line and NOT beyond',
  () => {
    const out = stripComments(wrap('var a=1; // gone\nvar b=2;'));
    assert.ok(!/gone/.test(out) && /var b=2/.test(out), out);
  });

test('J3. THE BUG: TWO separate block comments with a real statement between '
  + 'them -- the greedy regex spanned both and ate the statement, taking a count '
  + 'from two to ZERO',
  () => {
    const out = stripComments(wrap('/* one */ keepThisCall(); /* two */'));
    assert.ok(/keepThisCall\(\)/.test(out),
      'the statement between two block comments was eaten: ' + out);
    assert.ok(!/one/.test(out) && !/two/.test(out), out);
  });

test('J4. ...and the same across LINES, which is the shape the real file had',
  () => {
    const out = stripComments(wrap('/* a\n   b */\nkeepThisCall();\n/* c\n   d */'));
    assert.ok(/keepThisCall\(\)/.test(out), out);
    assert.ok(!/\ba\b/.test(out.replace(/keepThisCall/g, '')), out);
  });

// ── S. STRING LITERALS, THE NAIVE-STATE-MACHINE BUG ─────────────────────────
section('S. `/*` and `//` inside a STRING are literal (bug 3, the worst one)');

test('S1. THE WORST BUG: accept="image/*" must NOT open a comment. In the other '
  + 'direction this swallows the code an arm is looking for and PASSES',
  () => {
    const out = stripComments(
      '<input accept="image/*">\n<script>\nvar found = 1;\n</script>\n<div id="cg-employee"></div>');
    assert.ok(/id="cg-employee"/.test(out),
      'everything after accept="image/*" was swallowed, which is how arm E1 of '
      + 'sairnsenior_cert_gate failed against CORRECT markup: ' + out);
    assert.ok(/var found = 1/.test(out), out);
  });

test('S2. ...and `//` inside a URL string is not a comment either',
  () => {
    const out = stripComments(wrap("var u='https://example.test/x'; var after=1;"));
    assert.ok(/https:\/\/example\.test\/x/.test(out), out);
    assert.ok(/var after=1/.test(out), out);
  });

test('S3. `/*` inside a SINGLE-quoted and a BACKTICK string is literal too -- '
  + 'three quote characters, not one',
  () => {
    const out = stripComments(wrap("var a='x/*y'; var b=`p/*q`; var c=3;"));
    assert.ok(/x\/\*y/.test(out) && /p\/\*q/.test(out) && /var c=3/.test(out), out);
  });

test('S4. an ESCAPED quote does not end the string, so the `//` after it stays '
  + 'literal',
  () => {
    const out = stripComments(wrap("var a='it\\'s // not a comment'; var b=2;"));
    assert.ok(/not a comment/.test(out), out);
    assert.ok(/var b=2/.test(out), out);
  });

test('S5. OUTSIDE a script `/*` is NOT a comment start at all -- a CSS rule in '
  + '<style> survives, which the header states as deliberate',
  () => {
    const out = stripComments('<style>\n/* css comment */\n.x{color:red}\n</style>');
    assert.ok(/css comment/.test(out),
      'CSS comments are deliberately NOT removed; if this arm goes red somebody '
      + 'changed that rule and it is a new rule, not a tweak: ' + out);
  });

// ── B. THE BARE-FRAGMENT TRAP, and stripJs ──────────────────────────────────
section('B. a bare JS fragment: the fail-open, and the entry point that closes it');

const FRAG = 'var a=1; // dropMe\n/* alsoDropMe */\nvar b=2;';

test('B1. stripComments() on a BARE FRAGMENT strips NOTHING, and that is correct '
  + 'for the whole-file entry point -- outside <script> the /* rule does not apply',
  () => {
    const out = stripComments(FRAG);
    assert.ok(/dropMe/.test(out) && /alsoDropMe/.test(out),
      'if this arm goes red, stripComments has started treating bare input as '
      + 'JavaScript -- which would make B2 redundant and would change what every '
      + 'whole-file caller gets for text outside <script>: ' + out);
  });

test('B2. stripJs() on the same fragment DOES strip both -- this is the only '
  + 'reason a fragment call site can use the shared library at all',
  () => {
    const out = stripJs(FRAG);
    assert.ok(!/dropMe/.test(out), out);
    assert.ok(!/alsoDropMe/.test(out), out);
    assert.ok(/var a=1/.test(out) && /var b=2/.test(out), out);
  });

test('B3. stripJs() keeps string content literal, so a fragment containing a URL '
  + 'or image/* is not damaged',
  () => {
    const out = stripJs("var u='https://x.test/a'; var p='image/*'; var z=1;");
    assert.ok(/https:\/\/x\.test\/a/.test(out) && /image\/\*/.test(out)
              && /var z=1/.test(out), out);
  });

test('B4. stripJs() preserves the line count, same as the whole-file path',
  () => {
    assert.strictEqual(lines(stripJs(FRAG)).length, lines(FRAG).length);
  });

// ── A. THE FIVE ADVERSARIAL ATTACKS, BORROWED FROM A REVIEWER ──────────────
// tests/sairnvet_scribe_review_probe.js section A2 exists to ATTACK a comment
// stripper: it extracts api/sairnvet-transcribe.test.js's own character scanner
// and asks whether real code can be HIDDEN behind each of five shapes. Its
// history is the reason to borrow the fixtures rather than invent new ones: the
// arm originally attacked a REGEX-based stripper, the two attacks DEFEATED it,
// and the suite was rewritten with a character scanner in response.
//
// THE SHARED LIBRARY HAD NEVER FACED THEM. Two suites still carry their own
// character scanner precisely because a reviewer is pointed at it by name, so
// those two are deliberately NOT migrated -- and the attacks that justify them
// belong here, against the implementation everything else now depends on.
//
// THE QUESTION IS ALWAYS THE SAME: after stripping, is `SpeechRecognition`
// still visible? A stripper that hides real code makes an absence arm PASS on
// code that is present, which is the failing direction.
section('A. five adversarial attacks, borrowed from the scribe reviewer');

const ATTACKS = [
  ['a // inside a STRING literal',
   "var x = 'a//b'; var SR = window.SpeechRecognition;"],
  ['a // inside a REGEX literal',
   'var re = /\\/\\//; var SR = window.SpeechRecognition;'],
  ['a // inside a TEMPLATE literal',
   'var t = `a//b`; var SR = window.SpeechRecognition;'],
  ['a */ inside a string, before real code',
   "var s = '*/'; /* c */ var SR = window.SpeechRecognition;"],
  ['a division that is not a regex',
   'var r = a / b; var SR = window.SpeechRecognition;'],
];

ATTACKS.forEach(([label, src], n) => {
  test('A' + (n + 1) + '. stripJs survives ' + label,
    () => {
      const out = stripJs(src);
      assert.ok(/SpeechRecognition/.test(out),
        'REAL CODE WAS HIDDEN by the stripper, which makes an absence arm pass '
        + 'on code that is present.\n       in:  ' + src
        + '\n       out: ' + out.trim());
    });
});

test('A6. ...and the same five through the WHOLE-FILE entry point, because a '
  + 'fragment and a <script> block must not answer differently',
  () => {
    ATTACKS.forEach(([label, src]) => {
      const out = stripComments(wrap(src));
      assert.ok(/SpeechRecognition/.test(out),
        'hidden in whole-file mode but not fragment mode: ' + label
        + '\n       out: ' + out.trim());
    });
  });

// ── X. THE LIMITS, ASSERTED SO THEY ARE KNOWN RATHER THAN DISCOVERED ────────
section('X. the documented limits, pinned as limits');

test('X1. OFFSETS ARE NOT PRESERVED -- the output is SHORTER. A caller locating '
  + 'in raw text and slicing stripped text would read the wrong bytes, so this '
  + 'is asserted rather than assumed',
  () => {
    const src = wrap('var a=1; /* a long comment here */ var b=2;');
    assert.ok(stripComments(src).length < src.length,
      'if lengths are now equal, offsets may be preserved -- which would be an '
      + 'improvement, and the header paragraph forbidding raw-locate-then-slice '
      + 'must be rewritten rather than left stale');
  });

test('X2. empty input and input with no comments come back unchanged -- a '
  + 'stripper that alters clean code is worse than one that misses a comment',
  () => {
    assert.strictEqual(stripComments(''), '');
    assert.strictEqual(stripJs(''), '');
    const clean = wrap('var a=1;\nvar b=2;');
    assert.strictEqual(stripComments(clean), clean);
  });

// X3/X4 REPLACED A FIXTURE WHOSE EXPECTATION WAS WRONG, and the correction is
// recorded because it found the library is BETTER than its own header claimed.
// The first version asserted that a `</script>` inside a STRING ends script
// context. It does not: the boundary check is guarded by `if (!quote)`, so a
// quoted `</script>` is correctly ignored, and the comment after it was stripped
// as JavaScript exactly as it should be. The expectation was corrected -- not the
// library, and not the fixture bent to match output: X3 now pins the real
// strength, and X4 pins the real limit, which only stripJs() has.
test('X3. a `</script>` inside a STRING does NOT end script context -- the '
  + 'boundary check is guarded on quote state, so the comment after it is still '
  + 'stripped. This is a STRENGTH and is pinned so a future refactor cannot lose '
  + 'it quietly',
  () => {
    const out = stripComments(wrap("var s='</script>'; // this must go\nvar z=1;"));
    assert.ok(!/this must go/.test(out),
      'a quoted </script> ended script context, so a real JS comment after it '
      + 'survived: ' + out);
    assert.ok(/var z=1/.test(out), out);
  });

test('X4. THE REAL LIMIT, and it is stripJs()-only: an UNQUOTED `</script>` in a '
  + 'bare fragment ends script context, and nothing after it is stripped',
  () => {
    const out = stripJs("var a=1; // goes\n</script>\nvar b=2; // survives\n");
    assert.ok(!/goes/.test(out), 'the first comment should still be stripped: ' + out);
    assert.ok(/survives/.test(out),
      'the limit is CLOSED. GOOD -- but the paragraph in strip_comments.js naming '
      + 'it is now stale and must be rewritten rather than left: ' + out);
  });

console.log('\n' + (fail ? 'FAIL' : 'ALL') + ' -- ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
