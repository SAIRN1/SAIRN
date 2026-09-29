#!/usr/bin/env python3
"""The comment stripper behind the cross-tenant coverage grade, both ways.

    python tests/run_cross_tenant_isolation_scope_probe.py

Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.

CONTROLS_FOR = tools/cross_tenant_isolation_scope.py

── WHAT THIS IS ABOUT ─────────────────────────────────────────────────────
`driven_resources()` is the shared grader every suite's cross-tenant coverage
number comes from. It reads resource names out of a table body, and it strips
JS comments first -- because a comment quoting `['read', 'write']` was being
credited as a driven resource named `read`, which is a FAIL-OPEN: the name
lands in `driven`, shrinks `declared - driven`, and the resource keeps GENUINE
on a claim no arm exercises.

THE STRIPPER WAS NOT STRING-AWARE, AND SAID SO. Its own docstring accepted the
over-strip -- "a genuine `//` inside a string literal (a URL) would drop the
rest of that line" -- on the grounds that under-counting `driven` is the
fail-closed direction. That reasoning is sound about SAFETY and wrong about
MEASUREMENT: a grader that silently discards half a line whenever a URL appears
is not reporting the coverage it claims to report, and the direction of its
error is not the same as its error being acceptable. `//` inside a string is
not a comment in any reading of JavaScript.

── AND THE TWO DERIVATIONS ARE NOW INDEPENDENT, ON PURPOSE ────────────────
The driven set is derived in TWO places: `driven_resources()` in the grader,
and the inline dispatcher arm in tests/run_cross_tenant_scope_probe.py. On
2026-09-26 those were two copies of one decision and ONLY ONE GOT A FIX, which
is how the phantom `read` survived in the grader after the probe was repaired.
The repair then unified them onto one function -- which removes the drift and
removes the cross-check with it.

A SECOND COPY IS NOT A SECOND OPINION; A DIFFERENT METHOD IS. So the two are
independent again, deliberately, and by DIFFERENT MECHANISMS:

  * the grader scans character by character, tracking quote state;
  * `independent_strip()` below alternates a regex over strings-or-comments and
    replaces only the comment alternatives -- the classic lexer-ordering trick.

Arm D requires them to agree across the whole scanned corpus. A divergence is a
finding about one of them, which is exactly what one shared function cannot
produce.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

CONTROLS_FOR = ['tools/cross_tenant_isolation_scope.py']

try:
    import cross_tenant_isolation_scope as S                   # noqa: E402
except Exception as exc:                                       # noqa: BLE001
    sys.stderr.write('COULD NOT RUN -- tools/cross_tenant_isolation_scope.py '
                     'would not import (%s: %s). Nothing was measured.\n'
                     % (type(exc).__name__, exc))
    raise SystemExit(2)

fails = []


def check(name, ok, detail=''):
    print('  %s %s' % ('ok  ' if ok else 'FAIL', name))
    if not ok:
        print('       ' + str(detail)[:400])
        fails.append(name)


# ── THE INDEPENDENT IMPLEMENTATION ─────────────────────────────────────────
# Different mechanism from the grader's, same contract: comments become \x00,
# strings are untouched. The alternation puts STRINGS FIRST, so a comment
# marker inside a string is consumed as part of the string and never seen as a
# comment -- which is how a lexer resolves the same ambiguity.
#
# `'` AND `"` BODIES EXCLUDE NEWLINES, and that is not cosmetic. A JS string
# literal cannot contain a raw newline, and allowing one here made an
# APOSTROPHE IN HTML PROSE -- "don't" in a paragraph -- open a string that ran
# to the next apostrophe many lines away, swallowing real table rows. Found by
# arm D disagreeing with the grader's scanner on stonedesk.html, in the
# direction that LOST names. The backtick alternative keeps `re.S` behaviour
# because a template literal may legitimately span lines.
_TOKEN = re.compile(
    r'''("(?:\\.|[^"\\\n])*")'''      # double-quoted, one line
    r"""|('(?:\\.|[^'\\\n])*')"""     # single-quoted, one line
    r'|(`(?:\\.|[^`\\])*`)'           # template, may span lines
    r'|(/\*.*?\*/)'                   # block comment
    r'|(//[^\n]*)',                   # line comment
    re.S)


