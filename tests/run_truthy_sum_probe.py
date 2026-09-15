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
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['truthy_sum_check.py']

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
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
                       + list(args), cwd=tmp, capture_output=True, text=True, encoding='utf-8', errors='replace')
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
r = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace')
check('the real SAIRN tree currently has no UNBASELINED occurrence', r.returncode, 0)
# A FLOOR, NOT AN EQUALITY (2026-09-13). This was `'occurrences : 135' in
# r.stdout`, and it went red the first time an ordinary commit added a matching
# line -- 140 by 2026-09-13, from two currency-label concatenations in
# stonedesk.html. The question this arm exists to answer is "did the scan
# actually look at anything, or did it report CLEAN over an empty result", and
# an exact count answers a different and unstable question. Same reasoning as
# MIN_TEST_FILES in tools/run_all_tests.py: a floor, never an equality, and it
# is not to be raised to clear a failure -- a DROP means the scanner stopped
# seeing files and is the thing worth failing on.
#
# AND IT FLOORS ON THE RAW MATCH COUNT, NOT THE CANDIDATE COUNT. The first
# version of this floor pinned `occurrences`, which is post-classification --
# splitting string-literal concatenation out the same day took it 140 -> 82 and
# the arm went red over a correctness improvement. `raw ... matches inspected`
# is the number that answers "did it look".
_m = re.search(r'matches inspected\s*:\s*(\d+)', r.stdout)
check('...and it really did look -- the raw match count is reported', bool(_m), True)
check('...and it is not a collapsed scan -- at least 100 raw matches seen',
      bool(_m) and int(_m.group(1)) >= 100, True)

# ── 12. a STRING LITERAL on the left is concatenation, not a fold ──────────
# The whole reason this section exists: before 2026-09-13 every currency label
# anyone added tripped the check and was answered with a baseline entry, which
# is a checker teaching people to write exemptions.
rc, out = case('string-literal-concat', {
    'app.js': "var h = '<td>$' + (x.ytd || 0) + '</td>';\n"})
check('a string-literal left operand is NOT reported',
      (rc, 'NEW OCCURRENCE' in out), (0, False))
check('...and it is COUNTED, not silently dropped',
      'not a fold, so not counted : 1' in out, True)
check('...and --full names it', 'x.ytd' in case('concat-full', {
    'app.js': "var h = '<td>$' + (x.ytd || 0) + '</td>';\n"}, args=('--full',))[1], True)

# ONLY AN IMMEDIATELY PRECEDING LITERAL. A variable that happens to hold a
# string is the HAZARD and is not derivable here, so it must still be reported.
rc, out = case('string-variable-left', {
    'app.js': 'var h = prefix + (x.ytd || 0);\n'})
check('a VARIABLE on the left is still reported -- it may hold a string', rc, 1)

# A call returning a string ends in `)`, not a quote. Conservative on purpose.
rc, out = case('call-returning-string', {
    'app.js': "var h = label('$') + (x.ytd || 0);\n"})
check('a call on the left is still reported -- over-reporting is the safe side', rc, 1)

# A template literal is a string literal too.
rc, out = case('template-literal', {
    'app.js': 'var h = `total ` + (x.ytd || 0);\n'})
check('a template literal on the left is NOT reported', rc, 0)

# ── 13. a baseline key nothing matches any more is REPORTED ───────────────
rc, out = case('stale-baseline', {
    'app.js': 'var t = rows.reduce(function (s, o) { return s + (o.total || 0); }, 0);\n'},
    baseline={'app.js::o.total': 'grandfathered', 'app.js::o.gone': 'deleted long ago'})
check('a baseline key with nothing behind it is counted',
      'no longer present   : 1' in out, True)
check('...and the live one is not counted stale', rc, 0)

print()
if fails:
    print('%d FAILED' % fails)
    sys.exit(1)
print('ALL PASS -- a new uncoerced numeric fold cannot be added silently, and '
      'the tool does not report multiplication, coercion, comments or prose.')
