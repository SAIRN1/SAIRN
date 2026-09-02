"""Prove the claim matcher still blocks what matters after the 2026-09-02
generic-token change, and stops blocking what it never should have.

WHY THIS EXISTS. The change makes the tool QUIETER, and a gate made quieter
without a test is a gate on its way to protecting nothing. sairn_claim.py's own
comment states the asymmetry it must keep: over-flagging costs a five-second
read, under-flagging costs four hours. So the arms below weight the
false-negative side deliberately -- every historical TRUE block is re-run and
must still block.

Pure function-level assertions on blocks_alone(). No files written, no claims
committed, nothing touching .claude/claims -- which matters because `list` and
`check` overwrite that directory from origin/main (CLAUDE.md defect 2), so a
probe that exercised the CLI could destroy a real uncommitted claim.
"""
import importlib.util
import os
import subprocess
import sys

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
spec = importlib.util.spec_from_file_location(
    'sairnclaim', os.path.join(REPO, 'tools', 'sairn_claim.py'))
claim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claim)


def shared(a_subj, a_task, b_subj, b_task):
    return claim.tokens(a_subj, a_task) & claim.tokens(b_subj, b_task)


def verdict(a_subj, a_task, b_subj, b_task):
    s = shared(a_subj, a_task, b_subj, b_task)
    return ('BLOCK' if claim.blocks_alone(s) else 'note') if s else 'clear'


# (label, mine, theirs, expected)
CASES = [
    # ── MUST STILL BLOCK. These are the reason the tool exists. ────────────
    ('same app, same subject',
     ('sairnroofing', 'shared subcontractor compliance layer'),
     ('sairnroofing', 'subcontractor compliance panel wiring'), 'BLOCK'),
    ('the real 2026-08-30 duplication: same app, same gate',
     ('sairnfreedom', 'competitive scan'),
     ('sairnfreedom', 'competitive and patent scan'), 'BLOCK'),
    ('same app, adjacent phases -- arguably fair, and still blocks',
     ('sairnfreedom', 'phase 2'),
     ('sairnfreedom', 'phase 3'), 'BLOCK'),
    ('different app but a shared SPECIFIC feature word',
     ('sairnroofing', 'warranty registration'),
     ('sairnbuild', 'warranty tracking'), 'BLOCK'),
    ('two shared generic words is enough to be worth a read',
     ('sairnvet', 'audit fix'),
     ('stonedesk', 'audit fix'), 'BLOCK'),

    # ── MUST NOT BLOCK. Both are real false positives from the record. ─────
    ('2026-09-01: blocked on the word "audit" alone',
     ('sairnvet', 'employee auth deactivation audit'),
     ('stonedesk', 'safehtml audit'), 'note'),
    ('2026-09-02: blocked on the word "gap" alone (x2 that night)',
     ('sairnroofing', 'crew field labour scheduling depth gap A2'),
     ('sairnsenior', 'caregiver training hours in-service gap A6'), 'note'),
    ('2026-09-02, the second one',
     ('sairnroofing', 'crew field labour scheduling depth gap A2'),
     ('sairndental', 'payer enrolment credentialing lifecycle gap B1'), 'note'),
    ('genuinely unrelated work shares nothing',
     ('sairnroofing', 'crew scheduling'),
     ('sairnlaw', 'grounded definitions in drafting'), 'clear'),
]

fails = 0
for label, mine, theirs, expected in CASES:
    got = verdict(mine[0], mine[1], theirs[0], theirs[1])
    ok = got == expected
    fails += 0 if ok else 1
    print('%-5s %-8s (want %-5s)  %s' % ('ok' if ok else 'FAIL', got, expected, label))
    if not ok:
        print('        shared: %s' % sorted(shared(mine[0], mine[1], theirs[0], theirs[1])))

# ── the list itself must stay short and must not swallow an app name ───────
print()
too_long = len(claim.GENERIC_TOKENS) > 20
print('%-5s GENERIC_TOKENS is %d entries (cap 20 -- every addition makes the '
      'tool blinder)' % ('FAIL' if too_long else 'ok', len(claim.GENERIC_TOKENS)))
fails += 1 if too_long else 0

APPS = ['sairnroofing', 'sairnbuild', 'stonedesk', 'sairnlaw', 'sairnvet',
        'sairndental', 'sairnsenior', 'sairncare', 'sairncode', 'sairnbiz',
        'sairngrounds', 'sairnscape', 'sairnlegacy', 'sairndesign', 'sairnfreedom']
swallowed = [a for a in APPS if a in claim.GENERIC_TOKENS]
print('%-5s no app name is generic (%s)'
      % ('FAIL' if swallowed else 'ok', swallowed or 'none'))
fails += 1 if swallowed else 0

# A generic token that is also a stopword would be dead weight and a sign the
# two lists have started to drift into each other.
overlap = claim.GENERIC_TOKENS & claim.STOPWORDS
print('%-5s GENERIC_TOKENS and STOPWORDS are disjoint (%s)'
      % ('FAIL' if overlap else 'ok', sorted(overlap) or 'none'))
fails += 1 if overlap else 0

print('\n%d failure(s)' % fails)
sys.exit(1 if fails else 0)
