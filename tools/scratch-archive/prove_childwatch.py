# OWNER: cody
"""Prove the childwatch pid fix sees a NAMED child, where the old form saw none."""
import io, os, subprocess, sys, time

SP = os.path.dirname(os.path.abspath(__file__))
REPO = r'C:\Users\marsh\Documents\SAIRN-cody'

parent = subprocess.Popen(
    [sys.executable, '-c',
     'import subprocess,sys;subprocess.run([sys.executable,'
     '"tests/run_tier_a_review_gate_probe.py"],capture_output=True)'],
    cwd=REPO)
st = os.path.join(SP, 'proof.status')
io.open(st, 'w', encoding='utf-8').write('RUNNING %d x proof\n' % parent.pid)
w = subprocess.Popen([sys.executable, os.path.join(SP, 'childwatch.py'),
                      str(parent.pid), st, os.path.join(SP, 'proof_times.txt')],
                     cwd=REPO)
time.sleep(50)
parent.wait()
io.open(st, 'w', encoding='utf-8').write('EXIT 0 x proof\n')
w.wait(timeout=180)

rows = [l for l in io.open(os.path.join(SP, 'proof_times.txt.live'),
                           encoding='utf-8', errors='replace').read().splitlines()
        if l and not l.startswith('#') and not l.startswith('utc')]
needle = 'run_tier_a_review_gate_probe'
named = [l for l in rows if needle in l]
cols = [l.split('\t') for l in rows if l.count('\t') >= 2]
print('samples recorded          :', len(rows))
print('samples naming the child  :', len(named))
print('samples with an EMPTY cmd :', sum(1 for c in cols if not c[2].strip()))
for l in named[:3]:
    c = l.split('\t')
    print('   %s  pid %s  %s' % (c[0], c[1], c[2][-80:]))
print('VERDICT: %s' % ('the watcher now sees the real child'
                       if named else 'STILL BLIND -- do not use it'))
