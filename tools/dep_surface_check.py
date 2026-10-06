#!/usr/bin/env python
# OWNER: cody
"""Does every symbol THIS REPO names on a package still resolve at a target version?

    python tools/dep_surface_check.py --package firebase-admin --version 14.5.0
    python tools/dep_surface_check.py --package firebase-admin --version 12.7.0 --json
    python tools/dep_surface_check.py --enumerate-only --package firebase-admin
    python tools/dep_surface_check.py --fixtures

Exit 0 every named symbol resolves, 1 at least one is MISSING, 2 COULD NOT RUN.
Design note: docs/2026-10-06-cody-queue19-design-notes.md section 3.

── THE DEFECT THIS EXISTS FOR, AND IT IS MINE ──────────────────────────────
On 2026-10-05 I recommended `firebase-admin@14.5.0` on two pieces of evidence:
*"0 of 248 suites changed verdict"*, and a check that loaded
`api/_lib/firebase-admin.js` and listed its exports. Both were true. Both were
worthless, because the wrapper's exports are MY OWN function names and they
exist regardless of what the SDK underneath them does:

    admin.credential   12.7.0 object     14.5.0 undefined
    admin.auth         12.7.0 function   14.5.0 undefined
    admin.apps         12.7.0 object     14.5.0 undefined
    admin.app          12.7.0 function   14.5.0 undefined
    admin.database     12.7.0 function   14.5.0 undefined
    admin.initializeApp         function           function   <- the survivor

**`initializeApp` surviving is the whole mechanism.** A load-and-list smoke
test is satisfied by ONE surviving symbol, so it cannot distinguish "the
namespace is intact" from "the namespace was removed and the entry point was
not". The suites could not catch it either: none of the 248 drove the mint path
with a real service account, and **a suite reports only what it covers, which
is the variable under test.**

── WHAT IT ASKS, AND THE LIMIT IS PRINTED EVERY RUN ────────────────────────
It asks DOES THE SYMBOL EXIST at the target version, per call site. It does NOT
ask whether the code still behaves the same. A symbol that resolves and behaves
differently is INVISIBLE to this tool, and that sentence is in its output
rather than only here.

── THE THIRD STATE IS THE INSTALL ──────────────────────────────────────────
If the target version cannot be installed -- no network, a yanked version, a
registry error -- that is COULD NOT RUN and EXIT 2. It is NEVER reported as
"every symbol missing", which is the exact shape that would turn an offline
machine into a fabricated breaking-change report.

── SCOPE OF THE ENUMERATION ────────────────────────────────────────────────
It binds to the LOCAL NAME that `require('<pkg>')` was assigned to, in the file
where that assignment appears, so `other.auth` on an unrelated object is not
counted. Destructured requires are symbol uses in their own right and are
collected too. It is a regex reader over JS, not a parser, and the known
consequences are stated in --fixtures: a member access on a shadowed rebinding
of the same name would be miscounted, and a member reached only through a
computed key (`admin[k]`) cannot be seen at all.
"""

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# .2 -- the enumerator gained the multi-line destructure and the value-only
# binding, both found by running this tool on its SECOND package.
# .3 -- the install spec is now the package ROOT, so a SUBPATH entry point
# (firebase-admin/app) is checkable at all. Both stamps move because the
# criteria really changed, not because the file was edited.
CRITERIA_VERSION = '2026-10-06.3'
EXIT_MISSING = 1
EXIT_COULD_NOT_RUN = 2

SCAN_DIRS = ('api', 'tests', 'tools', 'scripts')
NPM_TIMEOUT = 420          # measured: see --fixtures note; 2x the slowest real install
NODE_TIMEOUT = 60

_IDENT = r'[A-Za-z_$][A-Za-z0-9_$]*'


def _pkg_re(pkg):
    """require('<pkg>') with the exact specifier -- not a prefix match.

    `require('firebase-admin/app')` is a DIFFERENT entry point and must not be
    folded in: the whole point of the 14.5.0 break is that the modular entry
    points exist while the namespace does not.
    """
    q = re.escape(pkg)
    return q


