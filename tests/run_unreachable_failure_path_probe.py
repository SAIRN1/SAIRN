"""Would the unreachable-failure-path scan have caught the defect it was built for?

    python tests/run_unreachable_failure_path_probe.py

A SCAN THAT REPORTS ZERO IS WORTH EXACTLY WHAT ITS ABLATION IS WORTH. This one
reports CONFIRMED 0 across 102 files, and that number means nothing on its own --
a scan that cannot see the defect it was written for reports zero on a broken
platform just as cheerfully as on a clean one.

So section 2 is the arm that matters: it takes the REAL stonedesk.html, restores
the REAL pre-fix `slabSyncOne()` body into it, and demands the scan report the
pair. The caller -- `pcToggleSlab()`, with its `ok === false` branch -- is NOT
mutated, because the caller was never wrong. It is still in the file exactly as it
was when the branch could not fire, which is what makes this a mutation of one
half of a real disagreement rather than a synthetic fixture.

Section 3 is the other direction on the same file: unmutated, the scan reports
nothing. Without it the mutation arm would pass for a scan that reports
everything.

Section 4 pins the two false-positive classes that the scan's FIRST REAL RUN
produced, because both were fixed and both would come back silently:
an expression-bodied arrow, and a function name defined more than once.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import unreachable_failure_path_scan as U                          # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


# ── 1. THE TOOL'S OWN BLIND LOCK RUNS FIRST ─────────────────────────────────
print('unreachable failure path -- would it have caught the one it was built for?')
print('\n1. the tool\'s own fixture lock, run through its CLI so the exit code counts')
r = subprocess.run([sys.executable, '-X', 'utf8',
                    os.path.join(REPO, 'tools', 'unreachable_failure_path_scan.py'),
                    '--fixtures'],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO)
check('--fixtures exits 0 with every arm green', r.returncode == 0,
      (r.returncode, (r.stdout or '')[-500:]))
check('...and it actually ran arms rather than printing a header',
      (r.stdout or '').count('  ok   ') >= 6, (r.stdout or '')[:300])

# ── 2. THE ARM THAT MATTERS ─────────────────────────────────────────────────
print('\n2. THE ABLATION: restore the real pre-fix slabSyncOne into the real file')

SD = os.path.join(REPO, 'stonedesk.html')
src = io.open(SD, encoding='utf-8', errors='replace').read()

# The FIXED body, taken from the file rather than re-typed -- from `async function
# slabSyncOne(slab){` to the closing brace at column 0.
start = src.find('async function slabSyncOne(slab){')
check('slabSyncOne is still in stonedesk.html under that name -- if this fails '
      'the function was renamed and this whole probe is asserting nothing',
      start > 0, start)

PRE_FIX = '\n'.join([
    'async function slabSyncOne(slab){',
    "  if(typeof sdData!=='function') return;",
    '  var lic=slabLicKey(); if(!lic) return;',
    '  try{',
    "    await sdData('write','slabs',slab);",
    '  }catch(e){}',
    '}'])

if start > 0:
    end = src.find('\n}\n', start)
    check('...and its body terminates at a column-0 brace, so the mutation '
          'replaces the whole function and not part of one', end > start,
          (start, end))
    if end > start:
        mutated = src[:start] + PRE_FIX + src[end + 3:]
        check('precondition: the mutation actually changed the file',
              mutated != src)
        c, a, sk = U.scan_text(mutated, 'stonedesk.html[MUTATED]')
        hit = [f for f in c if f['fn'] == 'slabSyncOne']
        check('THE ARM THAT MATTERS: with the pre-fix body restored, the scan '
              'reports slabSyncOne as CONFIRMED unreachable -- the caller was '
              'NOT touched, so this is one half of a real disagreement',
              len(hit) == 1, (c, a))
        if hit:
            check('...and it names the caller\'s line, not just the callee -- a '
                  'finding a reader cannot locate is a finding nobody checks',
                  hit[0]['test_line'] > 0 and hit[0]['fn_line'] > 0, hit[0])
            check('...and it says the branch CANNOT be taken rather than "may not"',
                  'false' in hit[0]['how'], hit[0])

# ── 3. THE OTHER DIRECTION, ON THE SAME FILE ────────────────────────────────
print('\n3. and the real file, unmutated, reports nothing')

c0, a0, sk0 = U.scan_text(src, 'stonedesk.html')
check('the shipped stonedesk.html has NO confirmed unreachable failure path -- '
      'without this arm the one above would pass for a scan that reports '
      'everything', not c0, c0)

# ── 4. THE TWO FALSE-POSITIVE CLASSES ITS FIRST REAL RUN PRODUCED ───────────
print('\n4. the two false positives from the first real run, pinned so they cannot '
      'come back')

ARROW = """
function dcRoomPolyBoundsCenter() {
  const xs=dcPoly.map(p=>p.x), ys=dcPoly.map(p=>p.y);
  return { x:(Math.min(...xs)+Math.max(...xs))/2, y:(Math.min(...ys)+Math.max(...ys))/2 };
}
function caller(){ var center = dcRoomPolyBoundsCenter(); use(center); }
"""
c1, a1, _ = U.scan_text(ARROW, 'fixture')
check('an EXPRESSION-BODIED ARROW does not make its enclosing function read as '
      'bare. The first version looked for the next `{` after the `=>` and found '
      'the function\'s OWN `return { x:..., y:... }`, blanked it, and reported '
      'a function with a real return', not c1 and not a1, (c1, a1))

REDEF = """
function render(){ return '<div>'; }
function other(){ var system = render(); use(system); }
function render(){ return; }
"""
c2, a2, sk2 = U.scan_text(REDEF, 'fixture')
check('a name DEFINED MORE THAN ONCE is refused rather than matched by '
      'position -- stonedesk.html defines `render` 23 times in 23 unrelated '
      'IIFEs, and pairing a caller at :30570 with a definition at :38046 is '
      'arithmetic, not analysis',
      not c2 and not a2 and any(n == 'render' for n, _l in sk2), (c2, a2, sk2))
check('...and the refusal is REPORTED rather than dropped -- a scan silently '
      'declining to judge is indistinguishable from one that judged and found '
      'nothing', bool(sk2), sk2)

print('')
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
    sys.exit(1)
print('ALL ARMS PASS')
