#!/usr/bin/env python
"""dependency_health_check.py (hover2's own build) -- the automated version
of the npm/Python currency audit that has so far only ever been run by
hand. Built after checking for overlap first (this role's own seq 103):
Hank's 2026-09-15 pass and cody's later delta-check were both one-off
manual audits, never wired as a re-runnable tool -- confirmed by grep,
nothing named dependency_health_check.py or equivalent existed anywhere in
this repo before this file. Approved to build 2026-09-23.

WHAT IT CHECKS, AND WHY EACH METHOD WAS RE-DERIVED RATHER THAN COPIED:

  NPM DIRECT DEPENDENCIES. Reads package.json's own "dependencies" object
  (never node_modules -- this clone carries none, Vercel installs at build
  time, so a tool that read node_modules would report nothing installed at
  all, the exact trap Hank's own audit named). Locked version comes from
  package-lock.json's packages["node_modules/<name>"].version, not the
  package.json range. Latest comes from the npm registry's own
  <pkg>/latest endpoint, live.

  PYTHON THIRD-PARTY IMPORTS. Hank's own measured method, re-run here: AST-
  parse every .py file's real import statements (never a regex over source
  text -- a regex is what matched 'a', 'the', 'that' and 'outside' out of
  prose inside docstrings the first time this was tried, a documented
  failure this file does not repeat), then INTERSECT that set against
  importlib.metadata.packages_distributions() -- the same "measured by
  intersecting real imports with installed distribution names" sentence
  the standing audit already used. A name in the import set that is NOT a
  real installed distribution is a local module (tools/foo.py importing
  tools/bar.py), not a dependency, and must not be counted -- 114 of 116
  raw import names in this repo are exactly that shape, checked directly
  before writing this tool.

  GITHUB ACTIONS NODE VERSION. .github/workflows/*.yml's own
  node-version: literal, compared against this clone's actual `node
  --version`. Mechanical, no network needed.

WHAT IS DELIBERATELY OUT OF SCOPE, NAMED RATHER THAN SILENTLY DROPPED:
  * Skills mirror-drift. Cody's 2026-08-25 fix made ~/.claude/skills/
    sairn-* NATIVE SYMLINKS into a real clone -- the two copies cannot
    diverge by construction any more, so a byte-diff checker here would
    only ever re-prove a structural invariant, not find real drift. If
    that symlink convention is ever reversed, this is the first place to
    add the check back.
  * Plugin version currency (superpower, vercel, postgres-grant-sweep,
    typescript-lsp). The standing audit already found two of four
    CANNOT be judged from local state -- the marketplace manifests
    declare no version and the marketplace itself is not a git checkout.
    Nothing changed that fact; re-measuring it here would report the same
    COULD-NOT-TELL every run for no new information.

Every latest-version lookup is LIVE, over the real network, on every run --
this is what "automated" means here as opposed to the prior manual passes,
which is also why a network failure is reported as its own COULD_NOT_CHECK
state (PR SS1.11 -- "could not run" is a third state, never folded into
"current" or "behind").

    python dependency_health_check.py
    python dependency_health_check.py --json
    python dependency_health_check.py --fixtures
"""
import io
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

REPO = r"C:\Users\marsh\Documents\SAIRN-hover2"


def semver_majors_behind(current, latest):
    """(major_diff, comparable:bool). Best-effort: strips a leading ^/~/v,
    splits on '.', compares the first numeric field only -- enough to
    answer 'how many majors behind', not a full semver order."""
    def first_num(v):
        v = re.sub(r'^[\^~v=\s]+', '', v or '')
        m = re.match(r'(\d+)', v)
        return int(m.group(1)) if m else None
    c, l = first_num(current), first_num(latest)
    if c is None or l is None:
        return None, False
    return l - c, True


# ------------------------------------------------------------------- NPM
def read_npm_direct_deps(repo=REPO):
    pkg = json.load(io.open(os.path.join(repo, 'package.json'), encoding='utf-8'))
    return dict(pkg.get('dependencies', {}))


def read_npm_locked_versions(repo=REPO, names=None):
    lock = json.load(io.open(os.path.join(repo, 'package-lock.json'), encoding='utf-8'))
    packages = lock.get('packages', {})
    out = {}
    for name in (names or []):
        entry = packages.get('node_modules/%s' % name)
        out[name] = entry.get('version') if entry else None
    return out


def fetch_npm_latest(name, fetcher):
    try:
        data = fetcher('https://registry.npmjs.org/%s/latest' % name)
        return json.loads(data).get('version'), None
    except Exception as e:
        return None, repr(e)


