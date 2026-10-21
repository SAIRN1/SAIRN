#!/usr/bin/env python
# OWNER: cc
# written 2026-10-21, batch b46
"""Is what is INSTALLED the thing the manifests DECLARE -- and is it what loads?

    python tools/dependency_integrity_check.py              # every manifest
    python tools/dependency_integrity_check.py --paths a b  # only manifests these paths depend on
    python tools/dependency_integrity_check.py --json       # machine-readable, for the push gate
    python tools/dependency_integrity_check.py --fixtures   # the criteria lock alone

Exit 0 every checked dependency is installed, matches, and is what loads;
1 at least one finding (DRIFT, SHADOW, MISSING); 2 COULD NOT RUN -- never
folded into either of the other two (PR 1.11).

CONCEPT (cc b46): a dependency installed is not verified until its resolution
is checked against the lock, every single time. A stale global copy or a
differently-versioned local install masks real test results indefinitely.

WHY IT EXISTS, MEASURED ON 2026-10-21 (cc b44/b45): C:\\Users\\marsh\\
node_modules held firebase-admin 12.7.0 and stripe. No clone had its own
node_modules, so Node's parent-directory walk found the home copy, and every
clone's SDK-dependent api tests ran against 12.7.0 while the lock said
13.10.0. Nothing failed. The tests were green on the wrong code, which is the
dangerous shape.

THE FOUR MANIFESTS, and what is checked for each:
  package.json + package-lock.json (npm)
    DECLARED  package.json's dependencies equal the lock root's (npm ci would
              refuse otherwise, and a hand edit can desync them)
    MISSING   a locked package has no node_modules/<path>/package.json
    DRIFT     its installed version is not the locked version, exactly
    SHADOW    a node_modules directory exists in an ANCESTOR of the clone --
              the home-directory copy, which wins whenever the clone lacks one
    LOADS     each direct dependency, resolved by node from api/_lib, lands
              under <clone>/node_modules and nowhere else
  tools/, tests/, docs/ requirements.txt (pip, this interpreter)
    MISSING   no distribution of that name is installed
    DRIFT     the installed version is below the >= floor, or differs from an == pin
    SHADOW    more than one distribution of that name is visible on sys.path
    LOADS     the module that imports is from the distribution that was checked

WHAT IT CANNOT TELL YOU: that the lock itself is safe (OSV and Dependabot do
that), or what a DIFFERENT interpreter or a deployed runtime has installed.
It checks this clone and this `python`.
"""
import json
import os
import re
import subprocess
import sys

CRITERIA_VERSION = '2026-10-21.1'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY_MANIFESTS = ('tools/requirements.txt', 'tests/requirements.txt', 'docs/requirements.txt')
NPM_MANIFEST = 'package.json'
REQ_RE = re.compile(r'^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(==|>=)\s*([0-9][0-9A-Za-z.+-]*)\s*$')


def _vkey(v):
    out = []
    for part in re.split(r'[.+-]', str(v)):
        m = re.match(r'(\d+)', part)
        out.append(int(m.group(1)) if m else 0)
    return tuple(out)


def _norm(name):
    return re.sub(r'[-_.]+', '-', name).lower()


# ── npm ────────────────────────────────────────────────────────────────────
def ancestor_node_modules(repo):
    found, d = [], os.path.dirname(os.path.abspath(repo))
    while True:
        cand = os.path.join(d, 'node_modules')
        if os.path.isdir(cand):
            found.append(cand)
        parent = os.path.dirname(d)
        if parent == d:
            return found
        d = parent


