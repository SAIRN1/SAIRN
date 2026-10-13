"""Control for tools/gate_skip.py and the push gate's blanket refusal.

    python tests/run_gate_skip_probe.py

A skip mechanism is an EXEMPTION mechanism, so the arms below are written in
the refusing direction first. The failure that matters is not "a legitimate
skip was refused" -- that costs one message -- it is "a skip was granted that
should not have been", which costs a push nobody checked.

WRITES NOTHING OUTSIDE A TEMPORARY DIRECTORY. SAIRN-SESSION-LOCKS is
redirected per-arm via HOME so the real clone's skip records are never
touched, and an arm asserts the redirection actually took.
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for.
CONTROLS_FOR = ['gate_skip.py']

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'gate_skip.py')
HOOK = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')
NL = chr(10)

if not os.path.isfile(TOOL):
    print('COULD NOT RUN -- %s is absent. This probe is about that file and '
          'reports nothing without it.' % TOOL)
    sys.exit(2)

_spec = importlib.util.spec_from_file_location('gate_skip_probe', TOOL)
GS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(GS)

passed, fails = 0, []


def ok(cond, label, detail=''):
    global passed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        fails.append(label)
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:400])


GOOD = GS.GOOD_WHY

print('1. the criteria lock passes on its own fixtures')
rc = subprocess.run([sys.executable, TOOL, '--fixtures'], capture_output=True,
                    text=True, encoding='utf-8', errors='replace')
ok(rc.returncode == 0, 'the shipped criteria lock is clean',
   (rc.returncode, (rc.stdout or '')[-300:]))
ok('14/14' in (rc.stdout or ''),
   '...and it really ran all of its fixtures rather than none',
   (rc.stdout or '')[-200:])

print('')
print('2. validate() refuses, and each refusal NAMES what to do instead')
for gate, why, mins, label in (
        ('seed-gte', GOOD, 30, 'an unknown gate id'),
        ('credentials', GOOD, 30, 'an UNSKIPPABLE gate'),
        ('syntax', GOOD, 30, '...and syntax is unskippable too'),
        ('hook-integrity', GOOD, 30, '...and so is hook-integrity'),
        ('all', GOOD, 30, 'the word `all`'),
        ('seed-gate,tier-a', GOOD, 30, 'a comma list'),
        ('seed-gate', '', 30, 'no reason at all'),
        ('seed-gate', 'x' * (GS.MIN_REASON - 1), 30, 'a reason one char short'),
        ('seed-gate', 'bypass' + ' ' * 40, 30, 'a reason that is only the mechanism'),
        ('seed-gate', GOOD, 0, 'a zero expiry'),
        ('seed-gate', GOOD, GS.MAX_MINUTES + 1, 'an expiry over the ceiling'),
        ('seed-gate', GOOD, -5, 'a negative expiry'),
        ('seed-gate', GOOD, 'soon', 'a non-numeric expiry')):
    granted, refusals = GS.validate(gate, why, mins, 'cc')
    ok(not granted, 'REFUSED: %s' % label, refusals)

granted, refusals = GS.validate('seed-gate', GOOD, 30, '')
ok(not granted, 'REFUSED: an agent that cannot be derived -- a skip with no '
   'author is not recorded as "unknown"', refusals)

print('')
print('3. the one shape it ACCEPTS, and the boundary')
granted, refusals = GS.validate('seed-gate', GOOD, 30, 'cc')
ok(granted, 'GRANTED: a real gate, a real reason, a sane expiry', refusals)
granted, _ = GS.validate('seed-gate', GOOD, GS.MAX_MINUTES, 'cc')
ok(granted, 'BOUNDARY: exactly the ceiling is allowed -- the bound is <=, '
   'not <')
granted, _ = GS.validate('seed-gate', GOOD, 1, 'cc')
ok(granted, 'BOUNDARY: one minute is allowed')

print('')
print('4. active() honours only a live, matching, READABLE record')
_home = tempfile.mkdtemp(prefix='gs_home_')
_real_home = os.environ.get('HOME')
_real_up = os.environ.get('USERPROFILE')
try:
    os.environ['HOME'] = _home
    os.environ['USERPROFILE'] = _home
    ok(GS._skip_dir().startswith(_home),
       'the probe really redirected the skip directory, so the real clone\'s '
       'records are untouched', GS._skip_dir())

    now = time.time()
    GS.grant('seed-gate', GOOD, 30, 'cc', now=now)
    rec, why = GS.active('seed-gate', agent='cc', now=now + 60)
    ok(rec is not None, 'a live record for this agent and gate is honoured', why)
    ok(rec and rec.get('skipped_findings') is None,
       '...and it starts with skipped_findings UNSET, so a skip that never '
       'records what it let through is visible as a hole rather than as a zero')

    rec, why = GS.active('seed-gate', agent='cc', now=now + 31 * 60)
    ok(rec is None and 'expired' in why,
       'EXPIRED: a record past its expiry is NOT honoured, and says so', why)

    rec, why = GS.active('tier-a', agent='cc', now=now + 60)
    ok(rec is None, 'a record for a DIFFERENT gate does not cover this one', why)

    rec, why = GS.active('seed-gate', agent='hank', now=now + 60)
    ok(rec is None, 'a record belonging to a DIFFERENT agent does not cover '
       'this one -- a skip is not transferable', why)

    # UNREADABLE IS NOT GRANTED. The one case where failing open would be
    # indistinguishable from a real grant.
    p = GS.skip_path('cc', 'seed-gate')
    io.open(p, 'w', encoding='utf-8').write('{ this is not json')
    rec, why = GS.active('seed-gate', agent='cc', now=now + 60)
    ok(rec is None and 'could not be read' in why,
       'CORRUPT: an unreadable record is NOT honoured -- failing open here '
       'would be indistinguishable from a real grant', why)

    # AND A TAMPERED record whose fields disagree with its filename.
    GS.grant('seed-gate', GOOD, 30, 'cc', now=now)
    doc = json.loads(io.open(p, encoding='utf-8').read())
    doc['agent'] = 'hank'
    io.open(p, 'w', encoding='utf-8').write(json.dumps(doc))
    rec, why = GS.active('seed-gate', agent='cc', now=now + 60)
    ok(rec is None, 'TAMPERED: a record whose own agent field disagrees with '
       'the name it is filed under is NOT honoured', why)

    # record_findings writes back what the gate would have said.
    GS.grant('seed-gate', GOOD, 30, 'cc', now=now)
    GS.record_findings('seed-gate', ['the seed drifted on 2 files'], agent='cc')
    doc = json.loads(io.open(p, encoding='utf-8').read())
    ok(doc.get('skipped_findings') == ['the seed drifted on 2 files'],
       'record_findings() writes the refusal the gate WOULD have raised into '
       'the record -- the field that turns the log from a count into evidence',
       doc.get('skipped_findings'))
finally:
    if _real_home is None:
        os.environ.pop('HOME', None)
    else:
        os.environ['HOME'] = _real_home
    if _real_up is None:
        os.environ.pop('USERPROFILE', None)
    else:
        os.environ['USERPROFILE'] = _real_up
    shutil.rmtree(_home, ignore_errors=True)
ok(not GS._skip_dir().startswith(_home),
   'the probe put the real skip directory back')

print('')
print('5. the BLANKET form fails loudly, and the hook says so in both paths')
src = io.open(HOOK, encoding='utf-8', errors='replace').read()
ok('_blanket_refusal_lines()' in src,
   'the push hook calls the shared refusal text rather than carrying a second '
   'copy of it')
ok(src.count('for line in _blanket_refusal_lines():') >= 2,
   'BOTH entry points refuse -- the Bash-command path and the env-var prepush '
   'path. Leaving one open would make the refusal a suggestion',
   src.count('for line in _blanket_refusal_lines():'))
ok('REFUSED, not honoured' in src,
   '...and the bypass row records that the blanket attempt was REFUSED rather '
   'than granted, so the log can tell an attempt from a grant')
ok('sys.exit(0)' not in src.split('override_in_command(cmd)')[1][:600],
   'the Bash path no longer exits 0 after an override -- that exit is what 80 '
   'of the 94 logged overrides used')

print('')
print('6. a DECLARED gate that is not WIRED is reported, not silent')
rc = subprocess.run([sys.executable, TOOL, '--gates'], capture_output=True,
                    text=True, encoding='utf-8', errors='replace')
out = (rc.stdout or '') + (rc.stderr or '')
ok('WIRED' in out, '--gates marks which ids the hook actually passes')
wired = GS.wired_gates()
ok(wired is not None and len(wired) > 0,
   'the wiring was read from the hook rather than assumed', wired)
ok(wired is not None and wired <= (set(GS.GATES) | set(GS.UNSKIPPABLE)),
   'every id the hook passes is one this file declares -- a stray id would '
   'grant nothing and is reported', wired)
if wired is not None and set(GS.GATES) - wired:
    ok(rc.returncode == 1 and 'NOT WIRED' in out,
       'an unwired declared id makes --gates EXIT 1 and name it, because a '
       'skip for it is granted and then ignored',
       (rc.returncode, out[-300:]))
else:
    ok(rc.returncode == 0,
       'every declared id is wired, so --gates exits 0', rc.returncode)

print('')
print('%d passed, %d failed' % (passed, len(fails)))
for f in fails:
    print('  FAILED: %s' % f)
sys.exit(1 if fails else 0)
