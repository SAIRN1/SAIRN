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

**ARM 1 IS GREEN SINCE 2026-10-15 AND IS NO LONGER EXPECTED RED.** hank landed
the two-form derivation; the arm is kept because it is the only thing that
would notice the escaping being dropped again.

── RE-ANCHORED 2026-10-16, cody b19, ON fourth's b24 F1 ────────────────────
hank's fix replaced the server derivation and this probe's extraction anchor --
`const acKey = ('AC-'...` -- stopped matching, so the whole file exited **3,
COULD NOT RUN**, and nothing surfaced it: an exit 3 is not a FAIL line in any
sweep, and `docs/known-red-suites.json` still described the file as `exit_code:
1` with `expected_red_scope: "ARM 1 ONLY"`, which cannot classify an exit 3.

**TWO THINGS CHANGED, AND THE SECOND IS THE POINT.**

1. The anchor is now a **STRUCTURE**: the server half is the BALANCED BLOCK of
   the `leg_aftercare` guard, taken from the `acEsc` helper to the `}` that
   closes the guard, so there is no character budget to outgrow. Both halves
   now need their helper extracted too (`legAcEsc` client-side, `acEsc`
   server-side) -- which is the first reason a one-expression anchor could not
   simply be re-aimed: the extracted expression would throw on an undefined
   identifier.
2. **THE ROT OF THIS FILE'S OWN ANCHOR IS EXIT 1, NOT EXIT 3, AND ARM 3 DRIVES
   IT.** The line between the two states is OWNERSHIP: a subject file that will
   not read is an external blocker and stays a COULD NOT RUN; an anchor that no
   longer matches a file that reads fine is a defect in THIS file, actionable
   by its owner, and it has to appear as a red arm so somebody is looking.
   Arm 3 renames the anchor in a COPY of each subject and requires exit 1 with
   the anchor named -- with an unmutated-copy control first, because "it exits
   1" is satisfied for ever by a probe that always exits 1.

── ARM 1 — THE leg_aftercare KEY WAS DELIMITER-AMBIGUOUS ───────────────────
`docs/2026-10-14-fourth-b20-leg-role-matrix-discharge.md` F4, the highest-value
defect in that review. As shipped until 2026-10-15:

    {case_id:'CS-7',   checkin_type:'1 Week'}  ->  AC-CS-7-1-WEEK
    {case_id:'CS-7-1', checkin_type:'Week'}    ->  AC-CS-7-1-WEEK   <- same key

`checkin_type` was normalised; `case_id` was passed through with `trim()`
alone, and `-` is both the joiner AND the normaliser's output character, so the
boundary between the two fields was not recoverable. The upsert is
`on_conflict=license_hash,aftercare_id` with `resolution=merge-duplicates`, so
a collision **silently overwrites a different case's check-in and returns
200.** The fix takes the `AC-` form only when the case id matches
`/^CS-[0-9]+-[0-9]+$/` **and** the type is one of the three shipped plan
values, and routes everything else through `ACX-` with `-` escaped to `~1`.
Measured on both extracted halves: `ACX-CS~17-1~1WEEK` vs `ACX-CS~17~11-WEEK`.

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
# TWO MORE INJECTION POINTS, never set on an ordinary run, added 2026-10-16 so
# ARM 3 can drive THIS PROBE against a copy whose extraction anchor has been
# renamed. Read-only in both cases: the probe only ever reads these two files
# as text, so a copy anywhere on disk is a faithful subject.
HTML = os.environ.get('SAIRN_B14_HTML', os.path.join(REPO, 'sairnlegacy.html'))
HANDLER = os.environ.get('SAIRN_B14_HANDLER',
                         os.path.join(REPO, 'api', 'sd-data.js'))
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

try:
    handler_src = io.open(HANDLER, encoding='utf-8').read().replace('\r\n', '\n')
except OSError as e:
    could_not_run('api/sd-data.js is not readable (%s).' % e)

