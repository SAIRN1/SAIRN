r"""tests/run_message_assertion_probe.py -- control pair for
tools/message_assertion_audit.py.

    python tests/run_message_assertion_probe.py

CONTROLS_FOR = ['tools/message_assertion_audit.py']
LIVE_PROBE_CLASS = 'FIXTURE'

WHY, AND THE TOOL'S FIRST TWO CRITERIA WERE BOTH WRONG -- which is the reason a
control pair for a classifier is not optional:

  v1 called ANY equality against a string literal a message assertion. Run over
  the real corpus it reported NINE mutation controls as "every assertion is a
  string check", when what each of them asserts is
  `strictEqual(fs.readFileSync(clean, 'utf8'), ORIGINAL)` -- a whole-file byte
  comparison against a saved baseline, the strongest behavioural check here.

  v2 fixed that, and then its FINDING UNIT was wrong: it asked for a file whose
  EVERY assertion is text, and over 589 real files that returns ZERO. A tool
  sitting on 1,464 string assertions reported no findings. A criterion that
  cannot fire on its own corpus has not been validated, it has been flattered.

So every arm below drives a fixture in BOTH directions: a shape that must be
TEXT, and a shape that must NOT be.

THE KNOWN-BAD CONTROLS, and every one must be classified the way it says:

  'literal' in out                      -> TEXT
  re.search('literal', out)             -> TEXT
  x.includes('literal') / assert.match  -> TEXT
  rc == 2 / len(rows) >= 3              -> VALUE
  readFileSync(f) === ORIGINAL          -> VALUE   (v1 got this wrong)
  handle(null) === 'REFUSED'            -> VALUE   (v1 got this wrong)
  rc == 1 and 'X' in out                -> VALUE   (one behaviour limb is enough)
  an unparseable file                   -> COULD NOT TELL, never zero
"""
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'message_assertion_audit.py')
sys.path.insert(0, os.path.join(REPO, 'tools'))
from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN  # noqa: E402

if not os.path.isfile(TOOL):
    print('COULD NOT RUN: tools/message_assertion_audit.py is not on disk. This '
          'control tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

import message_assertion_audit as M   # noqa: E402

NL = chr(10)
passed = failed = 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:400])


def kinds_py(text):
    d = tempfile.mkdtemp(prefix='sairn_maa_p_')
    try:
        p = os.path.join(d, 'f.py')
        io.open(p, 'w', encoding='utf-8', newline=NL).write(text)
        hits = M.scan_py(p)
        return None if hits is None else [k for _l, k, _s in hits]
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def kinds_js(text):
    d = tempfile.mkdtemp(prefix='sairn_maa_j_')
    try:
        p = os.path.join(d, 'f.js')
        io.open(p, 'w', encoding='utf-8', newline=NL).write(text)
        hits = M.scan_js(p)
        return None if hits is None else [k for _l, k, _s in hits]
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