def independent_strip(fragment):
    def repl(m):
        if m.group(4) or m.group(5):
            return '\x00'
        return m.group(0)
    return _TOKEN.sub(repl, fragment)


print('cross-tenant isolation scope -- the stripper, both ways')

# ── A. THE STRING-AWARE PROPERTY ───────────────────────────────────────────
URL_TABLE = (
    "const T = {\n"
    "  members: [\n"
    "    ['dnt_ar','ar_id'],\n"
    "    ['grd_jobs','job_id'],\n"
    "  ],\n"
    "};\n"
)
# The same table with a URL on the members line. `//` inside the string.
URL_TABLE_WITH_URL = (
    "const T = {\n"
    "  members: [\n"
    "    ['dnt_ar','ar_id'], ['grd_jobs','job_id'], // see https://x/y\n"
    "  ],\n"
    "};\n"
)
# The URL is in a STRING, and a real row follows it on the same line.
URL_IN_STRING = (
    "const T = {\n"
    "  doc: 'https://example.com/path',\n"
    "  members: [ ['sv_labresults','lab_id'] ],\n"
    "};\n"
)
STRING_THEN_ROW_SAME_LINE = (
    "const T = { doc: 'https://a/b', members: [ ['leg_plots','plot_id'] ] };\n"
)


def names(fn, frag):
    return set(S._ROW_NAME.findall(fn(frag)))


check('A1. a real comment naming a row is still stripped -- the fail-open this '
      'stripper exists for stays closed',
      names(S.strip_comments, URL_TABLE_WITH_URL) == {'dnt_ar', 'grd_jobs'},
      names(S.strip_comments, URL_TABLE_WITH_URL))

check('A2. THE ARM THIS FILE EXISTS FOR: a `//` inside a STRING is not a '
      'comment, and the row after it on the same line survives',
      names(S.strip_comments, STRING_THEN_ROW_SAME_LINE) == {'leg_plots'},
      'got %s -- the URL swallowed the rest of the line'
      % names(S.strip_comments, STRING_THEN_ROW_SAME_LINE))

check('A3. ...and a URL on its own line costs nothing either',
      names(S.strip_comments, URL_IN_STRING) == {'sv_labresults'},
      names(S.strip_comments, URL_IN_STRING))

check('A4. CONTROL: the plain table is unchanged by any of this',
      names(S.strip_comments, URL_TABLE) == {'dnt_ar', 'grd_jobs'},
      names(S.strip_comments, URL_TABLE))

# ── B. THE MARKER, WHICH IS THE OTHER HALF AND HAS ITS OWN HISTORY ─────────
# A comment replaced by '' lets `_ROW_NAME`'s `\s*` bridge the hole and read a
# flat array's first string as a row. That traded one fail-open for another.
FLAT_AFTER_COMMENT = (
    "const APPROVED = [\n"
    "  // 2026-09-21\n"
    "  'sf_accounts',\n"
    "];\n"
)
check('B1. a comment becomes a MARKER, not nothing -- a flat array after a '
      'comment must not read as a row',
      names(S.strip_comments, FLAT_AFTER_COMMENT) == set(),
      'got %s -- \\s* bridged the stripped comment'
      % names(S.strip_comments, FLAT_AFTER_COMMENT))

check('B2. ...and a comment BETWEEN `members: [` and a real pair costs nothing, '
      'because the pair carries its own bracket',
      names(S.strip_comments,
            "const T = { members: [\n  // note\n  ['rf_jobs','job_id'] ] };\n")
      == {'rf_jobs'})

check('B3. block comments too, not only `//`',
      names(S.strip_comments,
            "const T = { members: [ ['a_one','x'] /* ['phantom','y'] */ ] };\n")
      == {'a_one'})

# ── C. THE INDEPENDENT IMPLEMENTATION HOLDS THE SAME CONTRACT ──────────────
for label, frag, want in (
        ('a real comment', URL_TABLE_WITH_URL, {'dnt_ar', 'grd_jobs'}),
        ('a URL in a string', STRING_THEN_ROW_SAME_LINE, {'leg_plots'}),
        ('a flat array after a comment', FLAT_AFTER_COMMENT, set()),
        ('a block comment', "const T = { members: [ ['a_one','x'] "
                            "/* ['phantom','y'] */ ] };\n", {'a_one'})):
    check('C. independent_strip agrees on %s' % label,
          names(independent_strip, frag) == want,
          names(independent_strip, frag))

