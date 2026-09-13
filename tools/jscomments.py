#!/usr/bin/env python
r"""jscomments.py -- the ONE comment stripper every SAIRN scanner should use.

WHY THIS EXISTS. On 2026-09-04 `tools/` held SEVEN separate `strip_comments`
implementations, and measured against real app files three of them were
destroying most of the input:

    sairnvet.html (362 function declarations)
      sairn_dead_button_audit     94.6% survives    0 declarations lost
      sairn_dead_function_sweep   95.0% survives    0 declarations lost
      discarded_verdict_check     11.1% survives  350 declarations lost
      sairn_seam_check            10.0% survives  350 declarations lost
      sairn_stale_snapshot_scan   11.1% survives  350 declarations lost

    sairncare.html: the same three lost 200 of 212.
    stonedesk.html: the same three lost 405 of 1003.

A scanner reading 10% of a file and reporting CLEAN is not a weak check, it is
a false one -- and its clean result is evidence for the wrong conclusion, which
is the most expensive shape this platform keeps finding.

THE CAUSE IS ALREADY DOCUMENTED, IN ONE TOOL, AND WAS NEVER PROPAGATED.
`sairn_dead_function_sweep.py`'s own docstring records it:

    <input type="file" accept="image/*" capture="environment" ...>

The `/*` in that MIME wildcard opens a block comment. A naive `/\*.*?\*/` runs
forward to the first `*/` -- which lived inside a regex literal in a later
script -- and blanked 80.5% of sairncare.html. It was fixed there, in isolation,
and the three tools with the same regex were never checked. Same shape as the
orphaned NPS module whose damage twin nobody looked for.

WHAT THIS IMPLEMENTATION DOES. It is the state machine from
`sairn_dead_button_audit.py`, which measured best of the seven and was itself
written after that tool reported 58 phantom dead buttons. It walks the source
once and skips over strings, template literals and regex literals, so a `/*`,
a `//` or a `-->` inside any of them is left alone. Comments are blanked to
spaces rather than deleted, so byte offsets and line numbers stay usable and no
two identifiers are ever glued together.

Usage:
    from jscomments import strip_comments, mask_scripts
    code = strip_comments(html)          # comments gone, offsets intact

    python tools/jscomments.py --probe   # run the differential probe
    python tools/jscomments.py FILE      # report how much of FILE survives
"""
import re
import sys

# Characters after which a `/` starts a REGEX rather than a division. Anything
# else (an identifier, a digit, a closing paren) means divide.
_REGEX_OK = set('(,=:[!&|?{};+-*%~^') | {''}


def strip_comments(src):
    r"""Blank //, /* */ and <!-- --> comments, preserving length and newlines.

    Never strips inside a string, a template literal or a regex literal. That
    is the whole point: `accept="image/*"`, a URL containing `//`, and a regex
    like /a\/\/b/ must all survive untouched.
    """
    out = list(src)
    i, n = 0, len(src)
    prev = ''

    def kill(a, b):
        for k in range(a, b):
            if out[k] != '\n':
                out[k] = ' '

    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        if src.startswith('<!--', i):
            j = src.find('-->', i)
            j = n if j == -1 else j + 3
            kill(i, j); i = j; continue
        if c == '/' and nxt == '*':
            j = src.find('*/', i + 2)
            j = n if j == -1 else j + 2
            kill(i, j); i = j; continue
        if c == '/' and nxt == '/':
            j = src.find('\n', i)
            j = n if j == -1 else j
            kill(i, j); i = j; continue
        if c in '"\'`':
            q = c; j = i + 1
            while j < n:
                if src[j] == '\\':
                    j += 2; continue
                if src[j] == q:
                    j += 1; break
                if q != '`' and src[j] == '\n':
                    break
                j += 1
            i = j; prev = q; continue
        if c == '/' and prev in _REGEX_OK:
            j = i + 1; ok = False
            while j < n and src[j] != '\n':
                if src[j] == '\\':
                    j += 2; continue
                if src[j] == '[':
                    while j < n and src[j] not in ']\n':
                        j += 2 if src[j] == '\\' else 1
                if src[j] == '/':
                    ok = True; j += 1; break
                j += 1
            if ok:
                i = j; prev = '/'; continue
        if not c.isspace():
            prev = c
        i += 1
    return ''.join(out)


