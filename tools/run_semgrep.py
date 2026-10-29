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

  * AND THE APPS THEMSELVES WERE NEVER SCANNED BY THE SAIRN RULES (cody b62).
    The custom rules are `languages: [javascript, typescript]`, so Semgrep
    targets .js/.ts files only. Every app is an .html file whose code is
    INLINE <script>, and Semgrep removed extract mode (which read inline
    script) in 1.65.0 -- so 24 apps' JavaScript was never a target, and this
    tool only reported files that appeared in `errors`. A file Semgrep never
    targets is in neither `results` nor `errors`: silent. Now each tracked
    app's inline scripts are extracted to a .js twin with the SAME line numbers
    (everything else blanked), scanned with the same config, and mapped back to
    the .html path. And the report states what no rule here targets at all
    (the tracked .sql files), from Semgrep's own `paths.scanned`, rather than
    leaving it implied.

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
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(REPO, 'tools', 'semgrep')


# ── THE OUTPUT STREAM IS MADE SAFE BEFORE ANYTHING IS PRINTED ──────────────
# Found 2026-09-15 while running `--test` from a hook-shaped invocation.
#
# THE BUG: semgrep's own output contains U+2713 (a tick). On Windows, Python
# encodes stdout with the LOCALE encoding -- cp1252 -- whenever stdout is not a
# terminal, which is to say whenever a hook, a CI step or another script
# CAPTURES it. `print(out.strip())` then raised
# UnicodeEncodeError: 'charmap' codec can't encode character '✓'.
#
# AND THE FAILURE MODE IS THE WORST SHAPE THIS REPO RECORDS. Semgrep had
# already run and already passed. What the caller received was not a verdict
# and not a clean failure -- it was a TRACEBACK with a non-zero exit, from a
# check that had actually succeeded. A gate reading that exit code sees a
# failed scan. The tool works perfectly when a human runs it in a terminal and
# breaks in precisely the configuration that matters.
#
# UTF-8 RATHER THAN errors='replace' ON THE LOCALE ENCODING, deliberately:
# replacing silently turns a tick into `?` and a box-drawing rule into noise,
# which is information loss in a tool whose whole reason to exist is that it
# refuses to imply coverage it does not have. errors='replace' stays as the
# floor for anything UTF-8 still cannot carry.
#
# NOT SWEPT PLATFORM-WIDE, and the number is stated rather than left implied:
# 94 of 138 files in tools/ contain non-ASCII output characters and carry no
# such guard, so this is one instance of a class. Fixing the other 93 is a
# separate decision, not a rider on this one.
def _make_stdout_safe():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            # Python without io.TextIOWrapper.reconfigure, or a stream that is
            # not one. Nothing to do; the print below is still the old hazard,
            # which is why this is a try and not a hard requirement.
            pass


_make_stdout_safe()


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


_SCRIPT = re.compile(r'(<script\b([^>]*)>)(.*?)</script\s*>', re.S | re.I)
_JS_TYPE = re.compile(r'''\btype\s*=\s*["']?([\w/+.-]+)''', re.I)
JS_TYPES = ('', 'text/javascript', 'application/javascript', 'module')


def inline_js(html):
    """The page with everything but inline JavaScript blanked, newlines kept,
    so a finding's line in the twin IS its line in the .html. A <script src>
    is not inline, and a non-JS type (JSON, templates) is not JavaScript."""
    keep = [False] * len(html)
    for m in _SCRIPT.finditer(html):
        attrs = m.group(2)
        t = _JS_TYPE.search(attrs)
        if re.search(r'\bsrc\s*=', attrs, re.I) or (t and t.group(1).lower() not in JS_TYPES):
            continue
        for i in range(m.start(3), m.end(3)):
            keep[i] = True
    return ''.join(c if keep[i] or c == '\n' else ' ' for i, c in enumerate(html))


def tracked(*patterns):
    r = subprocess.run(['git', 'ls-files', '-z', '--'] + list(patterns), cwd=REPO,
                       capture_output=True)
    if r.returncode != 0:
        return None
    return [p for p in r.stdout.decode('utf-8', 'replace').split('\0')
            if p and not p.startswith(('archive/', 'docs/skill-backups/', 'node_modules/'))]


