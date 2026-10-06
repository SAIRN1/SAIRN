# OWNER: hank
"""cp1252_console_sweep.py -- which tools/*.py DIE when the console cannot
encode what they print?

    python tools/cp1252_console_sweep.py
    python tools/cp1252_console_sweep.py --timeout 25 --workers 8
    python tools/cp1252_console_sweep.py --only accepted_risk_expiry_audit.py
    python tools/cp1252_console_sweep.py --selftest

── WHY THIS IS A REAL POPULATION AND NOT A STYLE CHECK ───────────────────────
Every tool in this repo draws box rules with U+2500 and uses en/em dashes in its
prose. `cp1252` is the real console encoding on this machine, and it cannot
encode any of them. A tool that prints one dies with UnicodeEncodeError -- and
on the tools that matter it dies AT THE REPORTING STAGE, after the work is done,
so the process exits non-zero and prints nothing. `exit 1` is also what a
report-only checker returns for FINDINGS, so the surviving signal is
indistinguishable from a normal run.

MEASURED 2026-10-05: 296 tools driven, ONE crash --
tools/accepted_risk_expiry_audit.py, which computed the whole audit correctly
and could not say it. Five more had already been fixed one at a time over the
preceding day, one of which (citation_line_drift_check.py) died MID-SWEEP and
recorded an entire app as SOUND=0 DRIFTED=0 INCONCLUSIVE=0 over 51 citations --
a crash read as a clean file.

THE FIX IS ALWAYS THE STREAM, NEVER THE TEXT:

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

ASCII-ing one file fixes one file and leaves the pattern in the other ~295.

── IT RUNS IN A SCRATCH COPY, AND THAT IS NOT OPTIONAL ───────────────────────
A measurable fraction of these tools WRITE when run -- 22 were counted as
write-when-run on 2026-09-30, and ten write to the live platform. A sweep that
mutates its own subject produces a number about a tree nobody will see again.
The copy is made with `git archive HEAD`, so it is the committed tree and not a
dirty one, and it is made UNDER THE SYSTEM TEMP DIRECTORY -- never a path
hardcoded to one clone.

THE ROOT IS DERIVED FROM __file__, NOT FROM `git rev-parse --show-toplevel`,
and the repo documents the reason: the HOME directory is itself a git
repository, so git's upward discovery SUCCEEDS from anywhere beneath it and
answers about THAT repository -- exit 0, confident, wrong. See
tools/git_discovery_anchoring_check.py. A path derived from __file__ cannot be
wrong about which tree this file is in.

── A TIMEOUT IS A THIRD STATE ────────────────────────────────────────────────
Reported apart from crashes and apart from clean runs, always, and never folded
into the pass count. The 2026-10-05 run had 27 timeouts at 25s; re-driven at
600s, 26 answered and exactly one -- run_all_tests.py, which drives the whole
suite -- still did not. That one is COULD NOT TELL. `295 of 296` is a result;
`295` is not.

── EVERY ROW IS FLUSHED AS IT LANDS ──────────────────────────────────────────
The first version of this sweep buffered and wrote its report at the end. It was
killed at ten minutes and produced an EMPTY FILE -- a long run whose first check
is at the end, which is the standing convention it broke while enforcing a
different one. Each row is written and flushed as its tool finishes, so a kill
leaves a true partial answer.

── ITS OWN EXIT STATUS GOES TO A FILE ────────────────────────────────────────
Use tools/capture_exit.py (cody's) for any backgrounded run of this sweep:

    python tools/capture_exit.py --status sweep.status -- \
        python tools/cp1252_console_sweep.py
    python tools/capture_exit.py --read sweep.status

A backgrounded `cmd > out; echo $?` reports the status of the `echo`, so a
caller sees 0 whatever happened. Two tools were reported as "completed (exit
code 0)" while their captured stdout said 1 and 2. A harness completion status
is never this sweep's exit code.

EXIT: 0 no crash, 1 at least one crash, 2 COULD NOT RUN (no scratch copy).
"""
import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
import concurrent.futures as cf

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRITERIA_VERSION = '2026-10-06.1'

CRASH_MARKERS = ('UnicodeEncodeError', 'UnicodeDecodeError')


def forced_env():
    """An environment whose stdio genuinely cannot encode the box rules."""
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'cp1252'
    env['PYTHONUTF8'] = '0'
    env['PYTHONLEGACYWINDOWSSTDIO'] = '1'
    return env


