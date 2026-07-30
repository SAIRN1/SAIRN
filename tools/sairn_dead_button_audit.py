#!/usr/bin/env python3
"""
sairn_dead_button_audit.py -- non-functional-button audit for SAIRN apps.

Usage:  python3 sairn_dead_button_audit.py stonedesk.html [sairnbiz.html ...]

Bakes in the two Session 77 corrections plus one from Session 78:
  1. Comments are stripped before ANY counting. A `function foo()` written
     inside an explanatory comment is not a definition.
  2. A toast-only function body is NOT a finding until its callers are
     enumerated. Zero callers -> orphan (delete). Callers -> live button
     (wire up or relabel). Opposite fixes, so never guess.
  3. Section D is scope-aware, not name-based. Two same-named definitions
     only count as a real collision (D1) if they sit at the same depth
     inside the same enclosing function/IIFE -- tracked via a brace-depth
     scope stack, the same push/pop pattern already used successfully by
     tools/duplicate_global_check.py elsewhere in this repo. Same name in
     different scopes is D2, informational only. `window.NAME = IDENT;`
     (a bare-identifier alias/re-export, e.g. the idiomatic
     `window.foo = foo;` pattern used throughout this codebase) is not
     counted as a second definition at all -- only `window.NAME = function
     ...`/`=> ...` (an actual new function literal) is.
"""
import re
import sys
import collections

TOAST = r'(?:showToast|toast|showMsg|notify|alert)'
HANDLER = re.compile(r'\bon(?:click|change|submit|input|dblclick|keyup)\s*=\s*(["\'])(.*?)\1',
                     re.S | re.I)
DOM_BUILTINS = {
    'getElementById', 'querySelector', 'querySelectorAll', 'click', 'remove',
    'scrollIntoView', 'focus', 'blur', 'preventDefault', 'stopPropagation',
    'parseInt', 'parseFloat', 'String', 'Number', 'Boolean', 'Array', 'Object',
    'JSON', 'Math', 'Date', 'confirm', 'prompt', 'alert', 'setTimeout',
    'setInterval', 'encodeURIComponent', 'decodeURIComponent', 'isNaN',
    'fetch', 'print', 'open', 'close', 'reload', 'toLocaleString', 'toFixed',
    'if', 'for', 'while', 'switch', 'return', 'typeof', 'new', 'function',
    'catch', 'this',
}


def blank(s):
    """Replace with spaces, preserving newlines so line numbers stay true."""
    return re.sub(r'[^\n]', ' ', s)


def strip_comments(src):
    r"""Blank out //, /* */ and <!-- --> comments with a real state machine.

    A naive /\*.*?\*/ regex is UNSAFE here: a /* inside a string, a URL or a
    regex literal blanks thousands of lines of real code and every function
    definition in them then reads as 'never defined'. This is what produced
    58 phantom dead buttons on the first run of this script.
    """
    out = list(src)
    i, n = 0, len(src)
    prev = ''            # last significant char, for regex-vs-divide
    REGEX_OK = set('(,=:[!&|?{};+-*%~^') | {''}

    def kill(a, b):
        for k in range(a, b):
            if out[k] != '\n':
                out[k] = ' '

    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        # HTML comment
        if src.startswith('<!--', i):
            j = src.find('-->', i)
            j = n if j == -1 else j + 3
            kill(i, j); i = j; continue
        # block comment
        if c == '/' and nxt == '*':
            j = src.find('*/', i + 2)
            j = n if j == -1 else j + 2
            kill(i, j); i = j; continue
        # line comment
        if c == '/' and nxt == '/':
            j = src.find('\n', i)
            j = n if j == -1 else j
            kill(i, j); i = j; continue
        # string / template literal -- skip over, never strip inside
        if c in '"\'`':
            q = c; j = i + 1
            while j < n:
                if src[j] == '\\':
                    j += 2; continue
                if src[j] == q:
                    j += 1; break
                if q != '`' and src[j] == '\n':
                    break
                j += 1
            i = j; prev = q; continue
        # regex literal -- skip over, so /*/ and // inside it are safe
        if c == '/' and prev in REGEX_OK:
            j = i + 1; ok = False
            while j < n and src[j] != '\n':
                if src[j] == '\\':
                    j += 2; continue
                if src[j] == '[':
                    while j < n and src[j] not in ']\n':
                        j += 2 if src[j] == '\\' else 1
                if src[j] == '/':
                    ok = True; j += 1; break
                j += 1
            if ok:
                i = j; prev = '/'; continue
        if not c.isspace():
            prev = c
        i += 1
    return ''.join(out)


