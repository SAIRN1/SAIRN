"""tests/run_app_attribution_mutation_control.py

Run:  python tests/run_app_attribution_mutation_control.py

THE NEGATIVE CONTROL FOR tests/run_app_attribution_probe.py -- AND IT VERIFIES
ITS OWN SABOTAGE APPLIED.

Measured on this platform on 2026-09-13 by `tools/sabotage_control_check.py`:
23 of 39 negative controls NEVER VERIFY THEIR OWN SABOTAGE APPLIED. A control
that anchors on a string which no longer exists, mutates nothing, and then
reports "the probe went red" is reporting nothing -- it would pass identically
against a subject with the defect still in it.

Every mutation is asserted in FOUR parts, in order:

  1. the anchor is FOUND in tools/traceability_matrix.py exactly once
  2. the mutated copy DIFFERS from the original
  3. the mutant still PARSES (else a red probe is the FILE failing, not the rule)
  4. tests/run_app_attribution_probe.py, run against it, EXITS NON-ZERO

── WHY THE MUTATIONS LOOK LIKE THIS ─────────────────────────────────────────
An attribution table fails in a direction that LOOKS LIKE AN IMPROVEMENT. Every
mutation below raises the attributed count and lowers PLATFORM -- a substring
match instead of a token match, the `sd` refusal reversed, the two-app conflict
resolved by precedence instead of refused. Each one makes
docs/MASTER-PLAN.md's coverage columns look better, and each one is a number
that is wrong. That is the whole reason the probe checks safety properties
rather than only checking that SAIRNroofing went from 0 to 27.

tools/traceability_matrix.py is never left modified: the mutant is written in
place, the probe is run, the original is restored in a `finally`, and section 2
asserts the restore by comparing bytes rather than trusting that it ran.
"""

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'tools', 'traceability_matrix.py')
PROBE = os.path.join(ROOT, 'tests', 'run_app_attribution_probe.py')

with open(SRC, encoding='utf-8') as f:
    ORIGINAL = f.read()

passed = 0
failed = 0


def check(name, cond, detail=''):
    global passed, failed
    if cond:
        print('  ok   ' + name)
        passed += 1
    else:
        print('  FAIL ' + name + (('\n       ' + detail) if detail else ''))
        failed += 1


def section(s):
    print('\n' + s)


def run_probe_with(source):
    with open(SRC, 'w', encoding='utf-8', newline='') as f:
        f.write(source)
    try:
        r = subprocess.run([sys.executable, PROBE], cwd=ROOT, capture_output=True,
                           text=True, encoding='utf-8', errors='replace', timeout=300)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    finally:
        with open(SRC, 'w', encoding='utf-8', newline='') as f:
            f.write(ORIGINAL)


