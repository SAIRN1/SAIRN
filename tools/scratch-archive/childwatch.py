# OWNER: cody
"""Item 7: time every test file BY WATCHING THE SUITE RUN IT, not by a second run.

WHY NOT A SEPARATE TIMED RUN. Running 748 files again, alone, while a 748-file
suite is already running would make both numbers meaningless -- two CPU-bound
runs on four cores measure contention, not the files. And a file run alone can
take a DIFFERENT path from the one the suite drives: batch 23 measured
run_hover_audit_method_sabotage_probe.py at 567s alone where it stopped early on
a red baseline, which is why that number was reported as a lower bound on a
different path and the file was NOT named.

So this samples Win32_Process for the suite's grandchildren and records
first_seen / last_seen per command line. The duration is therefore accurate to
the sample interval, and the interval is stated with every figure.

HARD TIMEOUT: the item asks for one. This watcher does not kill anything -- it
RECORDS any child whose observed lifetime exceeds TIMEOUT_S and flags it, which
is the bound the item wants without a watcher that can terminate another
session's work.
"""
import io
import subprocess
import sys
import time

ROOT = sys.argv[1]
STATUS = sys.argv[2]
OUT = sys.argv[3]
INTERVAL = 15
TIMEOUT_S = 900
BOUND_S = 5 * 3600

PS = r'''
# ── THE PID IS INTERPOLATED, NOT PASSED AS A PARAMETER (fixed 2026-10-08) ───
# THE 2026-10-07/08 RUN RECORDED NOTHING AND LOOKED LIKE IT HAD. This script was
# invoked as `powershell -NoProfile -Command <script> -root <pid>`, and with
# -Command the trailing arguments are NOT bound to a param() block -- so $root
# was $null, the filter became "ParentProcessId=" and matched the handful of
# system processes whose parent is 0. Measured afterwards: 14,976 samples over
# 3h13m, 100% with an EMPTY command line, 6 distinct pids (0, 4, 236, 276, 1000,
# 4416) and ZERO test files. The summary then reported "6 distinct children,
# longest 11635s TIMEOUT", which reads like a finding and is an artefact of
# watching the kernel.
#
# A silent no-op dressed as a result -- the exact shape this platform keeps
# paying for, this time inside the measuring instrument.
$root = __ROOT__
function Kids($id) { Get-CimInstance Win32_Process -Filter ("ParentProcessId=" + $id) }
$lvl = @([int]$root)
for ($i=0; $i -lt 6; $i++) {
  $next = @()
  foreach ($p in $lvl) {
    foreach ($k in Kids $p) {
      Write-Output ("" + $k.ProcessId + "`t" + $k.CommandLine)
      $next += $k.ProcessId
    }
  }
  if ($next.Count -eq 0) { break }
  $lvl = $next
}
'''

seen = {}


def poll():
    script = PS.replace('__ROOT__', str(int(ROOT)))
    if '__ROOT__' in script:                     # refuse rather than watch pid 0
        raise SystemExit('childwatch: the root pid did not reach the script')
    r = subprocess.run(['powershell', '-NoProfile', '-Command', script],
                       capture_output=True, encoding='utf-8', errors='replace')
    out = []
    for line in (r.stdout or '').splitlines():
        if '\t' not in line:
            continue
        pid, cmd = line.split('\t', 1)
        out.append((pid.strip(), cmd.strip()))
    return out


def running():
    try:
        return 'RUNNING' in io.open(STATUS, encoding='utf-8', errors='replace').read()
    except Exception:
        return True


# ── APPEND AS WE GO, BECAUSE THE FIRST VERSION WROTE ONLY AT THE END ────────
# That version accumulated in memory and wrote the report once, on exit. The
# 2026-10-07 run was KILLED at 2h15m and every timing it had collected went with
# it -- convention 10, "no long run whose first check is at the end", committed
# inside a watcher built to measure a long run. Each sample is now flushed to a
# live log, so a kill costs the last 15 seconds instead of the whole run.
live = io.open(OUT + '.live', 'w', encoding='utf-8', newline='\n')
live.write('# appended per sample; the summary below is rebuilt from this\n')
live.write('utc\tpid\tcommand\n')
live.flush()

t0 = time.time()
while time.time() - t0 < BOUND_S:
    now = time.time()
    stamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))
    for pid, cmd in poll():
        key = (pid, cmd)
        if key not in seen:
            seen[key] = [now, now]
        else:
            seen[key][1] = now
        live.write('%s\t%s\t%s\n' % (stamp, pid, cmd))
    live.flush()
    if not running():
        break
    time.sleep(INTERVAL)
live.close()

rows = []
for (pid, cmd), (a, b) in seen.items():
    rows.append((b - a + INTERVAL, pid, cmd))
rows.sort(reverse=True)
f = io.open(OUT, 'w', encoding='utf-8', newline='\n')
f.write('# observed child lifetimes, sample interval %ds, so each figure is '
        '+/- %ds\n' % (INTERVAL, INTERVAL))
f.write('# TIMEOUT flag at %ds -- recorded, never killed\n' % TIMEOUT_S)
f.write('# distinct (pid, commandline) pairs observed: %d\n' % len(rows))
f.write('%-9s %-8s %-7s %s\n' % ('seconds', 'pid', 'flag', 'command'))
for secs, pid, cmd in rows:
    f.write('%9.0f %-8s %-7s %s\n'
            % (secs, pid, 'TIMEOUT' if secs > TIMEOUT_S else '', cmd[:150]))
f.close()
print('CHILDWATCH DONE: %d distinct children, longest %.0fs -> %s'
      % (len(rows), rows[0][0] if rows else 0, OUT))
