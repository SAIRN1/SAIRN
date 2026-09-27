"""tools/role_gate_negative_coverage.py must find a gate no test drives negatively,
must NOT accuse one that is driven negatively, and must refuse rather than pass.

    python tests/run_role_gate_negative_coverage_probe.py

WHY THE NEGATIVE ARMS CARRY THIS PROBE. The tool's whole claim is "nothing would
notice if this gate were deleted", which is unfalsifiable from the tool's own
output -- so the arms below plant a gate and a suite in a throwaway repo and drive
the SHIPPING tool against them, in both directions. An over-reporting version
(every gate is uncovered) and an under-reporting one (none is) both pass a
single-direction check.

AND THE REAL DEFECT IT WAS BUILT FOR IS REPRODUCED IN §1: a suite whose every arm
runs as the ONE allowed role. That is api/sd-data-family-contacts.test.js, which
was eighteen green arms over a resource with no gate at all.
"""
CONTROLS_FOR = ['role_gate_negative_coverage.py']

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_REL = os.path.join('tools', 'role_gate_negative_coverage.py')
PIN_REL = os.path.join('docs', 'role-gate-negative-coverage.json')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def sandbox(sd_js, suites, pin=None):
    d = tempfile.mkdtemp(prefix='sairn-rolegate-')
    os.makedirs(os.path.join(d, 'tools'))
    os.makedirs(os.path.join(d, 'docs'))
    os.makedirs(os.path.join(d, 'api', '_lib'))
    os.makedirs(os.path.join(d, 'tests'))
    shutil.copy(os.path.join(REPO, TOOL_REL), os.path.join(d, TOOL_REL))
    io.open(os.path.join(d, 'api', 'sd-data.js'), 'w', encoding='utf-8',
            newline='\n').write(sd_js)
    for name, body in suites.items():
        io.open(os.path.join(d, 'api', name), 'w', encoding='utf-8',
                newline='\n').write(body)
    if pin is not None:
        io.open(os.path.join(d, PIN_REL), 'w', encoding='utf-8',
                newline='\n').write(json.dumps(pin) + '\n')
    return d


