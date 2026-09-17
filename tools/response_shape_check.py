#!/usr/bin/env python
"""response_shape_check.py -- a Response used as if it were the body.

    python tools/response_shape_check.py            # sweep the repo
    python tools/response_shape_check.py --self-check

Exit 0 clean / 1 at least one finding / 2 could not run.

── WHY THIS EXISTS ─────────────────────────────────────────────────────────
`tools/sairn_http.py` returns `Response(status, body)` from both `fetch()` and
`fetch_json()`. Two tools bound that namedtuple to a name and then used the
name AS THE BODY:

  * `tools/cron_liveness_check.py` -- `isinstance(payload, dict)` is ALWAYS
    False for a namedtuple, so the out-of-band cron watchdog reader exited 2
    COULD NOT TELL on every input it would ever see, including a healthy
    platform. It had never once produced any other verdict.
  * `tools/audit_checkpoint_status.py` -- the identical line, with the same
    consequence for the audit-checkpoint status document.

**THE MODULE ALREADY HAD A GUARD AND THE BUG WALKED PAST IT.** `Response`
defines `__contains__` to raise on `'x' in response`, because that spelling was
silently False and cost seven minutes of a live verify in 2026-09-04. The
second tool's check reads

    if not isinstance(payload, dict) or 'ok' not in payload:

and `'ok' not in payload` would have raised that exact TypeError. It never ran:
`not isinstance(...)` was True first and `or` short-circuits. **The defence was
present, correct, and unreachable because of the thing it was defending
against** -- which is why a guard inside the type is not enough and this sweep
exists beside it.

── WHAT IT FLAGS, AND WHY NOT MORE ─────────────────────────────────────────
A name bound to a `fetch()`/`fetch_json()` result, later used in a way that only
makes sense on the BODY:

    isinstance(name, dict)      name.get(...)      name.keys()/.values()/.items()
    name['literal-string']      name.setdefault(...)

**TUPLE UNPACKING IS NOT FLAGGED** -- `status, body = fetch(...)` is the
documented shape and most callers use it. **`.status` and `.body` are not
flagged.** Indexing by an INTEGER is not flagged: `r[1]` is a legitimate tuple
read, and telling it apart from a mistake needs intent this cannot see.

**IT REPORTS, IT DOES NOT REWRITE.** Every finding names a file, a line and the
attribute that gave it away, because the fix differs per call site -- some want
`.body`, some want both halves, and one of the two real instances also needed a
non-200 branch that had never existed.

── WHAT IT CANNOT SEE, STATED RATHER THAN DISCOVERED ───────────────────────
A result passed straight into another function and misused there; a result
stored on an object attribute or in a dict; a dynamically-named call. The
binding has to be a plain local name in the same function, which is what both
real instances were and is the shape worth catching cheaply.
"""
import ast
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

FETCHERS = ('fetch', 'fetch_json')
# Attributes that only exist on the BODY. `.status`/`.body` are the Response's
# own and are the correct use.
BODY_ONLY_ATTRS = ('get', 'keys', 'values', 'items', 'setdefault')
SKIP_DIRS = ('__pycache__', '.git', 'node_modules')


def _is_fetch_call(node):
    """Is this a call to sairn_http's fetch()/fetch_json(), by any spelling?"""
    if not isinstance(node, ast.Call):
        return None
    f = node.func
    if isinstance(f, ast.Name) and f.id in FETCHERS:
        return f.id
    if isinstance(f, ast.Attribute) and f.attr in FETCHERS:
        return f.attr
    return None


class _Scope(ast.NodeVisitor):
    """One function body: which names hold a Response, and how are they used."""

    def __init__(self, path, findings):
        self.path, self.findings = path, findings
        self.bound = {}          # name -> (lineno, which fetcher)

    # ── binding ────────────────────────────────────────────────────────────
    def visit_Assign(self, node):
        which = _is_fetch_call(node.value)
        if which:
            for t in node.targets:
                # A TUPLE TARGET IS THE DOCUMENTED SHAPE and is never a finding.
                if isinstance(t, ast.Name):
                    self.bound[t.id] = (node.lineno, which)
                elif isinstance(t, (ast.Tuple, ast.List)):
                    for el in t.elts:
                        if isinstance(el, ast.Name):
                            self.bound.pop(el.id, None)
        else:
            # Rebinding a tracked name to something else clears it -- otherwise
            # a later, legitimate dict in the same function reads as a finding.
            for t in node.targets:
                if isinstance(t, ast.Name):
                    self.bound.pop(t.id, None)
        self.generic_visit(node)

    # ── misuse ─────────────────────────────────────────────────────────────
    def _flag(self, name, lineno, why):
        if name in self.bound:
            src_line, which = self.bound[name]
            self.findings.append({
                'file': self.path, 'line': lineno, 'name': name,
                'bound_at': src_line, 'fetcher': which, 'why': why,
            })

    def visit_Call(self, node):
        # isinstance(name, dict)
        f = node.func
        if (isinstance(f, ast.Name) and f.id == 'isinstance'
                and node.args and isinstance(node.args[0], ast.Name)):
            second = node.args[1] if len(node.args) > 1 else None
            names = []
            if isinstance(second, ast.Name):
                names = [second.id]
            elif isinstance(second, ast.Tuple):
                names = [e.id for e in second.elts if isinstance(e, ast.Name)]
            if 'dict' in names:
                self._flag(node.args[0].id, node.lineno,
                           'isinstance(%s, dict) is ALWAYS False for a Response'
                           % node.args[0].id)
        # name.get(...) and friends
        if (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                and f.attr in BODY_ONLY_ATTRS):
            self._flag(f.value.id, node.lineno,
                       '%s.%s() is a body call on a Response'
                       % (f.value.id, f.attr))
        self.generic_visit(node)

    def visit_Subscript(self, node):
        if isinstance(node.value, ast.Name):
            key = node.slice
            # INTEGER INDEXING IS A LEGITIMATE TUPLE READ and is left alone.
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                self._flag(node.value.id, node.lineno,
                           "%s[%r] indexes a Response by a string key"
                           % (node.value.id, key.value))
        self.generic_visit(node)