def check_npm(repo=REPO, fetcher=None):
    fetcher = fetcher or _real_fetch
    direct = read_npm_direct_deps(repo)
    locked = read_npm_locked_versions(repo, direct.keys())
    rows = []
    for name in sorted(direct):
        cur = locked.get(name)
        latest, err = (None, 'no locked version found') if cur is None else fetch_npm_latest(name, fetcher)
        majors, comparable = semver_majors_behind(cur, latest) if latest else (None, False)
        rows.append({
            'name': name, 'range': direct[name], 'locked': cur, 'latest': latest,
            'majors_behind': majors, 'error': err,
        })
    return rows


# ---------------------------------------------------------------- PYTHON
def scan_python_third_party_imports(repo=REPO):
    import ast
    stdlib = getattr(sys, 'stdlib_module_names', frozenset())
    names = set()
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '__pycache__')]
        for f in files:
            if not f.endswith('.py'):
                continue
            path = os.path.join(root, f)
            try:
                tree = ast.parse(io.open(path, encoding='utf-8', errors='ignore').read(), filename=path)
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for n in node.names:
                        names.add(n.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.level == 0 and node.module:
                        names.add(node.module.split('.')[0])
    return names - set(stdlib)


def resolve_real_python_deps(imported_names, packages_distributions_fn=None):
    """Intersect imported names against installed distributions. Returns
    {import_name: [dist_name, ...]} -- ONLY names that are real installed
    packages, never a local intra-repo module."""
    import importlib.metadata as md
    fn = packages_distributions_fn or md.packages_distributions
    pd = fn()
    return {n: pd[n] for n in sorted(imported_names) if n in pd}


def fetch_pypi_latest(dist_name, fetcher):
    try:
        data = fetcher('https://pypi.org/pypi/%s/json' % dist_name)
        return json.loads(data).get('info', {}).get('version'), None
    except Exception as e:
        return None, repr(e)


def check_python(repo=REPO, fetcher=None, version_fn=None):
    import importlib.metadata as md
    fetcher = fetcher or _real_fetch
    version_fn = version_fn or md.version
    imported = scan_python_third_party_imports(repo)
    real = resolve_real_python_deps(imported)
    rows = []
    for import_name, dists in real.items():
        for dist in dists:
            try:
                installed = version_fn(dist)
            except Exception as e:
                installed, err0 = None, repr(e)
            else:
                err0 = None
            latest, err1 = fetch_pypi_latest(dist, fetcher) if installed else (None, err0)
            err = err0 or err1
            majors, comparable = semver_majors_behind(installed, latest) if (installed and latest) else (None, False)
            rows.append({
                'import_name': import_name, 'dist': dist, 'installed': installed,
                'latest': latest, 'majors_behind': majors, 'error': err,
            })
    return rows, sorted(imported - set(real.keys()))  # second value: local-module candidates, for transparency


# ------------------------------------------------------------ GH ACTIONS
def check_node_version_pin(repo=REPO, node_version_fn=None):
    node_version_fn = node_version_fn or _real_node_version
    wf_dir = os.path.join(repo, '.github', 'workflows')
    pins = []
    if os.path.isdir(wf_dir):
        for fn in sorted(os.listdir(wf_dir)):
            if not fn.endswith(('.yml', '.yaml')):
                continue
            text = io.open(os.path.join(wf_dir, fn), encoding='utf-8').read()
            for m in re.finditer(r"node-version:\s*['\"]?(\d+)", text):
                pins.append({'file': fn, 'pinned_major': int(m.group(1))})
    local, err = node_version_fn()
    for p in pins:
        p['local_major'] = local
        p['drift'] = (local - p['pinned_major']) if (local is not None) else None
    return pins, local, err


def _real_node_version():
    try:
        out = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=15)
        m = re.match(r'v(\d+)', out.stdout.strip())
        return (int(m.group(1)) if m else None), None
    except Exception as e:
        return None, repr(e)


def _real_fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'sairn-hover2-dependency-health-check'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8')


