#!/usr/bin/env python
"""Negative controls for tools/gap_ledger.py.

    python tests/run_gap_ledger_probe.py

Exit 0 all arms pass, 1 any arm fails, 2 could not run.

WHAT THIS ASKS, and it is not "does the ledger look right":
  1. the criteria lock PASSES on a clean tool  -- the baseline, first, because
     every mutation below is meaningless against a red baseline;
  2. each criteria rule, NEUTRALISED ONE AT A TIME, turns the lock RED -- so
     the lock is load-bearing rather than decorative;
  3. an EMPTY CORPUS is exit 2 and not an empty ledger -- the one failure that
     would publish "every app is uncovered" as a result;
  4. a bare run writes NO TRACKED FILE.

THE MUTATIONS HAPPEN IN A COPY. tools/dead_rule_sweep.py's own history is the
reason: it used to mutate the tracked tool and restore it in a `finally`, which
is correct for every path the interpreter walks and worthless for the ones it
does not, and a run at the timeout left twenty tracked sources carrying
never-matching patterns in a clone four sessions push from.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_REL = 'tools/gap_ledger.py'
CONTROLS_FOR = ['gap_ledger.py']
NEVER = '(?!x)x'

FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('ok  ' if cond else 'FAIL', name,
                         '' if cond else '\n       ' + str(detail)[:300]))
    if not cond:
        FAIL.append(name)


def run(cwd, *args):
    r = subprocess.run([sys.executable, os.path.join(cwd, TOOL_REL)]
                       + list(args), capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=cwd, timeout=240)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def sandbox():
    """A throwaway tree with the tool, its sibling imports, and a tiny corpus."""
    d = tempfile.mkdtemp(prefix='gapledger-probe-')
    os.makedirs(os.path.join(d, 'tools'))
    os.makedirs(os.path.join(d, 'docs', 'cloud-research'))
    shutil.copy(os.path.join(REPO, TOOL_REL), os.path.join(d, TOOL_REL))
    # one app and one dedicated audit for it
    io.open(os.path.join(d, 'probeapp.html'), 'w', encoding='utf-8').write('<html></html>')
    io.open(os.path.join(d, 'docs', 'cloud-research',
                         'probeapp-competitive-gap-audit-2026-10-05.md'),
            'w', encoding='utf-8').write(
        '# audit\n\n## 5. Synthesis\n\n1. **A gap.** prose\n\n'
        '## 6. What this document does not establish or decide\n\nprose\n\n'
        '## 7. Decay\n\nA snapshot.\n')
    return d


print('GAP LEDGER -- negative controls')
d = sandbox()
try:
    # ── 1. the baseline ────────────────────────────────────────────────────
    rc, out = run(d, '--fixtures')
    ok('BASELINE: the criteria lock passes on the clean tool (exit 0)',
       rc == 0, 'exit=%d\n%s' % (rc, out[-400:]))
    if rc != 0:
        print('\nThe baseline is red, so no mutation below would mean '
              'anything. Stopping.')
        shutil.rmtree(d, ignore_errors=True)
        sys.exit(2)

    rc, out = run(d)
    ok('...and the bare run reads the sandbox corpus and finds the one row',
       rc in (0, 1) and 'rows: 1' in out, 'exit=%d\n%s' % (rc, out[-500:]))

    # ── 2. one mutation per criteria rule ──────────────────────────────────
    src = io.open(os.path.join(d, TOOL_REL), encoding='utf-8').read()
    RULES = ['SYNTH_HEAD', 'LIMITS_HEAD', 'DECAY_HEAD', 'ITEM', 'ITEM_PLAIN',
             'DATE_IN_NAME', 'AUDIT_NAME']
    for rule in RULES:
        # replace just this rule's pattern with one that can never match, and
        # leave the module importable so the failure is ABOUT THE RULE.
        pat = re.compile(r'^(%s = re\.compile\()' % rule, re.M)
        if not pat.search(src):
            ok('MUTATION %s: the rule could be located in the source' % rule,
               False, 'no module-level `%s = re.compile(` found' % rule)
            continue
        end = src.index('\n', pat.search(src).end())
        # rebuild the whole assignment as a single never-matching line
        start = pat.search(src).start()
        # a pattern can span lines; take up to the first line whose text
        # closes the call at depth 0
        depth, i = 0, src.index('(', start)
        while i < len(src):
            if src[i] == '(':
                depth += 1
            elif src[i] == ')':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        mutated = (src[:start] + '%s = re.compile(%r)' % (rule, NEVER)
                   + src[i + 1:])
        io.open(os.path.join(d, TOOL_REL), 'w', encoding='utf-8',
                newline='').write(mutated)
        rc, out = run(d, '--fixtures')
        ok('MUTATION %-13s neutralised -> the criteria lock goes RED' % rule,
           rc != 0, 'exit=%d\n%s' % (rc, out[-300:]))
        io.open(os.path.join(d, TOOL_REL), 'w', encoding='utf-8',
                newline='').write(src)

    # the restore really happened, or every arm after this is about the wrong code
    ok('the tool in the sandbox is byte-identical to the tracked one again',
       io.open(os.path.join(d, TOOL_REL), encoding='utf-8').read()
       == io.open(os.path.join(REPO, TOOL_REL), encoding='utf-8').read())

    # ── 3. an empty corpus is NOT an empty ledger ──────────────────────────
    docs = os.path.join(d, 'docs')
    shutil.rmtree(docs)
    os.makedirs(os.path.join(docs, 'cloud-research'))
    rc, out = run(d)
    ok('NO AUDIT DOCUMENTS -> exit 2 COULD NOT RUN, not a ledger saying every '
       'app is uncovered', rc == 2 and 'COULD NOT RUN' in out,
       'exit=%d\n%s' % (rc, out[-400:]))

    os.remove(os.path.join(d, 'probeapp.html'))
    rc, out = run(d)
    ok('NO APP FILES -> exit 2 as well, for the same reason from the other '
       'side', rc == 2, 'exit=%d\n%s' % (rc, out[-300:]))
finally:
    shutil.rmtree(d, ignore_errors=True)

# ── 4. the real tool writes nothing ───────────────────────────────────────
before = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO,
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace').stdout
subprocess.run([sys.executable, os.path.join(REPO, TOOL_REL)],
               capture_output=True, cwd=REPO, timeout=240)
after = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace').stdout
ok('a bare run of the REAL tool writes no tracked file', before == after,
   'git status changed:\n%s' % after)

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
