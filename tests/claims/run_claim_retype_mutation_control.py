"""tests/claims/run_claim_retype_mutation_control.py

Run:  python tests/claims/run_claim_retype_mutation_control.py

THE NEGATIVE CONTROL FOR THE RETYPED-TASK GUARD -- AND IT VERIFIES ITS OWN
SABOTAGE APPLIED.

Measured on this platform on 2026-09-13 by `tools/sabotage_control_check.py`:
23 of 39 negative controls NEVER VERIFY THEIR OWN SABOTAGE APPLIED. A control
that greps for a string that no longer exists, mutates nothing, and then reports
"the suite went red" is reporting nothing at all -- it would pass identically
against a subject with the defect still in it.

So every mutation below is asserted in THREE parts, in order:

  1. the anchor is FOUND in the shipped tool exactly once  (else: stale anchor)
  2. the mutated copy DIFFERS from the original            (else: no-op edit)
  3. run_push_verify_probe.py, run against the mutated tool, EXITS NON-ZERO

Part 1 is the arm that rots silently. Part 2 is the half the 23 skipped.

── WHY THIS EXISTS SEPARATELY FROM befb65e3'S OWN SABOTAGE RUN ───────────────
befb65e3 recorded that its three changes were sabotage-verified, and they were.
But its section-9 arms drive the retry with the SAME task string, while its own
commit message says the real incident was "the task string slightly retyped
between attempts". Driven with the two real strings, the tool as shipped still
published TWO claims from three attempts. A sabotage run proves an arm can go
red; it cannot tell you the arm is aimed at the case that actually happened.

The mutations are written to a temp copy. tools/sairn_claim.py is never touched,
and the closing section asserts that.
"""
# REQUIREMENT: the retyped-task guard in sairn_claim.py is proved by mutation,
#   with each sabotage verified to have found its anchor exactly once and to
#   have changed the file, so the control cannot quietly become a no-op against
#   a subject that still has the defect
#

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'tools', 'sairn_claim.py')
PROBE = os.path.join(ROOT, 'tests', 'claims', 'run_push_verify_probe.py')

with open(SRC, encoding='utf-8') as f:
    ORIGINAL = f.read()

passed = 0
failed = 0


def check(name, cond, detail=''):
    global passed, failed
    if cond:
        print('  ok   ' + name)
        passed += 1
    else:
        print('  FAIL ' + name + (('\n       ' + detail) if detail else ''))
        failed += 1


def baseline_ok(rc, out):
    """Is the probe usable as a negative control at all?

    Extracted so the refusal below can be DRIVEN in both directions rather
    than reasoned about. A control that stops on a red baseline is itself a
    guard, and a guard that has never been shown to fire is not yet a guard.
    """
    return rc == 0 and '11. a RETYPED task string' in out


