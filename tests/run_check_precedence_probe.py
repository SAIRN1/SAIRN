#!/usr/bin/env python
"""tests/run_check_precedence_probe.py -- controls for tools/check_precedence.py.

THE THING BEING TESTED IS A RULE, so the arms are about the rule holding under
pressure rather than about a scan finding something. Three properties matter
more than the rest:

  * RULE 4 (clean + could-not-run -> COULD_NOT_RUN) is the one that will be got
    wrong, because every instinct says two checks and only one complaint is a
    pass. Driven in both orders, and the teeth section proves that breaking it
    is caught rather than silently reported clean.

  * NO CONFIDENCE TIEBREAK. Asserted STRUCTURALLY, not by reading the file: the
    same claims are arbitrated with every rating attached to each side, and the
    verdict must not move. A grep for "confidence" would pass against a version
    that used it.

  * CARRIED, NOT ABSORBED. A finding that beats a could-not-run must still
    report the could-not-run. That is rule 2's entire content and it is the
    half that quietly disappears.

Exit 0 all arms passed, 1 otherwise.
"""

import io
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
SUBJECT = os.path.join(REPO, 'tools', 'check_precedence.py')

FAILS, PASSES = [], [0]


def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('    ok   %s' % label)
    else:
        FAILS.append(label)
        print('    FAIL %s' % label)
        if detail:
            print('         %s' % str(detail)[:400])


import check_precedence as P   # noqa: E402

F, C, U, X = P.FINDING, P.CLEAN, P.COULD_NOT_RUN, P.CONFLICT


def claims(*specs):
    out = []
    for i, s in enumerate(specs):
        kind = s[0] if isinstance(s, tuple) else s
        c = {'source': 'src%d' % i, 'subject': 'subj', 'property': 'prop', 'kind': kind}
        if isinstance(s, tuple) and len(s) > 1:
            c['value'] = s[1]
        if isinstance(s, tuple) and len(s) > 2:
            c['rating'] = s[2]
        out.append(c)
    return out


def v(*specs):
    return P.resolve_group(claims(*specs))['verdict']


# ══ A. the four rules, every ORDER, not one sample each ════════════════════
print('\nA. the rule table under every ordering')
ok('RULE 1 -- a finding beats a clean, both orders',
   v(F, C) == F and v(C, F) == F)
ok('RULE 2 -- a finding beats a could-not-run, both orders',
   v(F, U) == F and v(U, F) == F)
ok('RULE 4 -- a CLEAN does NOT rescue a could-not-run, both orders',
   v(C, U) == U and v(U, C) == U,
   'this is the one that gets decided the other way at 2am')
ok('RULE 3 -- two findings with DIFFERENT values conflict',
   v((F, 'A'), (F, 'B')) == X)
ok('...and two findings with the SAME value corroborate, they do not conflict',
   v((F, 'A'), (F, 'A')) == F)
ok('...and two findings with NO value at all corroborate',
   v(F, F) == F)

# Every permutation of all three kinds must give FINDING -- if any ordering
# produced something else the rule would depend on which checker ran first.
perms = set(P.resolve_group(claims(*p))['verdict']
            for p in itertools.permutations([F, C, U]))
ok('all SIX orderings of finding+clean+could-not-run give FINDING', perms == {F}, perms)

ok('agreement is not a case: CLEAN+CLEAN is CLEAN', v(C, C) == C)
ok('...CNR+CNR is COULD_NOT_RUN', v(U, U) == U)
ok('a single claim is not a disagreement', v(F) == F and v(C) == C and v(U) == U)

ok('an UNKNOWN kind is a CONFLICT -- a verdict with no rule is a finding about '
   'the table, not a reason to pick something',
   P.resolve_group([{'source': 'a', 'subject': 's', 'property': 'p',
                     'kind': 'NEW_VERDICT'}])['verdict'] == X)


# ══ B. NO CONFIDENCE TIEBREAK -- proved structurally ═══════════════════════
print('\nB. the rating cannot move a verdict')
RATINGS = ('HIGH', 'MEDIUM', 'LOW', 'UNKNOWN', None)
moved = []
for kinds in ((F, C), (C, F), (F, U), (C, U), (U, C)):
    base = P.resolve_group(claims(*kinds))['verdict']
    for r1, r2 in itertools.product(RATINGS, RATINGS):
        got = P.resolve_group(claims((kinds[0], None, r1), (kinds[1], None, r2)))['verdict']
        if got != base:
            moved.append((kinds, r1, r2, base, got))