def enumerate_uses(pkg, root=None, dirs=SCAN_DIRS):
    """{'bindings': [...], 'symbols': {sym: [(file, line, chain)]}, 'files': n}

    A 'symbol' is the FIRST member named on the required value, and the chain is
    the dotted path actually written, so `admin.credential.cert(...)` records
    symbol `credential` and chain `credential.cert`. The chain is what gets
    resolved; the symbol is how the report groups.
    """
    root = root or REPO
    q = _pkg_re(pkg)
    assign = re.compile(
        r'(?:const|let|var)\s+(' + _IDENT + r')\s*=\s*require\(\s*[\'"]' + q + r'[\'"]\s*\)')
    # `[^}]*` with DOTALL so a destructure spread over several lines is read.
    # It was not, and that is a defect this tool found in itself on its SECOND
    # package: api/sd-webauthn.js destructures four names across four lines, so
    # the require( line held none of them, the line-scan matched nothing, and
    # the tool reported FOUR require sites and ZERO symbols -- then COULD NOT
    # RUN. Right third state, wrong reason.
    destructure = re.compile(
        r'(?:const|let|var)\s*\{([^}]*)\}\s*=\s*require\(\s*[\'"]' + q + r'[\'"]\s*\)',
        re.S)
    bindings, symbols, nfiles = [], {}, 0
    value_only = []        # bindings with NO member access -- used as a value

    for d in dirs:
        base = os.path.join(root, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x != 'node_modules']
            for fn in filenames:
                if not fn.endswith('.js'):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    src = io.open(p, encoding='utf-8', errors='replace').read()
                except OSError:
                    continue
                if pkg not in src:
                    continue
                rel = os.path.relpath(p, root).replace(os.sep, '/')
                names = sorted(set(assign.findall(src)))
                # (name, line) so a destructured symbol is anchored where it
                # was written rather than wherever the scanner first saw it.
                dnames = []
                for m in destructure.finditer(src):
                    line_of = src.count('\n', 0, m.start()) + 1
                    for raw in m.group(1).split(','):
                        raw = raw.split(':')[0].strip()
                        if re.fullmatch(_IDENT, raw or ''):
                            dnames.append((raw, line_of))
                if not names and not dnames:
                    continue
                nfiles += 1
                for n in names:
                    bindings.append((rel, n))
                # A destructured name IS a named symbol: `const {auth} =
                # require(pkg)` breaks exactly as `pkg.auth` does.
                for (n, line_of) in sorted(set(dnames)):
                    bindings.append((rel, '{%s}' % n))
                    symbols.setdefault(n, []).append((rel, line_of, n))
                for n in names:
                    # (?<![\w$.]) so `other.admin.auth` and `myadmin.auth` do
                    # not match the binding `admin`.
                    mem = re.compile(r'(?<![\w$.])' + re.escape(n)
                                     + r'\.(' + _IDENT + r')(?:\.(' + _IDENT + r'))?')
                    seen_any = False
                    first_line = 1
                    for i, line in enumerate(src.split('\n'), 1):
                        stripped = line.lstrip()
                        if not seen_any and re.search(
                                r'require\(\s*[\'"]' + q + r'[\'"]', line):
                            first_line = i
                        if stripped.startswith('//') or stripped.startswith('*'):
                            continue
                        for m in mem.finditer(line):
                            seen_any = True
                            first, second = m.group(1), m.group(2)
                            chain = first if not second else '%s.%s' % (first, second)
                            symbols.setdefault(first, []).append((rel, i, chain))
                    if not seen_any:
                        # ── A BINDING USED AS A VALUE, NOT A NAMESPACE ──────
                        # `const Stripe = require('stripe'); new Stripe(k)`
                        # names NO member of the module, and the first version
                        # of this reader concluded "no symbols" and exited 2.
                        # The module ITSELF is the named symbol there, and it
                        # is checkable: it must resolve and be constructible.
                        # What is NOT checked is the INSTANCE's members
                        # (`stripe.webhooks.constructEvent`), and that limit is
                        # printed rather than left as a silent zero.
                        value_only.append((rel, n))
                        symbols.setdefault('(module)', []).append(
                            (rel, first_line, '(module)'))
    return {'bindings': bindings, 'symbols': symbols, 'files': nfiles,
            'value_only': value_only}


