
# REQUIREMENT: the recorded owner of each artefact still matches the evidence, so an
#   ownership claim cannot go stale without something saying so
#
#!/usr/bin/env python
"""tests/run_ownership_drift_probe.py

Run:  python tests/run_ownership_drift_probe.py

CONTROLS_FOR = ['ownership_evidence_drift.py']

THIS CHECKER IS RED TODAY, which is the unusual case on this platform and makes
the control pair MORE important rather than less. A checker that is always red
is as useless as one that is always green, so the arms that matter are the ones
proving it goes GREEN when the evidence is refreshed -- and that it refuses
rather than reporting zero drift when it cannot read either side.

EVERY ARM DRIVES THE MODULE DIRECTLY against temporary files. Nothing on disk is
mutated: the baseline and the snapshot are real files a reader trusts on sight.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

CONTROLS_FOR = ['ownership_evidence_drift.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import ownership_evidence_drift as D            # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + str(detail)[:300]))
    if not cond:
        fails.append(name)


def with_files(baseline, snapshot, fn):
    """Point the module at temporary files, run fn, always put it back."""
    tmp = tempfile.mkdtemp(prefix='ownership-drift-')
    b = os.path.join(tmp, 'b.json')
    s = os.path.join(tmp, 's.json')
    if baseline is not None:
        io.open(b, 'w', encoding='utf-8').write(json.dumps(baseline))
    if snapshot is not None:
        io.open(s, 'w', encoding='utf-8').write(json.dumps(snapshot))
    ob, os_ = D.BASELINE, D.SNAPSHOT
    try:
        D.BASELINE, D.SNAPSHOT = b, s
        return fn()
    finally:
        D.BASELINE, D.SNAPSHOT = ob, os_


def snap(n, at='2026-09-13'):
    d = {('t%d' % i): ['id'] for i in range(n)}
    d['_generated_at'] = at
    return d


def base(tables, at='2026-08-26'):
    return {'measurements': [{'measured_at': at, 'by': 'probe',
                              'tables_in_public': tables}]}


print('ownership evidence drift -- it must go GREEN, not only red\n')

print('1. the arithmetic')
r = with_files(base(251), snap(380), lambda: D.main(['--json']))
check('drift against more tables than were measured is a FINDING', r == 1, r)
r = with_files(base(380), snap(380), lambda: D.main(['--json']))
check('THE ARM THAT MATTERS: refreshing the evidence turns it GREEN -- a '
      'checker that can only ever be red is as useless as one always green',
      r == 0, r)
r = with_files(base(400), snap(380), lambda: D.main(['--json']))
check('a SHRINKING population is not a finding either -- tables get dropped',
      r == 0, r)

print('\n2. the most recent measurement wins, wherever it sits in the list')
out_of_order = {'measurements': [
    {'measured_at': '2026-09-13', 'by': 'probe', 'tables_in_public': 380},
    {'measured_at': '2026-08-26', 'by': 'probe', 'tables_in_public': 251},
]}
# APPENDED IN THE WRONG PLACE ON PURPOSE. "the last element" would pick the
# 2026-08-26 row here and UNDERSTATE the drift -- the direction that makes
# stale evidence look current, which is the failure this whole file is about.
r = with_files(out_of_order, snap(380), lambda: D.main(['--json']))
check('an entry appended out of order does not become the baseline', r == 0, r)

print('\n3. could-not-run is never folded into zero drift')
r = with_files(None, snap(380), lambda: D.main([]))
check('a missing baseline is COULD NOT RUN, not "nothing to compare"', r == 2, r)
r = with_files(base(251), None, lambda: D.main([]))
check('a missing snapshot is COULD NOT RUN', r == 2, r)
r = with_files({'measurements': []}, snap(380), lambda: D.main([]))
check('an EMPTY measurements list is a broken file, not a platform nobody has '
      'ever measured', r == 2, r)
r = with_files(base(251), {'_generated_at': 'x'}, lambda: D.main([]))
check('a snapshot that parses to ZERO tables is a broken reader, not an empty '
      'schema -- reporting zero drift off it would be the most reassuring '
      'possible wrong answer', r == 2, r)
r = with_files({'measurements': [{'measured_at': '2026-08-26'}]}, snap(380),
               lambda: D.main([]))
check('a measurement with no table count cannot be compared and says so', r == 2, r)

print('\n4. the real run, end to end')
p = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                 'ownership_evidence_drift.py')],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO)
out = (p.stdout or '') + (p.stderr or '')
flat = ' '.join(out.split())
check('it is RED against this repo today', p.returncode == 1, p.returncode)
check('...and names both populations rather than only the gap',
      'tables then' in out and 'tables now' in out, out[:300])
check('...and says outright this is NOT a claim the ACL has fired',
      'NOT A CLAIM THAT THE ACL HAS FIRED' in flat, out[:600])
check('...and names the one query that would close it',
      'supabase_admin_default_acl_check_2026-08-26.sql' in out, out[:600])
check('...and does not imply a green run would mean the evidence is current',
      'lower bound' in flat.lower(), out[:900])

print('\n5. the baseline records where its numbers came from')
real = json.loads(io.open(os.path.join(REPO, 'tools',
                                       'ownership_evidence_drift.json'),
                          encoding='utf-8').read())
m = real['measurements'][0]
for field in ('measured_at', 'by', 'recorded_in', 'tables_in_public', 'verbatim'):
    check('the measurement records %s -- a number with no provenance is the '
          'thing this platform keeps paying for' % field, field in m, sorted(m))

print('\n%s  run_ownership_drift_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