def check_npm(repo, node_resolve=True):
    rows = []
    pj = os.path.join(repo, 'package.json')
    lk = os.path.join(repo, 'package-lock.json')
    if not os.path.isfile(pj):
        return rows, None
    try:
        pkg = json.load(open(pj, encoding='utf-8'))
        lock = json.load(open(lk, encoding='utf-8'))['packages']
    except Exception as e:                                       # noqa: BLE001
        return rows, 'package.json / package-lock.json unreadable: %s' % e
    declared = dict(pkg.get('dependencies') or {})
    locked_root = dict((lock.get('') or {}).get('dependencies') or {})
    if declared != locked_root:
        rows.append(('DECLARED', 'package.json', 'dependencies %r != lock root %r' % (declared, locked_root)))
    for shadow in ancestor_node_modules(repo):
        rows.append(('SHADOW', shadow, 'a node_modules ABOVE the clone -- Node walks to it whenever the clone lacks a package'))
    for path, meta in sorted(lock.items()):
        if not path or not path.startswith('node_modules/') or meta.get('link'):
            continue
        inst = os.path.join(repo, *path.split('/'), 'package.json')
        if not os.path.isfile(inst):
            if meta.get('optional') or meta.get('dev') or meta.get('peer'):
                continue
            rows.append(('MISSING', path, 'locked %s, not installed' % meta.get('version')))
            continue
        try:
            got = json.load(open(inst, encoding='utf-8')).get('version')
        except Exception:                                        # noqa: BLE001
            got = None
        if got != meta.get('version'):
            rows.append(('DRIFT', path, 'locked %s, installed %s' % (meta.get('version'), got)))
    if node_resolve and declared and not any(r[0] == 'MISSING' and r[1].count('/') == 1 for r in rows):
        script = ("const p=require('path');const want=" + json.dumps(sorted(declared)) + ";"
                  "for(const m of want){try{console.log(m+'\\t'+require.resolve(m,{paths:[process.argv[1]]}))}"
                  "catch(e){console.log(m+'\\tERR '+e.code)}}")
        try:
            out = subprocess.run(['node', '-e', script, os.path.join(repo, 'api', '_lib')],
                                 capture_output=True, text=True, timeout=60).stdout
        except Exception as e:                                   # noqa: BLE001
            return rows, 'node could not be run to check resolution (%s) -- the LOADS check did not run' % e
        root = os.path.normcase(os.path.join(os.path.abspath(repo), 'node_modules'))
        for line in out.splitlines():
            if '\t' not in line:
                continue
            m, where = line.split('\t', 1)
            if where.startswith('ERR') or not os.path.normcase(os.path.abspath(where)).startswith(root + os.sep):
                rows.append(('LOADS', m, 'resolves to %s, not <clone>/node_modules' % where))
    return rows, None


# ── pip ────────────────────────────────────────────────────────────────────
def parse_requirements(path):
    reqs, bad = [], []
    for i, raw in enumerate(open(path, encoding='utf-8'), 1):
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        m = REQ_RE.match(line)
        if m:
            reqs.append((m.group(1), m.group(2), m.group(3)))
        else:
            bad.append('%s:%d %r is not NAME>=X or NAME==X' % (os.path.basename(path), i, line))
    return reqs, bad


def check_pip(repo, manifests):
    import importlib.metadata as md
    import importlib.util
    rows, cant = [], []
    dists = {}
    for d in md.distributions():
        n = d.metadata.get('Name')
        if n:
            dists.setdefault(_norm(n), []).append(d)
    try:
        top = md.packages_distributions()
    except Exception:                                            # noqa: BLE001
        top = {}
    for rel in manifests:
        path = os.path.join(repo, *rel.split('/'))
        if not os.path.isfile(path):
            continue
        reqs, bad = parse_requirements(path)
        cant += bad
        for name, op, ver in reqs:
            have = dists.get(_norm(name), [])
            locs = sorted({str(getattr(d, '_path', '?')) for d in have})
            if not have:
                rows.append(('MISSING', '%s %s' % (rel, name), 'declared %s%s, not installed in %s' % (op, ver, sys.executable)))
                continue
            vers = sorted({d.version for d in have}, key=_vkey)
            if len(locs) > 1:
                rows.append(('SHADOW', '%s %s' % (rel, name), '%d copies visible: %s' % (len(locs), ' | '.join(
                    '%s@%s' % (d.version, getattr(d, '_path', '?')) for d in have))))
            v = vers[0]
            if (op == '>=' and _vkey(v) < _vkey(ver)) or (op == '==' and v != ver):
                rows.append(('DRIFT', '%s %s' % (rel, name), 'declared %s%s, installed %s' % (op, ver, v)))
            mods = [m for m, ds in top.items() if _norm(name) in {_norm(x) for x in ds}]
            for mod in mods[:1]:
                spec = importlib.util.find_spec(mod)
                origin = os.path.normcase(str(getattr(spec, 'origin', '') or ''))
                homes = [os.path.normcase(os.path.dirname(str(getattr(d, '_path', '')))) for d in have]
                if spec is None or not any(origin.startswith(h + os.sep) for h in homes if h):
                    rows.append(('LOADS', '%s %s' % (rel, name), 'import %s loads from %s, not from the checked distribution' % (mod, origin or 'nowhere')))
    return rows, cant


