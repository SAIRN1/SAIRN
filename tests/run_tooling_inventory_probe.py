"""tests/run_tooling_inventory_probe.py -- attacks tools/tooling_inventory.py.

Run:  python tests/run_tooling_inventory_probe.py

WHY. The thing this generator replaces is a HAND-DERIVED inventory that was
correct on 2026-09-09 and stale by 2026-09-12 -- 77 tools became 97, 3
report-only became 29. A generator only fixes that if it fails loudly when the
repo moves, and if its classification is right in the first place.

Every arm below plants the defect on throwaway fixtures in a temp tree, or reads
the real repo, and demands the tool see it. A generator that cannot be made to
fail is indistinguishable from one that looks at nothing.
"""
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join(REPO, 'tools', 'tooling_inventory.py')

FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + detail))
    if not cond:
        FAIL.append(name)


def load():
    spec = importlib.util.spec_from_file_location('ti_' + str(len(FAIL)), TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ti = load()

print('\nA. the document on disk matches the repo right now')
rc = subprocess.run([sys.executable, TOOL, '--check'],
                    capture_output=True, text=True, cwd=REPO)
ok('--check passes against the committed document', rc.returncode == 0,
   (rc.stdout + rc.stderr).strip()[-300:])

print('\nB. the classification is derived, and each bucket is non-empty')
tools, cls, hk, gi, reg, suite = ti.classify()
ok('it found a real number of tools', len(tools) > 80, 'found %d' % len(tools))
for bucket in ('BLOCKING', 'REPORT-ONLY', 'ADVISORY', 'UNWIRED'):
    n = sum(1 for t in tools if cls[t] == bucket)
    ok('%s is non-empty (%d)' % (bucket, n), n > 0)
ok('the push gate itself is BLOCKING',
   cls.get('sairn_push_gate_hook.py') == 'BLOCKING', cls.get('sairn_push_gate_hook.py'))
ok('a tool the gate SHELLS OUT TO is BLOCKING, not unwired',
   cls.get('employee_auth_guard_check.py') == 'BLOCKING',
   cls.get('employee_auth_guard_check.py'))
ok('a REGISTRY tool is REPORT-ONLY',
   cls.get('md_table_check.py') == 'REPORT-ONLY', cls.get('md_table_check.py'))
ok('a SessionStart hook is ADVISORY',
   cls.get('sairn_claim_hook.py') == 'ADVISORY', cls.get('sairn_claim_hook.py'))

print('\nC. `catches` for report-only tools comes from REGISTRY, not from here')
# If it were duplicated into PURPOSES the two could disagree, which is the
# claim-in-two-places failure the whole document is about.
dup = [t for t, _p, _c in ti.registry() if t in ti.PURPOSES]
ok('no REGISTRY tool is also described in PURPOSES', dup == [], str(dup))

print('\nD. the hand-written half cannot drift in either direction')
saved = dict(ti.PURPOSES)
try:
    # A tool with no entry must REFUSE, not render a blank cell.
    victim = next(t for t in tools if t in ti.PURPOSES)
    del ti.PURPOSES[victim]
    doc, err = ti.build()
    ok('a tool with no PURPOSES entry refuses to generate', doc is None and bool(err),
       str(err)[:200])
    ok('...and the refusal NAMES it', bool(err) and victim in err, str(err)[:200])
finally:
    ti.PURPOSES.clear()
    ti.PURPOSES.update(saved)

saved = dict(ti.PURPOSES)
try:
    ti.PURPOSES['zz_tool_that_does_not_exist.py'] = ('CHECKER', 'nothing')
    doc, err = ti.build()
    ok('a PURPOSES entry for a missing tool refuses too',
       doc is None and bool(err) and 'zz_tool_that_does_not_exist.py' in err,
       str(err)[:200])
finally:
    ti.PURPOSES.clear()
    ti.PURPOSES.update(saved)

print('\nE. SUITE-ONLY requires an INVOCATION, not a mention')
# The first version accepted any mention and over-classified in the OPTIMISTIC
# direction: three LIVE tools named inside a LIST in tests/sairn_http_challenge.py
# read as "the suite runs this". SUITE-ONLY reads as coverage; UNWIRED reads as a
# gap. Getting that backwards is the one direction this document must not fail in.
sand = tempfile.mkdtemp(prefix='ti-probe-')
try:
    os.makedirs(os.path.join(sand, 'tests'))
    os.makedirs(os.path.join(sand, 'tools'))
    io.open(os.path.join(sand, 'tools', 'zz_mentioned.py'), 'w').write('# x\n')
    io.open(os.path.join(sand, 'tools', 'zz_invoked.py'), 'w').write('# x\n')
    io.open(os.path.join(sand, 'tests', 'zz_probe.py'), 'w', encoding='utf-8').write(
        "# a LIST that merely names it:\n"
        "NAMES = ['zz_mentioned.py']\n"
        "# and a real invocation:\n"
        "subprocess.run([sys.executable, 'tools/zz_invoked.py'])\n")
    old_repo = ti.REPO
    try:
        ti.REPO = sand
        refs = ti.suite_refs(['zz_mentioned.py', 'zz_invoked.py'])
    finally:
        ti.REPO = old_repo
    ok('an INVOKED tool is seen', 'zz_invoked.py' in refs, str(refs))
    ok('a merely MENTIONED tool is NOT seen -- that would overstate coverage',
       'zz_mentioned.py' not in refs, str(refs))
finally:
    shutil.rmtree(sand, ignore_errors=True)

print('\nF. --check really fails when the repo moves')
# The whole point. Mutate the generated document and demand --check notice.
doc_path = os.path.join(REPO, 'docs', 'TOOLING-INVENTORY.md')
orig = io.open(doc_path, encoding='utf-8', newline='').read()
try:
    # THE ANCHOR IS DERIVED, NOT TYPED. The first version hardcoded
    # '**97 files in `tools/`.**'. Adding tools/tooling_inventory.py itself made
    # that 98, the replace became a NO-OP, and both arms went green against an
    # UNMUTATED document -- a probe passing because it changed nothing, which is
    # precisely what tools/mutation_anchor_check.py exists to catch. Caught here
    # by the same suite run that caught it, one commit after writing it.
    m = re.search(r'\*\*(\d+) files in `tools/`\.\*\*', orig)
    ok('the count anchor still matches the document', bool(m),
       'the headline wording changed; this arm would silently test nothing')
    mutated = orig.replace(m.group(0), '**%d files in `tools/`.**' % (int(m.group(1)) - 20), 1)
    ok('the mutation really changed the document', mutated != orig)
    io.open(doc_path, 'w', encoding='utf-8', newline='').write(mutated)
    rc = subprocess.run([sys.executable, TOOL, '--check'],
                        capture_output=True, text=True, cwd=REPO)
    ok('a stale count makes --check exit non-zero', rc.returncode != 0,
       'exit=%d' % rc.returncode)
    ok('...and it says what to run', 'tooling_inventory.py' in rc.stdout, rc.stdout[:200])
finally:
    io.open(doc_path, 'w', encoding='utf-8', newline='').write(orig)
    after = io.open(doc_path, encoding='utf-8', newline='').read()
    ok('the document is restored byte-identical', after == orig)

print('\nG. the claim it makes about gate checks is read from the gate')
checks = dict(ti.gate_checks())
ok('it found the numbered CHECK blocks', len(checks) >= 9, str(sorted(checks)))
ok('check 1 is the seed load state', 'seed load state' in checks.get(1, ''), checks.get(1, ''))
ok('the numbering has no gap up to its maximum',
   sorted(checks) == list(range(1, max(checks) + 1)) if checks else False,
   str(sorted(checks)))

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
