#!/usr/bin/env python
"""invisible_in_pattern_check.py -- an unseeable character INSIDE A PATTERN.

    python tools/invisible_in_pattern_check.py              # sweep
    python tools/invisible_in_pattern_check.py --fixtures    # the blind lock only
    python tools/invisible_in_pattern_check.py <file>...     # scope to a file list

── THE DEFECT CLASS, AND WHY IT IS NARROWER THAN "AN INVISIBLE CHARACTER" ────
2026-09-14 was the THIRD confirmed instance on this platform of an invisible
character silently defeating an assertion, and all three were PRIVILEGE GUARDS:

    api/sv-auth.test.js   /<BS>delete<BS>/i   -- "NOTHING in this endpoint
                          deletes a credential row", on an app holding a
                          DEA-relevant register. Two literal 0x08 bytes where
                          word boundaries were meant, so the pattern matched a
                          backspace-delete-backspace byte sequence, which cannot
                          occur in source. `.test()` was always false, the
                          negation always true, and the guard passed
                          unconditionally for its entire life.

    plus the two found on 2026-09-10, same shape, one of them guarding a
    database privilege.

`tools/control_char_check.py` closed the C0 half and is push-gate check 11, and
the tree is clean of raw C0 bytes. **THIS TOOL DELIBERATELY DOES NOT RE-SCAN
C0.** Two checkers for one question is the second-copy shape the Guardian skill
says to resolve on discovery; the division of labour is stated here and in that
file rather than left for a reader to infer. What C0 does not cover is
everything ABOVE it, and a zero-width space or an NBSP inside `/.../` is exactly
as invisible and exactly as fatal as a backspace was.

── WHY "INSIDE A PATTERN" IS THE SCOPE, MEASURED RATHER THAN CHOSEN ──────────
A first pass swept every tracked text file for the whole invisible set. It found
**22,639 NBSP**, almost all in `docs/sources/sairnsenior/` -- captured statute
text, where an NBSP is what the legislature's own page served -- 91 ZWJ in the
archived ancestor branch (emoji sequences), three EM SPACES in more captured
statute, and **one U+FEFF in `sairnroofing.html`, which is CORRECT**: a BOM
deliberately prepended to CSV output so Excel reads it as UTF-8, with a comment
saying so.

So a whole-tree finding list is ~22,700 items of which zero are defects. That is
the shape this repo has already recorded as "how a check gets switched off before
it is ever promoted". **Invisibility is only load-bearing inside something that
MATCHES**: in a regex literal, or in a string handed straight to a regex
constructor. Everywhere else it is cosmetic. Findings are scoped there, and the
rest is reported as an INFORMATIONAL census so nothing is silently dropped.

── THE UNDER-REPORTING DIRECTION IS NAMED, NOT HIDDEN ────────────────────────
Deciding whether `/` starts a regex or divides is genuinely ambiguous in
JavaScript. The decision is DELEGATED to `jscomments._REGEX_OK` rather than
re-derived, because that scanner is the canonical one here and a second opinion
about the same character would be a second thing to keep in step. It is
conservative: a regex in a position that set does not list is not seen, so this
tool can UNDER-report -- the dangerous direction for a tripwire. That is why the
whole-file census runs too, and why its per-character totals are printed on a
clean run rather than only on a finding.

── THE BLIND LOCK ───────────────────────────────────────────────────────────
Convention 1 of `docs/2026-09-13-cross-domain-disciplines.md`: the criteria are
decided against synthetic fixtures BEFORE anything real is judged, the fixtures
run in ISOLATION rather than beside live data, and the tool exits 2 with
"nothing real was judged" if any of them classifies wrongly. FIXTURES below were
written from the defect shapes, and one of them is the sairnroofing BOM in its
real position -- a line this tool must NOT flag.

Exit 0 clean, 1 finding, 2 could-not-run. Three states, never two.
"""
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402
from checker_kit import tracked, finish                               # noqa: E402
from jscomments import _REGEX_OK                                      # noqa: E402

