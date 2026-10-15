#!/usr/bin/env python
# OWNER: cody
# written 2026-10-14, batch b14, item 3
# REQUIREMENT: a leg_aftercare check-in key must identify exactly one
#   (case_id, checkin_type) pair, because the row is upserted on
#   on_conflict=license_hash,aftercare_id with resolution=merge-duplicates and a
#   key two different pairs can share silently overwrites one family's check-in
#   with another's and returns 200. And a runtime cross-check that anchors on a
#   function name must degrade to UNPROVEN rather than pass when that anchor
#   moves, because a disarmed arm reads exactly like a passing one.
r"""The two arms b20's review routed to cody and nothing had written.

    python tests/run_b14_leg_aftercare_probe.py

Exit 0 every arm passes, 1 an arm FAILED, 3 COULD NOT RUN / UNPROVEN.

**ARM 1 IS RED ON PURPOSE AND MUST STAY RED UNTIL hank LANDS THE KEY FIX.**
That is not a regression and it is not this probe failing to work; it is the
arm doing the only job a failing-first arm has. Read the row in
`docs/known-red-suites.json` before treating this suite's exit 1 as new.

── ARM 1 — THE leg_aftercare KEY IS DELIMITER-AMBIGUOUS ────────────────────
`docs/2026-10-14-fourth-b20-leg-role-matrix-discharge.md` F4, the highest-value
defect in that review:

    {case_id:'CS-7',   checkin_type:'1 Week'}  ->  AC-CS-7-1-WEEK
    {case_id:'CS-7-1', checkin_type:'Week'}    ->  AC-CS-7-1-WEEK   <- same key

`checkin_type` is normalised; `case_id` is passed through with `trim()` alone,
and `-` is both the joiner AND the normaliser's output character, so the
boundary between the two fields is not recoverable. The upsert is
`on_conflict=license_hash,aftercare_id` with `resolution=merge-duplicates`, so
a collision **silently overwrites a different case's check-in and returns
200.**

WHY THE EXISTING CROSS-CHECK CANNOT CATCH THIS, which is the whole reason this
arm has to exist separately. `api/sd-data-leg-overlap.test.js`'s sibling in
`api/sd-data-leg-role-matrix.test.js` arm E4 extracts the client function and
compares it to the server's answer over four cases -- a real
cross-implementation test. **Both copies agree on the wrong answer here**, so
the colliding pair PASSES E4. A cross-implementation test is necessary and not
sufficient; this arm asserts the PROPERTY instead of the agreement.

REACHABILITY, carried over rather than restated more strongly than fourth
measured it: NOT reachable through the shipped UI (types come from a fixed
three-element plan and generated case ids always have three segments). It IS
reachable by any licence-key holder posting directly to the endpoint, and by
any future creation path with a free-text type.

── ARM 2 — THE ANCHOR THAT CAN BE RENAMED SILENTLY ────────────────────────
Same review, F3's caveat: `api/sd-data-leg-overlap.test.js`'s D4 arm reads the
clergy status literal out of `sairnlegacy.html` at runtime by anchoring on
`function clergyBookingConflict(`. **Renaming that function disarms the only
arm that reads the app's real literal.** The suite does the right thing -- it
routes to UNPROVEN and exits 3 rather than passing -- and NOTHING TESTED THAT.
A degradation nobody drives is a degradation nobody can rely on.

This arm moves the anchor on a FIXTURE COPY of the HTML (the suite honours
`LEG_HTML`) and requires exit 3 with the anchor named. **No api/ file is
edited; api/ is hank's and this probe only runs it.**

── WHAT IS DELIBERATELY NOT ASSERTED ──────────────────────────────────────
Not that the collision is reachable from the UI -- it is not, and claiming so
would be the overstatement fourth explicitly avoided. Not that the two copies
of the derivation disagree -- they agree, and arm E4 already covers that. Not
what the fixed key should look like: encoding the separator and hashing the
pair are both valid and that choice is hank's.
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, 'sairnlegacy.html')
HANDLER = os.path.join(REPO, 'api', 'sd-data.js')
# ONE INJECTION POINT, never set on an ordinary run. The counterfactual driver
# points this at a MUTATED COPY of the overlap suite to prove arm 2 goes red
# when the exit-3 degradation it depends on is removed. An env var rather than
# an edit, because the suite lives in api/ and api/ is hank's.
OVERLAP_SUITE = os.environ.get(
    'SAIRN_B14_OVERLAP_SUITE',
    os.path.join(REPO, 'api', 'sd-data-leg-overlap.test.js'))

fails = []
unproven = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:500]))
    if not cond:
        fails.append(name)


def cannot(name, why):
    print('  UNPROVEN ' + name + '\n         ' + str(why)[:400])
    unproven.append(name)


def could_not_run(why):
    print('COULD NOT RUN: %s Nothing was verified.' % why)
    sys.exit(3)


def node(expr_body, *args):
    """Run a JS snippet in node and return its stdout, or (None, why)."""
    d = tempfile.mkdtemp(prefix='sairn-b14-ac-')
    p = os.path.join(d, 'run.js')
    io.open(p, 'w', encoding='utf-8', newline='\n').write(expr_body)
    try:
        r = subprocess.run(['node', p] + list(args), capture_output=True,
                           text=True, encoding='utf-8', errors='replace')
    except OSError as e:
        return None, 'node would not start: %s' % e
    if r.returncode != 0:
        return None, (r.stdout or '') + (r.stderr or '')
    return (r.stdout or '').strip(), None


print('leg_aftercare key ambiguity, and the anchor that can be renamed '
      'silently\n')

# ── PRECONDITIONS. Every one of these is a COULD NOT RUN, never a pass ─────
try:
    html_src = io.open(HTML, encoding='utf-8').read().replace('\r\n', '\n')
except OSError as e:
    could_not_run('sairnlegacy.html is not readable (%s).' % e)

CLIENT_FN = re.search(
    r'function legAftercareId\(caseId,type\)\{([\s\S]*?)\n\}', html_src)
if not CLIENT_FN:
    could_not_run('legAftercareId() was not found in sairnlegacy.html, so the '
                  'client derivation could not be extracted. The anchor has '
                  'moved -- re-derive it rather than leaving this arm quiet.')

try:
    handler_src = io.open(HANDLER, encoding='utf-8').read().replace('\r\n', '\n')
except OSError as e:
    could_not_run('api/sd-data.js is not readable (%s).' % e)

# THE SERVER EXPRESSION IS EXTRACTED, NOT RETYPED. A second copy of another
# file's expression is the defect this app has already paid for twice, and it
# would make this arm pass while the real derivation drifted.
SERVER_EXPR = re.search(
    r"const acKey = ('AC-'[\s\S]*?);", handler_src)
if not SERVER_EXPR:
    could_not_run("the `const acKey = 'AC-' ...` derivation was not found in "
                  'api/sd-data.js, so the server half could not be extracted.')

# FAIL CLOSED ON THE SUITE ARM 2 DEPENDS ON (PR 1.11). An absent or
# LEG_HTML-ignoring suite is a third state: this probe says which file and
# which capability is missing, and refuses. It never skips arm 2 quietly.
try:
    overlap_src = io.open(OVERLAP_SUITE, encoding='utf-8').read()
except OSError as e:
    could_not_run('%s could not be read (%s), so arm 2 has nothing to drive.'
                  % (OVERLAP_SUITE, e))
if 'process.env.LEG_HTML' not in overlap_src:
    could_not_run('%s does not honour LEG_HTML, so arm 2 cannot point it at a '
                  'fixture copy of the HTML.'
                  % os.path.relpath(OVERLAP_SUITE, REPO))

# ── ARM 1: THE COLLISION, on BOTH derivations, each extracted from source ──
# The pair is fourth's, verbatim from the F4 finding.
PAIR_A = ['CS-7', '1 Week']
PAIR_B = ['CS-7-1', 'Week']
# The control pair: SAME case, different type. These must differ, which is what
# the existing arms already prove -- repeated here so that "the keys differ" is
# not satisfied by an extraction that returns a constant or throws.
CTRL_A = ['CS-7', '1 Week']
CTRL_B = ['CS-7', '1 Month']

DRIVER = r"""
'use strict';
const clientBody = process.argv[2];
const serverExpr = process.argv[3];
const cases = JSON.parse(process.argv[4]);
/* eslint-disable no-new-func */
const clientFn = new Function('caseId', 'type', clientBody);
// The server's expression names `payload`, so it is evaluated with one.
const serverFn = new Function('payload', 'return (' + serverExpr + ');');
const out = cases.map(function (c) {
  return {
    input: c,
    client: clientFn(c[0], c[1]),
    server: serverFn({ case_id: c[0], checkin_type: c[1] })
  };
});
process.stdout.write(JSON.stringify(out));
"""

got, why = node(DRIVER, CLIENT_FN.group(1), SERVER_EXPR.group(1),
                json.dumps([PAIR_A, PAIR_B, CTRL_A, CTRL_B]))
if got is None:
    could_not_run('the extracted derivations would not run in node: %s' % why)
try:
    rows = json.loads(got)
except ValueError:
    could_not_run('the driver did not return JSON: %r' % got[:200])

by_input = dict((json.dumps(r['input']), r) for r in rows)
a = by_input[json.dumps(PAIR_A)]
b = by_input[json.dumps(PAIR_B)]
c1 = by_input[json.dumps(CTRL_A)]
c2 = by_input[json.dumps(CTRL_B)]

# THE LIVENESS CONTROL FIRST. Without it, "the keys differ" could be satisfied
# by an extraction that silently produced empty strings for everything -- and
# it would then also satisfy the control pair below.
check('CONTROL (liveness): both extracted derivations actually RAN and '
      'produced AC- keys rather than empty strings',
      all(str(r['client']).startswith('AC-') and str(r['server']).startswith('AC-')
          for r in rows),
      json.dumps(rows)[:400])

check('CONTROL (not "everything collides"): the SAME case with two different '
      'check-in types derives two different keys, client and server',
      c1['client'] != c2['client'] and c1['server'] != c2['server'],
      'client %r vs %r / server %r vs %r'
      % (c1['client'], c2['client'], c1['server'], c2['server']))

check('CONTROL (the two copies agree, so this is a PROPERTY failure and not a '
      'drift between client and server)',
      all(r['client'] == r['server'] for r in rows),
      json.dumps(rows)[:400])

# ── THE ARM ITSELF. RED until the key fix lands. ──────────────────────────
check('1. ARM 1 (RED UNTIL hank FIXES THE KEY): two DIFFERENT '
      '(case_id, checkin_type) pairs cannot derive one aftercare key -- '
      '%r vs %r' % (PAIR_A, PAIR_B),
      a['client'] != b['client'] and a['server'] != b['server'],
      'client: %r -> %r and %r -> %r\nserver: %r and %r\n'
      'COLLISION. on_conflict=license_hash,aftercare_id with '
      'resolution=merge-duplicates means the second write silently overwrites '
      "the first case's check-in and returns 200. Fix is routed to hank: "
      'encode the separator or hash the pair.'
      % (PAIR_A, a['client'], PAIR_B, b['client'], a['server'], b['server']))

# ── ARM 2: the anchor must degrade to UNPROVEN, not pass ──────────────────
print('')


def run_overlap(leg_html):
    env = dict(os.environ)
    if leg_html is None:
        env.pop('LEG_HTML', None)
    else:
        env['LEG_HTML'] = leg_html
    env.pop('SAIRN_B14_OVERLAP_SUITE', None)
    try:
        r = subprocess.run(['node', OVERLAP_SUITE], capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           cwd=REPO, env=env)
    except OSError as e:
        return None, 'node would not start: %s' % e
    return r.returncode, (r.stdout or '') + (r.stderr or '')

ANCHOR = 'function clergyBookingConflict('
if html_src.count(ANCHOR) != 1:
    could_not_run('%r appears %d times in sairnlegacy.html, so moving it on a '
                  'fixture would not be a clean single mutation.'
                  % (ANCHOR, html_src.count(ANCHOR)))

d = tempfile.mkdtemp(prefix='sairn-b14-anchor-')
moved = os.path.join(d, 'sairnlegacy.html')
io.open(moved, 'w', encoding='utf-8', newline='\n').write(
    html_src.replace(ANCHOR, 'function clergyBookingConflictRenamedByB14(', 1))

base_code, base_out = run_overlap(None)
if base_code is None:
    could_not_run('the overlap suite would not run at all: %s' % base_out)

# THE CONTROL BEFORE THE ARM, because "it exits 3" is satisfied for ever by a
# suite that is ALWAYS unproven -- and that is a real state this platform has
# shipped. The baseline must NOT be 3.
check('CONTROL: against the REAL sairnlegacy.html the overlap suite does NOT '
      'exit 3, so arm 2 below is measuring the anchor and not a suite that is '
      'permanently unproven (baseline exit %s)' % base_code,
      base_code != 3,
      base_out[-500:])

mut_code, mut_out = run_overlap(moved)
if mut_code is None:
    could_not_run('the overlap suite would not run against the fixture: %s'
                  % mut_out)

check('2. with the clergyBookingConflict anchor MOVED, the overlap suite exits '
      '3 UNPROVEN rather than passing -- exit %s' % mut_code,
      mut_code == 3,
      'exit %s\n%s' % (mut_code, mut_out[-700:]))

check('   ...and it says so by NAME, so a reader learns which anchor moved '
      'rather than that something was unproven',
      'clergyBookingConflict' in mut_out and 'anchor absent' in mut_out,
      mut_out[-700:])

check('   ...and it is the CLERGY half that degraded, while the leg_bookings '
      'half -- whose anchor was NOT moved -- still reports a result, so the '
      'mutation was surgical rather than breaking the whole read',
      'D4[leg_bookings]' in mut_out,
      mut_out[-700:])

try:
    os.remove(moved)
    os.rmdir(d)
except OSError:
    pass

print('')
if unproven:
    print('%d UNPROVEN: %s' % (len(unproven), '; '.join(unproven)))
if fails:
    print('%d failure(s)' % len(fails))
    for f in fails:
        print('  - ' + f)
    print('\nARM 1 IS EXPECTED RED while api/sd-data.js builds the aftercare '
          'key by joining on "-". If ARM 1 is the ONLY failure above, this '
          'suite is in the state docs/known-red-suites.json records. Any '
          'OTHER failure here is new.')
    sys.exit(1)
sys.exit(3 if unproven else 0)
