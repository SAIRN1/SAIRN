# OWNER: cc
"""Plants the defect each alf_mar / alf_incidents scope arm exists to catch, and
confirms the arm goes RED.

WHY THIS IS A FILE AND NOT A ONE-OFF RUN. Both suites were green before
2026-10-05 in a way that proved nothing: `test-alf-mar.js` was 0/20 on its own
mock's throw, and `test-alf-incidents.js` asserted a 403 the gate had
deliberately stopped answering while its fixture ignored the very eq-clause the
self-scope is made of. Green is not evidence. The only thing that distinguishes
an arm that guards something from an arm that merely passes is whether removing
the guard turns it red, and that has to be re-runnable or it decays into a
sentence in a commit message.

PER-ARM, NOT PER-EXIT-CODE (standing discipline 12). Each mutation declares
WHICH named arms must redden; reddening some other arm does not count.

EVERY MUTANT IS `node --check`ED BEFORE IT IS RUN. A mutant that does not parse
makes the whole suite fail and scores as CAUGHT for entirely the wrong reason --
the 2026-09-25 sabotage-harness finding, where 6 of 15 dead arms were malformed
mutants.

THE MATCHER IS CASE-INSENSITIVE, AND THAT IS NOT TIDYING. The first run of this
harness scored M1 as SURVIVED because the arm says CLIENT-SUPPLIED and the
expectation said client-supplied. The mutation had been caught and the tool
reported the opposite -- a probe whose matcher is narrower than its subject,
which is the exact defect class this repo keeps paying for. Recorded here rather
than silently fixed.

AND CASE-INSENSITIVITY WAS ONLY THE INSTANCE. `dead_expectations()` closes the
CLASS: every expectation is checked against the arm names that actually exist
BEFORE any mutation runs, and one that matches nothing is a REFUSAL (exit 2)
rather than a verdict. An arm can be reworded, split or deleted as easily as
mis-cased, and each of those leaves a matcher that cannot match -- which is
indistinguishable from a missing guard and fails toward the LOUDER answer, the
direction that gets a real control deleted to make a probe green. Both
directions are driven: a mis-cased expectation still matches, and an
expectation naming an arm that does not exist refuses.

api/sd-data.js IS RESTORED BYTE-FOR-BYTE after every mutation and the final
state is checked against git rather than assumed.

WHAT THIS DOES NOT DO: it does not assert the gates are CORRECT, only that the
arms are load-bearing. Whether 200-self-scoped is the right answer for
alf_incidents is re-derived from four independent sources in
test-alf-incidents.js's own comment, not here.
"""
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node') or 'node'
TARGET = os.path.join(REPO, 'api', 'sd-data.js')
ORIG = open(TARGET, encoding='utf-8', newline='').read()

SUITES = {
    'alf-mar': os.path.join(REPO, 'tests', 'sairncare', 'test-alf-mar.js'),
    'alf-incidents': os.path.join(REPO, 'tests', 'sairncare',
                                  'test-alf-incidents.js'),
}

# (label, suite, old, new, the named arms that MUST go red)
MUTATIONS = [
    ('M1 the witness refusal is computed and not acted on',
     'alf-mar',
     '      if (alfRefusal) { res.status(alfRefusal.status).json(alfRefusal.body); return; }',
     '      if (false) { res.status(alfRefusal.status).json(alfRefusal.body); return; }',
     ['client-supplied witness_id is REFUSED']),

    ('M2 the witness lock refuses EVERY count, even a confirmed one',
     'alf-mar',
     '      if (alfRefusal) { res.status(alfRefusal.status).json(alfRefusal.body); return; }',
     "      if (alfRefusal || payload.entry_type === 'count') { "
     "res.status(403).json({ error: { code: 'WITNESS_REQUIRED', message: 'x' } }); return; }",
     ['WITH a server-recorded second signature']),

    ('M3 the self-scope eq-clause is dropped entirely',
     'alf-incidents',
     "      if (!incBroad) incQ += '&recorded_by=eq.' + enc(String(session.employee_id));",
     '      // MUTANT: scope dropped',
     ['sees ONLY their own filings',
      'does NOT see an incident filed by somebody else',
      'also read self-scoped']),

    # THE SHARP ONE, and the reason this file exists rather than three
    # single-line ablations. 6977854d explicitly REFUSED scoping on the
    # caller-supplied data.reported_by -- it "would let any employee read any
    # incident by claiming to have filed it, which is worse than the flat 403
    # it replaces." A suite that catches the clause being DELETED can still be
    # blind to it being MOVED to the forgeable field, which looks correct.
    ('M4 the self-scope moves to the FORGEABLE field (data->>reported_by)',
     'alf-incidents',
     "      if (!incBroad) incQ += '&recorded_by=eq.' + enc(String(session.employee_id));",
     "      if (!incBroad) incQ += '&data->>reported_by=eq.' + enc(String(session.employee_id));",
     ['sees ONLY their own filings',
      'does NOT see an incident filed by somebody else']),

    # The scope pointed the other way. A self-scope that also catches
    # management is not a leak, it is management losing a mandated-reporting
    # log -- and the management CONTROL inside the negative arm is what makes
    # the negative arm mean "scoped" rather than "unreachable".
    ('M5 the scope applies to BROAD roles too -- management loses the log',
     'alf-incidents',
     '      const incBroad = !!ALF_INCIDENT_READ_ROLES[session.role];',
     '      const incBroad = false;',
     ['does NOT see an incident filed by somebody else']),
]


