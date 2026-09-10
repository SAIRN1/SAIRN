"""Run Semgrep over this repo with the flags that stop it lying about coverage.

WHY THIS EXISTS RATHER THAN A DOCUMENTED COMMAND LINE. Semgrep's defaults are
tuned for a normal repo and this one is not normal, so a bare `semgrep scan`
reports a clean, confident result over a materially smaller repo than the one
you have:

  * FILES OVER 1 MB ARE SKIPPED SILENTLY. stonedesk.html is ~2 MB, so the
    platform's flagship app is not scanned at all. Measured 2026-09-10: the
    default run found `missing-integrity` once, on sairnbiz.html:7. With
    `--max-target-bytes 0` the SAME ruleset finds it twice more, on
    stonedesk.html:27373 and :27374 -- the identical defect, in the bigger app,
    invisible because of a size limit nobody set on purpose.
  * PER-RULE TIMEOUTS ARE ALSO SILENT. api/sd-data.js (731 KB) timed out on 3
    rules in the default run. A timeout is not a pass; this raises it and then
    REPORTS what still timed out rather than letting the summary imply coverage.

Both are the same shape this repo keeps finding elsewhere: a check that answers
"nothing found" when it means "did not look".

Usage:
    python tools/run_semgrep.py               # custom SAIRN rules
    python tools/run_semgrep.py --default     # the p/default registry ruleset
    python tools/run_semgrep.py --test        # unit-test the custom rules

Exit 0 clean, 1 findings, 2 something could not be scanned (NOT a pass).
Needs `pip install semgrep`. On Windows the console entry point shells out to
`pysemgrep`, which is in the same Scripts directory and is usually not on PATH
-- that is handled below rather than left as a footgun.
"""
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(REPO, 'tools', 'semgrep')


def scripts_dirs():
    out = []
    for scheme in (('nt_user', 'nt') if os.name == 'nt' else ('posix_user', 'posix_prefix')):
        try:
            d = sysconfig.get_path('scripts', scheme=scheme)
        except Exception:
            d = None
        if d and os.path.isdir(d) and d not in out:
            out.append(d)
    d = sysconfig.get_path('scripts')
    if d and os.path.isdir(d) and d not in out:
        out.append(d)
    return out


def semgrep_bin():
    """Absolute path to the semgrep executable.

    RESOLVED HERE RATHER THAN LEFT TO PATH. CreateProcess on Windows looks the
    executable up in the CURRENT process's PATH, not in the env= passed to
    subprocess, so prepending the Scripts directory to the child environment
    finds pysemgrep for semgrep and still fails to find semgrep itself.
    """
    found = shutil.which('semgrep')
    if found:
        return found
    for d in scripts_dirs():
        for name in ('semgrep.exe', 'semgrep'):
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
    return None


def env():
    e = dict(os.environ)
    # Semgrep writes findings containing '->' and other non-cp1252 characters;
    # without this the JSON write dies with UnicodeEncodeError after a full scan.
    e['PYTHONIOENCODING'] = 'utf-8'
    e['PYTHONUTF8'] = '1'
    # semgrep.exe is only a launcher -- it shells out to `pysemgrep`, which
    # lives beside it and is usually not on PATH. The child needs both.
    for d in scripts_dirs():
        if d not in e.get('PATH', ''):
            e['PATH'] = d + os.pathsep + e.get('PATH', '')
    return e


def main(argv):
    exe = semgrep_bin()
    if not exe:
        print('semgrep is not installed. `pip install semgrep --break-system-packages`')
        return 2
    if '--test' in argv:
        p = subprocess.run([exe, '--test', RULES], cwd=REPO, env=env(),
                           capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        out = (p.stdout or '') + (p.stderr or '')
        print(out.strip())
        # `--test` prints "No unit tests found" AND EXITS 0. That is why the
        # rules do not live in `.semgrep/`: semgrep does not discover tests
        # inside a dot-directory, so the suite silently reported success.
        if 'No unit tests found' in out:
            print('\nNO TESTS RAN. That is a failure, not a pass.')
            return 2
        return p.returncode

    config = 'p/default' if '--default' in argv else RULES
    tmp = os.path.join(tempfile.gettempdir(), 'sairn_semgrep.json')
    cmd = [exe, 'scan', '--config', config, '--json', '-o', tmp,
           '--metrics=off', '--no-git-ignore',
           '--max-target-bytes', '0', '--timeout', '60',
           '--exclude', 'node_modules', '--exclude', '.git',
           '--exclude', 'archive', '--exclude', 'docs/skill-backups',
           # The rule fixtures contain deliberate violations. Excluded from the
           # scan, never from `--test`, which is what proves the rules fire.
           '--exclude', 'tools/semgrep', REPO]
    p = subprocess.run(cmd, cwd=REPO, env=env(), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if not os.path.exists(tmp):
        print(((p.stdout or '') + (p.stderr or '')).strip()[-2000:])
        print('\nSemgrep produced no report. NOT a pass.')
        return 2

    d = json.load(open(tmp, encoding='utf-8'))
    results, errors = d.get('results', []), d.get('errors', [])
    sev = {}
    for x in results:
        sev[x['extra']['severity']] = sev.get(x['extra']['severity'], 0) + 1

    print('SEMGREP -- config %s' % config)
    print('  findings : %d  (%s)' % (len(results),
                                     ', '.join('%s %d' % (k, v) for k, v in sorted(sev.items())) or 'none'))
    for x in sorted(results, key=lambda r: (r['extra']['severity'] != 'ERROR', r['path'])):
        print('  %-8s %s:%s  %s' % (x['extra']['severity'], x['path'],
                                    x['start']['line'], x['check_id'].split('.')[-1]))

    # A file semgrep could not read is not a file with no findings in it.
    unscanned = {}
    for e in errors:
        t = e.get('type')
        t = t[0] if isinstance(t, list) else t
        pth = e.get('path')
        if isinstance(pth, list):
            pth = '/'.join(map(str, pth))
        unscanned.setdefault(str(pth), set()).add(str(t))
    if unscanned:
        print('\n  COULD NOT FULLY SCAN -- %d file(s). NOT a pass:' % len(unscanned))
        for pth, ts in sorted(unscanned.items()):
            print('    %-46s %s' % (pth, ','.join(sorted(ts))))

    if unscanned:
        return 2
    return 1 if results else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