def scratch_tree():
    """A copy of the COMMITTED tree, under the system temp dir.

    Returns (path, None) or (None, reason). `git archive` is anchored with -C so
    it cannot answer about the home-directory repository.
    """
    d = tempfile.mkdtemp(prefix='cp1252sweep-')
    tar = os.path.join(d, 'tree.tar')
    try:
        with io.open(tar, 'wb') as fh:
            p = subprocess.run(['git', '-C', REPO, 'archive', 'HEAD'],
                               stdout=fh, stderr=subprocess.PIPE)
        if p.returncode != 0:
            return None, 'git archive HEAD failed: %s' % (
                p.stderr.decode('utf-8', 'replace')[:200])
        root = os.path.join(d, 'tree')
        os.makedirs(root)
        p = subprocess.run(['tar', '-x', '-f', tar, '-C', root],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0:
            return None, 'tar extract failed: %s' % (
                p.stderr.decode('utf-8', 'replace')[:200])
        if not os.path.isdir(os.path.join(root, 'tools')):
            return None, 'the extracted copy has no tools/ directory'
        return root, None
    except Exception as e:                                       # noqa: BLE001
        return None, '%s: %s' % (type(e).__name__, e)


def classify(blob, rc):
    for m in CRASH_MARKERS:
        if m in blob:
            detail = ''
            for line in blob.split('\n'):
                if m in line:
                    detail = line.strip()[:190]
                    break
            return m, detail
    return 'ok rc=%d' % rc, ''


def drive(root, name, env, timeout):
    try:
        p = subprocess.run([sys.executable, os.path.join('tools', name)],
                           cwd=root, env=env, timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except subprocess.TimeoutExpired:
        return name, 'TIMEOUT', ''
    except Exception as e:                                       # noqa: BLE001
        return name, 'HARNESS-ERROR', '%s: %s' % (type(e).__name__, str(e)[:150])
    blob = p.stdout.decode('utf-8', 'replace')
    status, detail = classify(blob, p.returncode)
    return name, status, detail


def selftest():
    print('cp1252_console_sweep selftest -- criteria %s\n' % CRITERIA_VERSION)
    npass = nfail = 0

    def ck(label, cond, extra=''):
        nonlocal npass, nfail
        if cond:
            npass += 1
            print('  ok   ' + label)
        else:
            nfail += 1
            print('  FAIL ' + label)
            if extra:
                print('       ' + str(extra)[:200])

    env = forced_env()
    ck('A1. the forced environment really does say cp1252 -- without this every '
       'arm below would be measuring a UTF-8 console and finding nothing',
       env['PYTHONIOENCODING'] == 'cp1252' and env['PYTHONUTF8'] == '0')

    # A real child, not a string fixture: the box rule this repo uses everywhere.
    d = tempfile.mkdtemp(prefix='cp1252selftest-')
    try:
        bad = os.path.join(d, 'tools')
        os.makedirs(bad)
        p = os.path.join(bad, 'zz_boxrule.py')
        io.open(p, 'w', encoding='utf-8', newline='\n').write(
            u"print(u'\\u2500\\u2500 a box rule \\u2500\\u2500')\n")
        name, status, _ = drive(d, 'zz_boxrule.py', env, 30)
        ck('A2. a child printing the repo own box rule CRASHES under the forced '
           'console -- this is the defect being swept for, driven rather than '
           'asserted', status == 'UnicodeEncodeError', status)

        q = os.path.join(bad, 'zz_guarded.py')
        io.open(q, 'w', encoding='utf-8', newline='\n').write(
            u"import sys\n"
            u"if hasattr(sys.stdout, 'reconfigure'):\n"
            u"    sys.stdout.reconfigure(encoding='utf-8')\n"
            u"print(u'\\u2500\\u2500 a box rule \\u2500\\u2500')\n")
        name, status, _ = drive(d, 'zz_guarded.py', env, 30)
        ck('A3. the SAME text with the stream reconfigured does NOT crash. '
           'WITHOUT THIS ARM the sweep could be flagging every tool and A2 '
           'would still pass', status.startswith('ok'), status)

        r = os.path.join(bad, 'zz_findings.py')
        io.open(r, 'w', encoding='utf-8', newline='\n').write(
            u"import sys\nprint('two findings')\nsys.exit(1)\n")
        name, status, _ = drive(d, 'zz_findings.py', env, 30)
        ck('B1. a clean tool that exits 1 for FINDINGS is NOT counted as a '
           'crash -- exit 1 is a verdict on this platform, not a failure',
           status == 'ok rc=1', status)

        s = os.path.join(bad, 'zz_slow.py')
        io.open(s, 'w', encoding='utf-8', newline='\n').write(
            u"import time\ntime.sleep(5)\n")
        name, status, _ = drive(d, 'zz_slow.py', env, 1)
        ck('B2. a tool that outruns the timeout is TIMEOUT -- a third state, '
           'never folded into ok and never into a crash',
           status == 'TIMEOUT', status)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    root, why = scratch_tree()
    ck('C1. the scratch copy is a real tree with a tools/ directory, built from '
       'the COMMITTED HEAD rather than the working tree', root is not None, why)
    if root:
        ck('C2. ...and it is NOT the live clone, so a write-when-run tool '
           'cannot mutate the repo this sweep is reporting on',
           os.path.abspath(root) != os.path.abspath(REPO), root)
        shutil.rmtree(os.path.dirname(root), ignore_errors=True)

    print('\n%d passed, %d failed' % (npass, nfail))
    return 1 if nfail else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='drive tools/*.py under a cp1252 console')
    ap.add_argument('--timeout', type=int, default=25)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--only', action='append', default=None,
                    help='one tool basename; repeatable. Use for a re-drive.')
    ap.add_argument('--out', default=None, help='report path (default: beside the scratch copy)')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()

    root, why = scratch_tree()
    if root is None:
        print('COULD NOT RUN: no scratch copy -- %s' % why)
        print('This is NOT "no crashes". Nothing was driven.')
        return 2

    names = sorted(f for f in os.listdir(os.path.join(root, 'tools'))
                   if f.endswith('.py'))
    universe = len(names)
    if a.only:
        wanted = set(a.only)
        names = [n for n in names if n in wanted]
        missing = sorted(wanted - set(names))
        if missing:
            print('COULD NOT RUN: --only named %d tool(s) not present in '
                  'tools/: %s' % (len(missing), ', '.join(missing)))
            return 2

    out = a.out or os.path.join(os.path.dirname(root), 'cp1252-sweep.txt')
    env = forced_env()
    rows = []
    fh = io.open(out, 'w', encoding='utf-8', newline='\n')
    print('cp1252 CONSOLE SWEEP -- criteria %s' % CRITERIA_VERSION)
    print('  scratch copy : %s' % root)
    print('  report       : %s' % out)
    print('  SELECTED / UNIVERSE : %d / %d   (tools/*.py in the committed tree)'
          % (len(names), universe))
    print('  timeout      : %ds   (a timeout is a THIRD STATE, never a pass)' % a.timeout)
    print('')
    try:
        with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
            futs = [ex.submit(drive, root, n, env, a.timeout) for n in names]
            for f in cf.as_completed(futs):
                r = f.result()
                rows.append(r)
                fh.write('%-46s %-20s %s\n' % r)
                fh.flush()
    finally:
        crashed = [r for r in rows if r[1] in CRASH_MARKERS]
        timeouts = [r for r in rows if r[1] == 'TIMEOUT']
        harness = [r for r in rows if r[1] == 'HARNESS-ERROR']
        tail = []
        tail.append('')
        tail.append('SELECTED : %d of %d tools/*.py' % (len(rows), universe))
        tail.append('CRASHED  : %d  (UnicodeEncodeError / UnicodeDecodeError only)' % len(crashed))
        tail.append('TIMEOUT  : %d  (COULD NOT TELL at %ds -- not a pass)'
                    % (len(timeouts), a.timeout))
        tail.append('HARNESS  : %d' % len(harness))
        for t, k, _d in crashed:
            tail.append('  CRASH   %-42s %s' % (t, k))
        for t, _k, _d in timeouts:
            tail.append('  TIMEOUT %s' % t)
        for t, _k, d in harness:
            tail.append('  HARNESS %-42s %s' % (t, d))
        for line in tail:
            fh.write(line + '\n')
            print(line)
        fh.close()
        shutil.rmtree(os.path.dirname(root), ignore_errors=True)

    if timeouts:
        print('')
        print('RE-DRIVE THE TIMEOUTS BEFORE REPORTING A POPULATION:')
        print('  python tools/cp1252_console_sweep.py --timeout 600 --workers 1 \\')
        for t, _k, _d in timeouts[:6]:
            print('      --only %s \\' % t)
        print('      --out <path>')
    return 1 if crashed else 0


if __name__ == '__main__':
    sys.exit(main())