def blank_string_bodies(src):
    r"""Blank the CONTENTS of every string and template literal, keeping quotes.

    WHAT IT IS FOR. A scanner looking for evidence in CODE must not find it in
    PROSE, and in JavaScript the prose lives inside string literals -- a test
    NAME, an assertion message, a path constant. `strip_comments` deliberately
    leaves those alone because it is answering a different question.

        test('a verdict that IS read is not reported', ...)

    reads, to any regex, exactly like an assertion about a verdict not being
    reported. It is a label. On 2026-09-13 `tools/checker_control_check.py` was
    found crediting nine such lines as proof that a checker can fire, including
    the line that DECLARES which checker the file controls.

    Quotes and backticks are kept so the literal is still visibly a literal and
    every byte offset and line number stays true -- the same contract
    `strip_comments` holds. Interpolations inside a template literal are blanked
    with the rest: `${x}` is code, but a scanner that wanted it should be
    reading the AST, not this.

    THIS DUPLICATES THE WALK IN strip_comments RATHER THAN REFACTORING IT.
    Deliberate: that function is imported by tools across this repo and its
    behaviour is pinned by the probe below. Adding a second entry point cannot
    change what the first one returns; extracting a shared scanner could, and a
    stripper that quietly starts destroying input is the exact failure this
    whole file exists to have ended.
    """
    out = list(src)
    i, n = 0, len(src)
    prev = ''

    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        # Comments are skipped, not blanked -- this function's contract is
        # strings only. Callers that want both run strip_comments first.
        if src.startswith('<!--', i):
            j = src.find('-->', i)
            i = n if j == -1 else j + 3
            continue
        if c == '/' and nxt == '*':
            j = src.find('*/', i + 2)
            i = n if j == -1 else j + 2
            continue
        if c == '/' and nxt == '/':
            j = src.find('\n', i)
            i = n if j == -1 else j
            continue
        if c in '"\'`':
            q = c
            j = i + 1
            end = None                      # index of the CLOSING delimiter
            while j < n:
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == q:
                    end = j
                    j += 1
                    break
                if q != '`' and src[j] == '\n':
                    break
                j += 1
            # Blank strictly BETWEEN the delimiters, by index. An earlier
            # version skipped any char equal to the quote, which left the
            # BACKSLASH-ESCAPED quote in `'it\'s'` standing and turned one
            # string into a closed string followed by garbage code. Escaped
            # delimiters are interior bytes like any other.
            stop = end if end is not None else min(j, n)
            for k in range(i + 1, stop):
                if out[k] != '\n':
                    out[k] = ' '
            i = j
            prev = q
            continue
        if c == '/' and prev in _REGEX_OK:
            j = i + 1
            ok = False
            while j < n and src[j] != '\n':
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == '[':
                    while j < n and src[j] not in ']\n':
                        j += 2 if src[j] == '\\' else 1
                if src[j] == '/':
                    ok = True
                    j += 1
                    break
                j += 1
            if ok:
                i = j
                prev = '/'
                continue
        if not c.isspace():
            prev = c
        i += 1
    return ''.join(out)


def mask_scripts(src):
    """Blank <script> bodies so an HTML-side scan does not see JS."""
    out = list(src)
    for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', src, re.S | re.I):
        for i in range(m.start(1), m.end(1)):
            if out[i] != '\n':
                out[i] = ' '
    return ''.join(out)


# ── PROBE ─────────────────────────────────────────────────────────────────
# A stripper nobody has watched destroy a file is a stripper whose behaviour
# nobody knows. These are the cases that separated the seven implementations.
_CASES = [
    ('a line comment goes',
     "var a=1; // remRender() was deleted\nvar b=2;",
     lambda o: 'remRender' not in o and 'var a=1;' in o and 'var b=2;' in o),
    ('a block comment goes',
     "/* calls sendMessage() */\nvar c=3;",
     lambda o: 'sendMessage' not in o and 'var c=3;' in o),
    ('an HTML comment goes',
     "<!-- Was: Live tracking -->\n<p>real</p>",
     lambda o: 'Live tracking' not in o and '<p>real</p>' in o),
    ('// inside a string STAYS',
     "var s='// not a comment'; var t=1;",
     lambda o: "'// not a comment'" in o and 'var t=1;' in o),
    ('/* inside a string STAYS',
     "var s='/* nope */'; var v=4;",
     lambda o: "'/* nope */'" in o and 'var v=4;' in o),
    ('a template literal is untouched',
     "var t=`a // b ${x} /* c */`; var w=5;",
     lambda o: '${x}' in o and 'var w=5;' in o),
    ('a regex containing // survives',
     "var r=/a[/]b/; var q=2;",
     lambda o: 'var q=2;' in o),
    # The one that cost 80.5% of sairncare.html.
    ('accept="image/*" does not open a comment',
     '<input accept="image/*" capture="environment">\n'
     '<script>\nfunction realFn(){}\n</script>',
     lambda o: 'realFn' in o),
    ('a URL with // survives',
     "var u='https://x.y/z'; var n=1;",
     lambda o: 'https://x.y/z' in o and 'var n=1;' in o),
    ('length and newlines are preserved',
     "a\n// x\nb\n",
     lambda o: len(o) == len("a\n// x\nb\n") and o.count('\n') == 3),
]

