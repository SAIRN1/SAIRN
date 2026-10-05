#!/usr/bin/env python
# OWNER: fourth
r"""WHY DID THE PUSH FAIL? Classify the WHOLE output, never the last line.

    python tools/push_failure_reason.py            # run `git push`, classify it
    python tools/push_failure_reason.py --stdin     # classify output on stdin
    python tools/push_failure_reason.py --selftest  # fixtures, both directions

Exit 0 the push succeeded, 1 a classified refusal, 2 COULD NOT CLASSIFY.

── THE MISDIAGNOSIS THIS EXISTS FOR, 2026-10-05 ──────────────────────────
A push failed. The command piped it through `tail -3` and grepped for
`failed to push`, matched, and reported a lost race with another clone. It
was re-run TEN TIMES on that conclusion.

It was never a race. The gate had printed, forty lines above the bottom:

    Blocked: this push adds a tools/*.py file that does not say who owns it.

and, after that was fixed, a second one about a missing tool-inventory entry.
Both were one-line fixes sitting in plain text that nothing ever read, because
every look at the output was a `tail` or a `grep` for the symptom.

THE SYMPTOM IS AT THE BOTTOM AND THE CAUSE IS AT THE TOP. `error: failed to
push some refs` is git's epilogue and is present for EVERY failure -- a race,
a gate refusal, a bad credential. Matching it identifies nothing. The gate's
own `Blocked:` line names the cause, and there are 43 distinct ones.

── SO THE RULE THIS ENCODES ──────────────────────────────────────────────
A refusal is classified from the FULL text, and a `Blocked:` line ALWAYS wins
over a race signature. If both appear, the gate refused -- git's lock error
may simply be the next thing that happened. And anything unrecognised is
exit 2 COULD NOT CLASSIFY with the full output printed, never a guess: a
wrong label sent ten retries at a one-line fix once already.
"""

import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Git's own epilogue. Present on EVERY failure, so on its own it means
# "something failed" and nothing more. Never a classification.
EPILOGUE = re.compile(r'error: failed to push some refs', re.I)

# A genuine race with another clone. Each of these says the REMOTE moved.
RACE = [
    (re.compile(r'cannot lock ref .*: is at \w+ but expected \w+', re.I),
     'another clone pushed between this push being prepared and accepted'),
    (re.compile(r'the outgoing range \S+\.\.\S+ could not be read', re.I),
     'the gate could not read the push range -- the remote tip is a commit '
     'this clone does not have yet, i.e. somebody pushed during the attempt'),
    (re.compile(r'\[rejected\].*(non-fast-forward|fetch first)', re.I),
     'the branch moved; a fetch and rebase is needed before pushing'),
]

# The gate's own refusal. 43 distinct ones in sairn_push_gate_hook.py, so the
# text is NOT enumerated here -- the line itself is the message, and listing
# them would be a second copy that goes stale the next time one is added.
BLOCKED = re.compile(r'^\s*Blocked:\s*(.+)$', re.M)
COULD_NOT = re.compile(r'^\s*(COULD NOT (?:RUN|TELL)[^\n]*)$', re.M)


def classify(text):
    """(exit code, label, [detail lines]) from the FULL push output."""
    if not text.strip():
        return 2, 'COULD NOT CLASSIFY', ['the push produced no output at all']

    blocked = BLOCKED.findall(text)
    if blocked:
        # FIRST, AND BEFORE THE RACE CHECK, DELIBERATELY. A gate refusal and a
        # lock error can both appear -- the gate refuses, the human retries,
        # the remote has moved by then. Reporting the race would send the next
        # reader at the wrong problem, which is the whole incident above.
        detail = ['the push gate refused. %d refusal(s):' % len(blocked)]
        for b in blocked:
            detail.append('  * ' + b.strip())
        detail.append('')
        detail.append('THIS IS NOT A RACE. Fix the refusal above, then push.')
        return 1, 'GATE REFUSAL', detail

    for rx, why in RACE:
        m = rx.search(text)
        if m:
            return 1, 'RACE', ['matched: ' + m.group(0).strip(), why,
                               '', 'Fetch, rebase, re-derive any generated '
                               'document, then push again.']

    if EPILOGUE.search(text):
        # The symptom with no cause found. This is the state the incident
        # mislabelled, and it is exit 2 rather than a guess.
        notes = COULD_NOT.findall(text)
        detail = ['git reported a failed push and NOTHING in the output '
                  'matched a known refusal or race signature.',
                  'The full output follows -- read it rather than retrying.']
        if notes:
            detail.append('')
            detail.append('could-not-run notices seen (not themselves a refusal):')
            for n in notes[:6]:
                detail.append('  * ' + n.strip())
        detail.append('')
        detail.append('-' * 60)
        detail.extend(text.rstrip().split('\n'))
        return 2, 'COULD NOT CLASSIFY', detail

    return 0, 'PUSHED', ['no failure signature in the output']