# ── D. THE TWO DERIVATIONS, CROSS-CHECKED OVER THE REAL CORPUS ─────────────
# This is the arm one shared function cannot produce. Both implementations run
# over every file the grader scans; any file where they disagree is a finding
# about one of them.
def corpus():
    out = []
    for root, _dirs, files in os.walk(REPO):
        if any(x in root for x in ('node_modules', '.git', '__pycache__')):
            continue
        for f in files:
            if f.endswith(('.js', '.html')):
                out.append(os.path.join(root, f))
    return out


paths = corpus()
diverged, scanned = [], 0
for p in paths:
    try:
        body = io.open(p, encoding='utf-8', errors='replace').read()
    except OSError:
        continue
    scanned += 1
    a = set(S._ROW_NAME.findall(S.strip_comments(body)))
    b = set(S._ROW_NAME.findall(independent_strip(body)))
    if a != b:
        diverged.append((os.path.relpath(p, REPO).replace(os.sep, '/'),
                         sorted(a - b), sorted(b - a)))

check('D1. the corpus is non-empty, or every arm below is vacuous',
      scanned > 200, 'scanned %d files' % scanned)
check('D2. THE CROSS-CHECK: two INDEPENDENT strippers, different mechanisms, '
      'agree on every one of %d files' % scanned,
      not diverged,
      'diverged on %d file(s): %s' % (len(diverged), diverged[:3]))

# ── E. KNOWN-BAD CONTROL, ONE PER IMPLEMENTATION ───────────────────────────
# Arms A-D would all pass against a stripper that did nothing at all if the
# fixtures happened not to discriminate. These put the defect back.


class _Bad(object):
    """The PRE-FIX stripper: regex-only, not string-aware."""
    RE = re.compile(r'/\*.*?\*/|//[^\n]*', re.S)

    @staticmethod
    def strip(fragment):
        return _Bad.RE.sub('\x00', fragment)


check('E1. KNOWN-BAD: the pre-fix regex-only stripper DOES swallow the row '
      'after a URL -- so A2 is reading the fix and not agreeing with a fixture '
      'that never discriminated',
      names(_Bad.strip, STRING_THEN_ROW_SAME_LINE) != {'leg_plots'},
      'the pre-fix stripper kept the row too; this fixture proves nothing')

# THIS FIXTURE WAS WRONG ON ITS FIRST RUN AND IS RECORDED RATHER THAN QUIETLY
# SWAPPED. It used URL_TABLE_WITH_URL, whose comment is `// see https://x/y` --
# which carries no `['name'` pattern, so a NO-OP stripper produced the same
# answer as the real one and the arm failed against correct code. A known-bad
# control whose fixture cannot express the defect is the shape this repo sweeps
# for; the comment now contains a row.
PHANTOM_IN_COMMENT = (
    "const T = { members: [\n"
    "  ['dnt_ar','ar_id'],   // superseded: ['phantom_row','x']\n"
    "] };\n"
)
check('E2. KNOWN-BAD: a stripper that does NOTHING credits the phantom row, so '
      'A1 is real',
      names(lambda f: f, PHANTOM_IN_COMMENT) != {'dnt_ar'},
      'a no-op stripper produced the same answer as the real one')
check('E2b. ...and the real stripper does NOT credit it',
      names(S.strip_comments, PHANTOM_IN_COMMENT) == {'dnt_ar'},
      names(S.strip_comments, PHANTOM_IN_COMMENT))


def _empty_marker(fragment):
    return _Bad.RE.sub('', fragment)


check('E3. KNOWN-BAD: replacing a comment with NOTHING reintroduces the flat-'
      'array read, so B1 is real',
      names(_empty_marker, FLAT_AFTER_COMMENT) == {'sf_accounts'},
      'the empty-replacement stripper did not reproduce the bridging bug')

# ── F. THE ANCHORS THIS CONTROL DEPENDS ON (discipline 8) ──────────────────
check('F1. strip_comments and _ROW_NAME are still the names this file calls',
      hasattr(S, 'strip_comments') and hasattr(S, '_ROW_NAME'))
check('F2. driven_resources still returns None for a file with no table -- the '
      'third state this grader depends on',
      S.driven_resources('const x = 1;\n') is None)

print('\n%s  run_cross_tenant_isolation_scope_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