# blank_string_bodies() is the OPPOSITE question and needs its own cases: the
# prose lives inside the literals, and the code around them must survive.
_STRING_CASES = [
    ('a test NAME is blanked, the call around it is not',
     "test('a verdict that IS read is not reported', fn);",
     lambda o: 'not reported' not in o and 'test(' in o and ', fn);' in o),
    ('an assertion MESSAGE goes, the compared values stay',
     "assert.strictEqual(r.code, 1, 'a finding must exit non-zero');",
     lambda o: 'must exit' not in o and 'r.code, 1,' in o),
    ('a path constant naming a tool is blanked',
     "const T = path.join(ROOT, 'tools', 'fail_open_check.py');",
     lambda o: 'fail_open_check' not in o and 'path.join(ROOT,' in o),
    ('the declaration line itself is blanked',
     "const CONTROLS_FOR = ['discarded_verdict_check.py'];",
     lambda o: 'discarded_verdict' not in o and 'CONTROLS_FOR = [' in o),
    # An earlier version skipped any interior char equal to the quote, which
    # left the ESCAPED quote standing and turned one string into a closed
    # string followed by garbage. `var u = 2;` must still be there afterwards.
    ("a BACKSLASH-ESCAPED quote does not end the string",
     r"var s = 'it\'s escaped'; var u = 2;",
     lambda o: 'escaped' not in o and 'var u = 2;' in o and o.count("'") == 2),
    ('an escaped double quote likewise',
     'var d = "say \\"hi\\""; var v = 3;',
     lambda o: 'hi' not in o and 'var v = 3;' in o and o.count('"') == 2),
    ('a template literal is blanked, interpolation included',
     "var t = `hi ${x} there`; var w = 5;",
     lambda o: '${x}' not in o and 'var w = 5;' in o),
    ('a regex literal is NOT a string and survives',
     "var r = /a[/]b/; var q = 2;",
     lambda o: '/a[/]b/' in o and 'var q = 2;' in o),
    ('an UNTERMINATED string stops at the newline',
     "var m = 'oops\nvar w = 4;",
     lambda o: 'var w = 4;' in o),
    ('a comment is skipped, not blanked -- strings only',
     "// remRender() was deleted\nvar b = 2;",
     lambda o: 'remRender' in o and 'var b = 2;' in o),
    ('length and newlines are preserved',
     "var s = 'a\\nb';\nvar t = 1;\n",
     lambda o: len(o) == len("var s = 'a\\nb';\nvar t = 1;\n")
     and o.count('\n') == 2),
]


def probe():
    bad = 0
    for name, src, ok in _CASES:
        out = strip_comments(src)
        good = ok(out)
        print('  %s %s' % ('ok  ' if good else 'FAIL', name))
        if not good:
            print('       got: %r' % out[:90])
            bad += 1
    print('')
    for name, src, ok in _STRING_CASES:
        out = blank_string_bodies(src)
        good = ok(out)
        print('  %s blank_string_bodies: %s' % ('ok  ' if good else 'FAIL', name))
        if not good:
            print('       got: %r' % out[:90])
            bad += 1
    print('\n%d case(s) failed' % bad)
    return 1 if bad else 0


def measure(path):
    """How much of a real file survives, and how many declarations are lost."""
    with open(path, encoding='utf-8', errors='replace') as f:
        src = f.read()
    out = strip_comments(src)
    fns = set(re.findall(r'function\s+([A-Za-z_$][\w$]*)\s*\(', src))
    gone = [x for x in fns if ('function ' + x) not in out]

    # A declaration that appears ONLY inside a comment is SUPPOSED to disappear.
    # stonedesk.html has one: saUnlock, quoted in a note explaining the code that
    # was removed. Reporting it as "lost" made this tool's own output wrong in
    # the same way the tools it replaces are -- so it is classified, not counted.
    lines = src.split('\n')
    def only_in_comments(name):
        hits = [l for l in lines if ('function ' + name) in l]
        return hits and all(l.lstrip().startswith(('//', '*', '<!--')) for l in hits)
    quoted = sorted(x for x in gone if only_in_comments(x))
    lost = sorted(x for x in gone if x not in quoted)

    print('%s: %.1f%% of non-space content survives, %d/%d function '
          'declarations LOST' %
          (path, 100.0 * len(out.replace(' ', '')) / max(1, len(src.replace(' ', ''))),
           len(lost), len(fns)))
    if quoted:
        print('  correctly removed (declared only inside a comment): ' + ', '.join(quoted[:12]))
    if lost:
        print('  LOST: ' + ', '.join(lost[:12]))
    return 1 if lost else 0


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] == '--probe':
        sys.exit(probe())
    sys.exit(max(measure(a) for a in args))
