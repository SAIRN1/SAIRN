"""The control for tools/required_write_permission_check.py.

    python tests/run_required_write_permission_probe.py

Exit 0 all arms pass, 1 any arm fails, 2 could not run.

── WHY THE CHECK EXISTS (9b2735fa recurrence_open) ─────────────────────────
Two gates, each correct on its own, deadlocked one role for a fortnight:

  tools/tier_a_review_gate.py       DEMANDS a record in docs/tier-a-reviews.json
  tools/hover_auditor_scope_gate.py REFUSES that path from the auditor's clone

The auditor could neither push nor record. It fired at H2 seq 416 and again at
seq 422, and at 422 the record was written ON DISK to satisfy the push gate and
then reset because it could not be committed -- so the gate was satisfied by
something that did not persist, which is worse than either outcome alone.

9b2735fa removed the one TRIGGER that was firing. It did not, and could not,
answer the general question: IS EVERY FILE A SESSION IS REQUIRED TO WRITE INSIDE
THE SET IT IS PERMITTED TO WRITE? Nothing on this platform asked that. The next
gate demanding a record meets the same wall.

── THE FAILING-FIRST FIXTURE IS THE REAL PAIR, NOT AN INVENTED ONE ─────────
Arm 2 asserts the check FINDS the tier-a-reviews deadlock, for real auditor
sessions, against the real permission oracle. That pair is still latent at HEAD:
the skip clause stops the gate TRIPPING on auditor tooling, it does not stop the
gate DEMANDING that file if anything else trips it. A check that could not see
the case it was built for would be decoration.

── AND THE CONTROLS ARE WHAT KEEP IT FROM FLAGGING EVERYTHING ──────────────
A checker that reports every session against every path would "find" arm 2 and
be worthless. Arms 3-5 hold the other direction: a build agent under no
restriction is not reported, and a requirement the auditor IS permitted (the
defect register, which its own skill tells it to write) is not reported either.
"""
CONTROLS_FOR = ['required_write_permission_check.py']

import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'required_write_permission_check.py')

# ── FAIL CLOSED ON AN ABSENT SUBJECT (PR §1.11) ─────────────────────────────
if not os.path.isfile(TOOL):
    print('COULD NOT RUN -- tools/required_write_permission_check.py does not '
          'exist, so NOTHING was verified.')
    print('  MISSING  tools/required_write_permission_check.py')
    print('This is a FAILURE, not a skip.')
    sys.exit(2)

sys.path.insert(0, os.path.join(REPO, 'tools'))
import required_write_permission_check as C                      # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def run(*args):
    r = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                PYTHONUTF8='1'))
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('required-vs-permitted writes -- a gate must not demand what another '
      'gate forbids\n')

# ── A. THE REAL RUN ────────────────────────────────────────────────────────
rc, out = run()
check('A1. it runs and reports what it checked', 'SESSIONS_CHECKED:' in out,
      out[:400])
check('A2. ...and names its requirement population, so a reader can tell a '
      'clean answer from an empty one',
      'REQUIREMENTS:' in out, out[:400])
check('A3. ...and exits 1 on a finding, 0 clean, never anything else',
      rc in (0, 1), rc)
check('A4. ...and says plainly what it CANNOT see, because a checker that '
      'overstates its reach is worse than none',
      'cannot see' in out.lower(), out[-600:])

# ── B. THE CASE IT WAS BUILT FOR, AGAINST THE REAL ORACLES ─────────────────
rows = C.scan()
check('B1. scan() returns rows, so the population is not empty', bool(rows),
      rows)
bad = [r for r in rows if not r['permitted']]
check('B2. THE KNOWN DEADLOCK IS FOUND: an auditor session is REQUIRED to write '
      'docs/tier-a-reviews.json and is NOT PERMITTED to. This is the pair that '
      'blocked H2 twice and is still latent at HEAD -- 9b2735fa removed the '
      'trigger, not the requirement',
      any(r['session'].startswith('hover')
          and r['path'] == 'docs/tier-a-reviews.json' for r in bad),
      [(r['session'], r['path']) for r in bad])

# ── C. THE CONTROLS. Without these, "report everything" passes arm B2. ─────
check('C1. a BUILD AGENT is not reported for that same path -- no gate '
      'restricts what hank may write, so the requirement is satisfiable',
      not any(r['session'] == 'hank' and not r['permitted'] for r in rows),
      [(r['session'], r['path']) for r in rows
       if r['session'] == 'hank' and not r['permitted']])