# ── WHAT COUNTS AS INVISIBLE HERE. C0 is control_char_check's, not this one's.
INVISIBLE = {}
for _cp, _name in [
    (0x00A0, 'NBSP'), (0x00AD, 'SOFT HYPHEN'), (0x180E, 'MONGOLIAN VOWEL SEP'),
    (0x200B, 'ZERO WIDTH SPACE'), (0x200C, 'ZERO WIDTH NON-JOINER'),
    (0x200D, 'ZERO WIDTH JOINER'), (0x200E, 'LEFT-TO-RIGHT MARK'),
    (0x200F, 'RIGHT-TO-LEFT MARK'), (0x2028, 'LINE SEPARATOR'),
    (0x2029, 'PARAGRAPH SEPARATOR'),
    # ── THE BIDI OVERRIDES ARE THE SECURITY HALF (Trojan Source, CVE-2021-42574)
    # These make source READ differently from how it EXECUTES, which is a
    # strictly worse problem than a pattern that cannot match: a reviewer sees
    # one thing and the engine runs another, and no amount of care catches it.
    (0x202A, 'LRE'), (0x202B, 'RLE'), (0x202C, 'PDF'), (0x202D, 'LRO'),
    (0x202E, 'RLO'), (0x2066, 'LRI'), (0x2067, 'RLI'), (0x2068, 'FSI'),
    (0x2069, 'PDI'),
    (0x202F, 'NARROW NBSP'), (0x205F, 'MEDIUM MATHEMATICAL SPACE'),
    (0x2060, 'WORD JOINER'), (0x2061, 'FUNCTION APPLICATION'),
    (0x2062, 'INVISIBLE TIMES'), (0x2063, 'INVISIBLE SEPARATOR'),
    (0x2064, 'INVISIBLE PLUS'), (0x3000, 'IDEOGRAPHIC SPACE'),
    (0xFEFF, 'ZWNBSP / BOM'), (0xFFF9, 'INTERLINEAR ANCHOR'),
    (0xFFFA, 'INTERLINEAR SEPARATOR'), (0xFFFB, 'INTERLINEAR TERMINATOR'),
]:
    INVISIBLE[_cp] = _name
for _cp in range(0x2000, 0x200B):
    INVISIBLE.setdefault(_cp, 'UNUSUAL SPACE U+%04X' % _cp)

JS_EXT = ('.js', '.html', '.htm', '.mjs', '.cjs')
PY_EXT = ('.py',)
# A string literal handed straight to a regex constructor is the same defect
# wearing a different hat.
CTOR_JS = ('new RegExp(',)
CTOR_PY = ('re.compile(', 're.search(', 're.match(', 're.fullmatch(',
           're.sub(', 're.findall(', 're.split(')


def js_pattern_spans(src):
    """(start, end) of every JS regex literal body, delimiters excluded.

    Mirrors jscomments' walk, importing its _REGEX_OK so the one genuinely
    ambiguous judgement -- is this `/` a regex or a division -- has ONE source.
    """
    spans, i, n, prev = [], 0, len(src), ''
    while i < n:
        c = src[i]
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            while i < n and src[i] != '\n':
                i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in '\'"`':
            q, j = c, i + 1
            while j < n:
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == q:
                    j += 1
                    break
                if q != '`' and src[j] == '\n':
                    break
                j += 1
            i, prev = j, q
            continue
        if c == '/' and prev in _REGEX_OK:
            j, ok = i + 1, False
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
                spans.append((i + 1, j - 1))
                i, prev = j, '/'
                continue
        if not c.isspace():
            prev = c
        i += 1
    return spans


