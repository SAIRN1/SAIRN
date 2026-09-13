"""Does a negative control prove it actually broke its target?

    python tools/sabotage_control_check.py --fixtures    # the blind lock alone
    python tools/sabotage_control_check.py
    python tools/sabotage_control_check.py --json

── WHY, AND IT HAPPENED TWICE IN ONE FILE ────────────────────────────────
A negative control sabotages a real source file, runs the checker, and asserts
it goes red. The sabotage is almost always `src.replace('<anchor>', ...)`. When
the target is refactored the anchor stops matching, **str.replace silently does
nothing**, and the control then runs the checker against an UNMODIFIED file.

The two ways that goes wrong are both bad and only one is loud:

  * the arm FAILS, and somebody spends time debugging a tool that is working
    perfectly. That happened in tests/run_financial_invariant_probe.py when
    invariant_registry.js moved from `debit_total` to `debit_total_cents`;
  * the arm PASSES, because the checker legitimately reports nothing on a file
    nobody touched and the arm was written as "expect no findings". **A control
    that cannot break its target is indistinguishable from a control that
    works**, and it will report green forever.

The second is the reason this exists. The first is merely how it was noticed.

MEASURED on the day this was written: 17 probes sabotage a source file, and
ELEVEN of them never check that the sabotage applied.

── WHAT A GUARDED CONTROL LOOKS LIKE ─────────────────────────────────────
Any of these is enough, and the tool accepts all of them rather than demanding
one house style:

    assert old in src                      # the anchor is present before use
    assert mutated != src                  # the replacement changed something
    check('the anchor still matches', sab != src, ...)
    if src_after == src_before: raise       # explicit refusal

What is NOT enough is asserting only on the checker's verdict afterwards. That
is the shape the whole convention exists to catch.

── WHAT IT CANNOT SEE, said here rather than discovered later ───────────
  * a sabotage that applies but changes the WRONG thing -- an anchor that
    matched somewhere unintended. Uniqueness is a separate question, and
    tools/mutation_anchor_check.py is the tool for it;
  * a control whose assertion is simply wrong about what the checker should do;
  * probes that sabotage by writing a whole fixture file rather than patching a
    real one. Those have no anchor to go stale and are not counted.

Exit 0 when every sabotaging probe verifies its own sabotage, 1 when one does
not, 2 when the fixtures fail -- which means nothing real was scanned.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRITERIA_VERSION = '2026-09-13.1'

# Writes a file AND builds the content with a replacement: the patch-a-real-file
# shape. A probe that only writes a fresh fixture has no anchor to rot.
# BROADENED after the blind lock caught a real BIAS in the first version.
# It required `.replace(` to be followed by a QUOTE, so `src.replace(old, new)`
# -- which is the GUARDED idiom, the one that names its anchor in a variable it
# can assert on -- was never judged at all. A pattern that cannot see the
# well-written probes would have reported the careless ones as the whole
# population. And WRITES missed a bare `write(p, m)` helper, which is how the JS
# probes do it.
WRITES = re.compile(r"open\([^)]*['\"]w['\"]|writeFileSync|write\(")
REPLACES = re.compile(r"\.replace\(")

# Any of these proves the probe checked its own sabotage landed.
GUARDS = (
    re.compile(r"assert\s+[\w\.\[\]']+\s+in\s+\w+"),          # assert old in src
    re.compile(r"!=\s*(src|orig|before|_before|original)\b"),
    re.compile(r"!==" + r"\s*(src|orig|before|_before|original|s)" + chr(92) + "b"),
    # `if (m !== s) write(...)` -- the JS shape, where the SHORT name holds
    # the original. Matching only long names missed every JS probe.
    re.compile(r"if\s*\([^)]*!==[^)]*\)\s*write"),
    re.compile(r"assert\s+\w+\s*!=\s*\w+"),
    re.compile(r"anchor[^\n]{0,60}(match|found|applies|still)", re.I),
    re.compile(r"sabotage[^\n]{0,60}(applied|changed|matches)", re.I),
)


def strip_comments(src, js):
    lines = src.split('\n')
    marker = '//' if js else '#'
    return '\n'.join(l for l in lines if not l.strip().startswith(marker))


def analyse(rel, src):
    js = rel.endswith('.js')
    code = strip_comments(src, js)
    if not (WRITES.search(code) and REPLACES.search(code)):
        return None
    guarded = any(g.search(code) for g in GUARDS)
    return {'file': rel, 'guarded': guarded}


# ── FIXTURES: hand-decided before the tests tree was scanned ──────────────
FIXTURES = [
    ('an unguarded replace-and-write is reported',
     "src = open(p).read()\nopen(p,'w').write(src.replace('a','b'))\n", False),
    ('a guarded one with `assert old in src` is not',
     "src = open(p).read()\nassert old in src\nopen(p,'w').write(src.replace(old,new))\n", True),
    ('a guarded one comparing before and after is not',
     "src = open(p).read()\nm = src.replace('a','b')\nassert m != src\nopen(p,'w').write(m)\n", True),
    ('a JS probe using !== src is not',
     "const s = read(p);\nconst m = s.replace('a','b');\nif (m !== s) write(p, m);\n", True),
    ('CONTROL: a probe that writes a FRESH fixture is not judged at all',
     "open(p,'w').write('| A | B |\\n')\n", None),
    ('CONTROL: a probe that only reads is not judged',
     "src = open(p).read()\nassert 'x' in src\n", None),
    ('a GUARD IN A COMMENT does not count -- the check must be in the code',
     "# assert old in src\nsrc = open(p).read()\nopen(p,'w').write(src.replace('a','b'))\n", False),
]


def run_fixtures():
    bad = []
    for name, src, want in FIXTURES:
        got = analyse('x.py', src)
        gv = None if got is None else got['guarded']
        if gv != want:
            bad.append((name, want, gv))
    return bad


def main(argv):
    bad = run_fixtures()
    print('SABOTAGE CONTROL CHECK -- criteria %s, report only' % CRITERIA_VERSION)
    if bad:
        print('  !! THE CRITERIA FAILED THEIR OWN FIXTURES. NOTHING WAS SCANNED.')
        for n, w, g in bad:
            print('     expected %-6s got %-6s %s' % (w, g, n))
        return 2
    print('  blind lock: %d/%d fixtures correct, run before the tests tree was read.'
          % (len(FIXTURES), len(FIXTURES)))
    if '--fixtures' in argv:
        return 0

    rows = []
    for root, _d, files in os.walk(os.path.join(REPO, 'tests')):
        for f in sorted(files):
            if not (f.endswith('.py') or f.endswith('.js')):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, REPO).replace(os.sep, '/')
            a = analyse(rel, io.open(p, encoding='utf-8', errors='replace').read())
            if a:
                rows.append(a)

    unguarded = [r for r in rows if not r['guarded']]
    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'rows': rows,
                          'unguarded': [r['file'] for r in unguarded]}, indent=1))
        return 1 if unguarded else 0

    print('  probes that sabotage a real source file : %d' % len(rows))
    print('  of those, verifying the sabotage APPLIED : %d' % (len(rows) - len(unguarded)))
    print('  UNGUARDED                                : %d' % len(unguarded))
    print('')
    print('  An unguarded control can silently become a no-op on a rename. The')
    print('  loud outcome is an arm failing against a tool that works. THE QUIET')
    print('  ONE IS WORSE: an arm written as "expect no findings" keeps passing')
    print('  on a file nobody touched, and reports green forever.')
    for r in unguarded:
        print('    %s' % r['file'])
    if not rows:
        print('')
        print('  NOTHING MATCHED. That is not a clean result -- check the patterns')
        print('  still describe how probes in this repo sabotage a file.')
    return 1 if unguarded else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