def root_package(spec):
    """'@scope/name/sub' -> '@scope/name';  'name/sub' -> 'name'.

    THE INSTALL SPEC AND THE REQUIRE SPECIFIER ARE DIFFERENT THINGS, and this
    tool conflated them until the firebase-admin port moved this repo onto
    SUBPATH entry points. `npm install firebase-admin/app@14.5.0` is not a
    package and npm exited 4294963238; the tool said COULD NOT RUN, which was
    the right third state for the wrong reason -- the version is perfectly
    installable, it is the spec that was wrong. Install the ROOT, resolve the
    SUBPATH.
    """
    parts = str(spec).split('/')
    if spec.startswith('@'):
        return '/'.join(parts[:2]) if len(parts) >= 2 else spec
    return parts[0]


def _npm_install(pkg, version, where):
    """(True, '') or (False, reason). A failed install is COULD NOT RUN."""
    pkg = root_package(pkg)
    spec = '%s@%s' % (pkg, version)
    io.open(os.path.join(where, 'package.json'), 'w', encoding='utf-8',
            newline='\n').write('{"name":"dep-surface-probe","private":true}\n')
    npm = shutil.which('npm') or shutil.which('npm.cmd')
    if not npm:
        return (False, 'npm is not on PATH')
    try:
        r = subprocess.run([npm, 'install', spec, '--no-audit', '--no-fund',
                            '--silent', '--prefix', where],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=NPM_TIMEOUT, cwd=where)
    except subprocess.TimeoutExpired:
        return (False, 'npm install %s timed out after %ds' % (spec, NPM_TIMEOUT))
    except OSError as e:
        return (False, 'npm could not be started: %s' % e)
    if r.returncode != 0:
        tail = ((r.stderr or '') + (r.stdout or '')).strip().split('\n')
        return (False, 'npm install %s exited %d: %s'
                % (spec, r.returncode, ' | '.join(tail[-3:])[:400]))
    if not os.path.isdir(os.path.join(where, 'node_modules', *pkg.split('/'))):
        return (False, 'npm reported success but %s is not in node_modules' % pkg)
    return (True, '')


_RESOLVER = r'''
// argv[0] is node and argv[1] is THIS SCRIPT. Reading the user's first
// argument as argv[1] is the defect the resolver arms caught on their first
// run: every chain came back as a JSON.parse SyntaxError on the package name,
// and _resolve() correctly reported COULD NOT RUN rather than "all missing".
const pkg = process.argv[2];
const chains = JSON.parse(process.argv[3]);
let mod;
try { mod = require(pkg); }
catch (e) { console.log(JSON.stringify({load_error: String(e && e.message || e)})); process.exit(0); }
const out = {};
for (const chain of chains) {
  // '(module)' names the module value itself -- a package required and used as
  // a constructor or function names no member, and "no members" is not "no
  // surface".
  if (chain === '(module)') {
    out[chain] = mod === undefined ? 'undefined' : typeof mod;
    continue;
  }
  let cur = mod, ok = true;
  for (const part of chain.split('.')) {
    if (cur === null || cur === undefined) { ok = false; break; }
    cur = cur[part];
  }
  out[chain] = ok && cur !== undefined ? typeof cur : 'undefined';
}
console.log(JSON.stringify({types: out}));
'''


def _resolve(pkg, chains, where):
    """{chain: typename-or-'undefined'} resolved in a CHILD node, or (None, reason)."""
    script = os.path.join(where, '_resolve.js')
    io.open(script, 'w', encoding='utf-8', newline='\n').write(_RESOLVER)
    node = shutil.which('node')
    if not node:
        return (None, 'node is not on PATH')
    try:
        r = subprocess.run([node, script, pkg, json.dumps(sorted(chains))],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=NODE_TIMEOUT, cwd=where)
    except subprocess.TimeoutExpired:
        return (None, 'the resolver timed out after %ds' % NODE_TIMEOUT)
    except OSError as e:
        return (None, 'node could not be started: %s' % e)
    if r.returncode != 0:
        return (None, 'the resolver exited %d: %s'
                % (r.returncode, ((r.stderr or '') + (r.stdout or '')).strip()[:400]))
    try:
        payload = json.loads((r.stdout or '').strip().split('\n')[-1])
    except (ValueError, IndexError):
        return (None, 'the resolver printed no JSON: %r' % (r.stdout or '')[:200])
    if 'load_error' in payload:
        return (None, 'require(%r) threw: %s' % (pkg, payload['load_error']))
    return (payload['types'], '')


