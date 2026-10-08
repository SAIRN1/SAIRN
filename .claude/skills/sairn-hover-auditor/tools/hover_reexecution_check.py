#!/usr/bin/env python
"""Given a CLAIM (command, claimed exit code, optional claimed output
substrings), re-run the command for real in this clone and compare.
A mismatch is a finding regardless of what was reported.

Own tool, own location. Built 2026-10-06 (H1, batch H, item 6). Design
logged to hover-audit-log.jsonl before this file was written. Independent
of H2's own hover2_claim_reexecute.py -- same question, separate
implementation, same reason this platform runs two hover auditors at all.

THREE STATES, NEVER TWO: a process that fails to launch (bad path, no
interpreter, timeout) is COULD_NOT_RUN, never silently folded into MATCH
or MISMATCH.

CANNOT SEE: whether the claim's own INTERPRETATION of its output was
reasonable -- only whether the exit code and named substrings reproduce.
Does not sandbox a command's side effects; the caller is responsible for
only passing read-only/test commands, same discipline this role already
applies by hand to every command it runs.
"""
import subprocess
import sys

DEFAULT_TIMEOUT = 90

# shell=True does NOT raise OSError for a command the shell itself cannot
# find -- the SHELL launches fine and reports the failure as ordinary
# nonzero-exit output. FOUND BY THIS TOOL'S OWN SELFTEST, FIRST RUN (same
# shape H2's hover2_claim_reexecute.py already hit on this same Windows
# host, independently): cmd.exe answers "'x' is not recognized as an
# internal or external command", exit 1 -- not bash's exit 127 and not an
# OSError either. Both phrases are checked so a command-not-found reads as
# COULD_NOT_RUN rather than a false MISMATCH on this host.
_NOT_FOUND_PHRASES = (
    'is not recognized as an internal or external command',
    'command not found',
)


def reexecute(command, cwd, claimed_exit=None, claimed_contains=None, timeout=DEFAULT_TIMEOUT):
    """Every return value echoes the EXACT inputs used (command, cwd,
    claimed_exit, claimed_contains) -- added (batch J, item 7) after a real
    false mismatch (batch I) traced back to this role's own PARAPHRASE of a
    claim being passed in as if it were a literal quote. Recording the exact
    inputs alongside the verdict means a reader can tell, without re-deriving
    anything, whether a MISMATCH means the underlying claim was wrong or the
    re-execution's OWN claimed_contains string was never going to appear."""
    claimed_contains = claimed_contains or []
    inputs = {'command': command, 'cwd': cwd, 'claimed_exit': claimed_exit,
              'claimed_contains': list(claimed_contains)}
    try:
        p = subprocess.run(command, shell=True, cwd=cwd, capture_output=True,
                            text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {'verdict': 'COULD_NOT_RUN', 'reason': 'timed out after %ds' % timeout, 'inputs': inputs}
    except OSError as e:
        return {'verdict': 'COULD_NOT_RUN', 'reason': 'process did not launch: %s' % e, 'inputs': inputs}
    real_exit = p.returncode
    real_output = (p.stdout or '') + (p.stderr or '')
    if any(phrase in real_output for phrase in _NOT_FOUND_PHRASES):
        return {'verdict': 'COULD_NOT_RUN', 'reason': 'shell reported command not found: %s' % real_output.strip()[:200], 'inputs': inputs}
    mismatches = []
    if claimed_exit is not None and real_exit != claimed_exit:
        mismatches.append('exit: claimed %r, got %r' % (claimed_exit, real_exit))
    for needle in claimed_contains:
        if needle not in real_output:
            mismatches.append('missing claimed substring: %r' % needle)
    if mismatches:
        return {'verdict': 'MISMATCH', 'reason': '; '.join(mismatches),
                'real_exit': real_exit, 'real_output_tail': real_output[-500:], 'inputs': inputs}
    return {'verdict': 'MATCH', 'real_exit': real_exit, 'inputs': inputs}


# ---------------------------------------------------------------------------
# Selftest: one claim known true, one known false. Platform-independent --
# uses python -c so it does not depend on any repo file existing.
# ---------------------------------------------------------------------------

def _selftest():
    import os
    cwd = os.getcwd()
    ok = 0
    r1 = reexecute('python -c "import sys; print(\'ok-marker\'); sys.exit(0)"',
                   cwd, claimed_exit=0, claimed_contains=['ok-marker'])
    status1 = 'ok  ' if r1['verdict'] == 'MATCH' else 'FAIL'
    if r1['verdict'] == 'MATCH':
        ok += 1
    print('  %s known-TRUE claim (exit 0, contains ok-marker) -> %s' % (status1, r1['verdict']))

    r2 = reexecute('python -c "import sys; print(\'ok-marker\'); sys.exit(0)"',
                   cwd, claimed_exit=1, claimed_contains=['this-string-does-not-appear'])
    status2 = 'ok  ' if r2['verdict'] == 'MISMATCH' else 'FAIL'
    if r2['verdict'] == 'MISMATCH':
        ok += 1
    print('  %s known-FALSE claim (claimed exit 1 + wrong substring) -> %s (%s)'
          % (status2, r2['verdict'], r2.get('reason')))

    r3 = reexecute('this_binary_does_not_exist_anywhere_xyz --flag', cwd, claimed_exit=0)
    status3 = 'ok  ' if r3['verdict'] == 'COULD_NOT_RUN' else 'FAIL'
    if r3['verdict'] == 'COULD_NOT_RUN':
        ok += 1
    print('  %s nonexistent command -> %s, never forced into MATCH/MISMATCH' % (status3, r3['verdict']))

    print('%d/3 fixture checks correct' % ok)
    return ok == 3


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    print('usage: hover_reexecution_check.py --selftest  (library use: import and call reexecute())')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
