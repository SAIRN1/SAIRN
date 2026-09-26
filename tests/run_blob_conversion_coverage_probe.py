"""tools/blob_conversion_coverage.py must recognise every shape it claims to,
must not score an unconverted site as converted, and must refuse rather than pass.

    python tests/run_blob_conversion_coverage_probe.py

WHY THIS PROBE IS UNUSUALLY SUSPICIOUS OF ITS SUBJECT. The tool exists because a
completion proof used a grep pattern that could not match the sites it left
behind. Its own first two versions made the SAME class of mistake twice:

  1. a `[^,\\n]+` capture truncated `Object.assign({}, payload, {...})` at the
     first comma, so every inline spread scored BUILT -- immune -- and SPREAD
     read 0.
  2. a FILE-WIDE set of storedBlob-bound names scored the unconverted rf_claims
     write as converted, because `dataBlob` is bound twice in api/sd-data.js --
     once as a spread at 7111 and once as a real conversion at 7208.

Both were found by reading its output against the file, not by this probe, which
is exactly why the arms below pin the shapes rather than the totals. A total is
the thing that looked right both times.
"""
CONTROLS_FOR = ['blob_conversion_coverage.py']

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_REL = os.path.join('tools', 'blob_conversion_coverage.py')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def sandbox(js, pin=None):
    d = tempfile.mkdtemp(prefix='sairn-blobcov-')
    os.makedirs(os.path.join(d, 'tools'))
    os.makedirs(os.path.join(d, 'docs'))
    os.makedirs(os.path.join(d, 'api'))
    shutil.copy(os.path.join(REPO, TOOL_REL), os.path.join(d, TOOL_REL))
    io.open(os.path.join(d, 'api', 'demo.js'), 'w', encoding='utf-8',
            newline='\n').write(js)
    if pin is not None:
        io.open(os.path.join(d, 'docs', 'blob-conversion-coverage.json'), 'w',
                encoding='utf-8', newline='\n').write(json.dumps(pin) + '\n')
    return d


