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

    # == THE ENFORCING PATH COLLECTS TOO, AND THE CRASH HANDLER IS THE RISK ==
    # --preflight reported all 45 while the real gate still stopped at one, so
    # a session learned one fact per rebase cycle against a shared branch. The
    # enforcing path collects now. It still DENIES; it denies with the list.
    #
    # E3 IS THE ARM THE WHOLE CHANGE TURNS ON. The gate ends with
    # `except Exception: sys.exit(0)` -- and exit 0 means ALLOW. Code after a
    # deny() was written knowing it would never execute, so a continuation can
    # raise. Collecting WITHOUT touching that handler would have converted the
    # first continuation crash into a silent allow, which is strictly worse
    # than reaching one check. Both directions are driven.
    import io as _io

    def _drive(source, argv):
        inject = ('\ndef main():\n' +
                  '    deny(\'INJECTED FIRST: a stale generated document\')\n' +
                  '    deny(\'INJECTED SECOND: no register record\')\n' +
                  '    raise RuntimeError(\'continuation\')\n')
        src2 = source.replace('if __name__ == \'__main__\':',
                              inject + '\nif __name__ == \'__main__\':', 1)
        old = sys.argv
        sys.argv = argv
        buf = _io.StringIO()
        real = sys.stderr
        sys.stderr = buf
        code = 'NO EXIT'
        try:
            exec(compile(src2, TOOL, 'exec'), {'__name__': '__main__'})
        except SystemExit as e:
            code = e.code if e.code is not None else 0
        except Exception as e:
            code = 'RAISED %s' % type(e).__name__
        finally:
            sys.stderr = real
            sys.argv = old
        return code, buf.getvalue()

    code, out = _drive(src, ['gate', '--pre-push'])
    if code == 1 and 'INJECTED FIRST' in out and 'INJECTED SECOND' in out:
        ok('E1. a main() that denies TWICE then RAISES still exits 1, and BOTH ' +
           'reasons print -- the push is denied with the whole list even ' +
           'though a continuation crashed')
    else:
        bad('E1. a crash after collected denials must still deny',
            'exit=%r out=%s' % (code, out[-250:]))

    if 'check(s) refused this push' in out:
        ok('E2. ...and the header states HOW MANY refused, so a reader knows ' +
           'the list is the whole answer rather than the first item of one')
    else:
        bad('E2. the multi-denial header must be present', out[-250:])

    bad_src = src.replace('        _deny_now_if_any()\n        sys.exit(0)',
                          '        sys.exit(0)')
    if bad_src != src:
        code_b, _ = _drive(bad_src, ['gate', '--pre-push'])
        if code_b == 0:
            ok('E3. KNOWN-BAD CONFIRMED, AND IT IS WHY COLLECTING IS SAFE: with ' +
               'the denial-outranks-fail-open line removed, the same run exits ' +
               '0 -- it ALLOWS a push carrying two collected denials. That is ' +
               'the regression collecting would have introduced, and this arm ' +
               'fails if the line is ever removed again')
        else:
            bad('E3. the known-bad must ALLOW, proving the line is load-bearing',
                'exit=%r' % (code_b,))
    else:
        bad('E3. could not construct the known-bad',
            'the fail-open handler no longer matches the expected shape')

    if 'if \'--one\' not in sys.argv' in src:
        ok('E4. `--one` still restores stop-at-the-first, so the old ' +
           'behaviour is available rather than removed')
    else:
        bad('E4. the old behaviour must remain reachable')

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
