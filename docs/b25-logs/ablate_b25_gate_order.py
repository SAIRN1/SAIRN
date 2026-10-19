#!/usr/bin/env python
# OWNER: cody
# written 2026-10-19, batch b25
r"""ABLATION: does b25's gate-ordering arm bite, and does it bite WHERE THE
EXISTING ARM DOES NOT?

    python docs/b25-logs/ablate_b25_gate_order.py            POST-REPAIR
    python docs/b25-logs/ablate_b25_gate_order.py --before    PRE-REPAIR

Exit 0 every case as expected, 1 one or more not, 2 COULD NOT RUN.
`--before` takes the suite out of git and is EXPECTED to exit 1 -- that is the
differential, and it is driven from the first run rather than claimed.

── THE CONCEPT THE ARM ASSERTS ─────────────────────────────────────────────
An unauthenticated write to a session-gated resource must be refused by the
GATE before the handler body reads the payload, so it answers 403 and not the
handler's own 400 -- a 400 proves the gate did not fire and discloses the
validation rules to a caller who has not signed in.

── THE DISCRIMINATING MUTATION, AND WHY THE OBVIOUS ONE IS NOT IT ──────────
Removing `customers` from SD_SESSION_GATED turns BOTH write arms red, so it
proves the new arm runs and nothing about whether it was needed. The mutation
that separates them puts a payload check for `customers` BEFORE the gate:

    G1  an id-less `write customers` is answered 400 by an early body check,
        while a VALID payload still reaches the gate and is answered 403

Under G1 the pre-existing arm -- which sends `{id, customer_id}` -- stays
GREEN, and only b25's empty-payload arm goes red. That is the whole claim.

G2 and G3 are controls: G2 removes the gate entry (both arms must go red, so
the suite is not blind to the gate itself) and G3 is the UNMUTATED copy.

THE LIVE CLONE IS NEVER WRITTEN: api/ is copied to a temp tree and the suite is
pointed at the copy.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SUITE_REL = os.path.join('api', 'sd-data-scp-session-gate.test.js')
GATE_ANCHOR = ("    if (SD_SESSION_GATED[resource] && "
               "SD_SESSION_GATED[resource].indexOf(action) !== -1) {")
EARLY_400 = (
    "    if (resource === 'customers' && action === 'write' "
    "&& !(payload && payload.id)) {\n"
    "      res.status(400).json({ error: { message: "
    "'customer payload.id is required' } });\n"
    "      return;\n"
    "    }\n")

BEFORE = '--before' in sys.argv
BEFORE_REF = 'HEAD'

CASES = [
    ('G1', 'a payload check for customers placed BEFORE the gate '
           '(an id-less write answers 400; a valid one still reaches the gate)',
     GATE_ANCHOR, EARLY_400 + GATE_ANCHOR),
    ('G2', 'CONTROL: customers removed from SD_SESSION_GATED entirely -- BOTH '
           'write arms must go red, so the suite is not blind to the gate',
     "      'customers': ['read', 'write'],\n", ''),
]


def die(why):
    print('COULD NOT RUN: %s Nothing was verified.' % why)
    sys.exit(2)


def suite_source():
    if not BEFORE:
        return io.open(os.path.join(REPO, SUITE_REL), encoding='utf-8',
                       errors='replace').read()
    r = subprocess.run(['git', 'show', BEFORE_REF + ':' + SUITE_REL.replace(os.sep, '/')],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        return None
    return r.stdout


def run(mutation):
    work = tempfile.mkdtemp(prefix='b25-gate-')
    try:
        src = suite_source()
        if src is None:
            return (None, [], 'the suite does not exist at %s -- NOT DRIVEN'
                    % BEFORE_REF)
        # api/ wholesale FIRST, the suite on top SECOND, and the written file
        # read back -- b24's harness wrote the suite first and then copied the
        # library over it, which silently drove the disk copy in the --before
        # leg. That cost a wrong pre-repair measurement and is why this is an
        # assertion rather than a careful ordering.
        shutil.copytree(os.path.join(REPO, 'api'), os.path.join(work, 'api'))
        # tests/lib/ too: the suite require()s ../tests/lib/fn_span.js. THE
        # CONTROL CAUGHT THIS -- the first run came back exit 1 with
        # MODULE_NOT_FOUND, and without a control every "REFUSED" after it
        # would have been a copy that could not load at all. b23 and b24 each
        # had the same experience with a different missing dependency, which is
        # the argument for the control running first every time.
        tlib = os.path.join(REPO, 'tests', 'lib')
        if os.path.isdir(tlib):
            os.makedirs(os.path.join(work, 'tests'), exist_ok=True)
            shutil.copytree(tlib, os.path.join(work, 'tests', 'lib'))
        # ...and sairnscape.html, which the suite reads to check the CLIENT
        # half. Caught by the control on its SECOND run, after tests/lib was
        # added -- two dependencies, two refusals, and in both cases the
        # alternative was a "REFUSED" verdict from a copy that never executed
        # a single arm. THE APP IS NEVER MUTATED HERE; only api/sd-data.js is.
        for dep in ('sairnscape.html',):
            p = os.path.join(REPO, dep)
            if os.path.isfile(p):
                shutil.copy(p, os.path.join(work, dep))
        handler = os.path.join(work, 'api', 'sd-data.js')
        text = io.open(handler, encoding='utf-8', newline='').read()
        if mutation is not None:
            old, new = mutation
            n = text.count(old)
            if n != 1:
                return (None, [], 'anchor occurs %d times in api/sd-data.js, '
                        'expected 1 -- MUTATION NOT APPLIED' % n)
            text = text.replace(old, new, 1)
            io.open(handler, 'w', encoding='utf-8', newline='').write(text)
        dst = os.path.join(work, SUITE_REL)
        io.open(dst, 'w', encoding='utf-8', newline='\n').write(src)
        if io.open(dst, encoding='utf-8', errors='replace').read() != src:
            return (None, [], 'the suite in the temp tree is NOT the source '
                    'this leg asked for -- something overwrote it. NOT DRIVEN')
        r = subprocess.run(['node', dst], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', cwd=work)
        o = (r.stdout or '') + (r.stderr or '')
        reds = re.findall(r'^  FAIL (.+)$', o, re.M)
        return (r.returncode, reds, '')
    finally:
        shutil.rmtree(work, ignore_errors=True)


if not os.path.isdir(os.path.join(REPO, 'api')):
    die('api/ is absent.')

print('ABLATION -- b25 gate ordering, on a COPY. Live clone never written.')
if BEFORE:
    print('  --before: the suite is taken from %s (PRE-REPAIR, i.e. WITHOUT '
          'the empty-payload arm). G1 is EXPECTED to be ACCEPTED.'
          % BEFORE_REF)
print('')

rc, reds, note = run(None)
if rc is None:
    die(note)
print('  G3  CONTROL: the UNMUTATED copy                           exit=%s' % rc)
if rc != 0:
    print('')
    print('CONTROL FAILED -- nothing below is attributable.')
    for r_ in reds[:6]:
        print('    red: %s' % r_[:110])
    sys.exit(2)
print('')

bad = []
for name, what, old, new in CASES:
    rc, reds, note = run((old, new))
    if rc is None:
        print('  %-3s %-56s %s' % (name, what[:56], note))
        bad.append(name)
        continue
    empty_red = [r for r in reds if 'PAYLOAD THE HANDLER' in r]
    valid_red = [r for r in reds if 'write with NO session is refused' in r]
    # ── THE EXPECTATION IS PER LEG, AND THE FIRST VERSION WAS NOT ──────────
    # It applied the POST expectation to both legs, so the PRE run printed G1
    # and G2 as "NOT AS EXPECTED" when both were behaving exactly as a
    # pre-repair suite must. A harness that calls the correct pre-repair
    # result a failure is reporting on its own expectations rather than on the
    # subject -- the same class of defect as b24's silent clobber, just in the
    # labelling instead of the setup.
    if name == 'G1':
        if BEFORE:
            # PRE: the empty-payload arm does not exist, so NOTHING sees the
            # mutation. That is the hole, and it is the point of the leg.
            ok = not empty_red and not valid_red
            verdict = ('ACCEPTED -- the ordering is UNPROTECTED, which is the '
                       'finding this leg exists to establish' if ok
                       else '*** unexpected: something caught it pre-repair ***')
        else:
            ok = bool(empty_red) and not valid_red
            verdict = ('REFUSED -- and ONLY by the empty-payload arm, which is '
                       'the whole point' if ok
                       else '*** NOT DISCRIMINATING ***')
    else:
        if BEFORE:
            # PRE: only the valid-payload arm exists to catch a removed gate.
            ok = bool(valid_red) and not empty_red
            verdict = ('the valid-payload arm alone caught it -- correct, the '
                       'empty-payload arm does not exist in this leg' if ok
                       else '*** the control did not behave ***')
        else:
            ok = bool(empty_red) and bool(valid_red)
            verdict = ('BOTH write arms red (correct for this control)' if ok
                       else '*** the control did not behave ***')
    if not ok:
        bad.append(name)
    print('  %-3s %-56s exit=%-3s %s' % (name, what[:56], rc, verdict))
    print('        empty-payload arm red: %s   valid-payload arm red: %s'
          % (bool(empty_red), bool(valid_red)))

print('')
print('%d case(s) not as expected' % len(bad))
if bad:
    print('NOT AS EXPECTED: %s' % ', '.join(bad))
print('')
print('G1 IS THE ONE THAT MATTERS: under a body check placed before the gate,')
print("the pre-existing write arm stays GREEN because it sends a VALID")
print('payload. Only an arm that sends one the body would REFUSE can see the')
print('ordering at all.')
sys.exit(1 if bad else 0)