ok('NO pairing of ratings changes any verdict -- 125 combinations',
   not moved, moved[:4])
# THE OTHER DIRECTION, so the arm above cannot pass against an arbiter that
# ignores its inputs entirely: the KINDS must still move the verdict.
ok('CONTROL: changing the KINDS does move the verdict',
   len(set(v(*k) for k in ((F, C), (C, U), (C, C)))) == 3)
ok('...and the rating is still CARRIED into the output for a human to read',
   all('rating' in c
       for c in P.resolve(claims((F, None, 'HIGH'), (C, None, 'LOW')))[0]['claims']),
   P.resolve(claims((F, None, 'HIGH'), (C, None, 'LOW')))[0]['claims'])


# ══ C. carried, not absorbed ═══════════════════════════════════════════════
print('\nC. rule 2 carries the could-not-run rather than replacing it')
r = P.resolve_group(claims(F, U))
ok('the verdict is the finding', r['verdict'] == F)
ok('...and the could-not-run is CARRIED', len(r['carried']) == 1, r['carried'])
ok('...naming which source could not look',
   r['carried'][0]['source'] in ('src0', 'src1'), r['carried'])
r3 = P.resolve_group(claims(F, C, U))
ok('rules 1 and 2 together still carry the could-not-run', len(r3['carried']) == 1)
ok('a plain finding-vs-clean carries nothing', not P.resolve_group(claims(F, C))['carried'])
rc = P.resolve_group(claims((F, 'A'), (F, 'B'), U))
ok('a CONFLICT also carries the could-not-run rather than losing it',
   rc['verdict'] == X and len(rc['carried']) == 1, rc)


# ══ D. grouping, and the one-sided case that is NOT a disagreement ═════════
print('\nD. grouping by (subject, property)')
res = P.resolve([
    {'source': 'a', 'subject': 'x', 'property': 'p', 'kind': F},
    {'source': 'b', 'subject': 'x', 'property': 'p', 'kind': C},
    {'source': 'a', 'subject': 'x', 'property': 'q', 'kind': C},
    {'source': 'b', 'subject': 'y', 'property': 'p', 'kind': U},
])
by = {(r['subject'], r['property']): r['verdict'] for r in res}
ok('three distinct groups', len(res) == 3, by)
ok('the same subject with a DIFFERENT property is arbitrated separately',
   by[('x', 'p')] == F and by[('x', 'q')] == C, by)
ok('a different subject is not merged in', by[('y', 'p')] == U, by)