def ctor_spans(src, ctors):
    """(start, end) of the FIRST string literal argument to each constructor."""
    spans = []
    for ctor in ctors:
        at = 0
        while True:
            k = src.find(ctor, at)
            if k < 0:
                break
            at = k + len(ctor)
            j = at
            while j < len(src) and src[j] in ' \t':
                j += 1
            if j < len(src) and src[j] in '\'"`':
                q, e = src[j], j + 1
                while e < len(src):
                    if src[e] == '\\':
                        e += 2
                        continue
                    if src[e] == q:
                        break
                    e += 1
                spans.append((j + 1, e))
    return spans


def scan_text(path, src):
    """(findings, census) for one file's text."""
    findings = []
    census = {}
    for idx, ch in enumerate(src):
        cp = ord(ch)
        if cp in INVISIBLE:
            census[INVISIBLE[cp]] = census.get(INVISIBLE[cp], 0) + 1
    low = path.lower()
    spans = []
    if low.endswith(JS_EXT):
        spans = js_pattern_spans(src) + ctor_spans(src, CTOR_JS)
    elif low.endswith(PY_EXT):
        spans = ctor_spans(src, CTOR_PY)
    for a, b in spans:
        for idx in range(a, min(b, len(src))):
            cp = ord(src[idx])
            if cp in INVISIBLE:
                findings.append('%s:%d contains U+%04X %s INSIDE A PATTERN -- '
                                'invisible, and it changes what the pattern matches'
                                % (path, src.count('\n', 0, idx) + 1, cp, INVISIBLE[cp]))
    return findings, census


# ── THE BLIND LOCK ───────────────────────────────────────────────────────────
# (label, filename, source, must_flag). Hand-built, judged in ISOLATION, before
# any real file is opened. The LAST TWO are the ones that matter: a real-world
# benign occurrence this tool must stay silent about, and the exact live line
# from sairnroofing.html, because a checker that flags a correct BOM in a CSV
# writer is a checker somebody turns off.
# ── COMPOSED FROM chr(), NEVER TYPED AS LITERAL CHARACTERS ──────────────────
# The first version of this block held REAL zero-width spaces, a real NBSP, a
# real RLO and a real BOM. It was clean on its first sweep only because the file
# was not yet git-tracked; the run after the commit flagged THIS FILE, correctly,
# for containing an invisible character inside a pattern.
#
# NOT EXEMPTED -- REMOVED. An exemption would hide a real occurrence elsewhere in
# this same file, and it would leave bytes in the tree that a reader cannot see.
# control_char_check.py's own advice is the rule here: replace the raw byte with
# its escape, because what changes is that the file becomes SEARCHABLE and the
# intent becomes VISIBLE. Composed names also document which character each
# fixture is about, which a literal never could.
ZWSP = chr(0x200B)
NBSP = chr(0x00A0)
RLO = chr(0x202E)      # the Trojan Source override
BOM = chr(0xFEFF)

# (label, filename, source, must_flag). Hand-built, judged in ISOLATION, before
# any real file is opened. The LAST THREE are the ones that matter: two
# real-world benign occurrences this tool must stay SILENT about -- the exact
# live line from sairnroofing.html, and a C0 byte, which is the other tool's
# question -- plus a division that is not a regex.
FIXTURES = [
    ('a ZWSP inside a regex literal', 'f.js',
     'assert.ok(/de' + ZWSP + 'lete/i.test(src));', True),
    ('an NBSP inside a regex literal', 'f.js',
     'if (/a' + NBSP + 'b/.test(s)) { return 1; }', True),
    ('a bidi override inside a regex literal', 'f.js',
     'var re = /admin' + RLO + '/;', True),
    ('a ZWSP in a new RegExp string', 'f.js',
     "var re = new RegExp('de" + ZWSP + "lete', 'i');", True),
    ('a ZWSP in a python re.compile', 'f.py',
     "PAT = re.compile('de" + ZWSP + "lete')", True),
    ('a clean regex literal', 'f.js',
     'assert.ok(/delete/i.test(src));', False),
    ("an NBSP in ORDINARY PROSE is not this tool's finding", 'f.js',
     '// the' + NBSP + 'word here is prose, not a pattern' + '\\n' + 'var x = 1;', False),
    ('a division that is not a regex', 'f.js',
     'var r = total / count / 2;', False),
    ('the LIVE sairnroofing BOM -- correct, and must stay silent', 'f.js',
     "  // CRLF per RFC 4180, and a BOM so Excel reads it as UTF-8" + '\\n' +
     "  return '" + BOM + "'+[head].concat(body).join('" + chr(92) + "r" + chr(92) + "n')+'"
     + chr(92) + "r" + chr(92) + "n';", False),
    ("a C0 backspace is control_char_check's, NOT this tool's", 'f.js',
     'assert.ok(!/' + chr(8) + 'delete' + chr(8) + '/i.test(src));', False),
]