check('C2. the DEFECT REGISTER is NOT reported for an auditor -- its own skill '
      'tells it to write findings there and the scope gate allows it, so a '
      'checker flagging it would be flagging the working case',
      not any(r['session'].startswith('hover')
              and r['path'] == 'docs/defect-density-register.json'
              and not r['permitted'] for r in rows),
      [(r['session'], r['path']) for r in rows if not r['permitted']])
check('C3. an auditor\'s OWN claim file is NOT reported -- the per-clone '
      'AuditorScope landed today makes that requirement satisfiable, and if it '
      'regresses this arm goes red',
      not any(r['session'].startswith('hover')
              and r['path'] == '.claude/claims/%s.json' % r['session']
              and not r['permitted'] for r in rows),
      [(r['session'], r['path']) for r in rows if not r['permitted']])

# ── D. THE ORACLE ITSELF, DRIVEN BOTH WAYS ────────────────────────────────
check('D1. permitted() says YES to a path the auditor may write',
      C.permitted('hover', '.claude/skills/sairn-hover-auditor/SKILL.md'))
check('D2. ...and NO to one it may not', not C.permitted('hover', 'api/sd-data.js'))
check('D3. ...and YES to anything for an unrestricted build session, which is '
      'what makes C1 a control rather than a coincidence',
      C.permitted('hank', 'api/sd-data.js')
      and C.permitted('cody', 'docs/tier-a-reviews.json'))
check('D4. ...and it is PER-INSTANCE: hover2 may write its own claim file and '
      'not H1\'s',
      C.permitted('hover2', '.claude/claims/hover2.json')
      and not C.permitted('hover2', '.claude/claims/hover.json'))

# ── E. EVERY REQUIREMENT IS ANCHORED IN THE TOOL THAT IMPOSES IT ──────────
# A declared table rots. Each entry names a string that must still appear in the
# source of the tool that demands it, so a requirement removed upstream shows up
# as a stale ANCHOR rather than as a finding nobody can act on.
check('E1. every requirement carries a required_by, a trigger and an anchor',
      all(r.get('required_by') and r.get('trigger') and r.get('anchor')
          for r in C.REQUIREMENTS), C.REQUIREMENTS)
check('E2. ...and every anchor is still present in the tool that imposes it',
      C.stale_anchors() == [], C.stale_anchors())

# ── F. FAIL CLOSED: NO ORACLE MEANS NO VERDICT ───────────────────────────
# The permission oracle is tools/hover_auditor_scope_gate.py. If it cannot be
# read, this check cannot tell a permitted path from a forbidden one -- and
# reporting "no findings" then would be the exact shape it exists to catch.
wt = tempfile.mkdtemp(prefix='rwp-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach',
                      wt, 'HEAD'], capture_output=True, text=True,
                     encoding='utf-8', errors='replace')
if add.returncode != 0:
    check('F0. a worktree could be created -- without one nothing below ran',
          False, add.stderr.strip()[:200])
else:
    try:
        shutil.copyfile(TOOL, os.path.join(wt, 'tools',
                                           'required_write_permission_check.py'))
        gate = os.path.join(wt, 'tools', 'hover_auditor_scope_gate.py')
        os.rename(gate, gate + '.hidden')
        r = subprocess.run([sys.executable,
                            os.path.join(wt, 'tools',
                                         'required_write_permission_check.py')],
                           cwd=wt, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        o = (r.stdout or '') + (r.stderr or '')
        check('F1. with the permission oracle GONE it exits 2 COULD NOT RUN, '
              'never 0 -- "could not tell" is a third state and folding it into '
              '"no findings" is the defect this check is about',
              r.returncode == 2 and 'COULD NOT RUN' in o,
              'exit=%s out=%s' % (r.returncode, o[-300:]))
        check('F2. ...and it names the oracle it could not read',
              'hover_auditor_scope_gate' in o, o[-300:])
        check('F3. ...and prints NO session count beside the refusal, because a '
              'count printed next to a failure is the number a reader keeps',
              'SESSIONS_CHECKED:' not in o, o[-300:])
    finally:
        subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', wt],
                       capture_output=True, text=True)
        shutil.rmtree(wt, ignore_errors=True)

print()
if fails:
    print('%d ARM(S) FAILED: %s' % (len(fails), ', '.join(fails)))
else:
    print('ALL ARMS PASS -- the known deadlock is found, and nothing '
          'satisfiable is reported beside it.')
sys.exit(1 if fails else 0)