def run(*args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=900,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


print('CONTROL PAIR -- tools/message_assertion_audit.py' + NL)
print('CRITERIA, each against a fixture in BOTH directions')

# ── TEXT, the defect class: a literal checked for CONTAINMENT ─────────────
ok(kinds_py("assert 'NOT PROVISIONED' in out" + NL) == ['TEXT'],
   "`'literal' in out` is TEXT -- containment in captured output is the shape",
   kinds_py("assert 'NOT PROVISIONED' in out" + NL))
ok(kinds_py("assert re.search('NOT PROVISIONED', out)" + NL) == ['TEXT'],
   're.search with a string literal is TEXT',
   kinds_py("assert re.search('NOT PROVISIONED', out)" + NL))
ok(kinds_py("assert out.startswith('COULD NOT RUN')" + NL) == ['TEXT'],
   '.startswith with a literal is TEXT',
   kinds_py("assert out.startswith('COULD NOT RUN')" + NL))
ok(kinds_py("ok('could not tell' in out, 'it says so')" + NL) == ['TEXT'],
   "and it follows this repo's own helper -- ok(cond, label) is read as an "
   'assertion, with the LABEL not mistaken for the thing asserted',
   kinds_py("ok('could not tell' in out, 'it says so')" + NL))

# ── VALUE, and these are the ones v1 got wrong ────────────────────────────
ok(kinds_py('assert rc == 2' + NL) == ['VALUE'],
   'an exit-code comparison is VALUE', kinds_py('assert rc == 2' + NL))
ok(kinds_py('ok(len(rows) >= 3, "three rows")' + NL) == ['VALUE'],
   'a length comparison is VALUE', kinds_py('ok(len(rows) >= 3, "x")' + NL))
ok(kinds_py("assert out == 'REFUSED'" + NL) == ['VALUE'],
   "KNOWN-BAD THE OTHER WAY: EQUALITY against a literal is VALUE, not TEXT. v1 "
   "called it TEXT and that is what mis-reported nine mutation controls",
   kinds_py("assert out == 'REFUSED'" + NL))
ok(kinds_py("ok(rc == 1 and 'DROPPED' in out, 'exit and wording')" + NL)
   == ['VALUE'],
   'an arm with ONE behavioural limb is VALUE -- a message check standing beside '
   'an exit-code check is not a message-only arm',
   kinds_py("ok(rc == 1 and 'DROPPED' in out, 'x')" + NL))

# ── JAVASCRIPT, labelled weaker, driven the same way ─────────────────────
ok(kinds_js("assert.match(r.error.message, /not available to your role/);" + NL)
   == ['TEXT'], 'JS: assert.match against a regex is TEXT',
   kinds_js("assert.match(r.error.message, /x/);" + NL))
ok(kinds_js("assert.ok(src.includes('if(_crRecords===null)return null;'));" + NL)
   == ['TEXT'], 'JS: .includes with a literal is TEXT',
   kinds_js("assert.ok(src.includes('x'));" + NL))
ok(kinds_js('assert.strictEqual(r.status, 403);' + NL) == ['VALUE'],
   'JS: a numeric strictEqual is VALUE', kinds_js('assert.strictEqual(r.status, 403);' + NL))
BASELINE = ("assert.strictEqual(fs.readFileSync(clean, 'utf8'), ORIGINAL," + NL
            + "  'the mutation control did not restore the file');" + NL)
ok('TEXT' not in (kinds_js(BASELINE) or ['TEXT']),
   'KNOWN-BAD THE OTHER WAY, AND IT IS THE REAL ONE: a WHOLE-FILE BYTE '
   'COMPARISON against a saved baseline is NOT a message assertion. v1 reported '
   'NINE mutation controls as message-only on exactly this line',
   kinds_js(BASELINE))
ok('TEXT' not in (kinds_js("assert.strictEqual(handle(null), 'REFUSED', 'x');" + NL)
                  or ['TEXT']),
   'and an equality against an ENUM-SHAPED return value is not one either',
   kinds_js("assert.strictEqual(handle(null), 'REFUSED', 'x');" + NL))

# ── FAIL CLOSED ──────────────────────────────────────────────────────────
print(NL + 'FAIL CLOSED -- a zero must never read as clean coverage')
ok(kinds_py('def (' + NL) is None,
   'an UNPARSEABLE file is a could-not-tell (None), not an empty list. Zero '
   'string assertions out of a file nobody could read is the vacuous pass this '
   'repo names most often', kinds_py('def (' + NL))
ok(kinds_py('x = 1' + NL) == [],
   'and a file with NO assertions is an empty list -- a real zero, '
   'distinguishable from the unreadable one above', kinds_py('x = 1' + NL))

rc, out = run('--file', 'tests/_zz_no_such_test.py')
ok(rc == EXIT_COULD_NOT_RUN,
   'an absent --file is exit 2, not 0 (got %d) -- an empty corpus is not a clean '
   'one' % rc, out[-400:])
ok('not a clean one' in out or 'COULD NOT RUN' in out,
   'and it says why rather than printing a bare refusal', out[-400:])

# ── THE TOOL'S OWN SELFTEST RUNS BEFORE THE CORPUS ───────────────────────
print(NL + 'THE FIXTURE GATE -- it must run BEFORE the corpus, not after')
rc, out = run('--selftest')
ok(rc == EXIT_CLEAN, '--selftest exits 0 (got %d)' % rc, out[-400:])
ok('ALL ARMS PASS' in out, 'and every fixture arm passes', out[-400:])
rc, out = run('--show', '0')
i_fix = out.find('FIXTURE GATE')
i_corp = out.find('test files read')
ok(0 <= i_fix < i_corp,
   'the fixture gate is printed BEFORE the corpus numbers, so a corpus figure '
   'from a comparison that cannot fire is impossible to read as a result',
   (i_fix, i_corp))

# ── THE REAL CORPUS, reported not asserted ───────────────────────────────
print(NL + 'THE REAL CORPUS -- reported, not asserted')
rc, out = run('--show', '4')
print('  --   exit %d' % rc)
ok(rc in (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN),
   'it exits one of the three defined codes', out[-300:])
ok('COULD NOT CLASSIFY' in out,
   'and it reports the UNCLASSIFIED bucket as its own number -- it is over half '
   'the corpus, and folding it either way would decide the ratio by how much '
   'the tool failed to parse', out[-1200:])
ok('WEAKER AND IS NOT FOLDED IN' in out,
   'and it keeps the javascript estimate separate from the python parse, '
   'because regex and an AST are not the same evidence', out[-1600:])
ok('it does not mutate anything' in out,
   'and it says it mutates nothing, so the number is read as a population to '
   'mutate rather than as a defect count', out[-1600:])

# THE FINDING COUNT MUST BE ABLE TO FIRE ON THE REAL CORPUS. This is the arm
# that would have caught v2's unusable criterion.
import re as _re
m = _re.search(r'AT LEAST HALF THE CLASSIFIED ASSERTIONS: (\d+) of (\d+)', out)
ok(m is not None, 'the corpus line names both the finding count and the '
                  'scoreable denominator', out[-900:])
if m:
    hits, denom = int(m.group(1)), int(m.group(2))
    ok(denom > 0, 'the denominator is non-zero -- a ratio over zero files is '
                  'not a measurement', (hits, denom))
    ok(0 < hits < denom,
       'THE ARM THAT WOULD HAVE CAUGHT v2: the finding count is neither 0 nor '
       'the whole denominator (%d of %d). A criterion that fires on nothing has '
       'not been validated, and one that fires on everything has found nothing'
       % (hits, denom), (hits, denom))

print(NL + '%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
