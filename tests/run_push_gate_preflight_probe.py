#!/usr/bin/env python
"""Control for tools/sairn_push_gate_hook.py --preflight.

CONTROLS_FOR = ['sairn_push_gate_hook.py']

# REQUIREMENT: a session must be able to see EVERY push-gate finding in one
#   pass, and the ENFORCING path must be unchanged by the existence of that
#   mode.

WHY. `deny()` calls sys.exit(1) and there are 45 deny sites, so the enforcing
gate reaches exactly ONE of them. That is correct for enforcement -- when the
first check is fatal there is no value in running the other forty-four -- and
the cost lands on the session instead: you cannot learn what else is wrong
without fixing the first thing and pushing again.

MEASURED, ON MYSELF, THREE TIMES IN ONE SESSION. One batch was refused for
stale generated documents, fixed, re-pushed; refused for a missing
register-feed trailer, fixed, re-pushed; refused for an unrecorded Tier A
obligation, fixed, re-pushed. Three full rebase-regenerate-retry cycles against
a branch five clones push to, to learn three facts that were all true at the
same moment.

THE RISK IS THE REPORTING MODE WEAKENING THE REAL GATE, so P1 is the arm that
matters most and it is deliberately the dumbest one in the file: COLLECT must
be False at import. Everything else here is secondary to that.

THE SECOND RISK IS A PARTIAL SWEEP READING AS A CLEAN ONE. Code after a deny()
was written knowing it would never execute, so a continuation can crash. P3
requires the partial case to say so in its own output.

Run:  python tests/run_push_gate_preflight_probe.py
"""
import io
import os
import subprocess
import sys

CONTROLS_FOR = ['sairn_push_gate_hook.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')
sys.path.insert(0, os.path.join(REPO, 'tools'))

_pass = _fail = 0


def ok(n):
    global _pass
    _pass += 1
    sys.stdout.write('  ok   %s\n' % n)


def bad(n, why=''):
    global _fail
    _fail += 1
    sys.stdout.write('  FAIL %s\n' % n)
    if why:
        sys.stdout.write('       %s\n' % str(why)[:400])


def main():
    if not os.path.isfile(TOOL):
        sys.stderr.write('COULD NOT RUN: the push gate is absent. This '
                         'control tested nothing, which is not a pass.\n')
        return 2
    sys.stdout.write('PUSH GATE PREFLIGHT CONTROL -- criteria 2026-10-05.1\n\n')

    import sairn_push_gate_hook as g
    src = io.open(TOOL, encoding='utf-8').read()

    # ── THE ONE THAT MATTERS ───────────────────────────────────────────────
    if g.COLLECT is False and g.MODE == 'pretooluse' and g.COLLECTED == []:
        ok('P1. at import, COLLECT is False, MODE is pretooluse and COLLECTED '
           'is empty -- THE ENFORCING PATH IS UNCHANGED. A reporting mode that '
           'quietly stopped the real gate blocking would be worse than no mode '
           'at all, so this is the dumbest arm here and the most important')
    else:
        bad('P1. the enforcing defaults must be untouched',
            'COLLECT=%r MODE=%r COLLECTED=%r'
            % (g.COLLECT, g.MODE, g.COLLECTED))

    # deny() must RECORD and RETURN under COLLECT, and still exit otherwise.
    if 'if COLLECT:' in src and 'COLLECTED.append(reason)' in src:
        ok('P2. deny() records and returns when collecting')
    else:
        bad('P2. deny() must collect rather than exit in preflight')

    if 'sys.exit(1)' in src:
        ok('P3. ...and the exiting branch is still there, so P2 did not turn '
           'the gate into a reporter')
    else:
        bad('P3. the enforcing exit must survive')

    if ('COULD NOT COMPLETE THE SWEEP' in src
            and 'is not a clean bill for anything not listed' in src):
        ok('P4. a sweep that cannot finish reports a PARTIAL result and says '
           'it is not a clean bill -- code after a collected deny runs in a '
           'state its author never anticipated')
    else:
        bad('P4. the partial case must be named')

    if 'if code != 0:' in src:
        ok('P5. SystemExit(0) is NOT a crash. main() ends by exiting 0 to '
           'allow a push, so a COMPLETED sweep raises it -- the first version '
           'of preflight called that "could not complete" and reported a full '
           'sweep as partial, which is the opposite of the error this mode '
           'exists to prevent')
    else:
        bad('P5. a clean completion must not report as partial')

    tail = src.split('def preflight()')[1][:1200] if 'def preflight()' in src else ''
    if "MODE = 'prepush'" in tail:
        ok('P6. preflight reads the OUTGOING range like a real push, not the '
           'working tree -- otherwise it would preview a different question '
           'from the gate it claims to preview')
    else:
        bad('P6. preflight must use the push scope')

    # ── DRIVEN FOR REAL. Exit 0/1/2 are the three states; anything else is a
    #    crash, and a traceback would mean the mode is not usable.
    r = subprocess.run([sys.executable, TOOL, '--preflight'], cwd=REPO,
                       capture_output=True, timeout=400)
    out = (r.stdout or b'').decode('utf-8', 'replace') + \
          (r.stderr or b'').decode('utf-8', 'replace')
    if r.returncode in (0, 1, 2) and 'Traceback' not in out:
        ok('P7. driven against this clone: exit %d, one of the three declared '
           'states, no traceback' % r.returncode)
    else:
        bad('P7. preflight must return one of three states',
            'exit=%s\n%s' % (r.returncode, out[-400:]))

    if 'PUSH GATE PREFLIGHT' in out:
        ok('P8. ...and it identifies itself in its own output, so a reader '
           'cannot mistake it for the enforcing gate having run')
    else:
        bad('P8. the output must name the mode', out[-300:])

    if r.returncode == 0 and 'not a promise the push will pass' in out:
        ok('P9. a clean preflight REFUSES to promise the push will pass -- it '
           'runs the checks as they are, and a check needing state a real push '
           'creates can still refuse later')
    elif r.returncode in (1, 2) and 'FINDING(S)' in out:
        ok('P9. findings are reported with a count and each one in full, '
           'numbered -- the enforcing gate would have shown only the first')
    else:
        bad('P9. the verdict must carry its own limits', out[-400:])

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
