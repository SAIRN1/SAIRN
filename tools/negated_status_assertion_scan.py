"""REACHABILITY ASSERTED AS THE NEGATION OF ONE STATUS CODE.

    python tools/negated_status_assertion_scan.py
    python tools/negated_status_assertion_scan.py --selftest

Exit 0  no candidate found (or only rows the reader has nothing to look at)
Exit 1  candidates found -- A READ-LIST, NOT A VERDICT
Exit 2  COULD NOT RUN -- never folded into either of the other two

── THE CLASS, WHICH IS NOT HYPOTHETICAL ───────────────────────────────────────
On 2026-09-16 tests/app_session_isolation.js printed this, in green, for as long
as it was wrong:

    ok  PHASE 1 (still open): law_trusttx is reachable with the LICENCE ALONE
        -- no session -- and answers 403

It asserted `out.code !== 401`. The gate that had just been put in front of
attorney IOLTA trust money refuses with 403, so the arm was satisfied by the
refusal it was written to detect, and its own message interpolated the status
code that disproved it. A control over trust money reported a gate it could no
longer see.

`!== <one code>` for "it got through" is wrong whenever the endpoint has more
than one refusal shape, and api/sd-data.js has at least two: 401 NO_SESSION on
the generic path and 403 FORBIDDEN from SD_SESSION_GATED. It is satisfied by the
other code, by a 500, and by a harness fault -- each of which is the caller NOT
getting through.

AND THE REPAIR SHIPPED WITH A FRESH INSTANCE, THIRTY-EIGHT LINES BELOW A COMMENT
SAYING NOT TO. That is why this file exists: the author knew the rule, had just
written it down, had the counter-example open, and did it anyway. A rule that
survives only by being remembered has been measured here, once, and it did not.

── WHAT THIS IS AND IS NOT ────────────────────────────────────────────────────
A READ-LIST. Every row needs a human, because `!== <code>` IS CORRECT in one
common case and this tool cannot tell which case it is looking at:

  * asserting a caller GOT THROUGH  -> almost always wrong. Say `=== 200`.
  * asserting a SPECIFIC OTHER lock answered -- "this is the licence boundary,
    not the session gate" -> the negation is the claim, and naming the code it
    DOES expect is still better, because the negation is also satisfied by a
    500.

IT DOES NOT CLASSIFY BY MESSAGE TEXT. Keyword-matching "reaches" or "works"
would be wrong in both directions, and this platform has paid for that twice --
a signal-shaped probe that matched two user-facing sentences, and a key scan
that counted a line of prose. The row is printed with its assertion and its
message; the reader decides.

IT READS COMMENT-STRIPPED SOURCE, because a comment DISCUSSING `!== 401` -- of
which this repo now has several, including the ones written by the fix -- is not
an assertion. PR 1.2.
"""
import io
import os
import re
import subprocess
import sys

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout.strip()

# `!== 401`, `!= 403`, `!== 200` ... inside an assertion, with the code captured.
NEGATED = re.compile(r'!==?\s*(\d{3})\b')

# Only lines that are ASSERTING something. A bare `if (x !== 401)` in helper
# code is control flow, not a claim, and printing it would bury the rows that
# matter -- the failure mode of every over-reporting scanner in this repo.
ASSERTING = re.compile(r'\b(assert|assert\.\w+|ok|expect|strictEqual|t\.\w+)\s*\(')

SEARCH_DIRS = ('tests', 'api')


def fail(msg):
    print('COULD NOT RUN: ' + msg)
    print('This is exit 2, and it is not a pass.')
    sys.exit(2)


def strip_comments(src):
    """Line and block comments out; string literals left alone.

    Deliberately simple and deliberately NOT shared with the seven-way
    strip_comments mess this repo already paid for: it is used here only to
    decide whether a LINE is code, and a line that is half comment still counts
    as code, which is the safe direction for a read-list.
    """
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    return '\n'.join(re.sub(r'//.*$', '', l) for l in src.split('\n'))


def candidate_files():
    out = []
    for d in SEARCH_DIRS:
        root = os.path.join(REPO, d)
        if not os.path.isdir(root):
            fail('%s does not exist, so the sweep would report a clean tree it '
                 'never looked at.' % d)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [x for x in dirnames if x != 'node_modules']
            for f in filenames:
                if not f.endswith('.js'):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, f), REPO)
                rel = rel.replace(os.sep, '/')
                if d == 'api' and not rel.endswith('.test.js'):
                    continue
                out.append(rel)
    if not out:
        fail('no suite files found under %s. An empty sweep is indistinguishable '
             'from a clean one.' % ', '.join(SEARCH_DIRS))
    return sorted(out)