# ---------------------------------------------------------------- fixtures
def run_fixtures():
    bad = []

    def ck(name, cond):
        print(('  ok   ' if cond else '  FAIL ') + name)
        if not cond:
            bad.append(name)

    ck('semver_majors_behind: 17.7.0 vs 22.6.2 is 5 majors, comparable',
       semver_majors_behind('17.7.0', '22.6.2') == (5, True))
    ck('semver_majors_behind: a caret range is stripped before comparing',
       semver_majors_behind('^13.3.2', '14.0.2') == (1, True))
    ck('semver_majors_behind: an unparseable version reports not comparable, '
       'not a fabricated 0', semver_majors_behind('n/a', '1.0.0') == (None, False))

    def fake_npm_fetch(url):
        assert 'registry.npmjs.org' in url
        return json.dumps({'version': '99.0.0'})
    rows = check_npm(fetcher=fake_npm_fetch)
    names = {r['name'] for r in rows}
    ck('check_npm() reads the real three direct deps from this repo\'s own '
       'package.json (stripe, firebase-admin, @simplewebauthn/server)',
       names == {'stripe', 'firebase-admin', '@simplewebauthn/server'})
    ck('check_npm() reads LOCKED versions from package-lock.json, not the '
       'package.json range',
       all(r['locked'] and not r['locked'].startswith('^') for r in rows))
    ck('check_npm() computes majors_behind against the (stubbed) registry '
       'latest, not a hardcoded number',
       all(r['majors_behind'] is not None for r in rows))

    def fake_pd():
        # a local intra-repo module has NO entry at all -- packages_distributions()
        # never returns an empty-list placeholder for something that isn't installed
        return {'pypdf': ['pypdf']}
    real = resolve_real_python_deps({'pypdf', 'a_local_tool_module', 'os'}, fake_pd)
    ck('resolve_real_python_deps() keeps a name that IS an installed '
       'distribution (pypdf) and drops one that maps to nothing (a local '
       'intra-repo module, the real 114-of-116 shape measured against this '
       'repo)', real == {'pypdf': ['pypdf']})

    def fake_pypi_fetch(url):
        assert 'pypi.org' in url
        return json.dumps({'info': {'version': '9.9.9'}})
    p_rows, locals_ = check_python(fetcher=fake_pypi_fetch)
    ck('check_python() finds pypdf as a real dependency of this repo '
       '(matches the standing audit\'s own "exactly one" claim, re-measured)',
       any(r['dist'] == 'pypdf' for r in p_rows))
    ck('check_python() separately reports the non-dependency import names '
       'it excluded, for transparency, rather than silently dropping them',
       len(locals_) > 50)

    def fake_node_version():
        return 24, None
    pins, local, err = check_node_version_pin(node_version_fn=fake_node_version)
    ck('check_node_version_pin() reads the real pin from '
       '.github/workflows/nightly-backup.yml',
       any(p['file'] == 'nightly-backup.yml' and p['pinned_major'] == 24 for p in pins))
    ck('check_node_version_pin() computes drift against the (stubbed) local '
       'node version', all(p['drift'] == 0 for p in pins if p['file'] == 'nightly-backup.yml'))

    if bad:
        print('%d of 10 fixture(s) failed -- refusing to judge real dependencies' % len(bad))
        return 2
    print('OK -- 10/10 fixtures passed')
    return 0


def main(argv):
    if '--fixtures' in argv:
        return run_fixtures()

    fx_buf = io.StringIO()
    _stdout = sys.stdout
    sys.stdout = fx_buf
    try:
        fx_rc = run_fixtures()
    finally:
        sys.stdout = _stdout
    if fx_rc != 0:
        print(fx_buf.getvalue())
        print('FIXTURES FAILED -- nothing real was judged')
        return 2

    npm_rows = check_npm()
    py_rows, py_locals = check_python()
    node_pins, node_local, node_err = check_node_version_pin()

    as_json = '--json' in argv
    if as_json:
        print(json.dumps({'npm': npm_rows, 'python': py_rows,
                           'python_excluded_local_modules': py_locals,
                           'node_pins': node_pins, 'node_local': node_local,
                           'node_error': node_err}, indent=2))
        behind = any((r.get('majors_behind') or 0) > 0 for r in npm_rows + py_rows)
        return 1 if behind else 0

    print('DEPENDENCY HEALTH CHECK -- live registry lookups, %d npm + %d python '
          'real third-party dependencies' % (len(npm_rows), len(py_rows)))
    print('NPM (direct deps only, versions from package-lock.json):')
    for r in npm_rows:
        if r['error']:
            print('  %-24s COULD_NOT_CHECK -- %s' % (r['name'], r['error']))
        else:
            print('  %-24s locked=%-10s latest=%-10s majors_behind=%s' %
                  (r['name'], r['locked'], r['latest'], r['majors_behind']))
    print('PYTHON (real third-party imports only, %d local-module import '
          'names excluded):' % len(py_locals))
    if not py_rows:
        print('  none')
    for r in py_rows:
        if r['error']:
            print('  %-24s COULD_NOT_CHECK -- %s' % (r['dist'], r['error']))
        else:
            print('  %-24s installed=%-10s latest=%-10s majors_behind=%s' %
                  (r['dist'], r['installed'], r['latest'], r['majors_behind']))
    print('GITHUB ACTIONS node-version pins (local node major=%s%s):' %
          (node_local, '' if not node_err else ' -- COULD_NOT_CHECK: %s' % node_err))
    for p in node_pins:
        print('  %-24s pinned=%s drift=%s' % (p['file'], p['pinned_major'], p['drift']))
    print()
    print('OUT OF SCOPE, NAMED NOT SILENT: skills mirror-drift (structurally '
          'fixed by symlinks since 2026-08-25) and plugin version currency '
          '(2 of 4 plugins have no version this clone can read at all).')

    behind = any((r.get('majors_behind') or 0) > 0 for r in npm_rows + py_rows)
    errored = any(r.get('error') for r in npm_rows + py_rows) or bool(node_err)
    return 1 if (behind or errored) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
