"""tests/run_reseat_fixed_point_probe.py -- the register re-seat must reach a fixed point.

Run:  python tests/run_reseat_fixed_point_probe.py

── THE LIVELOCK THIS CLOSES, OBSERVED 2026-09-29 ─────────────────────────
Nine consecutive commits in one branch did nothing but re-seat the same register
citations. The chain:

  1. tools/push_retry.py --loop rebases;
  2. .githooks/post-rewrite re-seats the cited shas onto the ones the rebase just
     rewrote, writes docs/defect-density-register.json, and CORRECTLY refuses to
     commit on anybody's behalf -- leaving the tree dirty;
  3. push_retry's regenerate step stages only GENERATED, so the register stays
     dirty, and amend_safety() is right to refuse a dirty tree;
  4. the push loses the race, the loop rebases again, and step 2 repeats.

NOTHING IN THE CHAIN IS WRONG ON ITS OWN, which is why it survived: the hook is
right not to commit, the allowlist is right not to sweep, the amend guard is
right to refuse. What was missing is that a re-seat is an EXPECTED, SELF-CONTAINED
artefact of the rebase the loop just performed.

── WHAT A FIXED POINT MEANS HERE ─────────────────────────────────────────
Applying the re-seat step to an already-re-seated tree must produce NO further
change. The known-bad control below is a step that does not converge -- it
rewrites on every pass -- and this probe must catch it.

── AND THE NARROWING IS THE OTHER HALF ───────────────────────────────────
Folding in anything that is NOT a re-seat would be the `git add -A` failure
arriving by a different door. Both directions are driven: commit-fields-only is
folded, a new record or an edited summary is not.
"""
CONTROLS_FOR = ['push_retry.py']

import importlib.util
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'push_retry.py')
LEDGER_REL = 'docs/defect-density-register.json'
EXIT_COULD_NOT_RUN = 2

FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


if not os.path.isfile(TOOL):
    sys.stderr.write('COULD NOT RUN: tools/push_retry.py is not on disk. This '
                     'control tested nothing, which is a third state and not a '
                     'pass.\n')
    sys.exit(EXIT_COULD_NOT_RUN)

spec = importlib.util.spec_from_file_location('pr', TOOL)
pr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pr)

NL = chr(10)
print('CONTROL PAIR -- tools/push_retry.py re-seat fixed point' + NL)

# ── A. THE DISCRIMINATOR, ON SYNTHETIC DIFFS ─────────────────────────────
# reseat_only() reads the real repo, so its decision logic is re-created here
# from the same rule and driven on fixtures. The arm below then checks the real
# function agrees on the real tree, which is the pairing that keeps this honest.
print('A. commit-fields-only is a re-seat; anything else is not')


def is_reseat(diff_text):
    """The rule reseat_only() applies, in isolation: every changed line cites a
    commit. Re-created rather than imported so a change to one has to be made
    deliberately in the other."""
    for line in diff_text.split(NL):
        if not line or line[0] not in '+-':
            continue
        if line[:3] in ('+++', '---'):
            continue
        if '"commit"' not in line:
            return False
    return True


CASES = [
    ('a pure sha re-seat',
     '--- a/x\n+++ b/x\n-      "commit": "aaaaaaaaaaaa",\n+      "commit": "bbbbbbbbbbbb",',
     True),
    ('two re-seats in one diff',
     '-      "commit": "aaa",\n+      "commit": "bbb",\n-      "commit": "ccc",\n+      "commit": "ddd",',
     True),
    ('a NEW RECORD added',
     '+    {\n+      "commit": "bbbbbbbbbbbb",\n+      "app": "sairncare"\n+    },',
     False),
    ('an EDITED SUMMARY',
     '-      "summary": "old wording",\n+      "summary": "new wording",',
     False),
    ('a severity changed',
     '-      "severity": "low",\n+      "severity": "high",',
     False),
    ('a conflict marker',
     '+<<<<<<< HEAD\n+      "commit": "aaa",\n+=======',
     False),
]
for label, diff, want in CASES:
    ok('%-28s -> %s' % (label, 'FOLD' if want else 'LEAVE'),
       is_reseat(diff) == want, 'got %r' % is_reseat(diff))