def run(d, *args):
    r = subprocess.run([sys.executable, TOOL_REL] + list(args), cwd=d,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def counts(out):
    """{KIND: n} parsed from the tool's own table."""
    got = {}
    for line in out.split('\n'):
        p = line.split()
        if len(p) == 2 and p[0] in ('CONVERTED', 'RAW', 'SPREAD', 'NESTED', 'BUILT'):
            try:
                got[p[0]] = int(p[1])
            except ValueError:
                pass
    return got


PIN0 = {'unconverted': 0, 'converted': 0}

# ---------------------------------------------------------------------------
print('1. EVERY SHAPE IS RECOGNISED AS ITSELF -- one file, five shapes, no totals')
JS = """
const { storedBlob } = require('./_lib/blob');
async function h(payload, licHash) {
  const a = storedBlob(payload, ['id']);
  await fetch(u, { body: JSON.stringify({ license_hash: licHash, data: a }) });
  await fetch(u, { body: JSON.stringify({ license_hash: licHash, data: payload }) });
  const b = Object.assign({}, payload, { state: 'OH' });
  await fetch(u, { body: JSON.stringify({ license_hash: licHash, data: b }) });
  await fetch(u, { body: JSON.stringify({ license_hash: licHash, data: payload.data }) });
  await fetch(u, { body: JSON.stringify({ license_hash: licHash, data: { x: payload.x } }) });
}
"""
d = sandbox(JS, PIN0)
rc, out = run(d)
c = counts(out)
check('a storedBlob-bound name is CONVERTED', c.get('CONVERTED') == 1, str(c))
check('a bare `data: payload` is RAW', c.get('RAW') == 1, str(c))
check('an Object.assign({}, payload, {...}) bound to a name is SPREAD -- the '
      'shape a comma-truncating capture scored BUILT', c.get('SPREAD') == 1, str(c))
check('`data: payload.data` is NESTED, its own shape', c.get('NESTED') == 1, str(c))
check('a field-by-field literal is BUILT and NOT counted as a gap',
      c.get('BUILT') == 1, str(c))
check('...so UNCONVERTED is RAW+SPREAD only -- 2, not 3 and not 5',
      'UNCONVERTED (RAW + SPREAD): 2' in out, out[:600])
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n2. THE INLINE SPREAD, WHICH IS THE ONE ITS FIRST VERSION MISSED')
JS = """
async function h(payload, licHash) {
  await fetch(u, { body: JSON.stringify({ license_hash: licHash,
    data: Object.assign({}, payload, { recorded_by: session.employee_id }) }) });
}
"""
d = sandbox(JS, PIN0)
rc, out = run(d)
check('an INLINE Object.assign({}, payload, {...}) is SPREAD, not BUILT -- the '
      'comma inside the braces does not end the expression',
      counts(out).get('SPREAD') == 1, str(counts(out)))
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n3. THE SAME NAME BOUND TWICE -- the real defect, reproduced')
# api/sd-data.js binds `dataBlob` as a spread at 7111 and as a real conversion at
# 7208. A file-wide name set scored the FIRST, unconverted, write as converted.
JS = """
const { storedBlob } = require('./_lib/blob');
async function a(payload, licHash) {
  const dataBlob = Object.assign({}, payload, { m: 1 });
  await fetch(u, { body: JSON.stringify({ license_hash: licHash, data: dataBlob }) });
}
async function b(payload, licHash) {
  const dataBlob = storedBlob(payload, ['id']);
  await fetch(u, { body: JSON.stringify({ license_hash: licHash, data: dataBlob }) });
}
"""
d = sandbox(JS, PIN0)
rc, out = run(d)
c = counts(out)
check('the EARLIER binding is SPREAD and the later one CONVERTED -- one each, '
      'because the nearest binding above the use site is the one in scope',
      c.get('SPREAD') == 1 and c.get('CONVERTED') == 1, str(c))
check('...so the unconverted one is still counted: UNCONVERTED is 1, not 0',
      'UNCONVERTED (RAW + SPREAD): 1' in out, out[:600])
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n3b. A RE-BINDING TO SOMETHING ELSE CLEARS THE OLD VERDICT')
# The third defect of the same family. `merged` is a payload spread at
# api/sd-data.js:2824 and, 800 lines later, `Object.assign({}, curData, {...})`
# -- curData, the STORED row, not the request. The second binding matched no
# rule, the lookup walked past it to the first, and a PATCH that never touches
# the payload was reported as an unconverted payload spread. Overcounting is not
# the safe direction; it is the same tool wrong with more confidence.
JS = """
async function a(payload, licHash) {
  const merged = Object.assign({}, payload, { s: 1 });
  await fetch(u, { body: JSON.stringify({ license_hash: licHash, data: merged }) });
}
async function b(curData, licHash) {
  const merged = Object.assign({}, curData, { promoted_at: '' });
  await fetch(u, { body: JSON.stringify({ license_hash: licHash, data: merged }) });
}
"""
d = sandbox(JS, PIN0)
rc, out = run(d)
c = counts(out)
check('the payload spread is SPREAD and the curData merge is NOT -- 1, not 2',
      c.get('SPREAD') == 1, str(c))
check('...and the curData merge is BUILT, which is the honest answer: it never '
      'carried the request payload at all', c.get('BUILT') == 1, str(c))
check('...so UNCONVERTED is 1 -- the tool does not inflate its own remainder',
      'UNCONVERTED (RAW + SPREAD): 1' in out, out[:600])
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n4. A CORRECT OVERRIDE SITE IS NOT A GAP -- the other direction')
# `Object.assign(storedBlob(...), {...})` is stripped THEN overridden: spread-
# SHAPED and correct. Asking SPREAD before CONVERTED would fail every branch
# that has to re-apply a normalised value after stripping.
JS = """
const { storedBlob } = require('./_lib/blob');
async function h(payload, licHash) {
  const body = Object.assign(storedBlob(payload, ['id']), { state: 'OH' });
  await fetch(u, { body: JSON.stringify({ license_hash: licHash, data: body }) });
}
"""
d = sandbox(JS, PIN0)
rc, out = run(d)
c = counts(out)
check('strip-then-override is CONVERTED, not SPREAD', c.get('CONVERTED') == 1
      and not c.get('SPREAD'), str(c))
check('...and UNCONVERTED is 0, so the fix pattern does not read as a gap',
      'UNCONVERTED (RAW + SPREAD): 0' in out, out[:600])
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n5. A `data:` WITH NO license_hash BESIDE IT IS NOT A STORED BLOB')
JS = """
function local(payload) {
  const opts = Object.assign({}, payload, { on_date: '2026-01-01' });
  return evaluate({ data: opts });
}
"""
d = sandbox(JS, PIN0)
rc, out = run(d)
check('a local object called data, with no scope key near it, is not counted -- '
      'api/sd-data.js has three of these passing args to engines',
      '0 stored-blob site(s)' in out or counts(out) == {}, out[:400])
check('...and zero sites is COULD NOT TELL, not a clean zero: the write-body '
      'shape moving must not read as "nothing to convert"',
      run(d)[0] == 2 and 'NOTHING was measured' in run(d)[1], 'exit=%s' % run(d)[0])
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n6. THE RATCHET MOVES IN ONE DIRECTION AND SAYS SO')
JS_TWO = """
async function h(payload, licHash) {
  await fetch(u, { body: JSON.stringify({ license_hash: licHash, data: payload }) });
  await fetch(u, { body: JSON.stringify({ license_hash: licHash, data: payload }) });
}
"""
d = sandbox(JS_TWO, {'unconverted': 2, 'converted': 0})
rc, out = run(d)
check('at the pinned number it is OK and exits 0', rc == 0 and 'OK -- no worse' in out,
      'exit=%s :: %s' % (rc, out[-300:]))
check('...and says on the SAME run that a ratchet is not a pass',
      'A RATCHET IS NOT A PASS' in out, out[-500:])
shutil.rmtree(d, ignore_errors=True)

d = sandbox(JS_TWO, {'unconverted': 1, 'converted': 0})
rc, out = run(d)
check('a NEW raw blob write is a REGRESSION and exits 1',
      rc == 1 and 'REGRESSION' in out, 'exit=%s :: %s' % (rc, out[-300:]))
shutil.rmtree(d, ignore_errors=True)

d = sandbox(JS_TWO, {'unconverted': 5, 'converted': 0})
rc, out = run(d)
check('a CONVERSION reads as IMPROVED and asks to be re-pinned, exit 0',
      rc == 0 and 'IMPROVED' in out and '--repin' in out,
      'exit=%s :: %s' % (rc, out[-300:]))
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n7. AN ABSENT OR CORRUPT PIN IS EXIT 2, NEVER 0')
d = sandbox(JS_TWO, None)
rc, out = run(d)
check('no pin file -> exit 2 COULD NOT TELL', rc == 2 and 'COULD NOT TELL' in out,
      'exit=%s' % rc)
check('...and it says the numbers were measured but nothing was JUDGED',
      'nothing was JUDGED' in out, out[-300:])
shutil.rmtree(d, ignore_errors=True)

d = sandbox(JS_TWO, PIN0)
io.open(os.path.join(d, 'docs', 'blob-conversion-coverage.json'), 'w',
        encoding='utf-8', newline='\n').write('{ not json')
rc, out = run(d)
check('an unparseable pin -> exit 2', rc == 2 and 'will not parse' in out,
      'exit=%s' % rc)
io.open(os.path.join(d, 'docs', 'blob-conversion-coverage.json'), 'w',
        encoding='utf-8', newline='\n').write('{"converted": 3}')
rc, out = run(d)
check('a pin with NO integer `unconverted` -> exit 2, not a comparison against '
      'a missing field', rc == 2 and 'nothing to compare' in out, 'exit=%s' % rc)
shutil.rmtree(d, ignore_errors=True)

d = sandbox(JS_TWO, PIN0)
shutil.rmtree(os.path.join(d, 'api'))
rc, out = run(d)
check('api/ absent -> exit 2, and it says nothing was scanned',
      rc == 2 and 'nothing was scanned' in out, 'exit=%s' % rc)
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n8. AND THE REAL api/ -- so the arms above are not a fixture dialect')
before = [(p, io.open(p, 'rb').read(), os.path.getmtime(p)) for p in
          [os.path.join(REPO, 'api', 'sd-data.js'),
           os.path.join(REPO, 'api', '_lib', 'blob.js')]]
rc, out = run(REPO)
check('it runs against the shipping api/ and exits 0 or 1, never 2',
      rc in (0, 1), 'exit=%s :: %s' % (rc, out[-300:]))
c = counts(out)
# THIS ARM ASKED FOR RAW > 0 *AND* SPREAD > 0 AND THEN THE FIX MADE IT FALSE.
# Every SPREAD site in api/ was converted on 2026-09-26, so SPREAD is legitimately
# 0 and an arm requiring it went red over work having been DONE. It is rewritten
# rather than loosened: what it is actually for is "the classifier still sees real
# shapes in the real tree, so the fixtures are not a private dialect", and RAW and
# CONVERTED both being non-zero says that. SPREAD's recognition is pinned on
# fixtures in sections 1, 2, 3 and 3b, where it cannot be zeroed by a conversion.
check('it finds real RAW sites in the shipping tree -- 0 here would mean the '
      'classifier has stopped seeing the commonest unconverted shape',
      c.get('RAW', 0) > 0, str(c))
check('...and real CONVERSIONS too, so it is not just calling everything a gap',
      c.get('CONVERTED', 0) > 0, str(c))
check('...and the two account for real sites, so BUILT is not swallowing the tree',
      c.get('RAW', 0) + c.get('CONVERTED', 0) >= 20, str(c))
after = [(p, io.open(p, 'rb').read(), os.path.getmtime(p)) for p in
         [os.path.join(REPO, 'api', 'sd-data.js'),
          os.path.join(REPO, 'api', '_lib', 'blob.js')]]
check('IT WROTE NOTHING to api/ -- identical bytes AND unchanged mtimes, so a '
      'write-then-restore would fail this too', before == after,
      'an api file was written')

print('\n%s  run_blob_conversion_coverage_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
