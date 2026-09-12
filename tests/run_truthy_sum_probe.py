"""Probe tools/truthy_sum_check.py by attacking it -- every arm plants a defect
or a look-alike and demands the right answer.

    python tests/run_truthy_sum_probe.py

The arms worth having are not "does it find `+ (x || 0)`". Anyone would write
that. They are:

  * MULTIPLICATION IS SAFE. `2 * ("3" || 0)` is 6 because `*` has no string
    overload; `0 + ("3" || 0)` is "03" because `+` does. A checker that flagged
    both would be wrong about half of what it reports, and would train people
    to ignore it.
  * Number()/parseFloat/parseInt around the term means somebody already thought
    about it, and must go silent.
  * THE PATTERN QUOTED IN A COMMENT is not code.
  * THE PATTERN QUOTED IN A STRING is not code either, and that arm exists
    because the first version of the tool reported exactly this against its own
    subject: the refusal message in api/_lib/dental-ledger.js quotes the
    pattern verbatim to explain it. Fifty-two of the first 193 hits were prose.
  * A `//` INSIDE A URL must not eat the rest of the line -- the failure the
    comment-quote checker's own first version shipped with.
  * THE KEY IS FILE+FIELD, NOT A LINE NUMBER. Inserting a line above a
    grandfathered occurrence must not resurrect it; this repo has already been
    bitten by a line-keyed exemption file that a one-line import invalidated.
  * A MISSING BASELINE must report everything rather than pass quietly.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join(REPO, 'tools', 'truthy_sum_check.py')

fails = 0


def check(label, actual, expected):
    global fails
    if actual == expected:
        print('  ok    %s' % label)
        return True
    fails += 1
    print('FAIL  %s\n        expected %r\n        actual   %r'
          % (label, expected, actual))
    return False


def build(tmp, files, baseline=None):
    os.makedirs(os.path.join(tmp, 'tools'), exist_ok=True)
    shutil.copy(TOOL, os.path.join(tmp, 'tools', 'truthy_sum_check.py'))
    for name, body in files.items():
        full = os.path.join(tmp, name)
        if os.path.dirname(full):
            os.makedirs(os.path.dirname(full), exist_ok=True)
        io.open(full, 'w', encoding='utf-8', newline='\n').write(body)
    if baseline is not None:
        io.open(os.path.join(tmp, 'tools', 'truthy_sum_baseline.json'), 'w',
                encoding='utf-8').write(json.dumps({'grandfathered': baseline}))
    subprocess.run(['git', 'init', '-q'], cwd=tmp, capture_output=True)
    subprocess.run(['git', 'add', '-A'], cwd=tmp, capture_output=True)


def run(tmp, *args):
    r = subprocess.run([sys.executable,
                        os.path.join(tmp, 'tools', 'truthy_sum_check.py')]
                       + list(args), cwd=tmp, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


tmp = tempfile.mkdtemp(prefix='truthysum-')
n = [0]


def case(name, files, baseline=None, args=()):
    n[0] += 1
    d = os.path.join(tmp, '%02d-%s' % (n[0], name))
    os.makedirs(d)
    build(d, files, baseline)
    return run(d, *args)

# ── 1. the defect itself ──────────────────────────────────────────────────
rc, out = case('finds-it', {
    'app.js': 'var t = rows.reduce(function (s, o) { return s + (o.total || 0); }, 0);\n'})
check('an uncoerced + (x || 0) is reported', rc, 1)
check('and the field is named', 'o.total' in out, True)
check('and the file and line are named', 'app.js:1' in out, True)

# ── 2. MULTIPLICATION IS SAFE -- the arm that keeps this trustworthy ──────
rc, out = case('multiplication', {
    'app.js': 'var v = rows.reduce(function (s, i) { return s + Number(i.qty || 0) * (i.cost || 0); }, 0);\n'})
check('a `*` term alone is NOT reported -- * coerces, + does not',
      'i.cost' in out, False)

# ── 3. already coerced ────────────────────────────────────────────────────
for fn in ('Number', 'parseFloat', 'parseInt'):
    rc, out = case('coerced-' + fn, {
        'app.js': 'var t = rows.reduce(function (s, o) { return s + %s(o.total || 0); }, 0);\n' % fn})
    check('%s(...) around the term goes silent' % fn, (rc, 'o.total' in out),
          (0, False))

# ── 4. the pattern in a COMMENT is not code ───────────────────────────────
rc, out = case('in-comment', {
    'app.js': '// the old code was s + (o.total || 0) and it concatenated\nvar t = 1;\n'})
check('the pattern quoted in a // comment is NOT reported', rc, 0)
rc, out = case('in-block-comment', {
    'app.js': '/*\n * s + (o.total || 0)\n */\nvar t = 1;\n'})
check('...nor in a /* */ comment', rc, 0)

# ── 5. the pattern in a STRING is not code either ─────────────────────────
#     The arm that exists because the tool did exactly this on its first run.
rc, out = case('in-string', {
    'app.js': "var msg = 'the YTD reduce is s + (o.total || 0), which concatenates';\n"})
check('the pattern quoted in a STRING is NOT reported', rc, 0)
rc, out = case('in-template', {
    'app.js': 'var msg = `s + (o.total || 0)`;\n'})
check('...nor in a template literal', rc, 0)

# ── 6. a // inside a URL must not swallow the line ────────────────────────
rc, out = case('url', {
    'app.js': "var u = 'https://x.test/a'; var t = rows.reduce(function (s, o) { return s + (o.total || 0); }, 0);\n"})
check('a `//` inside a URL does not blind the rest of the line', rc, 1)
check('and the real occurrence after it is still found', 'o.total' in out, True)

# ── 7. THE KEY IS FILE+FIELD, NOT A LINE NUMBER ───────────────────────────
BODY = 'var t = rows.reduce(function (s, o) { return s + (o.total || 0); }, 0);\n'
BASE = {'app.js::o.total': 'grandfathered fixture'}
rc, out = case('baselined', {'app.js': BODY}, BASE)
check('a grandfathered occurrence is CLEAN', rc, 0)
rc, out = case('shifted', {'app.js': '\n\n\n\n' + BODY}, BASE)
check('...and stays clean after FOUR lines are inserted above it', rc, 0)
rc, out = case('new-field', {
    'app.js': BODY + 'var u = rows.reduce(function (s, o) { return s + (o.freight || 0); }, 0);\n'}, BASE)
check('a NEW field in the same file FAILS', rc, 1)
check('and only the new one is named',
      ('o.freight' in out, out.count('o.total ||') == 0), (True, True))
rc, out = case('new-file', {
    'app.js': BODY,
    'other.js': BODY}, BASE)
check('the SAME field in a different file FAILS -- the key is file+field',
      (rc, 'other.js' in out), (1, True))

# ── 8. a missing baseline must not pass quietly ───────────────────────────
rc, out = case('nobaseline', {'app.js': BODY})
check('with NO baseline file everything is reported', rc, 1)

# ── 9. the exclusions are real AND printed ────────────────────────────────
rc, out = case('excluded', {
    'app.js': 'var t = 1;\n',
    'archive/old.html': '<script>var t = rows.reduce(function (s, o) { return s + (o.total || 0); }, 0);</script>\n',
    'docs/skill-backups/x/viewer.html': '<script>var t = a + (b.c || 0);</script>\n'})
check('archive/ and docs/skill-backups/ are not scanned', rc, 0)
check('and the exclusion is PRINTED, not silent', 'not scanned' in out, True)

# ── 10. --full lists everything, marking what is new ──────────────────────
rc, out = case('full', {
    'app.js': BODY + 'var u = rows.reduce(function (s, o) { return s + (o.freight || 0); }, 0);\n'},
    BASE, args=('--full',))
check('--full lists both the grandfathered and the new one',
      ('o.total' in out, 'o.freight' in out), (True, True))

# ── 11. and the REAL repo is clean, since that is what it is for ──────────
r = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True, text=True)
check('the real SAIRN tree currently has no UNBASELINED occurrence', r.returncode, 0)
check('...and it really did look -- 135 occurrences inspected',
      'occurrences : 135' in r.stdout, True)

print()
if fails:
    print('%d FAILED' % fails)
    sys.exit(1)
print('ALL PASS -- a new uncoerced numeric fold cannot be added silently, and '
      'the tool does not report multiplication, coercion, comments or prose.')