# ── scope: which manifests does a set of paths depend on ───────────────────
def manifests_for(paths, repo):
    paths = [p.replace('\\', '/') for p in paths]
    want = set()
    npm_deps = []
    try:
        npm_deps = sorted((json.load(open(os.path.join(repo, 'package.json'), encoding='utf-8')).get('dependencies') or {}))
    except Exception:                                            # noqa: BLE001
        pass
    for p in paths:
        if p in ('package.json', 'package-lock.json'):
            want.add('npm')
        elif p in PY_MANIFESTS:
            want.add(p)
        elif p.endswith(('.js', '.mjs', '.cjs')) and npm_deps:
            try:
                src = open(os.path.join(repo, *p.split('/')), encoding='utf-8', errors='replace').read()
            except Exception:                                    # noqa: BLE001
                continue
            if any(re.search(r"""require\(\s*['"]%s['"]""" % re.escape(d), src) for d in npm_deps):
                want.add('npm')
        elif p.endswith('.py'):
            top = p.split('/')[0]
            man = top + '/requirements.txt'
            if man in PY_MANIFESTS and os.path.isfile(os.path.join(repo, *man.split('/'))):
                reqs, _ = parse_requirements(os.path.join(repo, *man.split('/')))
                try:
                    src = open(os.path.join(repo, *p.split('/')), encoding='utf-8', errors='replace').read()
                except Exception:                                # noqa: BLE001
                    continue
                import importlib.metadata as md
                try:
                    top_map = md.packages_distributions()
                except Exception:                                # noqa: BLE001
                    top_map = {}
                names = {_norm(n) for n, _, _ in reqs}
                mods = [m for m, ds in top_map.items() if names & {_norm(x) for x in ds}] or [n.replace('-', '_') for n in names]
                if any(re.search(r'^\s*(import|from)\s+%s\b' % re.escape(m), src, re.M) for m in mods):
                    want.add(man)
    return want


def run(repo, scope=None, node_resolve=True):
    findings, cant, checked = [], [], []
    if scope is None or 'npm' in scope:
        rows, err = check_npm(repo, node_resolve=node_resolve)
        if err:
            cant.append(err)
        if os.path.isfile(os.path.join(repo, 'package.json')):
            checked.append('package.json + package-lock.json')
        findings += rows
    py = [m for m in PY_MANIFESTS if scope is None or m in scope]
    if py:
        rows, bad = check_pip(repo, py)
        findings += rows
        cant += bad
        checked += [m for m in py if os.path.isfile(os.path.join(repo, *m.split('/')))]
    return findings, cant, checked


