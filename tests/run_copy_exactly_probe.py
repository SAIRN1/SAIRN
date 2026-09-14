"""Does copy_exactly_check actually detect drift, and does it refuse to guess?

    python tests/run_copy_exactly_probe.py

The arms that matter are not "does it produce output". They are:

  * it separates a REFLOWED line from real drift. Three false alarms on this
    platform came from calling a whitespace difference a change, and a checker
    that cries wolf on line wrapping is one people switch off.
  * it FAILS CLOSED. A missing spec, a missing app, a renamed heading and a
    block with no functions are four different could-not-check states and none
    of them is a pass -- PR 1.11, and "zero targets is not a clean sweep".
  * ARM 1 PROVES IT CAN FIRE against the real repository, so the fixture arms
    are not the only thing holding it up.
"""
import contextlib
import io as _io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
os.chdir(REPO)

import copy_exactly_check as cec   # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  ok   ' if cond else '  FAIL ') + name
          + (('\n        ' + str(detail)) if (detail and not cond) else ''))


def run_with(spec_text, app_text, argv=()):
    """Run main() against supplied file contents. Returns (rc, stdout)."""
    real = cec.read

    def fake(rel):
        if rel == cec.SPEC:
            return spec_text
        if rel == cec.APP:
            return app_text
        return real(rel)
    cec.read = fake
    buf = _io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = cec.main(list(argv))
    finally:
        cec.read = real
    return rc, buf.getvalue()


BLOCK = """## SAIRN CLAUDE ENGINE -- Copy Exactly

```javascript
function svStore(k,v){try{localStorage.setItem('sv_'+k,JSON.stringify(v));}catch(e){}}
function escHtml(s){return String(s||'').replace(/&/g,'&amp;');}
```
"""

print('--- 1. it fires against the REAL repository ---')
rc, out = run_with(cec.read(cec.SPEC), cec.read(cec.APP))
check('1a  the real run completes', rc == 0, rc)
check('1b  and it reports DRIFT rather than a clean sweep -- if this ever goes '
      'to 0 the spec was fixed, and the arm should be re-read not deleted',
      'DIFFERS 4' in out or 'DIFFERS 0' not in out, out[-400:])

print('\n--- 2. a target identical to the spec is identical ---')
same_app = 'function svStore(k,v){try{localStorage.setItem(\'sv_\'+k,JSON.stringify(v));}catch(e){}}\n' \
           'function escHtml(s){return String(s||\'\').replace(/&/g,\'&amp;\');}'
rc, out = run_with(BLOCK, same_app)
check('2a  it runs', rc == 0, rc)
check('2b  both functions come back identical', 'identical 2' in out, out)
check('2c  and nothing is reported as drift', 'DIFFERS 0' in out, out)

print('\n--- 3. REFLOWED IS NOT DRIFT ---')
reflowed = 'function svStore(k,v){\n  try{ localStorage.setItem(\'sv_\'+k, JSON.stringify(v)); }\n  catch(e){}\n}\n' \
           'function escHtml(s){return String(s||\'\').replace(/&/g,\'&amp;\');}'
rc, out = run_with(BLOCK, reflowed)
check('3a  a re-wrapped body is REFLOWED, not DIFFERS', 'reflowed 1' in out, out)
check('3b  and it is not counted as drift', 'DIFFERS 0' in out, out)

print('\n--- 4. a real change IS drift ---')
changed = 'function svStore(k,v){return st(\'sv_\'+k,v);}\n' \
          'function escHtml(s){return String(s||\'\').replace(/&/g,\'&amp;\');}'
rc, out = run_with(BLOCK, changed)
check('4a  a substantive change is DIFFERS', 'DIFFERS 1' in out, out)
check('4b  CONTROL: arm 3 and arm 4 gave different answers, so 3 is not '
      'passing because everything reads as reflowed',
      'reflowed 1' in run_with(BLOCK, reflowed)[1]
      and 'reflowed 0' in out, out)
check('4c  and it says the block would reintroduce it',
      'reintroduce' in out, out)

print('\n--- 5. a missing function is ABSENT, not silently skipped ---')
rc, out = run_with(BLOCK, 'function escHtml(s){return String(s||\'\').replace(/&/g,\'&amp;\');}')
check('5a  the missing one is reported', 'absent 1' in out, out)

print('\n--- 6. FOUR WAYS IT MUST REFUSE, and none of them is a pass ---')
rc, out = run_with(None, same_app)
check('6a  a missing SPEC exits 2', rc == 2, rc)
check('6b  and says COULD NOT CHECK', 'COULD NOT CHECK' in out, out)

rc, out = run_with(BLOCK, None)
check('6c  a missing APP exits 2', rc == 2, rc)

rc, out = run_with('# a spec with no such heading\n\nnothing here\n', same_app)
check('6d  a RENAMED heading exits 2 rather than reporting a clean sweep -- '
      'the block being gone is the one case a passing checker would hide',
      rc == 2, rc)
check('6e  and it says the tool is no longer looking at anything',
      'no longer looking' in out, out)

rc, out = run_with('## Copy Exactly\n\n```javascript\nvar X=1;\n```\n', same_app)
check('6f  a block with NO FUNCTIONS exits 2 -- zero targets is not a clean '
      'sweep', rc == 2, rc)

print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