# ── ARM 0: THIS PROBE'S OWN EXTRACTION ANCHORS ─────────────────────────────
# RE-ANCHORED 2026-10-16, cody b19, on fourth's b24 F1. hank replaced the
# server derivation and the old anchor -- `const acKey = ('AC-'...` -- stopped
# matching, because the key is now a TERNARY that starts with a regex test and
# only reaches the `'AC-'` literal in its consequent. This probe then exited
# 3, COULD NOT RUN, correctly and invisibly: an exit 3 is not a FAIL line in
# any sweep, docs/known-red-suites.json recorded the file at exit_code 1 with
# `expected_red_scope: ARM 1 ONLY`, and an exit 3 is neither of those.
#
# THE ROT OF THIS PROBE'S OWN ANCHOR IS NOW EXIT 1, NOT EXIT 3, AND THE LINE
# BETWEEN THE TWO IS OWNERSHIP. api/sd-data.js being unreadable is an external
# blocker and stays a COULD NOT RUN. An anchor that no longer matches a file
# that reads fine is a defect in THIS FILE -- actionable here, by its owner,
# and it must appear as a red arm so somebody is looking at it. ARM 3 drives
# that in both files and both directions.
#
# AND THE NEW ANCHOR IS A STRUCTURE, NOT A CHARACTER WINDOW. The server half
# is taken as the BALANCED BLOCK of the `leg_aftercare` guard, from the
# `acEsc` helper above it to the `}` that closes the guard, so there is no
# character budget for the branch to outgrow. The old form could only have
# been re-aimed at another `[\s\S]*?` span with a different expiry date.
CLIENT_ESC_ANCHOR = 'function legAcEsc(s){'
CLIENT_FN_ANCHOR = 'function legAftercareId(caseId,type){'
SERVER_ESC_ANCHOR = 'const acEsc = (s) =>'
SERVER_GUARD_ANCHOR = ("if (resource === 'leg_aftercare' && payload "
                       "&& acCase && acRawType) {")


def balanced_from(src, start):
    """Index just past the `}` matching the first `{` at or after `start`.

    NAIVE about braces inside strings, template literals and regex literals,
    and NOTHING HERE TRUSTS IT ON ITS OWN: the extracted text is handed to
    node, which re-parses it, and the liveness control below requires it to
    actually PRODUCE a key. A mis-extraction throws or returns nothing; it
    cannot pass quietly, which is the only property that makes a brace
    counter acceptable in place of a parser.
    """
    try:
        i = src.index('{', start)
    except ValueError:
        return None
    depth = 0
    while i < len(src):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


ANCHOR_ROWS = (
    ('0a', 'sairnlegacy.html', CLIENT_ESC_ANCHOR, html_src),
    ('0b', 'sairnlegacy.html', CLIENT_FN_ANCHOR, html_src),
    ('0c', 'api/sd-data.js', SERVER_ESC_ANCHOR, handler_src),
    ('0d', 'api/sd-data.js', SERVER_GUARD_ANCHOR, handler_src),
)
anchors_live = True
for _tag, _where, _text, _src in ANCHOR_ROWS:
    _n = _src.count(_text)
    check('%s. EXTRACTION ANCHOR LIVE: %r occurs exactly once in %s'
          % (_tag, _text, _where), _n == 1,
          'FOUND %d. THE ANCHOR HAS ROTTED -- this is a defect in '
          'tests/run_b14_leg_aftercare_probe.py, not in %s, and it is exit 1 '
          'rather than exit 3 ON PURPOSE: the last time this happened the '
          'probe exited 3 and no sweep showed a FAIL line for it. RE-ANCHOR '
          'IT: find the current derivation and take the BALANCED BLOCK, never '
          'a character window. Arm 1 and its three controls were not built, '
          'so nothing about the key property was measured on this run.'
          % (_n, _where))
    if _n != 1:
        anchors_live = False

