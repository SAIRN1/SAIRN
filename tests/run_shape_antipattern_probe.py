"""tests/run_shape_antipattern_probe.py

Run:  python tests/run_shape_antipattern_probe.py

The control pair for tools/shape_antipattern_check.py -- item 90.

CONTROLS_FOR = ['shape_antipattern_check.py']

Scaffolded by tools/new_checker.py and then completed, which is the first real
use of that generator.

THREE SHAPES, AND EACH NEEDS BOTH DIRECTIONS SEPARATELY. A combined "it found
something" arm would be satisfied by a checker that detects one shape and is
blind to the other two -- and since S2 reports ZERO against the real tree today,
that is not a hypothetical: without a per-shape positive arm, S2 could have
stopped working entirely and nothing here would have noticed.

THE NEGATIVE ARMS ARE THE MEASURED ONES. Every one below is a real line from
this repo that the first draft flagged and should not have:

    Number(body.prior_count) || 0        api/_lib/ai-rate-limit.js
    Number(dd.value) after a .trim() check   sairnlaw.html
    function isWeekend(d)                sairnfreedom.html

Those three false positives are why the criterion narrowed twice. They are
pinned here so the narrowing cannot be undone by somebody widening the pattern
back out.
"""
# REQUIREMENT: each shape shape_antipattern_check.py detects is driven
#   positively AND negatively on its own, because one shape reports zero
#   against the real tree and a combined arm would be satisfied by a checker
#   blind to it
#
import io
import os
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['shape_antipattern_check.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'shape_antipattern_check.py')
FAIL = []
NL = chr(10)


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else NL + '        ' + str(detail)[:600]))
    if not cond:
        FAIL.append(name)


def run(*args):
    r = subprocess.run([sys.executable, TOOL] + list(args),
                       capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO, timeout=900)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


TMP = tempfile.mkdtemp(prefix='shape-probe-')


def write(name, body):
    p = os.path.join(TMP, name)
    io.open(p, 'w', encoding='utf-8', newline='').write(body)
    if io.open(p, encoding='utf-8').read() != body:
        raise AssertionError('the fixture did not land: ' + name)
    return p


print('shape_antipattern_check -- the control pair')

# ── A. the blind lock ──────────────────────────────────────────────────────
print(NL + '--- A. the fixtures, in isolation ---')
rc, out = run('--fixtures')
ok('A1 the lock runs before any real file is opened',
   'before any real file' in out, out)
ok('A2 and it passes -- the rule is written', rc == 0 and 'fixtures correct' in out,
   'rc=%d%s%s' % (rc, NL, out))
ok('A3 the lock covers all three shapes, not just the one that reports today',
   out.count('S1:') >= 2 and out.count('S2:') >= 2 and out.count('S3:') >= 2, out)

# ── B. each shape fires on its own ─────────────────────────────────────────
print(NL + '--- B. each shape, planted separately ---')
s1 = write('s1.js', 'const hour = Number(req.query.client_hour);' + NL + 'return hour;' + NL)
rc, out = run(s1)
ok('B1 S1 fires on Number() over an outside value', rc == 1 and 'S1 PRIMITIVE' in out,
   'rc=%d%s%s' % (rc, NL, out))

s2 = write('s2.js', 'function isAllowed(u, role) {' + NL + '  if (!u) return false;' + NL +
                    '  if (!role) return false;' + NL + '  return true;' + NL + '}' + NL)
rc, out = run(s2)
ok('B2 S2 fires on a guard collapsing two distinct reasons into one bit',
   rc == 1 and 'S2 BOOLEAN' in out, 'rc=%d%s%s' % (rc, NL, out))

s3 = write('s3.js', 'if (pct === null) {' + NL + '  out.a = null;' + NL +
                    '  out.b = null;' + NL + '  out.c = null;' + NL + '}' + NL)
rc, out = run(s3)
ok('B3 S3 fires on three nulls in one branch', rc == 1 and 'S3 OPTIONAL' in out,
   'rc=%d%s%s' % (rc, NL, out))

# ── C. THE PAIR, from lines the first draft got wrong ──────────────────────
print(NL + '--- C. the measured false positives, pinned ---')
c1 = write('c1.js', 'return { count: Number(body.prior_count) || 0 };' + NL)
rc, out = run(c1)
ok('C1 `Number(x) || 0` is a GUARD, not the truthy-coercion bug -- ai-rate-limit.js',
   rc == 0, 'rc=%d%s%s' % (rc, NL, out))

c2 = write('c2.js',
           'if (!dd || !String(dd.value).trim()) { return; }' + NL +
           'payload.designated_period_days = Number(dd.value);' + NL)
rc, out = run(c2)
ok('C2 an emptiness check two lines up closes the Number("") path -- sairnlaw.html',
   rc == 0, 'rc=%d%s%s' % (rc, NL, out))

c3 = write('c3.js', 'function isWeekend(d) {' + NL + '  if (!d) return false;' + NL +
                    '  return true;' + NL + '}' + NL)
rc, out = run(c3)
ok('C3 A PURE PREDICATE IS NOT BOOLEAN BLINDNESS -- sairnfreedom.html', rc == 0,
   'rc=%d%s%s' % (rc, NL, out))

c4 = write('c4.js', 'const n = Number(3);' + NL + 'if (pct === null) {' + NL +
                    '  out.a = null;' + NL + '  out.b = null;' + NL + '}' + NL)
rc, out = run(c4)
ok('C4 a literal and a two-null branch together stay silent', rc == 0,
   'rc=%d%s%s' % (rc, NL, out))

# ── D. the boundary with the checker that already owns the other half ──────
print(NL + '--- D. it does not re-detect what truthy_sum_check owns ---')
d1 = write('d1.js', 'const t = hist.reduce(function (s, o) { return s + (o.total || 0); }, 0);' + NL)
rc, out = run(d1)
ok('D1 the `(x || 0)` FOLD is truthy_sum_check.py\'s finding, not this one -- '
   'two checkers for one question is the duplication the Guardian skill refuses',
   rc == 0, 'rc=%d%s%s' % (rc, NL, out))

print('')
if FAIL:
    print('shape_antipattern: %d ARM(S) FAILED -- %s' % (len(FAIL), ', '.join(FAIL)))
    sys.exit(1)
print('shape_antipattern: all arms pass')