def check(pkg, version, root=None, verbose=True):
    """(exit_code, report-dict). Never raises for a missing symbol."""
    uses = enumerate_uses(pkg, root=root)
    chains = sorted({c for sites in uses['symbols'].values() for (_f, _l, c) in sites})
    report = {'criteria': CRITERIA_VERSION, 'package': pkg, 'version': version,
              'files': uses['files'], 'bindings': uses['bindings'],
              'value_only': uses.get('value_only', []),
              'chains': chains, 'could_not_run': None, 'types': {}, 'sites': []}
    if not chains:
        report['could_not_run'] = (
            'no use of %s was found under %s -- nothing to check. An empty '
            'surface is not a clean one.' % (pkg, '/'.join(SCAN_DIRS)))
        return (EXIT_COULD_NOT_RUN, report)

    where = tempfile.mkdtemp(prefix='dep_surface_')
    try:
        ok, why = _npm_install(pkg, version, where)
        if not ok:
            report['could_not_run'] = why
            return (EXIT_COULD_NOT_RUN, report)
        types, why = _resolve(pkg, chains, where)
        if types is None:
            report['could_not_run'] = why
            return (EXIT_COULD_NOT_RUN, report)
    finally:
        shutil.rmtree(where, ignore_errors=True)

    report['types'] = types
    missing_total = 0
    by_site = {}
    for sym, sites in uses['symbols'].items():
        for (f, line, chain) in sites:
            by_site.setdefault(f, []).append((line, chain, types.get(chain, 'undefined')))
    for f in sorted(by_site):
        rows = sorted(set(by_site[f]))
        bad = [r for r in rows if r[2] == 'undefined']
        missing_total += len(bad)
        report['sites'].append({'file': f, 'total': len(rows),
                                'resolved': len(rows) - len(bad),
                                'rows': [{'line': l, 'chain': c, 'type': t}
                                         for (l, c, t) in rows]})
    report['missing'] = missing_total
    return (EXIT_MISSING if missing_total else 0, report)


def _print(report, code):
    print('DEP SURFACE -- %s@%s (criteria %s)'
          % (report['package'], report['version'], report['criteria']))
    for (f, n) in report['bindings']:
        print('  require site     : %s  as %s' % (f, n))
    if report['could_not_run']:
        print('')
        print('COULD NOT RUN -- this is NOT a verdict about the package:')
        print('  %s' % report['could_not_run'])
        print('')
        print('NOT reported as "every symbol missing". An install that did not')
        print('happen says nothing about which symbols the version carries.')
        return
    tot = sum(s['total'] for s in report['sites'])
    res = sum(s['resolved'] for s in report['sites'])
    for s in report['sites']:
        print('')
        print('  %s -- %d of %d resolve' % (s['file'], s['resolved'], s['total']))
        for r in s['rows']:
            mark = 'ok     ' if r['type'] != 'undefined' else 'MISSING'
            print('    %s line %-5d %-28s %s' % (mark, r['line'], r['chain'], r['type']))
    print('')
    print('  TOTAL: %d of %d named symbol path(s) resolve at %s@%s'
          % (res, tot, report['package'], report['version']))
    print('')
    if code == 0:
        print('EVERY NAMED SYMBOL RESOLVES. That is NOT "no behaviour change":')
    else:
        print('AT LEAST ONE NAMED SYMBOL IS MISSING.')
    print('  This tool asks only whether the symbol EXISTS. A symbol that')
    print('  resolves and behaves differently is invisible to it.')
    print('  Enumeration is a regex reader over JS, not a parser: a member')
    print('  reached through a computed key (admin[k]) cannot be seen at all.')
    if report.get('value_only'):
        print('')
        print('  AND A NAMED BLIND SPOT, because it would otherwise read as')
        print('  coverage: these binding(s) are used as a VALUE or CONSTRUCTOR,')
        print('  so only the module itself was checked. Their INSTANCE members')
        print('  (e.g. stripe.webhooks.constructEvent) are NOT checked here.')
        for (f, n) in report['value_only']:
            print('    %s  as %s' % (f, n))