def run_fixtures(verbose=True):
    """Returns a list of wrong verdicts. Empty means the criteria are locked."""
    wrong = []
    for label, name, src, must_flag in FIXTURES:
        found, _ = scan_text(name, src)
        got = bool(found)
        if got != must_flag:
            wrong.append('%s -- expected %s, got %s'
                         % (label, 'FLAG' if must_flag else 'SILENT',
                            'FLAG' if got else 'SILENT'))
        elif verbose:
            print('  ok   %s' % label)
    return wrong


def main(argv):
    only_fixtures = '--fixtures' in argv
    args = [a for a in argv if not a.startswith('--')]

    print('BLIND LOCK -- %d fixture(s), judged before any real file is opened'
          % len(FIXTURES))
    wrong = run_fixtures(verbose=only_fixtures)
    if wrong:
        print('\nREFUSING: the criteria do not classify their own fixtures.')
        for w in wrong:
            print('  x %s' % w)
        print('\nNOTHING REAL WAS JUDGED. Fix the criteria, or fix a fixture whose '
              'expected verdict was itself wrong -- and say in this file which one '
              'you did.')
        return EXIT_COULD_NOT_RUN
    print('  %d/%d fixtures correct.' % (len(FIXTURES), len(FIXTURES)))
    if only_fixtures:
        return EXIT_CLEAN

    if args:
        files, notes = [os.path.relpath(a, REPO).replace('\\', '/') for a in args], []
    else:
        files, notes = tracked('*.js', '*.html', '*.htm', '*.py', '*.mjs', '*.cjs')

    findings, could_not_run, census, scanned = [], [], {}, 0
    for f in files:
        p = os.path.join(REPO, f)
        if not os.path.isfile(p):
            could_not_run.append('%s -- not on disk, so it was NOT scanned' % f)
            continue
        try:
            src = io.open(p, encoding='utf-8').read()
        except Exception as e:
            could_not_run.append('%s -- unreadable (%s), so it was NOT scanned'
                                 % (f, type(e).__name__))
            continue
        scanned += 1
        fs, cs = scan_text(f, src)
        findings.extend(fs)
        for k, v in cs.items():
            census[k] = census.get(k, 0) + v

    print('\n  files scanned : %d' % scanned)
    for n in notes:
        print('  not scanned   : %s' % n)
    # ── THE CENSUS IS PRINTED EVEN ON A CLEAN RUN, and it is deliberately NOT
    # a finding list. This tool can under-report inside patterns (see the header
    # on _REGEX_OK), so a total of zero here is the only thing that would let a
    # reader conclude nothing invisible exists anywhere. A non-zero total with
    # no findings means: present, and not in a position where it matches.
    print('\n  CENSUS -- every invisible character in scanned files, IN OR OUT of a '
          'pattern.\n  Informational, not findings: an NBSP in captured statute text '
          'and a BOM\n  written into a CSV on purpose are both correct.')
    if census:
        for k in sorted(census, key=lambda x: -census[x]):
            print('    %-30s %6d' % (k, census[k]))
    else:
        print('    none')

    return finish(findings, could_not_run,
                  clean_line='CLEAN -- no invisible character inside any regex '
                             'literal or regex-constructor string.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
