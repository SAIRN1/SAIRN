#!/usr/bin/env python
# REQUIREMENT: tools/citation_arm_depth_check.py must be able to FIND a cited test
#   that never loads its subject -- it answered 85 of 85 clean on its first run
#   against this repo, and a detector whose only evidence is a clean sweep is
#   indistinguishable from one that cannot detect anything
#
# Run: python tests/run_citation_arm_depth_probe.py
#
# ── WHY THIS EXISTS, IN ONE SENTENCE ──────────────────────────────────────
# `docs/2026-09-13-cross-domain-disciplines.md` item 1: lock a check's criteria
# against SYNTHETIC FIXTURES before trusting it on real data. The detector was
# written to find a specific shape -- a test file named for a module, sitting
# beside it, that never loads it -- and the repo has none, so the real data
# cannot tell a working detector from a broken one.
#
# BOTH DIRECTIONS, because a detector that says "finding" for everything is
# equally useless: every POSITIVE fixture must be caught and every NEGATIVE
# fixture must be left alone.

import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

import citation_arm_depth_check as C  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  ok   ' if cond else '  FAIL ') + name
          + (('\n       ' + detail) if not cond and detail else ''))


def section(t):
    print('\n' + t)


ROOT = tempfile.mkdtemp(prefix='citdepth-')


def fixture(name, body):
    """Write <name>.js and <name>.test.js; the test body is the variable."""
    io.open(os.path.join(ROOT, name + '.js'), 'w', encoding='utf-8').write(
        'module.exports = function () { return 1; };\n')
    io.open(os.path.join(ROOT, name + '.test.js'), 'w', encoding='utf-8').write(body)
    return (name + '.js', name + '.test.js')


try:
    print('citation_arm_depth_check -- can it find the shape it was built for?\n')

    section('A. POSITIVE fixtures -- these MUST be reported')
    src, t = fixture('orphan', "const assert=require('assert');\nassert.ok(true);\n")
    check('A1. a test that loads nothing at all is a finding',
          C.loads(t, src, ROOT) is False)

    src, t = fixture('commented',
                     "// This file covers commented.js end to end.\n"
                     "/* see commented.js for the endpoint under test */\n"
                     "const assert=require('assert');\nassert.ok(true);\n")
    check('A2. A MENTION IN A COMMENT IS NOT COVERAGE -- the finding class '
          'itself, so accepting prose would make the tool vacuous',
          C.loads(t, src, ROOT) is False)

    src, t = fixture('neighbour',
                     "const other=require('./somethingelse.js');\n"
                     "const assert=require('assert');\nassert.ok(other);\n")
    check('A3. loading a DIFFERENT module is still a finding',
          C.loads(t, src, ROOT) is False)

    section('B. NEGATIVE fixtures -- these must NOT be reported')
    src, t = fixture('required', "const m=require('./required.js');\nm();\n")
    check('B1. require with the .js extension', C.loads(t, src, ROOT) is True)

    src, t = fixture('extless', "const m=require('./extless');\nm();\n")
    check('B2. require without the extension', C.loads(t, src, ROOT) is True)

    src, t = fixture('resolved',
                     "const id=require.resolve('./resolved.js');\nconsole.log(id);\n")
    check('B3. require.resolve, the stub-injection shape portal.test.js uses',
          C.loads(t, src, ROOT) is True)

    src, t = fixture('imported', "import m from './imported.js';\nm();\n")
    check('B4. an ESM import', C.loads(t, src, ROOT) is True)

    src, t = fixture('readoff',
                     "const fs=require('fs');\n"
                     "const s=fs.readFileSync(__dirname+'/readoff.js','utf8');\n"
                     "if(!s) throw new Error('x');\n")
    check('B5. read off disk -- how the HTML/source-extracting suites work',
          C.loads(t, src, ROOT) is True)

    src, t = fixture('pathjoin',
                     "const path=require('path');\n"
                     "const p=path.join(__dirname,'pathjoin.js');\n"
                     "require(p);\n")
    check('B6. a path built with path.join still names the file',
          C.loads(t, src, ROOT) is True)

    section('C. the COULD-NOT-TELL state is its own answer')
    check('C1. a test file that does not exist returns None, not False -- '
          '"I could not read it" must never be reported as "it does not load"',
          C.loads('no-such-file.test.js', 'no-such-file.js', ROOT) is None)

    section('D. controls on the fixtures themselves')
    # A1 and B1 differ in exactly one respect. If the harness were broken --
    # wrong root, every read failing -- A1 would still "pass" (None is not
    # True, but the assert is `is False`, so it would fail) while a subtler
    # break could make everything answer the same. This asserts the two
    # directions actually DIFFER on this harness.
    s1, t1 = fixture('ctrl_neg', "const assert=require('assert');\n")
    s2, t2 = fixture('ctrl_pos', "const m=require('./ctrl_pos.js');\n")
    check('D1. the harness distinguishes the two directions -- a positive and '
          'a negative fixture do not return the same value',
          C.loads(t1, s1, ROOT) != C.loads(t2, s2, ROOT),
          'both answered %r' % (C.loads(t1, s1, ROOT),))
    check('D2. ...and the fixtures were really written to disk, so A* and B* '
          'are not passing over empty reads',
          os.path.isfile(os.path.join(ROOT, 'ctrl_pos.test.js'))
          and os.path.getsize(os.path.join(ROOT, 'ctrl_pos.test.js')) > 0)

    section('E. the real repo, for context rather than as evidence')
    rows = C.analyse()
    bad = [r for r in rows if r['loads'] is False]
    print('   %d co-located pairs, %d do not load their subject'
          % (len(rows), len(bad)))
    check('E1. the walk found a non-trivial population -- a clean result over '
          'two pairs would mean nothing', len(rows) >= 20,
          'only %d pairs found; the sweep is not measuring the repo' % len(rows))
    for r in bad:
        print('   FINDING %s does not load %s' % (r['test'], r['source']))

finally:
    shutil.rmtree(ROOT, ignore_errors=True)

print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