def scan_source(src, path):
    findings = []
    tree = ast.parse(src, filename=path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            sc = _Scope(path, findings)
            for child in node.body:
                sc.visit(child)
    # One function can be visited twice (Module walk plus its own def), so the
    # same finding can be recorded twice. Deduped on identity rather than by
    # walking more cleverly -- the walk is the readable half.
    seen, out = set(), []
    for f in findings:
        k = (f['file'], f['line'], f['name'], f['why'])
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def sweep(roots=('tools', 'tests')):
    out, unreadable = [], []
    for root in roots:
        base = os.path.join(REPO, root)
        if not os.path.isdir(base):
            continue
        for dirpath, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in sorted(files):
                if not fn.endswith('.py'):
                    continue
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, REPO).replace(os.sep, '/')
                try:
                    src = io.open(p, encoding='utf-8', errors='replace').read()
                except Exception as e:                             # noqa: BLE001
                    unreadable.append((rel, str(e)[:80]))
                    continue
                try:
                    out += scan_source(src, rel)
                except SyntaxError as e:
                    unreadable.append((rel, 'SyntaxError: %s' % e))
    return out, unreadable


# ── THE BLIND LOCK, RUN ON EVERY RUN AND NOT ONLY UNDER --self-check ───────
# A checker that has silently stopped classifying must not then report the
# repository clean. Both directions: a fixture it MUST flag and a fixture it
# MUST NOT, because a checker that flags everything is as useless as one that
# flags nothing -- and this one's whole risk is over-reporting the documented
# unpack that most callers use.
FIXTURES = [
    ('MUST FLAG -- the exact cron_liveness shape', True, '''
def f():
    payload = fetch_json(url, method='POST')
    if not isinstance(payload, dict):
        return 2
'''),
    ('MUST FLAG -- .get() on the response', True, '''
def f():
    r = sairn_http.fetch_json(url)
    return r.get('ok')
'''),
    ('MUST FLAG -- string subscript', True, '''
def f():
    r = H.fetch(url)
    return r['error']
'''),
    ('MUST NOT FLAG -- the documented unpack', False, '''
def f():
    status, body = sairn_http.fetch(url)
    return isinstance(body, dict) and body.get('ok')
'''),
    ('MUST NOT FLAG -- .status and .body', False, '''
def f():
    r = sairn_http.fetch_json(url)
    return r.status, r.body.get('ok')
'''),
    ('MUST NOT FLAG -- integer index is a tuple read', False, '''
def f():
    r = sairn_http.fetch(url)
    return r[1]
'''),
    ('MUST NOT FLAG -- a plain dict that never touched fetch', False, '''
def f():
    payload = json.loads(raw)
    return isinstance(payload, dict) and payload.get('ok')
'''),
    ('MUST NOT FLAG -- rebound to something else before use', False, '''
def f():
    r = sairn_http.fetch_json(url)
    r = r.body
    return isinstance(r, dict)
'''),
]


def self_check(verbose=True):
    bad = []
    for label, must_flag, src in FIXTURES:
        got = bool(scan_source(src, '<fixture>'))
        ok = (got == must_flag)
        if verbose:
            print('  %-4s %s' % ('ok' if ok else 'FAIL', label))
        if not ok:
            bad.append(label)
    return bad


def main(argv):
    only_self = '--self-check' in argv
    print('THE BLIND LOCK -- both directions, every run')
    bad = self_check()
    if bad:
        print('\nCOULD NOT RUN: the checker failed its own fixtures (%d). '
              'Not reporting a sweep it cannot be trusted to have made.'
              % len(bad))
        return EXIT_COULD_NOT_RUN
    if only_self:
        print('\nself-check clean.')
        return EXIT_CLEAN

    findings, unreadable = sweep()
    print('')
    if unreadable:
        # PR 1.11: a file that could not be parsed is a third state and is
        # never folded into "clean".
        print('COULD NOT READ %d file(s):' % len(unreadable))
        for rel, why in unreadable:
            print('  %s -- %s' % (rel, why))
        print('')
    if not findings:
        print('CLEAN: no caller binds a fetch()/fetch_json() result and then '
              'uses it as the body.')
        return EXIT_COULD_NOT_RUN if unreadable else EXIT_CLEAN

    print('%d FINDING(S) -- a Response used as if it were the body:' % len(findings))
    for f in findings:
        print('  %s:%d  %s' % (f['file'], f['line'], f['why']))
        print('        bound from %s() at line %d' % (f['fetcher'], f['bound_at']))
    print('')
    print('THE FIX DIFFERS PER SITE and is not applied here: some want '
          '`.body`,\nsome want both halves, and both real instances also needed '
          'a non-200\nbranch that had never existed.')
    return EXIT_FINDING


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