def scan_text(src):
    """[(line_no, code, line)] for every ASSERTED negation of a status code."""
    hits = []
    for i, line in enumerate(strip_comments(src).split('\n'), 1):
        if not ASSERTING.search(line):
            continue
        for m in NEGATED.finditer(line):
            hits.append((i, m.group(1), line.strip()))
    return hits


def main(argv):
    if '--selftest' in argv:
        return selftest()
    files = candidate_files()
    rows, scanned = [], 0
    for rel in files:
        try:
            src = io.open(os.path.join(REPO, rel), encoding='utf-8',
                          errors='replace').read()
        except OSError as e:                                     # noqa: BLE001
            fail('could not read %s: %s' % (rel, e))
        scanned += 1
        for n, code, line in scan_text(src):
            rows.append((rel, n, code, line))

    print('NEGATED STATUS ASSERTIONS -- a READ-LIST, not a verdict')
    print('  %d suite file(s) scanned, comment-stripped' % scanned)
    print('  %d asserted `!== <status>` occurrence(s)\n' % len(rows))
    if not rows:
        print('  none. That is a statement about %d files, not about the '
              'platform.' % scanned)
        return 0
    for rel, n, code, line in rows:
        print('  %s:%d  !== %s' % (rel, n, code))
        print('      %s' % (line[:150]))
    print('')
    print('EVERY ROW NEEDS A HUMAN. `!== <code>` is correct when the claim IS')
    print('"some OTHER lock answered" -- and wrong when the claim is "the caller')
    print('got through", because the negation is also satisfied by the other')
    print('refusal code, by a 500, and by the harness throwing.')
    print('')
    print('The 2026-09-16 instance was the second kind: a control over attorney')
    print('trust money asserted `!== 401` against a gate that refuses 403, and')
    print('printed "is reachable with the LICENCE ALONE ... and answers 403".')
    return 1


# ── THE SELF-TEST, BLIND-LOCKED ─────────────────────────────────────────────
# Fixtures first, in both directions, and the criteria are fixed here rather
# than after looking at the tree.
FIXTURES = [
    ('the exact 2026-09-16 defect',
     "  ok(out.code !== 401, 'law_trusttx is reachable with the LICENCE ALONE');",
     1),
    ('the corrected form is NOT reported',
     "  ok(out.code === 200, 'law_trusttx is reachable with the LICENCE ALONE');",
     0),
    ('a negation in a COMMENT is not an assertion',
     "  // this used to read ok(out.code !== 401, ...) and that was the defect",
     0),
    ('a negation in CONTROL FLOW is not an assertion',
     "  if (res.statusCode !== 403) { retry(); }",
     0),
    ('node:assert form is reported',
     "  assert.notStrictEqual(res.statusCode, 401);",
     0),          # notStrictEqual carries no literal `!==`; stated, not implied
    ('assert with an inline negation IS reported',
     "  assert.ok(res.statusCode !== 401, 'reached');",
     1),
    ('a block comment spanning the line is stripped',
     "  /* ok(a.code !== 401, 'x'); */",
     0),
    ('two negations on one asserting line are two rows',
     "  ok(a.code !== 401 && b.code !== 403, 'both got through');",
     2),
]


def selftest():
    bad = []

    def arm(name, ok, detail=''):
        print(('  ok   ' if ok else '  FAIL ') + name + ('' if ok else '  ' + str(detail)))
        if not ok:
            bad.append(name)

    print('SELFTEST -- criteria locked against fixtures before the real run\n')
    for name, src, want in FIXTURES:
        got = len(scan_text(src))
        arm('%-52s -> %d' % (name, want), got == want, 'got %d' % got)

    # AND THE REAL TREE, as a separate statement.
    print('')
    files = candidate_files()
    arm('the sweep reaches a real number of suite files', len(files) > 100,
        len(files))
    known = 'tests/app_session_isolation.js'
    arm('...including %s, which is where the class was found' % known,
        known in files, [f for f in files if 'isolation' in f][:3])
    src = io.open(os.path.join(REPO, known), encoding='utf-8').read()
    arm('...and that file no longer asserts a reachability negation -- it was '
        'fixed, so a hit here would mean the fix regressed',
        not [r for r in scan_text(src) if 'code !== ' in r[2]],
        [r[2][:80] for r in scan_text(src)][:3])

    print('')
    if bad:
        print('%d selftest arm(s) failed' % len(bad))
        return 2
    print('OK: the criteria separate the shipped defect from its repair, and '
          'ignore comments and control flow.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
