# -*- coding: utf-8 -*-
"""Does tests/run_floor_layers_probe.py actually NOTICE each layer going away?

cc's docs/ablation/floor_layers.py removed each of the three layers from
tools/run_all_tests.py and ran cody's OLD floor probe against each mutant. All
three stayed green -- FINDING 2. This re-runs that measurement against the NEW
probe, which is the only thing that turns "arms added" into "arms that work".

tools/ IS CC'S AND IS NEVER WRITTEN. The tool is COPIED to a temp directory,
the copy is mutated, and the probe is pointed at the copy by putting that
directory first on sys.path. cc's own harness edited the tracked tool in place
and had to assert byte-identity afterwards; copying removes the need for that
assurance entirely.
"""
import io, json, os, shutil, subprocess, sys, tempfile

REPO = os.getcwd()
TOOL = os.path.join(REPO, 'tools', 'run_all_tests.py')
PROBE = os.path.join(REPO, 'tests', 'run_floor_layers_probe.py')

LAYERS = [
    ('ratchet', 'the floor is read from the pin instead of the literal',
     'MIN_TEST_FILES = _read_floor()[0]',
     'MIN_TEST_FILES = _MIN_TEST_FILES_FLOOR',
     # KEYED ON R4, NOT R1. Removing this layer leaves _read_floor()
     # intact, so R1 -- which calls it directly -- stays green. Only an
     # arm on the module CONSTANT can see wiring being cut.
     'R4'),
    ('tracked-intersection',
     'the raise is clamped to the count git tracks',
     '    count = min(count, tracked)',
     '    count = count',
     'T1'),
    ('silence-breaking', '`behind` is inside the early-return condition',
     '    if not failures and not skipped and not retried and not shrunk \\\n'
     '            and not behind:',
     '    if not failures and not skipped and not retried and not shrunk:',
     'S1'),
]

src = io.open(TOOL, encoding='utf-8').read()
print('ABLATION -- tests/run_floor_layers_probe.py vs the three layers')
print('tools/ is COPIED, never written. %d layer(s).\n' % len(LAYERS))


def write_pin(docsdir):
    """A floor pin ABOVE the literal, beside a copy of the tool.

    THE COPY NEEDS THE REAL TREE'S SHAPE or the ratchet layer is untestable:
    the tool computes _FLOOR_PATH from its OWN location, so a bare copy in a
    flat temp dir cannot resolve docs/test-file-floor.json, falls back to the
    last-resort literal, and the mutant becomes indistinguishable from the
    original. That is exactly why the first ablation run reported
    "ratchet NOT CAUGHT" against an arm that was fine.
    """
    io.open(os.path.join(docsdir, 'test-file-floor.json'), 'w',
            encoding='utf-8', newline=chr(10)).write(
        json.dumps({'floor': 900,
                    'how': 'ablation fixture, above the literal'}) + chr(10))


def drive(tooldir):
    """Run the probe against the copy of the tool in `tooldir`.

    VIA THE PROBE'S OWN INJECTION POINT, not PYTHONPATH. The first spelling
    shadowed tools/ with PYTHONPATH and the probe's own
    `sys.path.insert(0, REPO/tools)` won, so every mutant run imported the
    REAL tool and all three layers reported NOT CAUGHT -- against arms that
    were fine.
    """
    env = dict(os.environ)
    env['SAIRN_B16_RUN_ALL_TESTS'] = os.path.join(tooldir, 'run_all_tests.py')
    r = subprocess.run([sys.executable, '-u', PROBE], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=300, env=env)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def arm_state(out, tag):
    for line in out.split('\n'):
        s = line.strip()
        if s.startswith('ok   ' + tag) or s.startswith('ok  ' + tag):
            return 'ok'
        if s.startswith('FAIL ' + tag):
            return 'FAIL'
        if s.startswith('UNPROVEN ' + tag):
            return 'UNPROVEN'
    return None


base = tempfile.mkdtemp(prefix='floor-ablate-base-')
_bt = os.path.join(base, 'tools'); os.makedirs(_bt)
_bd = os.path.join(base, 'docs'); os.makedirs(_bd)
write_pin(_bd)
shutil.copy2(TOOL, os.path.join(_bt, 'run_all_tests.py'))
rc0, out0 = drive(_bt)
print('BASELINE (unmutated copy) -> exit %d' % rc0)
for _n, _w, _f, _r, tag in LAYERS:
    print('    %-4s %s' % (tag, arm_state(out0, tag)))
if rc0 != 0:
    print('\nCOULD NOT RUN: the baseline copy is not green, so no mutation '
          'below would mean anything.')
    sys.exit(2)

bad = 0
for name, what, find, repl, tag in LAYERS:
    print('')
    if find not in src:
        print('=== %-22s UNPROVEN: the layer anchor is not in the tool. The '
              'layer may have been reworded -- re-read it rather than '
              'trusting this row.' % name)
        bad += 1
        continue
    d = tempfile.mkdtemp(prefix='floor-ablate-')
    tdir = os.path.join(d, 'tools'); os.makedirs(tdir)
    ddir = os.path.join(d, 'docs'); os.makedirs(ddir)
    write_pin(ddir)
    io.open(os.path.join(tdir, 'run_all_tests.py'), 'w', encoding='utf-8',
            newline='\n').write(src.replace(find, repl, 1))
    rc, out = drive(tdir)
    st = arm_state(out, tag)
    good = (st in ('FAIL', 'UNPROVEN')) and rc != 0
    print('=== %-22s %s' % (name, 'CAUGHT' if good else '*** NOT CAUGHT ***'))
    print('    removed  : %s' % what)
    print('    probe    : exit %d, arm %s -> %s' % (rc, tag, st))
    if not good:
        bad += 1
        for l in [x.strip() for x in out.split('\n') if x.strip()][-4:]:
            print('      (tail) ' + l[:150])
    shutil.rmtree(d, ignore_errors=True)

shutil.rmtree(base, ignore_errors=True)
print('')
print('tools/run_all_tests.py untouched:',
      io.open(TOOL, encoding='utf-8').read() == src)
print('%d of %d layer(s) caught' % (len(LAYERS) - bad, len(LAYERS)))
sys.exit(1 if bad else 0)