def run_probe(tool_path):
    env = dict(os.environ)
    env['SAIRN_CLAIM_TOOL'] = tool_path
    r = subprocess.run([sys.executable, PROBE], cwd=ROOT, env=env,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


# EVERY MUTATION IS A REAL DEFECT SOMEBODY COULD WRITE, never a syntax error.
# A control that sabotages by breaking the parse proves only that the file still
# has to parse.
MUTATIONS = [
    {
        'name': 'the retyped-task guard is removed entirely -- the shipped defect',
        'find': "    if stuck:\n",
        'replace': "    if False:\n",
    },
    {
        'name': 'an unreadable origin is treated as PUBLISHED -- the fail-OPEN '
                'version of published_claim_ids',
        'find': "            if published is None or c.get('id') not in published:",
        'replace': "            if published is not None and c.get('id') not in published:",
    },
    {
        'name': 'the guard matches on task as well, so it only ever fires on the '
                'case the byte-for-byte guard already caught',
        'find': "            if c.get('status') != 'active' or c.get('subject') != subj:",
        'replace': "            if (c.get('status') != 'active' or c.get('subject') != subj\n"
                   "                    or c.get('task') != task):",
    },
    {
        'name': 'the refusal stops naming the earlier wording, so it cannot be acted on',
        'find': "        print('  already here (unpublished): %s' % (earlier.get('task') or '(no task)'))",
        'replace': "        print('  already here (unpublished): (an earlier claim)')",
    },
    {
        'name': 'the refusal stops printing the command that publishes the earlier entry',
        'find': "        print('  python tools/sairn_claim.py claim %s %s' % (subj, earlier.get('task') or ''))",
        'replace': "        print('  python tools/sairn_claim.py list')",
    },
]


def main():
    print('sairn_claim.py retyped-task guard: every arm is shown to FAIL on a '
          'sabotaged subject\n')
    tmp = tempfile.mkdtemp(prefix='sairn-claim-mutation-')
    try:
        # ── 0. BASELINE ──────────────────────────────────────────────────────
        # The probe must be GREEN against the untouched tool first. Without
        # this, every "went red" below could be a probe that is red for an
        # unrelated reason.
        print('0. baseline -- the probe is green against the shipped tool')
        clean = os.path.join(tmp, 'clean_sairn_claim.py')
        shutil.copy(SRC, clean)
        rc, out = run_probe(clean)
        baseline_green = rc == 0
        reached_11 = '11. a RETYPED task string' in out
        check('run_push_verify_probe.py passes against an unmutated copy '
              '(exit %s)' % rc, baseline_green, out[-800:])
        check('...and it really ran section 11, so the arms below have something '
              'to break', reached_11, out[-400:])
        # THE REFUSAL ITSELF IS DRIVEN, BOTH WAYS. Without this the "stop on a
        # red baseline" rule below is a branch nothing has ever taken, which is
        # the same shape as the vacuous arms it was added to prevent.
        check('the baseline rule ACCEPTS this run', baseline_ok(rc, out))
        check('...and REFUSES a probe that exited non-zero',
              not baseline_ok(1, out))
        check('...and REFUSES a probe that never reached section 11, even at '
              'exit 0 -- a probe that stops early proves nothing either',
              not baseline_ok(0, 'ok everything\n69 passed, 0 failed'))

        # ── A RED BASELINE STOPS THE RUN. IT DOES NOT PRODUCE 25 PASSES ──────
        # FOUND 2026-09-22 (Fourth), and it is this file's own subject turned on
        # itself. Section 0 was failing -- `527b31bf` moved session identity
        # from the folder name to a per-clone marker, and the probe's throwaway
        # clone had neither the marker nor the tool's new sibling module, so
        # run_push_verify_probe.py exited 1 against a CLEAN tool.
        #
        # EVERY ARM BELOW ASSERTS "the probe FAILS on this mutation", AND A
        # PROBE THAT FAILS UNCONDITIONALLY SATISFIES ALL OF THEM. So the five
        # sabotages were reported as caught by a control that would have said
        # the same with the mutations never applied: 25 of 26 passes vacuous,
        # in the file whose whole job is proving a guard can fail. That is
        # tool-bugs item 10 -- a red baseline hides the health of everything
        # behind it.
        #
        # The baseline arm was working perfectly: it FAILED and said so. What
        # was missing was anything that stopped the run once it had.
        if not baseline_ok(rc, out):
            print('\nCOULD NOT RUN -- the baseline is red, so "the probe failed '
                  'on this\nmutation" cannot be distinguished from "the probe '
                  'fails on everything".\nThe five mutation sections are SKIPPED '
                  'rather than reported as caught.')
            print('\n%d passed, %d failed' % (passed, failed))
            return 2

        print('\n1. each mutation: found, applied, and caught')
        for idx, m in enumerate(MUTATIONS, 1):
            print('\n  [%d] %s' % (idx, m['name']))

            hits = ORIGINAL.count(m['find'])
            check('the anchor is present in tools/sairn_claim.py EXACTLY once '
                  '(found %d)' % hits, hits == 1)
            if hits != 1:
                continue

            mutated = ORIGINAL.replace(m['find'], m['replace'])
            check('the mutated copy differs from the original', mutated != ORIGINAL)
            path = os.path.join(tmp, 'mutant_%d_sairn_claim.py' % idx)
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(mutated)
            with open(path, encoding='utf-8') as f:
                on_disk = f.read()
            check('...and the mutation is present in the file on disk the probe '
                  'will copy', m['replace'].split('\n')[0] in on_disk)
            # A mutation that no longer parses would take the probe red for the
            # wrong reason, and this control would read that as evidence.
            try:
                compile(on_disk, path, 'exec')
                parses = True
            except SyntaxError as e:                              # noqa: BLE001
                parses = False
                print('       SyntaxError: %s' % e)
            check('...and it still PARSES, so a red probe is the guard failing '
                  'and not the file', parses)
            if not parses:
                continue

            rc, out = run_probe(path)
            tail = '\n'.join([l for l in out.split('\n') if l.strip()][-8:])
            # ── "FAILED" IS NOT THE SAME CLAIM AS "CAUGHT" ──────────────────
            # A non-zero exit can mean the guard refused the mutation, or it
            # can mean the probe fell over before it ever tested one. Those
            # look identical from an exit code, and telling them apart is the
            # whole point of a negative control. THREE PARTS:
            #   1. it exited non-zero at all;
            #   2. it REACHED the section that tests this guard, so the failure
            #      is downstream of the mutation rather than upstream of it;
            #   3. it reported a FAILED ARM rather than crashing -- a traceback
            #      is a broken probe, not a caught defect.
            reached = '11. a RETYPED task string' in out
            armed = '  FAIL ' in out
            crashed = 'Traceback (most recent call last)' in out
            check('run_push_verify_probe.py FAILS on it (exit %s)' % rc,
                  rc != 0, tail)
            check('...and it REACHED the section that tests this guard, so the '
                  'failure is the mutation and not an earlier collapse',
                  reached, tail)
            check('...and it reported a FAILED ARM rather than a traceback, so '
                  'the guard refused rather than the probe breaking',
                  armed and not crashed, tail)

        # ── 2. THE SHIPPED TOOL IS UNTOUCHED ─────────────────────────────────
        print('\n2. tools/sairn_claim.py was never written to')
        with open(SRC, encoding='utf-8') as f:
            check('the shipped tool is byte-identical to how this run found it',
                  f.read() == ORIGINAL)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('\n%d passed, %d failed' % (passed, failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
