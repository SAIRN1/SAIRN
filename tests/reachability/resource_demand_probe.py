"""tests/reachability/resource_demand_probe.py -- R6 can be shown to FIRE on a
resource nobody asks for, and to stay quiet on one that is asked for.

    python tests/reachability/resource_demand_probe.py

R6 IS THE RUNG R4 AND R5 CANNOT REACH, and the reason is arithmetic: they take
the ROUTE as the unit, and `/api/sd-data` is one route carrying 385 registered
resources. It is among the most-served endpoints on the platform, so every
resource behind it reads as reachable whether or not anything has ever asked
for it by name.

THE FAILURE MODE THIS SUITE IS MOSTLY ABOUT IS THE CLOSED LOOP. The registry is
where a resource name is DECLARED. Counting a declaration as a use would make
every resource reachable by definition and the rung would be a mirror -- the
same shape as a generator's `--check` comparing a document to its own output.
Section 2 pins that the registry is excluded and that excluding it is what
makes the rung capable of a finding at all.

AND THE OTHER DIRECTION: a rung that reports every resource is a rung nobody
reads. Section 3 pins that a name mentioned ANYWHERE a caller could reach it --
any app HTML, any api/ module -- stays quiet.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_reachability_check as R                             # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


def run_r6():
    """Capture just the R6 section from a real full run."""
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                     'sairn_reachability_check.py')],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
    out = p.stdout or ''
    i = out.find('=== R6:')
    return (out[i:] if i >= 0 else ''), p.returncode


print('1. the rung runs, and says what it measured')
sect, rc = run_r6()
check('1a  R6 appears in a full run', sect != '')
check('1b  it prints a DENOMINATOR, so a short list cannot read as a clean tree',
      'registered resources :' in sect)
check('1c  it states that it never gates and never suggests removal -- the same '
      'standing rule R4 and R5 carry, for the same reason',
      'report only, never gates' in sect)
check('1d  it says what it CANNOT see, including a name built at runtime',
      'CANNOT SEE' in sect and 'BUILT at runtime' in sect)
check('1e  a rung that finds nothing OPEN says it is a MEASURED zero',
      'measured zero' in sect or 'NOT ASKED FOR BY ANY' in sect)

print('2. THE CLOSED LOOP -- the registry is not a caller')
corpus = R._mention_corpus()
reg_dir = os.path.join(REPO, 'api', '_resources')
# Every name lives in the registry. If the registry were part of the corpus,
# every resource would be "asked for" and the rung could never find anything.
reg_text = ''
for f in sorted(os.listdir(reg_dir)):
    if f.endswith('.js'):
        reg_text += io.open(os.path.join(reg_dir, f), encoding='utf-8').read()
check('2a  the acknowledged resources ARE declared in the registry',
      "'dnt_ar'" in reg_text and "'dnt_revenue'" in reg_text)
check('2b  ...and are NOT in the corpus the rung searches -- excluding the '
      'registry is what makes a finding possible at all',
      "'dnt_ar'" not in corpus and "'dnt_revenue'" not in corpus)
check('2c  CONTROL: the corpus is not simply empty -- a resource that IS asked '
      'for is in it', "'dnt_patients'" in corpus or '"dnt_patients"' in corpus)

print('3. FIRES on a resource nobody asks for, quiet on one that is')
registered = R._registered_resources()
check('3a  the registry parses to real apps and names',
      len(registered) >= 10 and sum(len(v) for v in registered.values()) > 300,
      '%d apps, %d names' % (len(registered), sum(len(v) for v in registered.values())))
unrequested = []
for app in sorted(registered):
    for name in sorted(registered[app]):
        if ("'" + name + "'") in corpus or ('"' + name + '"') in corpus:
            continue
        unrequested.append((app, name))
check('3b  FIRES: it finds exactly the two resources named nowhere',
      sorted(unrequested) == [('sairndental', 'dnt_ar'), ('sairndental', 'dnt_revenue')],
      unrequested)
check('3c  SILENT: every other registered resource is named somewhere a caller '
      'could reach it -- so the rung is not reporting the whole registry',
      len(unrequested) < 5, len(unrequested))

print('4. ACKNOWLEDGEMENTS are visible, reasoned, and cannot rot')
check('4a  both findings are acknowledged, so the OPEN list is empty today',
      all(x in R.R6_ACKNOWLEDGED for x in unrequested), unrequested)
check('4b  every acknowledgement carries a written reason naming WHERE the '
      'decision is argued, not just a note',
      all(len(v) > 80 and '.js' in v for v in R.R6_ACKNOWLEDGED.values()))
check('4c  the acknowledged COUNT is printed every run -- one nobody can see is '
      'a suppression', 'ACKNOWLEDGED (' in sect)
check('4d  an acknowledgement whose resource IS named again is reported STALE, '
      'so the list cannot outlive what it excused',
      'STALE ACKNOWLEDGEMENT' in io.open(os.path.join(REPO, 'tools',
                                                      'sairn_reachability_check.py'),
                                         encoding='utf-8').read())
# The acknowledgement must be ABOUT something real: the file it cites has to
# exist, or the reason is unverifiable prose.
# THE CITATION IS RESOLVED AS WRITTEN, not re-prefixed. The first version of
# this arm joined the citation onto `api/` when the citation already carried it,
# and stripped the wrong punctuation -- so it reported two real, present files as
# missing. A control that fails on correct input is one somebody switches off.
for (app, name), why in R.R6_ACKNOWLEDGED.items():
    cited = [w.strip('`,."()') for w in why.split() if w.endswith('.js')]
    for c in cited:
        check('4e  ' + name + ' cites ' + c + ', which exists',
              os.path.isfile(os.path.join(REPO, c.replace('/', os.sep))), c)

print('5. it does not gate')
check('5a  a full run with only acknowledged R6 rows still exits 0 -- R6 cannot '
      'change the exit code', rc == 0, 'exit %d' % rc)

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
