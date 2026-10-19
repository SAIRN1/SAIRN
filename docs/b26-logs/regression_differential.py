# b26 regression run -- every suite that references api/sd-data.js, driven
# ALONE, in a DISPOSABLE WORKTREE, with its real exit code captured per file
# and its last printed line recorded the way tools/run_all_tests.py does.
#
# THE CONCEPT: a conversion touching 193 call sites in one 19,800-line handler
#   has a blast radius nobody can read, so the whole set of suites that
#   reference that handler is driven and each one's exit code is compared
#   against docs/known-red-suites.json -- a failure already registered is
#   ATTRIBUTABLE, and anything else is NEW and is the finding.
#
# SEGMENTED on purpose (convention 10): a verdict is flushed per suite and a
# running tally every 20, so a run killed at minute 20 still yields what it
# got through.
import io, json, os, subprocess, sys, tempfile, time

REPO = os.getcwd()
reg = json.load(io.open('docs/known-red-suites.json', encoding='utf-8'))
KNOWN = {e['file']: e for e in reg.get('entries', [])}

cands = []
for d in ('api', 'api/_lib', 'api/_resources', 'tests'):
    if not os.path.isdir(d):
        continue
    for f in sorted(os.listdir(d)):
        p = (d + '/' + f)
        if not os.path.isfile(p):
            continue
        if not (f.endswith('.test.js') or (d == 'tests' and f.endswith('.js'))):
            continue
        try:
            t = io.open(p, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        if 'sd-data' in t:
            cands.append(p)

print('B26 REGRESSION -- suites referencing api/sd-data.js')
print('  repo      ' + REPO)
print('  suites    ' + str(len(cands)))
print('  registry  ' + str(len(KNOWN)) + ' known-red entries')
print('  NOTE: JS only. The .py half of the tree is not in this run and is '
      'NOT counted as clean.')
sys.stdout.flush()

env = dict(os.environ)
env['SAIRN_BYPASS_LOG'] = os.path.join(tempfile.gettempdir(),
                                       'b26-regr-bypass.jsonl')
rows = []
t0 = time.time()
for i, p in enumerate(cands):
    try:
        r = subprocess.run(['node', p], cwd=REPO, capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           env=env, timeout=300)
        out = (r.stdout or r.stderr or '').strip().splitlines()
        tail = out[-1] if out else '(no output)'
        code = r.returncode
    except subprocess.TimeoutExpired:
        tail, code = 'TIMED OUT after 300s', None
    state = ('GREEN' if code == 0 else
             'SKIPPED' if code == 3 else
             'RED_KNOWN' if p in KNOWN else 'RED_NEW')
    rows.append({'file': p, 'exit': code, 'state': state, 'tail': tail})
    if state in ('RED_NEW', 'RED_KNOWN'):
        print('  %-11s %-56s exit %s' % (state, p[:56], code))
        print('        ' + tail[:150])
        sys.stdout.flush()
    if (i + 1) % 20 == 0:
        c = {}
        for x in rows:
            c[x['state']] = c.get(x['state'], 0) + 1
        print('    ... %d/%d  %s  (%.0fs)'
              % (i + 1, len(cands), json.dumps(c), time.time() - t0))
        sys.stdout.flush()

c = {}
for x in rows:
    c[x['state']] = c.get(x['state'], 0) + 1
print('')
print('REGRESSION RESULT -- %d suites, %.0fs' % (len(rows), time.time() - t0))
for k, n in sorted(c.items(), key=lambda y: -y[1]):
    print('  %-11s %4d' % (k, n))
print('')
new = [x for x in rows if x['state'] == 'RED_NEW']
print('RED AND NOT REGISTERED (the finding, if any): ' + str(len(new)))
for x in new:
    print('  * %s  exit %s' % (x['file'], x['exit']))
    print('      ' + x['tail'][:200])
io.open('b26_regression.json', 'w', encoding='utf-8').write(
    json.dumps({'measured': '2026-10-19', 'by': 'cody b26',
                'suites': len(rows), 'summary': c, 'rows': rows}, indent=1))
print('\nwrote b26_regression.json')
sys.exit(0 if not new else 1)