# ── criteria lock ──────────────────────────────────────────────────────────
def fixtures():
    import shutil
    import tempfile
    ok = bad = 0

    def check(label, got, want):
        nonlocal ok, bad
        if got == want:
            ok += 1
        else:
            bad += 1
            print('  LOCK FAILED  %s\n               wanted %r\n               got    %r' % (label, want, got))

    def tree(lock_ver, inst_ver, declared='^1.0.0', locked_decl='^1.0.0'):
        t = tempfile.mkdtemp(prefix='depint-')
        repo = os.path.join(t, 'clone')
        os.makedirs(os.path.join(repo, 'node_modules', 'pkg'))
        json.dump({'dependencies': {'pkg': declared}}, open(os.path.join(repo, 'package.json'), 'w'))
        json.dump({'packages': {'': {'dependencies': {'pkg': locked_decl}},
                                'node_modules/pkg': {'version': lock_ver}}}, open(os.path.join(repo, 'package-lock.json'), 'w'))
        if inst_ver is not None:
            json.dump({'version': inst_ver}, open(os.path.join(repo, 'node_modules', 'pkg', 'package.json'), 'w'))
        return t, repo

    kinds = lambda rows: sorted({r[0] for r in rows})               # noqa: E731
    t, r = tree('1.2.3', '1.2.3')
    check('npm: installed == locked -> no finding', kinds(check_npm(r, node_resolve=False)[0]), [])
    shutil.rmtree(t, ignore_errors=True)
    t, r = tree('1.2.3', '1.2.4')
    check('npm: installed 1.2.4 vs locked 1.2.3 -> DRIFT (exact, not semver-compatible)', kinds(check_npm(r, node_resolve=False)[0]), ['DRIFT'])
    shutil.rmtree(t, ignore_errors=True)
    t, r = tree('1.2.3', None)
    check('npm: locked but not installed -> MISSING', kinds(check_npm(r, node_resolve=False)[0]), ['MISSING'])
    shutil.rmtree(t, ignore_errors=True)
    t, r = tree('1.2.3', '1.2.3', declared='^2.0.0')
    check('npm: package.json disagrees with the lock root -> DECLARED', kinds(check_npm(r, node_resolve=False)[0]), ['DECLARED'])
    shutil.rmtree(t, ignore_errors=True)
    t, r = tree('1.2.3', '1.2.3')
    os.makedirs(os.path.join(t, 'node_modules', 'pkg'))
    check('npm: a node_modules in an ANCESTOR -> SHADOW (the 2026-10-21 incident)', kinds(check_npm(r, node_resolve=False)[0]), ['SHADOW'])
    shutil.rmtree(t, ignore_errors=True)
    check('version order: 6.16.1 < 6.20.1', _vkey('6.16.1') < _vkey('6.20.1'), True)
    check('version order: 6.21.2 >= 6.20.1', _vkey('6.21.2') >= _vkey('6.20.1'), True)
    check('version order: 13.10.0 > 13.9.0 (not string order)', _vkey('13.10.0') > _vkey('13.9.0'), True)
    tdir = tempfile.mkdtemp(prefix='depint-req-')
    p = os.path.join(tdir, 'requirements.txt')
    open(p, 'w').write('# c\npypdf>=6.20.1\nfoo==1.0\nbad line\n')
    reqs, badl = parse_requirements(p)
    check('requirements: >= and == parsed, comments skipped', reqs, [('pypdf', '>=', '6.20.1'), ('foo', '==', '1.0')])
    check('requirements: an unparseable line is reported, not skipped', len(badl), 1)
    shutil.rmtree(tdir, ignore_errors=True)
    print('DEPENDENCY INTEGRITY -- criteria lock %s: %d/%d fixtures classify correctly' % (CRITERIA_VERSION, ok, ok + bad))
    return 0 if not bad else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--fixtures' in argv:
        return fixtures()
    if fixtures() != 0:
        print('COULD NOT RUN: the criteria lock is broken, so no verdict below would mean anything.')
        return 2
    scope = None
    if '--paths' in argv:
        i = argv.index('--paths')
        paths = [a for a in argv[i + 1:] if not a.startswith('--')]
        scope = manifests_for(paths, REPO)
    findings, cant, checked = run(REPO, scope)
    as_json = '--json' in argv
    code = 2 if cant else (1 if findings else 0)
    if as_json:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'scope': sorted(scope) if scope is not None else 'all',
                          'checked': checked, 'findings': [{'kind': k, 'what': w, 'detail': d} for k, w, d in findings],
                          'could_not_run': cant, 'exit': code}))
        return code
    print('DEPENDENCY INTEGRITY -- interpreter %s' % sys.executable)
    print('  scope   : %s' % ('every manifest' if scope is None else (sorted(scope) or 'none of the four manifests -- nothing to check')))
    print('  checked : %s' % (', '.join(checked) or 'nothing'))
    for k, w, d in findings:
        print('  %-8s %s -- %s' % (k, w, d))
    for c in cant:
        print('  COULD NOT RUN: %s' % c)
    print({0: 'CLEAN: every checked dependency is installed, matches its declaration, and is what loads.',
           1: 'FINDING: %d dependency row(s) do not match what is declared.' % len(findings),
           2: 'COULD NOT RUN: part of the check did not run, and that is not a pass.'}[code])
    return code


if __name__ == '__main__':
    sys.exit(main())