def extract_apps(outdir):
    """({twin path: tracked .html path}, [apps that could not be read]).
    An unreadable app is returned, never skipped: it is a could-not-scan."""
    twins, unreadable = {}, []
    apps = tracked('*.html')
    if apps is None:
        return twins, ['(git ls-files failed -- no app list)']
    for rel in apps:
        try:
            src = open(os.path.join(REPO, rel), encoding='utf-8', errors='replace').read()
        except OSError as e:
            unreadable.append('%s (%s)' % (rel, e))
            continue
        js = inline_js(src)
        if not js.strip():
            continue
        twin = os.path.join(outdir, rel.replace('/', '__') + '.inline.js')
        with open(twin, 'w', encoding='utf-8', newline='') as fh:
            fh.write(js)
        twins[os.path.normcase(os.path.abspath(twin))] = rel
    return twins, unreadable


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
    twin_dir = tempfile.mkdtemp(prefix='sairn-semgrep-apps-')
    twins, unreadable_apps = extract_apps(twin_dir)
    cmd = [exe, 'scan', '--config', config, '--json', '-o', tmp,
           '--metrics=off', '--no-git-ignore',
           '--max-target-bytes', '0', '--timeout', '60',
           '--exclude', 'node_modules', '--exclude', '.git',
           '--exclude', 'archive', '--exclude', 'docs/skill-backups',
           # The rule fixtures contain deliberate violations. Excluded from the
           # scan, never from `--test`, which is what proves the rules fire.
           '--exclude', 'tools/semgrep', REPO, twin_dir]
    p = subprocess.run(cmd, cwd=REPO, env=env(), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if not os.path.exists(tmp):
        shutil.rmtree(twin_dir, ignore_errors=True)
        print(((p.stdout or '') + (p.stderr or '')).strip()[-2000:])
        print('\nSemgrep produced no report. NOT a pass.')
        return 2

    d = json.load(open(tmp, encoding='utf-8'))
    shutil.rmtree(twin_dir, ignore_errors=True)
    results, errors = d.get('results', []), d.get('errors', [])

    def home(pth):
        return twins.get(os.path.normcase(os.path.abspath(os.path.join(REPO, str(pth)))), pth)
    for x in results:
        x['path'] = home(x['path'])
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
        unscanned.setdefault(str(home(pth)), set()).add(str(t))
    if unscanned:
        print('\n  COULD NOT FULLY SCAN -- %d file(s). NOT a pass:' % len(unscanned))
        for pth, ts in sorted(unscanned.items()):
            print('    %-46s %s' % (pth, ','.join(sorted(ts))))

    # WHAT THIS CONFIG NEVER TARGETS, stated rather than implied: Semgrep's own
    # list of scanned paths against what is tracked. A language no rule here
    # covers is a SCOPE LIMIT, printed every run; it is not a pass for it.
    scanned = {os.path.normcase(os.path.abspath(os.path.join(REPO, q)))
               for q in (d.get('paths') or {}).get('scanned', [])}
    print('\n  APPS: inline JavaScript of %d tracked .html file(s) scanned via '
          'line-preserving twins' % len(set(twins) & scanned))
    not_twinned = sorted(set(twins) - scanned)
    sql = tracked('*.sql')
    if sql is None:
        print('  COULD NOT LIST tracked files -- coverage below is unknown')
        return 2
    sql_hit = [q for q in sql if os.path.normcase(os.path.abspath(os.path.join(REPO, q))) in scanned]
    print('  NOT COVERED: %d of %d tracked .sql file(s) -- no rule in this config '
          'targets SQL' % (len(sql) - len(sql_hit), len(sql)))
    if not_twinned or unreadable_apps:
        print('  COULD NOT SCAN the inline JS of %d app(s). NOT a pass:'
              % (len(not_twinned) + len(unreadable_apps)))
        for t in not_twinned:
            print('    ' + twins[t])
        for t in unreadable_apps:
            print('    ' + t)

    if unscanned or not_twinned or unreadable_apps:
        return 2
    return 1 if results else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