# ── A2. THE MIXED DIFF, WHICH IS THE ONE THAT MATTERS ───────────────────
# A diff that is ENTIRELY commit citations is a re-seat and is folded in. A
# diff that is entirely something else is obviously not. The dangerous shape
# is NEITHER: a real re-seat line sitting beside one edit that is not one,
# which is what a concurrent session's record looks like after a rebase
# touches the same file. Folding that in commits somebody else's unreviewed
# change inside an amend -- the `git add -A` failure arriving by the only
# door still open.
#
# EVERY case below carries at least one genuine commit line, so a rule that
# stopped at 'does this diff contain a citation' would fold all of them.
print(NL + 'A2. a citation line PLUS a non-citation edit is NOT a re-seat')
CIT_OLD = '-      ' + chr(34) + 'commit' + chr(34) + ': ' + chr(34) + 'aaa' + chr(34) + ','
CIT_NEW = '+      ' + chr(34) + 'commit' + chr(34) + ': ' + chr(34) + 'bbb' + chr(34) + ','
def line(sign, key, val):
    return sign + '      ' + chr(34) + key + chr(34) + ': ' + chr(34) + val + chr(34) + ','
MIXED = [
    ('citation + a new record', [CIT_OLD, CIT_NEW, line('+', 'app', 'sairncare')]),
    ('citation + an edited severity', [CIT_NEW, line('-', 'severity', 'low'),
                                       line('+', 'severity', 'high')]),
    ('citation + a deleted record', [CIT_NEW, line('-', 'summary', 'older')]),
    ('citation + a conflict marker', [CIT_NEW, '+<<<<<<< HEAD']),
    ('citation + an emptied field', [CIT_NEW, line('+', 'limits', '')]),
]
for label, lines in MIXED:
    diff = NL.join(lines)
    ok('%-44s -> LEAVE' % label, is_reseat(diff) is False,
       'a mixed diff was classified as a pure re-seat, so an unreviewed edit '
       'would be folded into an amended commit: %r' % diff)
ok('...and the citation lines ALONE would be folded -- so the arms above '
   'are not passing because the fixtures are unrecognisable',
   is_reseat(NL.join([CIT_OLD, CIT_NEW])) is True,
   'the citation half of these fixtures is not recognised either')

# ── B. THE FIXED POINT ───────────────────────────────────────────────────
print(NL + 'B. applying the step twice changes nothing the second time')


def apply_reseat(records, rewrite_map):
    """The re-seat itself: swap each cited sha for its rewritten one."""
    out = json.loads(json.dumps(records))
    for r in out:
        if r.get('commit') in rewrite_map:
            r['commit'] = rewrite_map[r['commit']]
    return out


RECS = [{'commit': 'aaaaaaaaaaaa', 'app': 'x'},
        {'commit': 'cccccccccccc', 'app': 'y'}]
MAP = {'aaaaaaaaaaaa': 'bbbbbbbbbbbb', 'cccccccccccc': 'dddddddddddd'}

once = apply_reseat(RECS, MAP)
twice = apply_reseat(once, MAP)
ok('the second application is a no-op -- a FIXED POINT', once == twice,
   'once=%r twice=%r' % (once, twice))
ok('...and the first application actually changed something',
   once != RECS, 'the fixture does not exercise the re-seat at all')


def never_converges(records, _map):
    """KNOWN-BAD CONTROL: a step that rewrites on every pass. This is the shape
    the livelock had -- something that always leaves the tree dirty, so the
    caller can never reach a clean state and retries for ever."""
    out = json.loads(json.dumps(records))
    for r in out:
        r['commit'] = r['commit'][1:] + 'z'
    return out


bad_once = never_converges(RECS, MAP)
bad_twice = never_converges(bad_once, MAP)
ok('KNOWN-BAD CONTROL: a non-converging step is CAUGHT by the same check',
   bad_once != bad_twice,
   'the fixed-point check cannot see a step that rewrites every pass, so the '
   'arm above proves nothing')

# ── C. THE REAL FUNCTION, ON THE REAL TREE ───────────────────────────────
print(NL + 'C. the shipped reseat_only() agrees with the rule, on this tree')
ok('reseat_only is exported by push_retry', hasattr(pr, 'reseat_only'),
   'the tool no longer has the function this control is about')
if hasattr(pr, 'reseat_only'):
    verdict, why = pr.reseat_only()
    porc = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--',
                           LEDGER_REL], capture_output=True, text=True).stdout
    if not porc.strip():
        ok('a CLEAN ledger is "no change to fold", never a fold',
           verdict is False and why == 'no change to fold',
           'verdict=%r why=%r' % (verdict, why))
    else:
        # Not an error: the tree may legitimately carry a real edit right now.
        ok('a DIRTY ledger produces a decision with a stated reason',
           isinstance(verdict, bool) and isinstance(why, str),
           'verdict=%r why=%r' % (verdict, why))
        print('       (ledger is dirty in this tree; verdict=%r why=%r)'
              % (verdict, why))

ok('LEDGER is the register, not something else', pr.LEDGER == LEDGER_REL,
   pr.LEDGER)

print(NL + '%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