if not anchors_live:
    print('')
    print('%d failure(s)' % len(fails))
    for _f in fails:
        print('  - ' + _f)
    print('\nONE OR MORE OF THIS PROBE\'S OWN EXTRACTION ANCHORS NO LONGER '
          'MATCHES. Both subject files read fine, so this is not a COULD NOT '
          'RUN -- it is this file being out of date with the code it reads. '
          'Exit 1, by name, so it is visible in a sweep.')
    sys.exit(1)

CLIENT_SRC = (
    html_src[html_src.index(CLIENT_ESC_ANCHOR):
             balanced_from(html_src, html_src.index(CLIENT_ESC_ANCHOR))]
    + '\n'
    + html_src[html_src.index(CLIENT_FN_ANCHOR):
               balanced_from(html_src, html_src.index(CLIENT_FN_ANCHOR))])
_sv0 = handler_src.index(SERVER_ESC_ANCHOR)
_sv1 = balanced_from(handler_src, handler_src.index(SERVER_GUARD_ANCHOR, _sv0))
SERVER_SRC = handler_src[_sv0:_sv1] if _sv1 else ''

check('0e. and the two extractions came back as BALANCED, NON-EMPTY blocks '
      'that mention the key they are supposed to derive -- a brace counter '
      'that walked off the end returns nothing, and an empty extraction '
      'would make every arm below vacuous',
      bool(CLIENT_SRC) and bool(SERVER_SRC)
      and 'const acKey' in SERVER_SRC
      and CLIENT_SRC.count('{') == CLIENT_SRC.count('}')
      and SERVER_SRC.count('{') == SERVER_SRC.count('}'),
      'client %d chars, server %d chars, `const acKey` in server: %s'
      % (len(CLIENT_SRC), len(SERVER_SRC), 'const acKey' in SERVER_SRC))

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
const clientSrc = process.argv[2];
const serverSrc = process.argv[3];
const cases = JSON.parse(process.argv[4]);
/* eslint-disable no-new-func */
// BOTH HALVES ARE EXTRACTED SOURCE, NEVER RETYPED, and both now need their
// own helper: the client's legAftercareId() calls legAcEsc() and the server's
// acKey ternary calls acEsc(). Extracting the key expression alone -- which is
// what this driver used to do -- would now throw on an undefined identifier,
// and that is the FIRST reason a one-expression anchor could not simply be
// re-aimed at the new code.
const clientFn = new Function(clientSrc + '\nreturn legAftercareId;')();
// The server half is a guarded BLOCK that assigns `payload.id`, not an
// expression, so it is run as a body and the mutated payload is the answer.
const serverFn = new Function('resource', 'payload',
                              serverSrc + '\nreturn payload.id;');