def run(suite):
    p = subprocess.run([NODE, SUITES[suite]], cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace',
                       timeout=900)
    out = (p.stdout or '') + (p.stderr or '')
    reds = [l.strip()[5:].strip() for l in out.split('\n')
            if l.strip().startswith('FAIL')]
    # EVERY arm name, passing or failing. Needed by the dead-expectation guard
    # below: an expectation can only be checked against the arms that exist.
    names = [l.strip()[4:].strip() for l in out.split('\n')
             if l.strip().startswith('PASS') or l.strip().startswith('ok ')]
    names += reds
    summ = [l for l in out.split('\n') if 'passed,' in l]
    return reds, (summ[-1].strip() if summ else '?'), names


def dead_expectations(arm_names_by_suite):
    """── THE FIX FOR THE DEFECT THIS FILE COMMITTED ON ITS FIRST RUN ────────

    The first run of this harness scored M1 as SURVIVED. The arm HAD gone red;
    the arm says CLIENT-SUPPLIED and the expectation said client-supplied, so a
    case-sensitive compare reported the OPPOSITE of what happened.

    MAKING THE MATCH CASE-INSENSITIVE FIXED THAT ONE INSTANCE AND NOT THE
    CLASS. Case is only one of the ways an expectation stops matching: an arm
    can be reworded, retitled, split in two, or deleted outright, and every one
    of those leaves an expectation that matches nothing and a mutation that
    scores SURVIVED for a reason that has nothing to do with the subject.

    A matcher that cannot match is indistinguishable from a guard that is
    missing -- and it fails toward the LOUDER verdict, which is the direction
    that gets a real control deleted to make a probe green.

    SO THE EXPECTATION IS CHECKED AGAINST THE ARMS THAT ACTUALLY EXIST, before
    any mutation runs, and an unmatchable one is a REFUSAL rather than a
    verdict. This is the same question `once()` asks of a sabotage anchor,
    asked of the matcher instead of the subject.
    """
    dead = []
    for label, suite, _old, _new, must in MUTATIONS:
        pool = [n.lower() for n in arm_names_by_suite.get(suite, [])]
        for m in must:
            if not any(m.lower() in n for n in pool):
                dead.append((label, suite, m))
    return dead


def main():
    print('tests/run_alf_scope_mutation_probe.py')
    print()
    print('BASELINE at HEAD -- a mutation run on a red tree measures nothing')
    arm_names = {}
    for s in SUITES:
        reds, summ, names = run(s)
        arm_names[s] = names
        print('  %-16s %s   reds=%d  arms seen=%d'
              % (s, summ, len(reds), len(names)))
        if reds:
            print('    REFUSING TO MUTATE: the baseline is not green, so no '
                  'verdict below could be attributed to a mutation.')
            return 2
    print()

    # ── DEAD-EXPECTATION GUARD. See dead_expectations() for why this is not
    # ── tidying. An expectation that matches no arm is a matcher that cannot
    # ── fail, and it reports SURVIVED about a subject it never looked at.
    dead = dead_expectations(arm_names)
    print('MATCHER SELF-CHECK -- can every expectation match a real arm?')
    if dead:
        print('  REFUSING: %d expectation(s) match NO arm in their suite. A '
              'matcher that cannot match scores SURVIVED for a reason that has '
              'nothing to do with the subject.' % len(dead))
        for label, suite, m in dead:
            print('    %s  [%s]  expected-red text never appears: %r'
                  % (label, suite, m))
        print('  Re-derive the expectation from the suite output -- never '
              're-type it.')
        return 2
    print('  all %d expectation(s) across %d mutation(s) match a live arm'
          % (sum(len(m[4]) for m in MUTATIONS), len(MUTATIONS)))
    print()

    bad = 0
    for label, suite, old, new, must in MUTATIONS:
        if ORIG.count(old) != 1:
            print('REFUSED   %s' % label)
            print('           anchor matches %d times, not 1. An anchor that '
                  'is not unique picks a line nobody chose.' % ORIG.count(old))
            bad += 1
            continue
        open(TARGET, 'w', encoding='utf-8', newline='').write(
            ORIG.replace(old, new, 1))
        chk = subprocess.run([NODE, '--check', TARGET], capture_output=True,
                             text=True)
        if chk.returncode != 0:
            print('REFUSED   %s -- mutant does not parse' % label)
            open(TARGET, 'w', encoding='utf-8', newline='').write(ORIG)
            bad += 1
            continue
        reds, summ, _names = run(suite)
        open(TARGET, 'w', encoding='utf-8', newline='').write(ORIG)

        hit = [m for m in must if any(m.lower() in r.lower() for r in reds)]
        miss = [m for m in must if m not in hit]
        print('%s  %s' % (('CAUGHT' if not miss else 'SURVIVED').ljust(9), label))
        print('           %s -> %s, %d red arm(s)' % (suite, summ, len(reds)))
        for r in reds:
            print('             - ' + r[:104])
        if miss:
            print('           *** EXPECTED RED AND WAS NOT: %s' % miss)
            bad += 1
        print()

    open(TARGET, 'w', encoding='utf-8', newline='').write(ORIG)
    d = subprocess.run(['git', 'diff', '--stat', '--', 'api/sd-data.js'],
                       cwd=REPO, capture_output=True, text=True)
    dirty = d.stdout.strip()
    print('api/sd-data.js restored; git diff: %s'
          % (repr(dirty) if dirty else 'clean'))
    if dirty:
        print('  *** THE SUBJECT WAS LEFT MODIFIED. That is worse than any '
              'verdict above.')
        return 2
    print('%d mutation(s) survived or were refused' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