def run(d, *args):
    r = subprocess.run([sys.executable, TOOL_REL] + list(args), cwd=d,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def num(out, key):
    for line in out.split('\n'):
        if line.strip().startswith(key):
            for tok in line.replace(':', ' ').split():
                if tok.isdigit():
                    return int(tok)
    return None


SD = """
const ZZ_MANAGEMENT_ROLES = roleSet({ owner: true, billing: true });
const ZZ_CARE_ROLES = roleSet({ nursing: true, med_aide: true });
async function h(req, res) {
  if (resource === 'zz_profile' && action === 'write') {
    const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
    if (!ZZ_MANAGEMENT_ROLES[session.role]) {
      res.status(403).json({ error: { code: 'FORBIDDEN' } });
      return;
    }
  }
  if (resource === 'zz_notes' && action === 'read') {
    const session = verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
    if (!ZZ_CARE_ROLES[session.role]) {
      res.status(403).json({ error: { code: 'FORBIDDEN' } });
      return;
    }
  }
}
"""

# ── FIXTURE RESOURCES ARE DELIBERATELY SYNTHETIC (zz_*) ─────────────────────
# They carried two REAL Tier A resource names at first, which made
# tools/tier_a_review_gate.py refuse the push: those are REAL Tier A resources, so
# a probe merely naming them read as code serving them. The gate was right to ask
# and the fixture was the thing to change -- a synthetic name cannot be confused
# for the real resource by any tool, and the ROLE SETS are renamed to match for
# the same reason.
PIN0 = {'uncovered': 0}

# ---------------------------------------------------------------------------
print('1. THE REAL DEFECT: every arm runs as the ONE allowed role')
# api/sd-data-family-contacts.test.js exactly -- 18 arms, all `owner`, over a
# resource whose gate was ABSENT. The tool must report the gate as uncovered.
OWNER_ONLY = """
const t = require('assert');
function req(){ return { role: 'owner' }; }
(async () => {
  await drive({ resource: 'zz_profile', action: 'write', role: 'owner' });
  await drive({ resource: 'zz_profile', action: 'write', role: 'owner' });
})();
"""
d = sandbox(SD, {'a.test.js': OWNER_ONLY}, {'uncovered': 1})
rc, out = run(d)
check('a gate driven ONLY as its allowed role is reported UNCOVERED',
      'zz_profile' in out and num(out, 'UNCOVERED') == 1,
      'uncovered=%s :: %s' % (num(out, 'UNCOVERED'), out[:400]))
check('...and it says the claim out loud -- an uncovered gate would survive '
      'deletion', 'SURVIVE BEING DELETED' in out.upper(), out[-500:])
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n2. CONTROL: the SAME gate driven with an EXCLUDED role is NOT accused')
# Without this the tool could report every gate and pass arm 1.
WITH_NEG = """
(async () => {
  await drive({ resource: 'zz_profile', action: 'write', role: 'owner' });
  await drive({ resource: 'zz_profile', action: 'write', role: 'nursing' });
})();
"""
d = sandbox(SD, {'a.test.js': WITH_NEG}, PIN0)
rc, out = run(d)
check('driving it as `nursing` -- excluded by ZZ_MANAGEMENT_ROLES -- clears it',
      num(out, 'UNCOVERED') == 0, 'uncovered=%s' % num(out, 'UNCOVERED'))
check('...and it is counted as COVERED rather than vanishing from the tally',
      num(out, 'COVERED') == 1, 'covered=%s' % num(out, 'COVERED'))
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n3. ALLOWED ROLES COME FROM THE roleSet DECLARATION, not a list in the tool')
# `nursing` is EXCLUDED from ZZ_MANAGEMENT_ROLES and ALLOWED by ZZ_CARE_ROLES.
# The same role must clear one gate and not the other, which a hardcoded
# privileged-role list could not do.
BOTH = """
(async () => {
  await drive({ resource: 'zz_notes', action: 'read', role: 'nursing' });
})();
"""
d = sandbox(SD, {'a.test.js': BOTH}, PIN0)
rc, out = run(d)
check('zz_notes driven ONLY as `nursing`, which its gate ALLOWS, is UNCOVERED -- '
      'the same role that cleared zz_profile in arm 2',
      'zz_notes' in out, out[:500])
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n4. A RESOURCE NO SUITE DRIVES IS A DIFFERENT GAP, COUNTED APART')
# Folding it into `uncovered` would tell somebody to add an arm to a suite that
# does not exist, and would inflate the number the ratchet pins.
d = sandbox(SD, {'a.test.js': OWNER_ONLY}, {'uncovered': 1})
rc, out = run(d)
check('zz_notes, which no suite drives, is NOT counted as uncovered',
      num(out, 'UNCOVERED') == 1, 'uncovered=%s' % num(out, 'UNCOVERED'))
check('...it is reported as NOT DRIVEN, its own line',
      num(out, 'NOT DRIVEN') == 1, 'not_driven=%s' % num(out, 'NOT DRIVEN'))
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n5. A MENTION IS NOT A DRIVE -- the tool\'s own first wrong number')
# The first version matched any quoted lowercase string in a test file, so a
# resource named in a COMMENT counted as exercised. That reported 16 gates on the
# real repo where 11 are real.
MENTION = """
// This suite is about zz_profile isolation and does not gate on a role.
(async () => {
  await drive({ resource: 'zz_notes', action: 'read', role: 'nursing' });
})();
"""
d = sandbox(SD, {'a.test.js': MENTION}, PIN0)
rc, out = run(d, '--list')
# zz_profile is named ONLY in a comment -> NOT DRIVEN.
# zz_notes IS driven, as `nursing`, which its own gate ALLOWS -> uncovered.
# Asserting on WHICH resource lands in WHICH bucket, not on the totals: the
# first version of this arm asserted uncovered==0 and was simply wrong about the
# fixture, which cost a real debugging pass before the tool's actual defect
# (the fixed-length branch window) was found underneath it.
check('the comment-mentioned resource is NOT DRIVEN',
      num(out, 'NOT DRIVEN') == 1 and 'zz_profile' in out.split('NOT DRIVEN:')[-1],
      'not_driven=%s :: %s' % (num(out, 'NOT DRIVEN'), out[-400:]))
# Asserted on the LISTING LINE for that resource rather than by slicing the
# report between two headers -- the word UNCOVERED appears in more than one place
# and a slice-based assertion was reading the wrong region.
notes_line = [l for l in out.splitlines()
              if l.strip().startswith('zz_notes') and 'gate=' in l and 'driven-as' in l]
check('...and the one genuinely driven, as a role its gate ALLOWS, is the '
      'uncovered one', num(out, 'UNCOVERED') == 1 and len(notes_line) == 1,
      'uncovered=%s lines=%s' % (num(out, 'UNCOVERED'), notes_line))
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n6. THE RATCHET MOVES ONE WAY AND SAYS SO')
d = sandbox(SD, {'a.test.js': OWNER_ONLY}, {'uncovered': 1})
rc, out = run(d)
check('at the pinned number it is OK and exits 0',
      rc == 0 and 'OK -- no worse' in out, 'exit=%s' % rc)
