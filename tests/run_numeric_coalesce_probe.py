"""Does the numeric-default scanner find the real defect shape and nothing else?

WRITTEN BEFORE THE SCANNER. Every arm was run against a missing
tools/numeric_default_coalesce_scan.py first and every one failed.

THE SHAPE, FROM THE REAL DEFECT ON 2026-09-29. sairnbiz.html:4959 read

    return {fy:c.fy||d.fy, ot:c.ot||d.ot, terms:c.terms||d.terms};

with `d.ot === 40`. `0` and `''` are falsy, so a user who typed 0 -- or cleared
the field -- had their value replaced by 40 BEFORE the validator ran. The
validator's own `n<=0` branch was unreachable for exactly those two values, and
the note that exists to warn about a rejected setting compared 40 against 40
and said nothing.

WHAT MADE IT EXPENSIVE IS WHERE IT LIVED. Four existing test arms drove the
validator directly with a raw value and all four passed: the substitution
happened ONE LAYER ABOVE where every arm entered. So the class this scanner
hunts is not "a falsy coalesce" -- it is "a getter that substitutes a default
before validation can see the input".

── THE DISCRIMINATION THAT MATTERS ─────────────────────────────────────────
Most `x || default` in this repo are harmless and flagging them would bury the
one that is not. The scanner's rule:

  FLAG    the default is a NON-ZERO numeric literal -- a typed 0 becomes that
          number, which is a different value, silently
  CLEAR   the default is 0 or 0.0 -- a typed 0 becomes 0, no information lost
  CLEAR   the default is a string -- '' genuinely means unset for a fiscal-year
          name, and there is no rejectable empty string there
  CLEAR   `??` with any default -- it substitutes on null/undefined ONLY, which
          is the correct operator and the shape the fix uses
  FLAG    `if (!x)` followed by a numeric assignment to x

── THE ARMS ────────────────────────────────────────────────────────────────
C1  the exact pre-fix sairnbiz shape                 -> MUST be flagged
C2  the post-fix hasOwnProperty shape                -> MUST NOT be flagged
C3  `x || 0`                                          -> MUST NOT be flagged
C4  `name || 'Untitled'`                              -> MUST NOT be flagged
C5  `if (!count) count = 10;`                         -> MUST be flagged
C6  the defect shape inside a COMMENT                 -> MUST NOT be flagged
C7  the defect shape inside a STRING LITERAL          -> MUST NOT be flagged
C8  `x ?? 40`                                         -> MUST NOT be flagged
C9  Python `x = cfg.get('n') or 40`                    -> MUST be flagged
C10 Python `x = cfg.get('n', 40)`                      -> MUST NOT be flagged
C11 ABLATION on the real repo: re-introduce
    `ot:c.ot||d.ot` into a COPY of sairnbiz.html      -> MUST be flagged, and
    the unmodified file at that site MUST NOT be

C6 AND C7 ARE THE RECURRING CLASS. This is the seventh instance on this
platform of a predicate satisfiable by comment or string-constant text rather
than by behaviour, and it is being designed out at the start rather than found
by the next sweep.

C11 IS THE ONE THAT PROVES THE REST. A scanner run only on code that is already
fixed cannot distinguish "clean" from "blind". Per the twelfth cross-domain
discipline: reintroduce ONE named defect into otherwise-clean code and measure
what the scanner alone catches.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'numeric_default_coalesce_scan.py')

PASS, FAIL = [], []


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append(name)
    print('%-4s %-62s %s' % ('ok' if ok else 'FAIL', name, detail))


def scan(path):
    p = subprocess.run([sys.executable, TOOL, '--file', path],
                       cwd=REPO, capture_output=True, text=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


if not os.path.isfile(TOOL):
    print('COULD NOT RUN -- tools/numeric_default_coalesce_scan.py does not exist.')
    print('That is not a pass. Every arm below is unrun.')
    sys.exit(2)

FIXTURES = [
    ('C1 the pre-fix sairnbiz shape is flagged', '.js', True, '''\
function sbCfg(){
  var d={fy:'January',ot:40,terms:'Net 30'};
  var c=ld('sb_cfg',null);
  if(!c) return d;
  return {fy:c.fy||d.fy, ot:c.ot||d.ot, terms:c.terms||d.terms};
}
'''),
    ('C2 the post-fix hasOwnProperty shape is not flagged', '.js', False, '''\
function sbCfg(){
  var d={fy:'January',ot:40,terms:'Net 30'};
  var c=ld('sb_cfg',null);
  if(!c) return d;
  var hasOt=Object.prototype.hasOwnProperty.call(c,'ot') && c.ot!==null && c.ot!==undefined;
  return {fy:c.fy||d.fy, ot:hasOt?c.ot:d.ot, terms:c.terms||d.terms};
}
'''),
    ('C3 a zero default is not flagged', '.js', False, '''\
function total(){ var n = cfg.count || 0; return n * 2; }
var pad = opts.pad || 0;
'''),
    ('C4 a string default is not flagged', '.js', False, '''\
var name = row.name || 'Untitled';
var fy = c.fy || 'January';
'''),
    ('C5 if-not on a number with a numeric assignment is flagged', '.js', True, '''\
function page(){
  var count = opts.count;
  if (!count) count = 10;
  return count;
}
'''),
    ('C6 the shape inside a comment is not flagged', '.js', False, '''\
// This used to read ot: c.ot || 40 and a typed 0 became 40. Fixed.
/* also: var n = cfg.n || 168; was the old line */
var n = (cfg.n === undefined) ? 168 : cfg.n;
'''),
    ('C7 the shape inside a string literal is not flagged', '.js', False, '''\
var help = "the old code was: ot = c.ot || 40, which swallowed a typed zero";
var msg = 'threshold = c.ot || 40';
'''),
    ('C8 nullish coalescing is not flagged', '.js', False, '''\
var ot = c.ot ?? 40;
var hours = cfg.hours ?? 168;
'''),
    # C8b is the real stonedesk.html:31807 shape, reduced. An ODD BACKTICK in a
    # comment ran on as a template literal through the NEXT comment's `//`,
    # blanked it, closed at the first backtick on that line, and left
    # `(x.rate||28)` looking like live code. The first stripper reported two
    # comments on stonedesk.html as defects because of it.
    ('C8b an odd backtick in a comment does not leak the next comment', '.js',
     False, '''\
// the six sites were the payroll KPI, the `summary row
// `(x.hrs||0)*(x.rate||28)` appeared at six sites: the payroll KPI,
//   * `'Headcount: ' + (p.headcount || 1)` asserted a one-person shop
var n = (cfg.n === undefined) ? 168 : cfg.n;
'''),
    ('C9 python `or` with a nonzero numeric default is flagged', '.py', True, '''\
def threshold(cfg):
    n = cfg.get('ot') or 40
    return n
'''),
    ('C10 python dict.get with a default is not flagged', '.py', False, '''\
def threshold(cfg):
    n = cfg.get('ot', 40)
    return n
'''),
]

for name, ext, want_flag, body in FIXTURES:
    d = tempfile.mkdtemp(prefix='numeric_coalesce_probe_')
    try:
        p = os.path.join(d, 'fixture' + ext)
        io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
        rc, out = scan(p)
        if want_flag:
            check(name, rc == 1, 'exit=%d' % rc)
        else:
            check(name, rc == 0, 'exit=%d\n%s' % (rc, out if rc else ''))
    finally:
        shutil.rmtree(d, ignore_errors=True)

# ── C11 -- the ablation, on the real file ───────────────────────────────────
REAL = os.path.join(REPO, 'sairnbiz.html')
FIXED = 'ot:hasOt?c.ot:d.ot'
BROKEN = 'ot:c.ot||d.ot'
if not os.path.isfile(REAL):
    check('C11 ablation on sairnbiz.html', False, 'sairnbiz.html is absent')
else:
    src = io.open(REAL, encoding='utf-8', newline='').read()
    if src.count(FIXED) != 1:
        check('C11 ablation on sairnbiz.html', False,
              'the fixed shape %r appears %d times, not once -- the probe\'s '
              'own anchor is stale' % (FIXED, src.count(FIXED)))
    else:
        d = tempfile.mkdtemp(prefix='numeric_coalesce_ablate_')
        try:
            clean = os.path.join(d, 'sairnbiz.html')
            io.open(clean, 'w', encoding='utf-8', newline='').write(src)
            rc_clean, out_clean = scan(clean)

            broken = os.path.join(d, 'sairnbiz_ablated.html')
            io.open(broken, 'w', encoding='utf-8', newline='').write(
                src.replace(FIXED, BROKEN))
            rc_broken, out_broken = scan(broken)

            check('C11a the real sairnbiz.html is clean at the fixed site',
                  BROKEN not in out_clean, 'exit=%d' % rc_clean)
            check('C11b re-introducing ot:c.ot||d.ot IS flagged',
                  rc_broken == 1 and 'd.ot' in out_broken,
                  'exit=%d' % rc_broken)
        finally:
            shutil.rmtree(d, ignore_errors=True)

print('')
print('%d passed, %d failed' % (len(PASS), len(FAIL)))
for f in FAIL:
    print('  FAILED: %s' % f)
sys.exit(1 if FAIL else 0)