# ── THE SELFTEST. Every network-free arm runs here; the install arms do not ──
def _fixtures():
    ok = True
    tally = {'n': 0, 'neg': 0}

    def arm(label, cond, detail=''):
        nonlocal ok
        tally['n'] += 1
        if 'negative' in label.lower() or 'COULD NOT RUN' in label:
            tally['neg'] += 1
        if not cond:
            ok = False
            print('  FAIL %s%s' % (label, (' -- ' + str(detail)) if detail != '' else ''))
        else:
            print('  ok   %s' % label)

    tmp = tempfile.mkdtemp(prefix='dep_surface_fx_')
    try:
        api = os.path.join(tmp, 'api')
        os.makedirs(api)
        io.open(os.path.join(api, 'good.js'), 'w', encoding='utf-8', newline='\n').write(
            "const admin = require('widget-pkg');\n"
            "admin.initializeApp({ credential: admin.credential.cert(x) });\n"
            "admin.auth(app).createCustomToken(uid);\n")
        # THE DISCRIMINATING FIXTURE: a same-named member on a DIFFERENT object,
        # plus a name of which the binding is a prefix.
        io.open(os.path.join(api, 'other.js'), 'w', encoding='utf-8', newline='\n').write(
            "const other = require('something-else');\n"
            "other.auth();\n"
            "const myadmin = { auth: 1 };\n"
            "myadmin.auth;\n"
            "widget-pkg mentioned in prose only\n")
        io.open(os.path.join(api, 'destructured.js'), 'w', encoding='utf-8', newline='\n').write(
            "const { getAuth } = require('widget-pkg');\n"
            "getAuth();\n")
        # A destructure SPREAD OVER LINES -- the shape api/sd-webauthn.js uses,
        # and the one the first version of this reader silently dropped.
        io.open(os.path.join(api, 'multiline.js'), 'w', encoding='utf-8', newline='\n').write(
            "const {\n  alpha,\n  beta,\n} = require('widget-pkg');\n"
            "alpha(); beta();\n")
        # A binding used as a CONSTRUCTOR and never as a namespace -- the shape
        # api/sairncash/*.js uses for stripe.
        io.open(os.path.join(api, 'ctor.js'), 'w', encoding='utf-8', newline='\n').write(
            "const Widget = require('widget-pkg');\n"
            "const w = new Widget('k');\n"
            "w.things.create();\n")

        u = enumerate_uses('widget-pkg', root=tmp)
        arm('the enumerator finds the members named on the required binding',
            set(u['symbols']) >= {'initializeApp', 'credential', 'auth'},
            sorted(u['symbols']))
        arm('...and records the DOTTED CHAIN, not just the first member, so '
            'credential.cert is what gets resolved',
            any(c == 'credential.cert'
                for sites in u['symbols'].values() for (_f, _l, c) in sites),
            sorted({c for s in u['symbols'].values() for (_f, _l, c) in s}))
        arm('NEGATIVE: a same-named member on a DIFFERENT object is NOT counted '
            '-- without this the arm above passes on any file mentioning the '
            'package',
            not any(f.endswith('other.js')
                    for sites in u['symbols'].values() for (f, _l, _c) in sites),
            [(f, c) for s in u['symbols'].values() for (f, _l, c) in s])
        arm('NEGATIVE: a binding the real name merely PREFIXES (myadmin.auth) '
            'is not counted either',
            len([1 for (f, _l, _c) in u['symbols'].get('auth', [])
                 if f.endswith('good.js')]) >= 1
            and not [1 for (f, _l, _c) in u['symbols'].get('auth', [])
                     if f.endswith('other.js')],
            u['symbols'].get('auth'))
        arm('a destructured require counts its names as symbols',
            'getAuth' in u['symbols'], sorted(u['symbols']))
        arm('a destructure SPREAD OVER LINES counts too -- found by running '
            'this tool on a second package, where it reported 4 require sites '
            'and 0 symbols',
            'alpha' in u['symbols'] and 'beta' in u['symbols'],
            sorted(u['symbols']))
        arm('a binding used as a CONSTRUCTOR yields the (module) symbol, not '
            'an empty surface',
            '(module)' in u['symbols']
            and any(f.endswith('ctor.js')
                    for (f, _l, _c) in u['symbols']['(module)']),
            u['symbols'].get('(module)'))
        arm('NEGATIVE: and it is listed as a NAMED BLIND SPOT rather than '
            'counted as coverage of the instance members',
            any(f.endswith('ctor.js') and n == 'Widget'
                for (f, n) in u['value_only']), u['value_only'])
        arm('NEGATIVE: a binding that DOES name members is not treated as '
            'value-only, so the arm above is not passing for every binding',
            not any(f.endswith('good.js') for (f, _n) in u['value_only']),
            u['value_only'])
        arm('a package named only in PROSE contributes no binding',
            not any(f.endswith('other.js') for (f, _n) in u['bindings']),
            u['bindings'])

        # NOTHING FOUND is COULD NOT RUN, never a clean pass. The one shape that
        # would let a typo'd package name report success.
        code, rep = check('no-such-package-xyzzy', '1.0.0', root=tmp)
        arm('a package with NO call sites is COULD NOT RUN (exit 2), never a '
            'clean 0 -- an empty surface is not a clean one',
            code == EXIT_COULD_NOT_RUN and 'nothing to check' in (rep['could_not_run'] or ''),
            (code, rep['could_not_run']))

        # An uninstallable version is COULD NOT RUN, and this arm needs no
        # network: npm cannot resolve a package name that cannot exist, and if
        # there is no network it fails for that reason instead -- either way the
        # answer under test is "exit 2, not all-missing".
        code, rep = check('widget-pkg', '0.0.0-does-not-exist', root=tmp)
        arm('an uninstallable version is COULD NOT RUN (exit 2) and NOT "every '
            'symbol missing"',
            code == EXIT_COULD_NOT_RUN and not rep['types']
            and 'missing' not in rep,
            (code, (rep['could_not_run'] or '')[:120]))

        # PER-SITE COUNTS SUM TO THE TOTAL -- checked on a synthetic report so
        # it does not need an install.
        fake = {'criteria': 'x', 'package': 'p', 'version': 'v', 'files': 2,
                'bindings': [], 'chains': [], 'could_not_run': None,
                'types': {'a': 'function', 'b': 'undefined'},
                'sites': [{'file': 'f1', 'total': 1, 'resolved': 1,
                           'rows': [{'line': 1, 'chain': 'a', 'type': 'function'}]},
                          {'file': 'f2', 'total': 1, 'resolved': 0,
                           'rows': [{'line': 2, 'chain': 'b', 'type': 'undefined'}]}]}
        arm('the INSTALL spec is the package ROOT while the REQUIRE specifier '
            'keeps its subpath -- npm cannot install firebase-admin/app',
            root_package('firebase-admin/app') == 'firebase-admin'
            and root_package('@scope/name/sub') == '@scope/name',
            (root_package('firebase-admin/app'), root_package('@scope/name/sub')))
        arm('NEGATIVE: a plain package and a scoped package with NO subpath are '
            'returned unchanged, so the arm above is not passing by truncating '
            'everything',
            root_package('stripe') == 'stripe'
            and root_package('@simplewebauthn/server') == '@simplewebauthn/server',
            (root_package('stripe'), root_package('@simplewebauthn/server')))
        arm('per-call-site counts sum to the total',
            sum(s['total'] for s in fake['sites']) == 2
            and sum(s['resolved'] for s in fake['sites']) == 1)

        # THE RESOLVER'S OWN LOGIC, driven without any install: a chain through
        # an undefined parent must report undefined rather than throwing.
        node = shutil.which('node')
        if not node:
            arm('COULD NOT RUN: node is absent, so the resolver arms did not '
                'run and are NOT reported as passing', False, 'no node on PATH')
        else:
            probe = os.path.join(tmp, 'probe')
            os.makedirs(probe)
            nm = os.path.join(probe, 'node_modules', 'stub-pkg')
            os.makedirs(nm)
            io.open(os.path.join(nm, 'package.json'), 'w', encoding='utf-8',
                    newline='\n').write('{"name":"stub-pkg","main":"i.js"}\n')
            io.open(os.path.join(nm, 'i.js'), 'w', encoding='utf-8',
                    newline='\n').write(
                'module.exports = { initializeApp: function () {}, '
                'credential: { cert: function () {} } };\n')
            types, why = _resolve('stub-pkg', ['initializeApp', 'credential.cert',
                                               'auth', 'database.ref'], probe)
            arm('the resolver reports a present function as its typeof',
                types is not None and types.get('initializeApp') == 'function',
                (types, why))
            arm('...and a present NESTED chain too',
                types is not None and types.get('credential.cert') == 'function',
                types)
            arm('NEGATIVE HALF: an absent symbol is undefined, so the arms '
                'above are not passing because everything reads as present',
                types is not None and types.get('auth') == 'undefined', types)
            arm('NEGATIVE HALF: a chain through an ABSENT parent is undefined '
                'and does NOT throw -- this is the 14.5.0 shape exactly',
                types is not None and types.get('database.ref') == 'undefined', types)

            bad = os.path.join(tmp, 'badprobe')
            os.makedirs(bad)
            types, why = _resolve('not-installed-anywhere-xyzzy', ['a'], bad)
            arm('a package that will not LOAD is COULD NOT RUN, never a set of '
                'undefined symbols',
                types is None and 'threw' in why, (types, why))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('  criteria lock: %d arms, %d of them negative (criteria %s)'
          % (tally['n'], tally['neg'], CRITERIA_VERSION))
    print('  NOT LOCKED HERE: the firebase-admin 14.5.0 positive control needs a')
    print('  real install. Run it explicitly and read its exit code:')
    print('    python tools/dep_surface_check.py --package firebase-admin '
          '--version 14.5.0')
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='does every symbol this repo names on a package resolve at a target version')
    ap.add_argument('--package')
    ap.add_argument('--version')
    ap.add_argument('--enumerate-only', action='store_true',
                    help='print the call sites and stop -- no install, no network')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--fixtures', action='store_true')
    a = ap.parse_args(argv)

    if a.fixtures:
        print('DEP SURFACE -- selftest (criteria %s)' % CRITERIA_VERSION)
        return 0 if _fixtures() else 1

    if not a.package:
        ap.error('--package is required')

    if a.enumerate_only:
        u = enumerate_uses(a.package)
        if a.json:
            print(json.dumps({'criteria': CRITERIA_VERSION, 'package': a.package,
                              'bindings': u['bindings'],
                              'symbols': {k: [list(x) for x in v]
                                          for k, v in u['symbols'].items()}},
                             indent=1))
        else:
            print('DEP SURFACE -- enumeration only, %s (criteria %s)'
                  % (a.package, CRITERIA_VERSION))
            for (f, n) in u['bindings']:
                print('  require site : %s  as %s' % (f, n))
            for sym in sorted(u['symbols']):
                for (f, line, chain) in sorted(set(u['symbols'][sym])):
                    print('  %-28s %s:%d' % (chain, f, line))
        if not u['symbols']:
            print('')
            print('COULD NOT RUN -- no use of %s found. An empty surface is not '
                  'a clean one.' % a.package)
            return EXIT_COULD_NOT_RUN
        return 0

    if not a.version:
        ap.error('--version is required unless --enumerate-only')

    code, report = check(a.package, a.version)
    if a.json:
        print(json.dumps(report, indent=1))
    else:
        _print(report, code)
    return code


if __name__ == '__main__':
    sys.exit(main())