def selftest():
    """Fixtures in BOTH directions. A classifier that says RACE to everything
    is as useless as the tail-grep it replaces, so every arm names what must
    NOT be returned as well as what must."""
    cases = [
        ('owner-header refusal, with the git epilogue underneath -- THE '
         'INCIDENT, reproduced',
         'COPY-EXACTLY -- no propagation detected\n'
         'Blocked: this push adds a tools/*.py file that does not say who\n'
         'owns it.\n  NO OWNER: 1\n'
         'error: failed to push some refs to \'https://github.com/x/y.git\'\n',
         1, 'GATE REFUSAL'),
        ('inventory refusal',
         'Blocked: this push adds a tools/ file with no entry in the tool\n'
         'inventory, and the generator refuses to run because of it.\n'
         'error: failed to push some refs\n', 1, 'GATE REFUSAL'),
        ('a REAL race, no Blocked line anywhere',
         ' ! [remote rejected]   main -> main (cannot lock ref '
         '\'refs/heads/main\': is at e8c2910 but expected c47c4fe)\n'
         'error: failed to push some refs\n', 1, 'RACE'),
        ('unreadable range -- also a race',
         'Blocked by nothing; the outgoing range abc123..def456 could not be '
         'read.\nerror: failed to push some refs\n', 1, 'RACE'),
        ('BOTH a refusal and a lock error -- the refusal must win',
         'Blocked: seed files do not match the live licence.\n'
         ' ! [remote rejected] main -> main (cannot lock ref: is at a but '
         'expected b)\nerror: failed to push some refs\n', 1, 'GATE REFUSAL'),
        ('failure with no recognisable cause -- must NOT be called a race',
         'error: failed to push some refs to \'https://github.com/x/y.git\'\n',
         2, 'COULD NOT CLASSIFY'),
        ('a COULD NOT RUN notice is not itself a refusal',
         'COULD NOT RUN -- java is not on PATH\n'
         'error: failed to push some refs\n', 2, 'COULD NOT CLASSIFY'),
        ('a clean push',
         'To https://github.com/x/y.git\n   9d91812b..3407178b  main -> main\n',
         0, 'PUSHED'),
        ('empty output',
         '', 2, 'COULD NOT CLASSIFY'),
        ('a seam-check warning alone is NOT a failure',
         'Seam check COULD NOT TELL for at least one endpoint/engine pair. '
         'The push is allowed.\nTo github.com\n   a..b  main -> main\n',
         0, 'PUSHED'),
    ]
    bad = 0
    for name, text, want_code, want_label in cases:
        code, label, _d = classify(text)
        ok = (code == want_code and label == want_label)
        print(('  ok   ' if ok else '  FAIL ') + name)
        if not ok:
            bad += 1
            print('        wanted %d/%s, got %d/%s'
                  % (want_code, want_label, code, label))
    # A control on the CONTROLS: the fixture set must exercise every verdict,
    # or an unreached branch looks tested.
    seen = set(classify(t)[1] for _n, t, _c, _l in cases)
    for want in ('GATE REFUSAL', 'RACE', 'COULD NOT CLASSIFY', 'PUSHED'):
        if want not in seen:
            print('  FAIL CONTROL: no fixture produces %s' % want)
            bad += 1
    print('\n%d case(s), %d failed' % (len(cases), bad))
    return 1 if bad else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--selftest' in argv:
        return selftest()
    if '--stdin' in argv:
        text = sys.stdin.read()
    else:
        p = subprocess.run(['git', 'push'], cwd=REPO, capture_output=True)
        text = (p.stdout + p.stderr).decode('utf-8', 'replace')
    code, label, detail = classify(text)
    print(label)
    for d in detail:
        print(d)
    return code


if __name__ == '__main__':
    sys.exit(main())
