# -*- coding: utf-8 -*-
"""ITEM 8 -- time tools/dead_rule_sweep.py to COMPLETION, with the load recorded.

BATCH 18 GOT A LOWER BOUND, NOT A NUMBER: TIMEOUT at 1800 s, and it had printed
three lines in thirty minutes. The item then refused to propose a bound, because
a bound from a run that did not finish is invented. This run removes the ceiling
far enough to get an actual number.

LOAD IS SAMPLED, NOT ASSUMED. Windows has no load average, so the honest
equivalent is recorded instead: the number of other python/node processes on the
box and the system-wide CPU percentage, sampled every 15 s for the whole run.
Batch 18's measurement went from 0 to 12 other processes while it ran and that
contaminated its second half; this one reports min/max/mean so a reader can see
the conditions rather than take my word for them.

IN A THROWAWAY CLONE, NOT THE LIVE CLONE AND NOT A LINKED WORKTREE. Item 6 of
this batch established that this very tool REGISTERS A WORKTREE AND LEAVES IT
REGISTERED, so running it anywhere that matters leaks a registration -- and every
registration is another door to the shared .git/config.
"""
import io
import json
import os
import subprocess
import sys
import threading
import time

CLONE = sys.argv[1]
TOOL = sys.argv[2]
CEILING = int(sys.argv[3]) if len(sys.argv) > 3 else 7200
S = os.path.dirname(os.path.abspath(__file__))

samples = []
stop = threading.Event()


def sampler():
    while not stop.is_set():
        try:
            p = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 "$p=@(Get-CimInstance Win32_Process -Filter \"Name='python.exe' "
                 "OR Name='node.exe'\").Count; "
                 "$c=(Get-CimInstance Win32_Processor | "
                 "Measure-Object -Property LoadPercentage -Average).Average; "
                 "\"$p,$c\""],
                capture_output=True, text=True, timeout=25)
            n, c = (p.stdout or '0,0').strip().split(',')[:2]
            samples.append((time.time(), int(n or 0), float(c or 0)))
        except Exception:                                   # noqa: BLE001
            samples.append((time.time(), -1, -1.0))         # COULD NOT SAMPLE
        stop.wait(15)


th = threading.Thread(target=sampler, daemon=True)
th.start()
time.sleep(1)

print('SUBJECT   tools/%s' % TOOL, flush=True)
print('CLONE     %s   (a CLONE -- this tool leaks a worktree registration)'
      % CLONE, flush=True)
print('CEILING   %ds, unbuffered' % CEILING, flush=True)
print('', flush=True)

t0 = time.time()
try:
    r = subprocess.run([sys.executable, '-u', os.path.join('tools', TOOL)],
                       cwd=CLONE, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=CEILING)
    code, out = r.returncode, r.stdout.decode('utf-8', 'replace')
except subprocess.TimeoutExpired as e:
    code = 'TIMEOUT-AT-%d' % CEILING
    out = (e.output or b'').decode('utf-8', 'replace')
el = time.time() - t0
stop.set()
th.join(timeout=30)

io.open(os.path.join(S, 'i8.%s.out' % TOOL), 'w', encoding='utf-8').write(out)
good = [s for s in samples if s[1] >= 0]
procs = [s[1] for s in good]
cpu = [s[2] for s in good]
print('EXIT       %s' % code, flush=True)
print('WALL TIME  %.1fs  (%.2f min)' % (el, el / 60.0), flush=True)
print('', flush=True)
print('LOAD, sampled every 15s for the whole run (%d sample(s), %d unreadable):'
      % (len(good), len(samples) - len(good)), flush=True)
if good:
    print('  other python/node processes : min %d  max %d  mean %.1f'
          % (min(procs), max(procs), sum(procs) / float(len(procs))), flush=True)
    print('  system CPU %%               : min %.0f  max %.0f  mean %.1f'
          % (min(cpu), max(cpu), sum(cpu) / float(len(cpu))), flush=True)
io.open(os.path.join(S, 'i8.samples.json'), 'w', encoding='utf-8').write(
    json.dumps([{'t': round(t - t0, 1), 'procs': n, 'cpu': c}
                for t, n, c in samples], indent=1))
print('', flush=True)
lines = [l for l in out.split('\n') if l.strip()]
print('output: %d non-empty line(s). First 6:' % len(lines), flush=True)
for l in lines[:6]:
    print('    %s' % l[:150], flush=True)
print('  last 6:', flush=True)
for l in lines[-6:]:
    print('    %s' % l[:150], flush=True)