MUTATIONS = [
    {
        'name': 'token-exact becomes startswith -- `sc` claims SAIRNscape\'s '
                'scp_ files for SAIRNcode',
        'find': "    hit = APP_ALIASES.get(first_token(path))\n"
                "    alias = hit[0] if (hit and hit[0] in app_names) else None",
        'replace': "    _tok = first_token(path)\n"
                   "    hit = next((v for k, v in APP_ALIASES.items() if _tok.startswith(k)), None)\n"
                   "    alias = hit[0] if (hit and hit[0] in app_names) else None",
    },
    {
        'name': 'the first token becomes a whole-path substring search -- the '
                'original sin app_of() was written to avoid',
        'find': "def first_token(path):\n"
                "    \"\"\"The first -, _ or . delimited token of a path's basename.\"\"\"\n"
                "    return re.split(r'[-_.]', os.path.basename(path))[0].lower()",
        'replace': "def first_token(path):\n"
                   "    \"\"\"The first -, _ or . delimited token of a path's basename.\"\"\"\n"
                   "    low = path.lower()\n"
                   "    for k in APP_ALIASES:\n"
                   "        if k in low:\n"
                   "            return k\n"
                   "    return re.split(r'[-_.]', os.path.basename(path))[0].lower()",
    },
    {
        'name': 'the two-app conflict is resolved by PRECEDENCE instead of '
                'refused -- the defect the probe found in the first draft',
        'find': "    if direct != 'PLATFORM' and alias and alias != direct:\n"
                "        return 'PLATFORM'",
        'replace': "    if False:\n"
                   "        return 'PLATFORM'",
    },
    # NOT "the alias wins over direct": with the conflict guard in place that
    # rewrite is SEMANTICALLY EQUIVALENT -- after the guard, a set alias and a
    # non-PLATFORM direct are always the same app -- and the first version of
    # this control asserted it went red when it could not. THE CONTROL CAUGHT
    # ITS OWN NO-OP MUTATION, which is the arm that exists for exactly that.
    # This is the version that really removes app_of()'s answer from the
    # decision.
    {
        'name': 'app_of() is cut out of the decision entirely, so a full app '
                'name loses to a three-letter alias',
        'find': "    direct = app_of(path, app_names)\n"
                "    hit = APP_ALIASES.get(first_token(path))",
        'replace': "    direct = 'PLATFORM'\n"
                   "    hit = APP_ALIASES.get(first_token(path))",
    },
    {
        'name': 'the refused `sd` group is admitted -- 25 shared-endpoint tests '
                'become StoneDesk\'s',
        'find': "    'sb':      ('sairnbiz',      ",
        'replace': "    'sd':      ('stonedesk',     'ADMITTED BY A MUTATION'),\n"
                   "    'sb':      ('sairnbiz',      ",
    },
    {
        'name': 'an alias is added for an app that does not exist -- the typo case',
        'find': "    'grd':     ('sairngrounds',  ",
        'replace': "    'grnds':   ('sairngrnds',    'A TYPO, WHICH IS THE POINT'),\n"
                   "    'grd':     ('sairngrounds',  ",
    },
    # ALSO NOT `REFUSED_ALIASES = {} or {`: an empty dict is FALSY, so `or`
    # returns the populated one and NOTHING CHANGES. That was the second no-op
    # this control rejected on its first run. Dropping a real entry is the
    # defect -- the refusal for the largest refused group stops being recorded
    # anywhere, and "PLATFORM" goes back to reading as a gap nobody got to.
    {
        'name': 'the `sd` refusal is deleted, so nothing records WHY 25 '
                'shared-endpoint tests are PLATFORM',
        'find': "    'sd': ('stonedesk', 25,",
        'replace': "    '_sd_refusal_deleted_by_mutation': (None, 0,",
    },
    {
        'name': 'aliases leak into app_of() itself, so index-row PROSE is '
                'attributed by a three-letter token',
        'find': "    low = text.lower()\n"
                "    hits = [a for a in app_names if a in low]",
        'replace': "    low = text.lower()\n"
                   "    hits = [a for a in app_names if a in low]\n"
                   "    hits += [v[0] for k, v in APP_ALIASES.items() if k in low\n"
                   "             and v[0] in app_names]",
    },
]

print('app attribution: every arm is shown to FAIL on a sabotaged table\n')

tmp = tempfile.mkdtemp(prefix='app-attribution-mutation-')
try:
    section('0. baseline -- the probe is green against the shipped table')
    rc, out = run_probe_with(ORIGINAL)
    check('tests/run_app_attribution_probe.py passes unmutated (exit %s)' % rc,
          rc == 0, '\n'.join(out.split('\n')[-8:]))
    check('...and it really reached section 7, so the measured-floor arms below '
          'have something to break', '7. the finding, measured' in out)

    section('1. each mutation: found, applied, parses, and caught')
    for idx, m in enumerate(MUTATIONS, 1):
        print('\n  [%d] %s' % (idx, m['name']))
        hits = ORIGINAL.count(m['find'])
        check('the anchor is present in tools/traceability_matrix.py EXACTLY '
              'once (found %d)' % hits, hits == 1)
        if hits != 1:
            continue
        mutated = ORIGINAL.replace(m['find'], m['replace'])
        check('the mutated source differs from the original', mutated != ORIGINAL)

        path = os.path.join(tmp, 'mutant_%d.py' % idx)
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(mutated)
        with open(path, encoding='utf-8') as f:
            on_disk = f.read()
        check('...and the mutation is present in the bytes on disk',
              m['replace'].split('\n')[0] in on_disk)
        try:
            compile(on_disk, path, 'exec')
            parses = True
        except SyntaxError as e:
            parses = False
            print('       SyntaxError: %s' % e)
        check('...and it still PARSES, so a red probe is the RULE failing and '
              'not the file', parses)
        if not parses:
            continue

        rc, out = run_probe_with(mutated)
        check('the probe FAILS on it (exit %s)' % rc, rc != 0,
              '\n'.join([l for l in out.split('\n') if l.strip()][-6:]))

    section('2. tools/traceability_matrix.py was restored byte for byte')
    with open(SRC, encoding='utf-8') as f:
        check('the shipped tool is byte-identical to how this run found it',
              f.read() == ORIGINAL)
finally:
    try:
        with open(SRC, 'w', encoding='utf-8', newline='') as f:
            f.write(ORIGINAL)
    except OSError:
        pass
    shutil.rmtree(tmp, ignore_errors=True)

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(1 if failed else 0)