const out = cases.map(function (c) {
  return {
    input: c,
    client: clientFn(c[0], c[1]),
    server: serverFn('leg_aftercare', { case_id: c[0], checkin_type: c[1] })
  };
});
process.stdout.write(JSON.stringify(out));
"""

got, why = node(DRIVER, CLIENT_SRC, SERVER_SRC,
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
# THE LIVENESS CONTROL NOW ACCEPTS BOTH PREFIXES, AND THAT IS NOT A LOOSENING.
# It asserted `startswith('AC-')` on both halves. hank's fix routes anything
# outside the three shipped plan types through an ESCAPED form prefixed `ACX-`,
# which does not start with `AC-` -- so this control would have gone red on a
# correct derivation, in the arm whose whole job is to prove the extraction
# ran. The property it needs is "a key came back", not "a key of one shape":
# `^ACX?-` plus a non-empty remainder keeps it from passing on '', null or a
# constant.
KEY_RE = re.compile(r'^ACX?-\S')
check('CONTROL (liveness): both extracted derivations actually RAN and '
      'produced an AC-/ACX- key with a body, rather than empty strings, null '
      'or a constant',
      all(KEY_RE.match(str(r['client'] or '')) and KEY_RE.match(str(r['server'] or ''))
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

# ── THE ARM ITSELF. GREEN SINCE hank's FIX; IT STAYS AS THE REGRESSION ────
# It was RED ON PURPOSE from b14 until 2026-10-15. hank's fix is the two-form
# derivation this probe now extracts: the `AC-` form is taken only when the
# case id matches /^CS-[0-9]+-[0-9]+$/ AND the type is one of the three shipped
# plan values, and everything else goes through `ACX-` with `-` escaped to
# `~1`, so the field boundary is recoverable. The arm is kept, not deleted --
# it is the only thing that would notice the escape being dropped again.
check('1. two DIFFERENT (case_id, checkin_type) pairs cannot derive one '
      'aftercare key -- %r vs %r' % (PAIR_A, PAIR_B),
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

# ── ARM 3: THE ARM THAT GOES RED WHEN THIS PROBE'S OWN ANCHOR ROTS ────────
# fourth's b24 F1, second half: arm 2 above proves the DIFFERENT anchor in
# api/sd-data-leg-overlap.test.js degrades honestly, and nothing covered THIS
# file's own. So the anchor rot that actually happened -- hank replacing the
# server derivation -- produced an exit 3 that no sweep surfaced, while the
# register still described the file as exit 1 with a named red arm.
#
# DRIVEN, NOT ASSERTED, AND FAILING-FIRST IN BOTH FILES: this probe is re-run
# as a subprocess against a COPY whose anchor has been renamed, and must come
# back EXIT 1 with the anchor named -- not exit 3, and not exit 0.
# SAIRN_B14_NO_SABOTAGE stops the child recursing; without it the UNMUTATED
# control run below would fork for ever.
print('')
if os.environ.get('SAIRN_B14_NO_SABOTAGE') == '1':
    print('(arm 3 not run: this IS the arm-3 child, SAIRN_B14_NO_SABOTAGE=1)')
else:
    print('3. this probe\'s OWN extraction anchors, driven')

    def self_run(handler=None, html=None):
        env = dict(os.environ, SAIRN_B14_NO_SABOTAGE='1',
                   PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
        if handler:
            env['SAIRN_B14_HANDLER'] = handler
        if html:
            env['SAIRN_B14_HTML'] = html
        try:
            r = subprocess.run([sys.executable, os.path.abspath(__file__)],
                               capture_output=True, text=True,
                               encoding='utf-8', errors='replace',
                               cwd=REPO, env=env)
        except OSError as e:
            return None, 'python would not start: %s' % e
        return r.returncode, (r.stdout or '') + (r.stderr or '')

    _d3 = tempfile.mkdtemp(prefix='sairn-b19-anchor-')
    _h_ok = os.path.join(_d3, 'sd-data-unmutated.js')
    _h_bad = os.path.join(_d3, 'sd-data-anchor-renamed.js')
    _p_ok = os.path.join(_d3, 'sairnlegacy-unmutated.html')
    _p_bad = os.path.join(_d3, 'sairnlegacy-anchor-renamed.html')
    io.open(_h_ok, 'w', encoding='utf-8', newline='\n').write(handler_src)
    io.open(_h_bad, 'w', encoding='utf-8', newline='\n').write(
        handler_src.replace(SERVER_ESC_ANCHOR,
                            'const acEscRenamedByB19 = (s) =>', 1))
    io.open(_p_ok, 'w', encoding='utf-8', newline='\n').write(html_src)
    io.open(_p_bad, 'w', encoding='utf-8', newline='\n').write(
        html_src.replace(CLIENT_FN_ANCHOR,
                         'function legAftercareIdRenamedByB19(caseId,type){', 1))

    _c_ok, _o_ok = self_run(handler=_h_ok, html=_p_ok)
    # THE CONTROL BEFORE THE ARM. "it exits 1" is satisfied for ever by a probe
    # that always exits 1, and this file spent two days doing exactly that on a
    # red arm. The unmutated COPY -- same bytes, different path -- must come
    # back 0, which also proves the two new env injection points do not
    # themselves change the verdict.
    check('3a. CONTROL: run against UNMUTATED COPIES of both files at new '
          'paths, this probe exits 0 -- so 3b/3d measure the rename and not a '
          'probe that is red anyway, and the two injection points are inert '
          '(exit %s)' % _c_ok, _c_ok == 0, (_o_ok or '')[-600:])

    _c_h, _o_h = self_run(handler=_h_bad, html=_p_ok)
    check('3b. with the SERVER anchor %r renamed, this probe exits 1 -- the '
          'state the real rot produced was exit 3, which no sweep shows as a '
          'FAIL (exit %s)' % (SERVER_ESC_ANCHOR, _c_h),
          _c_h == 1, (_o_h or '')[-600:])
    # THE FIRST SPELLING OF THIS ARM WAS `'COULD NOT RUN' not in _o_h` AND IT
    # FAILED ON ITS OWN SUBJECT'S PROSE. The child's failure summary explains
    # "this is not a COULD NOT RUN", so the substring is present in exactly the
    # output that proves the arm's point. Recorded rather than quietly swapped:
    # a scanner looking for a verdict inside text that DISCUSSES the verdict
    # finds the discussion. The verdict has a shape -- could_not_run() prints a
    # line that STARTS with it -- so the arm reads the line, not the file.
    _cnr_lines = [l for l in (_o_h or '').split('\n')
                  if l.startswith('COULD NOT RUN:')]
    check('3c. ...and it is NOT a COULD NOT RUN verdict (no line STARTS with '
          'it), and it names the anchor and the file, so a reader learns '
          'which anchor rotted rather than that something was unverifiable',
          _c_h == 1 and not _cnr_lines
          and SERVER_ESC_ANCHOR in (_o_h or '')
          and 'EXTRACTION ANCHOR LIVE' in (_o_h or ''),
          'verdict lines: %r\n%s' % (_cnr_lines, (_o_h or '')[-500:]))

    _c_p, _o_p = self_run(handler=_h_ok, html=_p_bad)
    check('3d. THE OTHER FILE TOO: with the CLIENT anchor %r renamed, exit 1 '
          'and named -- one file covered would leave the other able to rot '
          'silently, which is the whole shape of this finding (exit %s)'
          % (CLIENT_FN_ANCHOR, _c_p),
          _c_p == 1 and CLIENT_FN_ANCHOR in (_o_p or ''), (_o_p or '')[-600:])
    check('3e. ...and the SERVER anchors still passed in that run, so 3d was a '
          'surgical mutation of one anchor rather than a probe that fell over',
          '0c. EXTRACTION ANCHOR LIVE' in (_o_p or '')
          and '  FAIL 0c.' not in (_o_p or ''), (_o_p or '')[-600:])

    for _f in (_h_ok, _h_bad, _p_ok, _p_bad):
        try:
            os.remove(_f)
        except OSError:
            pass
    try:
        os.rmdir(_d3)
    except OSError:
        pass

print('')
if unproven:
    print('%d UNPROVEN: %s' % (len(unproven), '; '.join(unproven)))
if fails:
    print('%d failure(s)' % len(fails))
    for f in fails:
        print('  - ' + f)
    print('\nTHIS SUITE IS GREEN AT HEAD SINCE 2026-10-16 and its row is in '
          'docs/known-red-suites.json `recovered`. ARM 1 IS NO LONGER '
          'EXPECTED RED -- hank\'s two-form derivation landed. Any failure '
          'above is NEW: a 0a-0e failure means THIS FILE\'s extraction anchor '
          'has rotted and needs re-anchoring on a balanced block; arm 1 means '
          'the key is ambiguous again; arm 2 means the overlap suite stopped '
          'degrading to exit 3; arm 3 means this file can no longer detect '
          'its own anchor rot.')
    sys.exit(1)
sys.exit(3 if unproven else 0)
