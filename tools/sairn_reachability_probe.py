"""sairn_reachability_probe.py -- the SAIRNcash gap class, swept across every app.

THE GAP. A mechanism is DEFINED, CORRECT and COMMENTED AS NECESSARY -- and
nothing calls it on the path a real returning customer takes. SAIRNcash's
reverifyTrial() worked the whole time; initApp() only ran on a Stripe return or
straight after startTrial(), so a returning user with a valid unexpired trial hit
the paywall with no way past. The Aug 18 live verification signed in, reloaded,
and PASSED -- because the path it exercised was one of the two that did call
initApp(). A passing live verification proves the path YOU took works, not that
the path a CUSTOMER takes exists.

HOW TO READ THE OUTPUT, AND ITS KNOWN OVER-REPORTING. This traces reachability
from page-load entry points only (DOMContentLoaded / load / window.onload).
**For a licence-gated app that is the wrong entry point** -- the real one is the
gate/login button -- so `checkTrialGate` flags on six apps and is fine in all
six, reached via gateSubmit / sbApplyLoggedIn / grdApplyLoggedIn. Verified by
hand 2026-08-30.

**The signal that needs no entry-point tracing is CALLERS=0.** A function nothing
references anywhere is dead regardless of how the app is entered. Sort by that
column first; treat "unreachable-from-load" as a prompt to look, not a finding.

This is a PROBE, not a gate. It over-reports by construction and is the fourth
over-reporting checker written on 2026-08-30 -- a checker that cries wolf gets
switched off, so it prints its own caveat rather than a verdict.
"""
import re, sys, glob, os, collections

RESTORE = re.compile(r'^(?:.*)(reverify|restore|resume|rehydrate|recheck|'
                     r'checksession|loadstate|hydrate|refreshsession|'
                     r'validatetrial|checktrial|checklicen|verifylicen|'
                     r'checkauth|restoresession|bootstrapsession)', re.I)

def funcs(s):
    d = {}
    for m in re.finditer(r'function\s+([A-Za-z_$][\w$]*)\s*\(', s):
        d[m.group(1)] = m.start()
    for m in re.finditer(r'(?:window\.|var\s+|let\s+|const\s+)([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?function', s):
        d.setdefault(m.group(1), m.start())
    return d

def body(s, start):
    i = s.find('{', start)
    if i < 0: return ''
    depth, j = 0, i
    while j < len(s) and j < i + 20000:
        if s[j] == '{': depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0: return s[i:j+1]
        j += 1
    return s[i:i+20000]

for path in sorted(glob.glob('*.html')):
    s = open(path, encoding='utf-8', errors='replace').read()
    F = funcs(s)
    if not F: continue
    calls = {n: set(re.findall(r'(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(', body(s, p))) & set(F)
             for n, p in F.items()}
    # entry points: load handlers + inline onload + init-named funcs called at top level
    entry = set()
    for m in re.finditer(r"addEventListener\(\s*['\"](?:DOMContentLoaded|load)['\"]\s*,\s*([A-Za-z_$][\w$]*)", s):
        entry.add(m.group(1))
    for m in re.finditer(r"addEventListener\(\s*['\"](?:DOMContentLoaded|load)['\"]\s*,\s*(?:async\s*)?function[^{]*\{([^}]{0,4000})", s, re.S):
        entry |= set(re.findall(r'(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(', m.group(1))) & set(F)
    for m in re.finditer(r'window\.onload\s*=\s*([A-Za-z_$][\w$]*)', s):
        entry.add(m.group(1))
    entry &= set(F)
    # transitive closure from entries
    seen, stack = set(), list(entry)
    while stack:
        n = stack.pop()
        if n in seen: continue
        seen.add(n)
        stack.extend(calls.get(n, ()) - seen)
    targets = [n for n in F if RESTORE.match(n)]
    if not targets: continue
    unreachable = [n for n in targets if n not in seen]
    callers = {n: len(re.findall(r'(?<![.\w$])'+re.escape(n)+r'\s*\(', s)) - 1 for n in targets}
    flag = 'FLAG' if unreachable else 'ok  '
    print(f"{flag} {path:28} entries={len(entry):2} restore-shaped={len(targets)} "
          f"unreachable-from-load={unreachable if unreachable else 'none'}")
    for n in targets:
        print(f"       {n:26} call-sites={callers[n]:2} reachable-from-load={n in seen}")