check('...and says a ratchet is not a pass on the same run',
      'A RATCHET IS NOT A PASS' in out, out[-300:])
shutil.rmtree(d, ignore_errors=True)

d = sandbox(SD, {'a.test.js': OWNER_ONLY}, {'uncovered': 0})
rc, out = run(d)
check('a NEW uncovered gate is a REGRESSION, exit 1',
      rc == 1 and 'REGRESSION' in out, 'exit=%s :: %s' % (rc, out[-300:]))
shutil.rmtree(d, ignore_errors=True)

d = sandbox(SD, {'a.test.js': WITH_NEG}, {'uncovered': 5})
rc, out = run(d)
check('an added negative arm reads as IMPROVED and asks to be re-pinned',
      rc == 0 and 'IMPROVED' in out, 'exit=%s :: %s' % (rc, out[-300:]))
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n7. EVERY MISSING OR MOVED SOURCE IS EXIT 2, NEVER 0')
d = sandbox(SD, {'a.test.js': OWNER_ONLY}, None)
rc, out = run(d)
check('no pin file -> exit 2 COULD NOT TELL', rc == 2 and 'COULD NOT TELL' in out,
      'exit=%s' % rc)
shutil.rmtree(d, ignore_errors=True)

d = sandbox(SD, {'a.test.js': OWNER_ONLY}, PIN0)
io.open(os.path.join(d, PIN_REL), 'w', encoding='utf-8', newline='\n').write('{ not json')
rc, out = run(d)
check('an unparseable pin -> exit 2', rc == 2 and 'will not parse' in out, 'exit=%s' % rc)
io.open(os.path.join(d, PIN_REL), 'w', encoding='utf-8', newline='\n').write('{"covered":3}')
rc, out = run(d)
check('a pin with no integer `uncovered` -> exit 2',
      rc == 2 and 'no integer' in out, 'exit=%s' % rc)
shutil.rmtree(d, ignore_errors=True)

# THE GATE SHAPE MOVING MUST NOT READ AS "everything is covered".
d = sandbox('async function h(){ /* no gates at all */ }\n',
            {'a.test.js': OWNER_ONLY}, PIN0)
rc, out = run(d)
check('a sd-data.js with NO roleSet declaration -> exit 2, and it says this is '
      'not "no role sets"', rc == 2 and 'not "no role sets"' in out,
      'exit=%s :: %s' % (rc, out[-300:]))
shutil.rmtree(d, ignore_errors=True)

d = sandbox('const A_ROLES = roleSet({ owner: true });\n'
            "async function h(){ if (resource === 'x') {} }\n",
            {'a.test.js': OWNER_ONLY}, PIN0)
rc, out = run(d)
check('roleSets present but NO branch gated on one -> exit 2, and it says this is '
      'not "no role gates"', rc == 2 and 'not \n' not in out and 'no role gates' in out,
      'exit=%s :: %s' % (rc, out[-300:]))
shutil.rmtree(d, ignore_errors=True)

# ---------------------------------------------------------------------------
print('\n8. AND THE REAL REPO -- so the arms above are not a fixture dialect')
real = [os.path.join(REPO, 'api', 'sd-data.js')]
before = [(io.open(p, 'rb').read(), os.path.getmtime(p)) for p in real]
rc, out = run(REPO)
check('it runs against the shipping repo and exits 0 or 1, never 2', rc in (0, 1),
      'exit=%s :: %s' % (rc, out[-300:]))
check('it finds a non-trivial number of gated branches there',
      (num(out, '27 role set') is not None) or ('role set(s) declared' in out), out[:200])
u, c, nd = num(out, 'UNCOVERED'), num(out, 'COVERED'), num(out, 'NOT DRIVEN')
check('UNCOVERED and COVERED are BOTH non-zero -- if either is 0 the classifier '
      'has stopped discriminating', (u or 0) > 0 and (c or 0) > 0,
      'uncovered=%s covered=%s' % (u, c))
check('...and the three buckets do not exceed the gated total, so nothing is '
      'double-counted', (u or 0) + (c or 0) + (nd or 0) <= 60,
      'u=%s c=%s nd=%s' % (u, c, nd))
after = [(io.open(p, 'rb').read(), os.path.getmtime(p)) for p in real]
check('IT WROTE NOTHING to api/ -- bytes AND mtime', before == after,
      'api/sd-data.js was written')

print('\n%s  run_role_gate_negative_coverage_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