def mask_scripts(src):
    """Blank out <script> bodies so HTML-side scans don't see JS."""
    out = list(src)
    for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', src, re.S | re.I):
        for i in range(m.start(1), m.end(1)):
            if out[i] != '\n':
                out[i] = ' '
    return ''.join(out)


FUNC_DECL_RE = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(')
FUNC_ANON_RE = re.compile(r'function\s*\(')
VAR_FUNC_RE = re.compile(
    r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?'
    r'(?:function\b|\([^()]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)')
# Session 78 correction: the original `\(` alternative matched ANY
# assignment starting with '(' -- including plain parenthesized
# expressions like `var _v = (window.sd_jobs && ...)`, not just arrow
# functions. Now requires an actual `=>` after the (non-nested)
# parenthesized param list, or a single bare-identifier arrow param.
WINDOW_ASSIGN_RE = re.compile(r'window\.([A-Za-z_$][\w$]*)\s*=\s*')
FUNC_LITERAL_RHS_RE = re.compile(r'(?:async\s*)?function\b|\([^()]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>')


def find_scoped_definitions(src):
    """Single pass over comment-stripped src. Tracks brace depth and a
    scope stack the same way this repo's tools/duplicate_global_check.py
    already does (push a pending scope marker when a function signature is
    seen, resolve it on the next '{', pop on the matching '}') -- reused
    here rather than reinvented, since that approach already works on this
    exact codebase.

    Returns: dict name -> list of (scope_id, line). scope_id 0 is
    top-level/global; every function/IIFE body gets its own id, valid for
    definitions written directly inside it (not further nested).

    `window.NAME = IDENT;` (a bare identifier on the right, e.g. the
    idiomatic `window.foo = foo;` export/alias pattern used throughout
    this codebase) is deliberately NOT counted as a definition site -- it
    re-exports an existing definition under the same name, it doesn't
    create a second one. Only `window.NAME = function...`/`=> ...`
    (a real function literal on the right) counts. Without this, nearly
    every exported function in the file would falsely show as
    "duplicated" by its own export line.
    """
    n = len(src)
    i = 0
    depth = 0
    scope_stack = [[0, None]]   # [scope_id, pending_open_depth_or_None]... see below
    # Simpler model: stack of active scope ids with the depth at which
    # each was opened (the depth value that exists WHILE inside it).
    active = [0]                # active[-1] = current innermost scope id
    entry_depth = {0: -1}       # scope_id -> depth value just before it opened
    pending_scope_id = None     # a scope id waiting for its opening '{'
    next_id = 1
    defs = collections.defaultdict(list)

    def cur_line(pos):
        return src.count('\n', 0, pos) + 1

    while i < n:
        c = src[i]
        if c == '\n':
            i += 1
            continue

        if pending_scope_id is None:
            m = FUNC_DECL_RE.match(src, i)
            if m:
                defs[m.group(1)].append((active[-1], cur_line(m.start())))
                pending_scope_id = next_id
                next_id += 1
                i = m.end()
                continue
            m = VAR_FUNC_RE.match(src, i)
            if m:
                defs[m.group(1)].append((active[-1], cur_line(m.start())))
                # only var/let/const = function(...) opens a new scope here;
                # `= (` (arrow-with-parenthesized-params, e.g. `(x) => {`)
                # also matched by VAR_FUNC_RE's trailing \( alt -- the
                # scope for that gets picked up by the generic arrow check
                # below when its '{' is reached, so only pre-arm a pending
                # scope for the `function` spelling here.
                if src[m.end() - 1] not in '(':
                    pending_scope_id = next_id
                    next_id += 1
                i = m.end()
                continue
            m = WINDOW_ASSIGN_RE.match(src, i)
            if m:
                rest = src[m.end():m.end() + 60].lstrip()
                if FUNC_LITERAL_RHS_RE.match(rest):
                    defs[m.group(1)].append((active[-1], cur_line(m.start())))
                    if re.match(r'(?:async\s*)?function\b', rest):
                        pending_scope_id = next_id
                        next_id += 1
                # else: bare-identifier alias (window.foo = foo;) or a
                # non-function RHS (string/number/object literal) -- not a
                # new definition, skip.
                i = m.end()
                continue
            m = FUNC_ANON_RE.match(src, i)
            if m:
                # anonymous function expression / IIFE not already caught
                # above (e.g. `(function(){...})()`, callback args)
                pending_scope_id = next_id
                next_id += 1
                i = m.end()
                continue

        if c == '{':
            depth += 1
            if pending_scope_id is not None:
                active.append(pending_scope_id)
                entry_depth[pending_scope_id] = depth - 1
                pending_scope_id = None
            i += 1
            continue
        if c == '}':
            if len(active) > 1 and entry_depth.get(active[-1]) == depth - 1:
                active.pop()
            depth -= 1
            i += 1
            continue
        # arrow-function body opening: `... ) => {` or `x => {`
        if c == '=' and src[i:i + 2] == '=>':
            j = i + 2
            while j < n and src[j] in ' \t\r\n':
                j += 1
            if j < n and src[j] == '{':
                pending_scope_id = next_id
                next_id += 1
            i += 2
            continue
        i += 1
    return defs


def audit(path):
    with open(path, encoding='utf-8', errors='replace') as fh:
        raw = fh.read()
    src = strip_comments(raw)          # <-- correction 1
    html = mask_scripts(src)

    def ln(pos):
        return src.count('\n', 0, pos) + 1

    # ---- definitions (comment-free) ----
    defined = collections.defaultdict(list)
    for m in re.finditer(r'function\s+([A-Za-z_$][\w$]*)\s*\(', src):
        defined[m.group(1)].append(ln(m.start()))
    for m in re.finditer(
            r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\()', src):
        defined[m.group(1)].append(ln(m.start()))
    for m in re.finditer(r'window\.([A-Za-z_$][\w$]*)\s*=', src):
        defined[m.group(1)].append(ln(m.start()))

    # ---- every call site anywhere (handlers + JS body) ----
    calls = collections.defaultdict(list)
    for m in re.finditer(r'\b([A-Za-z_$][\w$]*)\s*\(', src):
        calls[m.group(1)].append(ln(m.start()))
    handler_calls = collections.defaultdict(list)
    for m in HANDLER.finditer(html):
        for c in re.finditer(r'\b([A-Za-z_$][\w$]*)\s*\(', m.group(2)):
            handler_calls[c.group(1)].append(ln(m.start()))

    findings = collections.OrderedDict()

    # A. handler target with no definition -> hard dead button
    findings['A. DEAD BUTTON -- handler target never defined'] = [
        f'{n}()  x{len(v)}  handler line(s) {v[:8]}'
        for n, v in sorted(handler_calls.items())
        if n not in defined and n not in DOM_BUILTINS
    ]

    # B. inline handler whose only action is a toast
    findings['B. DEAD BUTTON -- inline handler is toast-only'] = [
        f'L{ln(m.start())}: {m.group(2).strip()[:120]}'
        for m in HANDLER.finditer(html)
        if re.fullmatch(TOAST + r'\s*\(.*\)', m.group(2).strip().rstrip(';').strip(), re.S | re.I)
    ]

    # C. toast-only function bodies, SPLIT by caller count  <-- correction 2
    live, orphan = [], []
    for m in re.finditer(r'function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{(.*?)\}', src, re.S):
        name, body = m.group(1), m.group(2).strip()
        if len(body) > 220 or not body:
            continue
        stmts = [s.strip() for s in body.split(';') if s.strip()]
        if not stmts or not any(re.match(TOAST + r'\s*\(', s, re.I) for s in stmts):
            continue
        if not all(re.match(TOAST + r'\s*\(', s, re.I) or re.match(r'return\b', s) for s in stmts):
            continue
        sites = [p for p in calls.get(name, []) if p not in defined.get(name, [])]
        row = f'L{ln(m.start())}: {name}()  callers={len(sites)} {sites[:6]}'
        (live if sites else orphan).append(row)
    findings['C1. LIVE toast-only function (wire up or relabel)'] = live
    findings['C2. ORPHAN toast-only function, zero callers (delete)'] = orphan

    # D. duplicate definitions, scope-aware (correction 3, Session 78):
    # only a REAL collision if both definitions sit at the same depth
    # inside the same enclosing function/IIFE. Two save() in two
    # different closures are not a collision -- no hardcoded name
    # blocklist needed once scope is actually tracked.
    scoped_defs = find_scoped_definitions(src)
    d1, d2 = [], []
    for name, sites in sorted(scoped_defs.items()):
        by_scope = collections.defaultdict(list)
        for scope_id, line in sites:
            by_scope[scope_id].append(line)
        same_scope_hits = {sid: lines for sid, lines in by_scope.items() if len(lines) > 1}
        if same_scope_hits:
            for sid, lines in same_scope_hits.items():
                d1.append(f'{name}  x{len(lines)} in the SAME scope  lines {lines}')
        elif len(by_scope) > 1:
            d2.append(name)
    findings['D1. DUPLICATE, SAME scope (later silently wins -- real, fix)'] = d1
    findings['D2. same name, DIFFERENT scopes (informational, count only)'] = \
        [f'{len(d2)} names reused across unrelated scopes (not listed -- not a collision)'] if d2 else []

    # E. placeholder copy, excluding input placeholder= and CSS class names
    place = []
    for pat in (r'coming next build', r'coming soon', r'not yet implemented',
                r'future build', r'future release', r'under construction',
                r'work in progress', r'\bTODO\b', r'\bFIXME\b'):
        for m in re.finditer(pat, src, re.I):
            place.append(f'L{ln(m.start())}: {pat}')
    # Session 2 correction: the bare `placeholder` word scan that used to
    # run here was 0-for-7 across StoneDesk (CSS ::placeholder selectors)
    # and SAIRNvet (honest prose + a correctly-named placeholderId var) --
    # never found a real finding. Cut. The phrase list above stays as-is,
    # including `work in progress`, despite SAIRNbuild's one standing
    # false positive (construction-domain term) -- it's 6 true / 1 false
    # overall and earns its place.
    findings['E. PLACEHOLDER copy'] = place

    print('=' * 72)
    print(f'{path}   {len(raw):,} bytes')
    print('=' * 72)
    total = 0
    for head, rows in findings.items():
        print(f'\n{head}  -> {len(rows)}')
        total += len(rows)
        for r in rows[:40]:
            print(f'   {r}')
        if len(rows) > 40:
            print(f'   ... {len(rows) - 40} more')
    print(f'\nTOTAL FLAGGED: {total}')
    print('Reminder: A and B are fixes. C1 vs C2 are OPPOSITE fixes -- read the '
          'caller list, do not guess. D and E need a human read before action.\n')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        audit(p)