# ══ E. the CLI, and a conflict must not be reported as a pass ══════════════
print('\nE. the CLI and its exit codes')
TMP = tempfile.mkdtemp(prefix='prec_')
try:
    def run_claims(cs, *extra):
        p = os.path.join(TMP, 'c.json')
        io.open(p, 'w', encoding='utf-8').write(json.dumps(cs))
        return subprocess.run([sys.executable, SUBJECT, '--claims', p] + list(extra),
                              capture_output=True, text=True, encoding='utf-8',
                              errors='replace', cwd=REPO)

    r = run_claims(claims(C, C))
    ok('all clean -> exit 0', r.returncode == 0, r.stdout[-300:])
    r = run_claims(claims(F, C))
    ok('a finding -> exit 1', r.returncode == 1, r.stdout[-300:])
    r = run_claims(claims(C, U))
    ok('RULE 4 through the CLI -> exit 2, NOT 0', r.returncode == 2, r.stdout[-400:])
    r = run_claims(claims((F, 'A'), (F, 'B')))
    ok('a conflict -> exit 3', r.returncode == 3, r.stdout[-300:])
    ok('...and it says out loud that a conflict blocks nothing',
       'BLOCKS NOTHING' in r.stdout, r.stdout[:300])
    ok('...and it does NOT silently pick a winner',
       'CONFLICT' in r.stdout and 'src0' in r.stdout and 'src1' in r.stdout,
       r.stdout[:400])

    r = run_claims(claims(F, C), '--json')
    body = json.loads(r.stdout[r.stdout.index('{'):])
    ok('--json emits parseable output with the reason', body['results'][0]['reason'])

    # A conflict must outrank a finding in the exit code, or a run containing
    # both would be read as an ordinary finding and the question would be lost.
    mixed = (claims((F, 'A'), (F, 'B')) +
             [{'source': 'z', 'subject': 'other', 'property': 'p', 'kind': F}])
    r = run_claims(mixed)
    ok('a conflict outranks a finding in the exit code', r.returncode == 3, r.returncode)

    # ── TEETH ──────────────────────────────────────────────────────────────
    print('\nF. teeth -- breaking rule 4 must not report a clean platform')
    src = io.open(SUBJECT, encoding='utf-8').read()
    ANCHOR = "    if cnrs:\n"
    ok('the teeth anchor is present and unambiguous', src.count(ANCHOR) == 1,
       'anchor stale -- section F tests NOTHING')
    broken = src.replace(ANCHOR, "    if cnrs and not cleans:\n")
    ok('the neutering changed the source', broken != src)
    bp = os.path.join(TMP, 'broken_prec.py')
    io.open(bp, 'w', encoding='utf-8').write(broken)
    p = os.path.join(TMP, 'c4.json')
    io.open(p, 'w', encoding='utf-8').write(json.dumps(claims(C, U)))
    rb = subprocess.run([sys.executable, bp, '--claims', p], capture_output=True,
                        text=True, encoding='utf-8', errors='replace', cwd=REPO)
    ok('the broken copy runs at all', rb.returncode in (0, 1, 2, 3), rb.stderr[-300:])
    # THE POINT. The rule table is proved on every run BEFORE any claim is
    # arbitrated, so a broken rule 4 becomes COULD NOT RUN instead of a clean
    # sweep that used the exact precedence this file forbids.
    ok('TEETH: a broken rule 4 exits COULD NOT RUN (2), never CLEAN (0)',
       rb.returncode == 2, 'exit %s\n%s' % (rb.returncode, rb.stdout[-400:]))
    ok('...and says the rule table failed, rather than printing a verdict',
       'rule table failed' in rb.stdout, rb.stdout[:300])

    # Second teeth: break rule 1 instead, to show the lock is not only watching
    # rule 4.
    ANCHOR2 = "    if findings:\n"
    ok('the second teeth anchor is present', src.count(ANCHOR2) == 1)
    broken2 = src.replace(ANCHOR2, "    if findings and not cleans:\n")
    ok('the second neutering changed the source', broken2 != src)
    bp2 = os.path.join(TMP, 'broken2.py')
    io.open(bp2, 'w', encoding='utf-8').write(broken2)
    rb2 = subprocess.run([sys.executable, bp2, '--claims', p], capture_output=True,
                         text=True, encoding='utf-8', errors='replace', cwd=REPO)
    ok('TEETH: a broken rule 1 is ALSO caught by the lock', rb2.returncode == 2,
       'exit %s' % rb2.returncode)

    rg = subprocess.run([sys.executable, SUBJECT, '--self-check'],
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace', cwd=REPO)
    ok('CONTROL: the real subject passes its own rule table', rg.returncode == 0,
       rg.stdout[-300:])
finally:
    shutil.rmtree(TMP, ignore_errors=True)
    ok('the scratch directory is gone', not os.path.isdir(TMP))


# ══ G. the live mapping is taken from each tool's own semantics ════════════
print('\nG. the live pairing mapping')
ok('confidence UNKNOWN is COULD_NOT_RUN, not a low rating',
   P._confidence_kind({'confidence': 'UNKNOWN'})[0] == U)
ok('confidence LOW is a FINDING -- the state that tool exits 1 for',
   P._confidence_kind({'confidence': 'LOW'})[0] == F)
ok('confidence HIGH and MEDIUM are CLEAN',
   P._confidence_kind({'confidence': 'HIGH'})[0] == C
   and P._confidence_kind({'confidence': 'MEDIUM'})[0] == C)
ok('fusion COULD NOT TELL is COULD_NOT_RUN',
   P._fusion_kind({'state': 'COULD NOT TELL'})[0] == U)
ok('fusion UNCORRECTED is a FINDING',
   P._fusion_kind({'state': 'UNCORRECTED -- corrector failed'})[0] == F)
ok('fusion FUSED is CLEAN', P._fusion_kind({'state': 'FUSED'})[0] == C)
# NO INVENTED THRESHOLD. If somebody adds a `fused >= 0.8` cutoff, the mapping
# stops being derived from the tools' own exit semantics and starts
# manufacturing disagreements out of an arbitrary line.
psrc = io.open(SUBJECT, encoding='utf-8').read()
ok('the mapping uses NO numeric threshold on the fused score',
   'fused' not in psrc.split('def _fusion_kind')[1].split('def ')[0],
   psrc.split('def _fusion_kind')[1].split('def ')[0][:300])


print('\n' + '=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
