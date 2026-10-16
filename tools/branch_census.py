"""BRANCH CENSUS -- the span is BOUNDED MECHANICALLY and a caller value is
followed THROUGH ITS ASSIGNMENTS, so neither the count nor the CALLER figure is
a lower bound nobody can see.

WHY THIS FILE EXISTS, in three measured failures of its own predecessors:

  b23 (branch_census_b23.py) read `method:` and the URL out of a window that ran
      from the fetch assignment until braces balanced OR 14 lines, whichever
      came first. Its CALLER test was a REGEX OVER THAT BLOB, so a caller value
      arriving through an earlier variable was invisible and 33 GETs were
      reported SERVER-ONLY by the `else` branch of a three-way. CALLER was a
      LOWER BOUND and the report said so, which is better than not saying it and
      is still a number nobody can use.
  b24 (pick_branches_b24.py) used a FIXED 14-line window for `method:` with no
      brace check at all. Three pre-write GETs are followed inside 14 lines by
      the real upsert, so it reported 25 write-guarded branches where there are
      22, and the b24 handoff attributed the difference to the file having moved.
  b25 proved the file had NOT moved -- identical blob sha across 36 commits --
      and fixed the span by bounding it at the next `await fetch(`. That fix
      lived in a one-off script with no fixtures, so nothing stopped the next
      census from re-introducing either bug.

THE THREE RULES THIS FILE LOCKS, each with fixtures in BOTH directions:

  R1 SPAN-BOUNDED-AT-THE-NEXT-FETCH. The window for reading a fetch's own
     options ends at the next `await fetch(`, never at a line count.
  R2 GUARD-TO-FETCH BINDING IS NEAREST-BACKWARD AND STOPS AT A FETCH OF ANOTHER
     VARIABLE. A guard is attached to the fetch that assigned ITS OWN variable.
  R3 A CALLER VALUE IS FOLLOWED THROUGH ASSIGNMENTS, transitively, and an
     identifier whose origin CANNOT BE RESOLVED IS ITS OWN THIRD STATE. It is
     never folded into SERVER-ONLY, which is what made CALLER a lower bound.

CRITERIA ARE LOCKED BEFORE THE REAL FILE IS READ: --selftest runs the fixtures
and a non-zero exit from it is a refusal to report a census at all.

  python tools/branch_census.py --selftest     fixtures only, both directions
  python tools/branch_census.py --ablate       per-RULE, per-ARM contribution
  python tools/branch_census.py                the census (selftest first)

-- INSTALLED UNDER tools/ ON 2026-10-16 (cc b16), FROM fourth b26 ----------
Routed with its full source inline in
`docs/2026-10-15-fourth-b26-branch-census-routed-to-cc.md`, and that is the
whole reason this file exists at this path. The three versions above each lived
in a session scratchpad; each was rebuilt from scratch by the next batch; each
rebuild re-introduced one of the bugs the previous one had fixed. A routing note
pointing at a scratchpad path is a fourth rebuild waiting to happen, so fourth
carried the source into the routing document rather than the path.

TWO CHANGES FROM THE ROUTED SOURCE, BOTH NAMED SO A DIFF AGAINST THE ROUTING
DOCUMENT IS NOT MISTAKEN FOR DRIFT:

  1. `REPO` is DERIVED from this file's own location rather than the absolute
     `C:\\Users\\marsh\\Documents\\SAIRN-fourth` the routed copy carried. The
     routing note asks for exactly this. A tool under `tools/` that hardcodes
     one clone's path measures that clone from every clone, which is the
     `presync_tier_a_dryrun.py:34` defect cc routed to the auditors in b15.
  2. `SRC` is now resolved at CALL time rather than at import time, so
     `--selftest` and `--ablate` do not depend on the target existing. The
     fixtures are the entry condition; making them unreachable when the target
     is missing would invert that.

NOTHING ELSE IS CHANGED. CRITERIA_VERSION is fourth's, unbumped on purpose:
this install re-homes the program and does not re-specify it, and a version
bumped by a move would make the next real criteria change invisible.

THE KNOWN LIMITATION, carried here rather than left to be rediscovered:
`origin()` is INTRA-PROCEDURAL. An identifier that is a FUNCTION PARAMETER
resolves to UNRESOLVED -- which is correct, and is the point of the third state
-- but it is not CALLER, and some of those are. fourth's worked example,
resolved by hand in b26:

    api/sd-data.js:10556  const rfJobGate = async (lh, hdrs, jobId, session, response) => {
                          const jr = await fetch(rest('rf_jobs?...&job_id=eq.' + enc(jobId) ...
    api/sd-data.js:10612  const gate = await rfJobGate(licHash, headers, payload.job_id, session, res);
    api/sd-data.js:10746  const gate = await rfJobGate(licHash, headers, payload.job_id, session, res);

So `:10556` IS CALLER once the call sites are followed. The residual is an
ENUMERATED set of lines rather than a hidden default inside a 33. THE
INTER-PROCEDURAL EXTENSION IS NOT DONE HERE AND IS NOT CC'S: fourth's b27 claim
names `census inter-procedural` as its own work, so doing it here would be two
sessions writing one extension. When it lands it needs a fixture in BOTH
directions for the parameter case, or it is the same prose problem again.
"""
import io
import os
import re
import sys

CRITERIA_VERSION = '2026-10-15.b26.1'
# DERIVED, not hardcoded -- see change (1) in the module docstring.
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BOTH = re.compile(r'(\w+)\.status\s*===\s*404\s*\|\|\s*\1\.status\s*===\s*400')
METHOD = re.compile(r"method:\s*'(POST|PATCH|DELETE|PUT)'")
FETCH_ANY = re.compile(r'await\s+fetch\s*\(')
IDENT = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')


def src_path():
    """Resolved at CALL time -- see change (2) in the module docstring."""
    return os.path.join(REPO, 'api', 'sd-data.js')


# Identifiers that are the SERVER's own by construction. Anything derived from
# these is server-only however many hops away it is.
SERVER_ROOTS = frozenset([
    'licHash', 'lh', 'APP', 'app', 'nowISO', 'enc', 'rest', 'headers',
    'String', 'Number', 'JSON', 'Math', 'Object', 'Array', 'Date', 'Boolean',
])
CALLER_ROOTS = frozenset(['payload', 'body', 'req', 'q', 'query'])
SESSION_ROOTS = frozenset(['session', 'lawSess', 'sess', 'sfSess', 'senSess',
                           'alfSess', 'svSess', 'legSess'])
# Words that appear inside a URL string but are not identifiers to trace.
NOISE = frozenset(['select', 'eq', 'order', 'limit', 'and', 'or', 'not',
                   'on_conflict', 'desc', 'asc', 'is', 'in', 'true', 'false',
                   'null', 'headers', 'method', 'Prefer', 'body'])


# -- RULE TOGGLES, so --ablate can remove ONE and measure what it alone buys --
class Rules(object):
    def __init__(self, r1=True, r2=True, r3=True):
        self.r1 = r1   # span bounded at the next fetch
        self.r2 = r2   # guard-to-fetch binding stops at another variable's fetch
        self.r3 = r3   # follow a caller value through assignments


def find_assignment(lines, idx, var, rules):
    """Nearest backward `const/let/var <var> = await fetch(`.

    R2: the walk stops if it meets `await fetch(` assigned to a DIFFERENT
    variable first -- that fetch's guard is not this one's.
    """
    assign = re.compile(r'\b(?:const|let|var)\s+' + re.escape(var)
                        + r'\s*=\s*await\s+fetch\s*\(')
    other = re.compile(r'\b(?:const|let|var)\s+(?!' + re.escape(var)
                       + r'\b)[A-Za-z_$][\w$]*\s*=\s*await\s+fetch\s*\(')
    for j in range(idx, max(0, idx - 60), -1):
        if assign.search(lines[j]):
            return j
        if rules.r2 and other.search(lines[j]):
            return None
    return None


def span(lines, start, guard_idx, rules):
    """The lines belonging to the fetch assigned at `start`.

    R1: ends at the next `await fetch(` or at the guard, whichever is first.
    Without R1 it is a flat 14-line window, which is the b24 bug.
    """
    if not rules.r1:
        return lines[start:min(len(lines), start + 14)]
    end = guard_idx
    for j in range(start + 1, guard_idx):
        if FETCH_ANY.search(lines[j]):
            end = j
            break
    return lines[start:max(end, start + 1)]


def url_idents(blob):
    """Identifiers interpolated into the URL expression of a rest(...) call."""
    m = re.search(r'rest\s*\(', blob)
    if not m:
        return []
    i = m.end()
    depth = 1
    out = []
    while i < len(blob) and depth > 0:
        c = blob[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        i += 1
    expr = blob[m.end():i - 1]
    # drop string literals -- a URL's own text is not an identifier
    expr = re.sub(r"'[^']*'", " ", expr)
    expr = re.sub(r'"[^"]*"', " ", expr)
    for name in IDENT.findall(expr):
        if name in NOISE or name in ('enc', 'String', 'encodeURIComponent'):
            continue
        out.append(name)
    return out


def origin(lines, name, from_idx, rules, hops=0, seen=None):
    """CALLER / SESSION / SERVER / UNRESOLVED for one identifier.

    R3 is the transitive walk. With R3 off this only answers from the name
    itself, which is the b23 behaviour and is what makes CALLER a lower bound.
    """
    seen = seen or set()
    if name in seen or hops > 6:
        return 'UNRESOLVED'
    seen.add(name)
    if name in CALLER_ROOTS:
        return 'CALLER'
    if name in SESSION_ROOTS:
        return 'SESSION'
    if name in SERVER_ROOTS:
        return 'SERVER'
    if not rules.r3:
        return 'SERVER'          # the b23 `else` branch, kept so --ablate can measure it
    assign = re.compile(r'\b(?:const|let|var)\s+' + re.escape(name)
                        + r'\s*=\s*(.+)$')
    for j in range(from_idx, max(0, from_idx - 400), -1):
        mm = assign.search(lines[j])
        if not mm:
            continue
        rhs = mm.group(1)
        rhs = re.sub(r"'[^']*'", " ", rhs)
        rhs = re.sub(r'"[^"]*"', " ", rhs)
        names = [n for n in IDENT.findall(rhs) if n not in NOISE]
        if not names:
            return 'SERVER'      # assigned from a literal
        verdicts = [origin(lines, n, j, rules, hops + 1, seen) for n in names]
        for want in ('CALLER', 'SESSION'):
            if want in verdicts:
                return want
        if all(v == 'SERVER' for v in verdicts):
            return 'SERVER'
        return 'UNRESOLVED'
    # A function PARAMETER or a destructure this walk does not model.
    return 'UNRESOLVED'


def census(text, rules=None):
    rules = rules or Rules()
    lines = text.split('\n')
    rows = []
    for i, l in enumerate(lines):
        if l.lstrip().startswith(('//', '*')):
            continue
        m = BOTH.search(l)
        if not m:
            continue
        var = m.group(1)
        win5 = ' '.join(lines[i:i + 5])
        if re.search(r'\bnotProvisioned\s*\(', win5):
            shape = 'A-helper'
        elif 'NOT_PROVISIONED' in win5:
            shape = 'B-inline-503'
        elif 'provisioned: false' in win5:
            shape = 'C-200-empty'
        else:
            shape = 'other'
        start = find_assignment(lines, i, var, rules)
        if start is None:
            rows.append({'line': i + 1, 'var': var, 'shape': shape,
                         'method': None, 'influence': None,
                         'state': 'UNCLASSIFIED'})
            continue
        blob = ' '.join(span(lines, start, i, rules))
        mm = METHOD.search(blob)
        method = mm.group(1) if mm else 'GET'
        names = url_idents(blob)
        verdicts = [origin(lines, n, start, rules) for n in names]
        if 'CALLER' in verdicts:
            influence = 'CALLER'
        elif 'SESSION' in verdicts:
            influence = 'SESSION'
        elif 'UNRESOLVED' in verdicts:
            influence = 'UNRESOLVED'
        else:
            influence = 'SERVER-ONLY'
        rows.append({'line': i + 1, 'var': var, 'shape': shape,
                     'method': method, 'influence': influence,
                     'state': 'OK', 'fetch_line': start + 1,
                     'idents': names})
    return rows


# ===================== FIXTURES, BOTH DIRECTIONS =============================
# Each fixture is (name, source, expected). Locked BEFORE the real file is read.
F = []

# THE REAL SHAPE at api/sd-data.js:5061-5072, which b24 typed as a POST: the
# pre-write GET, its own guard immediately after it, and the real upsert
# ELEVEN LINES LATER -- inside a flat 14-line window and outside a window
# bounded at the next fetch. The fixture is the shipped layout, not a
# convenient one: an earlier draft put the guard AFTER the upsert, which is a
# shape this file does not contain, and it failed for that reason.
F.append(('R1 a pre-write GET with the upsert 11 lines later is a GET', """
      const existingPhoto = await fetch(rest('grd_photos?license_hash=eq.' + enc(licHash)), { headers });
      if (existingPhoto.status === 404 || existingPhoto.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED' } });
        return;
      }
      const exRows = await existingPhoto.json();
      if (Array.isArray(exRows) && exRows.length) {
        res.status(409).json({ error: { code: 'ALREADY' } });
        return;
      }
      const row = { license_hash: licHash, data: storedBlob(payload, []) };
      const w = await fetch(rest('grd_photos?on_conflict=license_hash'), {
        method: 'POST',
        headers: headers
      });
""", {'method': 'GET', 'influence': 'SERVER-ONLY'}))

F.append(('R1 the OPPOSITE: a real write branch is still a POST', """
      const w = await fetch(rest('alf_op_audits?on_conflict=license_hash'), {
        method: 'POST',
        headers: headers
      });
      if (w.status === 404 || w.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED' } });
      }
""", {'method': 'POST', 'influence': 'SERVER-ONLY'}))

F.append(('R2 a guard binds to ITS OWN variable, not the nearest fetch', """
      const a = await fetch(rest('t_a?license_hash=eq.' + enc(licHash)), { headers });
      const b = await fetch(rest('t_b?on_conflict=x'), { method: 'POST', headers: headers });
      if (a.status === 404 || a.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED' } });
      }
""", {'method': 'UNCLASSIFIED'}))

F.append(('R3 a caller value arriving DIRECTLY is CALLER', """
      const r = await fetch(rest('t?license_hash=eq.' + enc(licHash) + '&id=eq.' + enc(payload.id)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
      }
""", {'method': 'GET', 'influence': 'CALLER'}))

F.append(('R3 THE ONE b23 MISSED: a caller value through a VARIABLE is CALLER', """
      const jobId = payload.job_id;
      const r = await fetch(rest('t?license_hash=eq.' + enc(licHash) + '&job_id=eq.' + enc(jobId)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
      }
""", {'method': 'GET', 'influence': 'CALLER'}))

F.append(('R3 TWO hops still reaches CALLER', """
      const raw = payload.job_id;
      const jobId = String(raw);
      const r = await fetch(rest('t?job_id=eq.' + enc(jobId)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
      }
""", {'method': 'GET', 'influence': 'CALLER'}))

F.append(('R3 THE OPPOSITE: a server value through a variable stays SERVER-ONLY', """
      const own = enc(licHash);
      const r = await fetch(rest('t?license_hash=eq.' + own), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
      }
""", {'method': 'GET', 'influence': 'SERVER-ONLY'}))

F.append(('R3 a SESSION value is SESSION, not CALLER and not SERVER', """
      const r = await fetch(rest('t?emp=eq.' + enc(session.employee_id)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
      }
""", {'method': 'GET', 'influence': 'SESSION'}))

F.append(('R3 THE THIRD STATE: an unresolvable identifier is UNRESOLVED, '
          'never SERVER-ONLY', """
      const r = await fetch(rest('t?x=eq.' + enc(mysteryFromAParameter)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
      }
""", {'method': 'GET', 'influence': 'UNRESOLVED'}))

F.append(('a commented-out guard is not a branch', """
      // if (r.status === 404 || r.status === 400) {
""", {'none': True}))


def selftest(verbose=True):
    bad = 0
    if verbose:
        print('FIXTURES -- criteria %s' % CRITERIA_VERSION)
    for name, src, want in F:
        rows = census(src)
        if want.get('none'):
            ok = (len(rows) == 0)
            got = '%d row(s)' % len(rows)
        elif not rows:
            ok, got = False, 'NO ROW FOUND'
        elif want.get('method') == 'UNCLASSIFIED':
            ok = rows[0]['state'] == 'UNCLASSIFIED'
            got = rows[0]['state']
        else:
            r = rows[0]
            ok = (r['state'] == 'OK' and r['method'] == want['method']
                  and r['influence'] == want['influence'])
            got = '%s/%s/%s' % (r['state'], r['method'], r['influence'])
        if not ok:
            bad += 1
        if verbose:
            print('  %-4s %-62s got %s' % ('ok' if ok else 'FAIL', name[:62], got))
    if verbose:
        print('  %d/%d fixtures classify correctly' % (len(F) - bad, len(F)))
    return bad


def ablate():
    """Per RULE, per ARM. Not per exit code -- an exit code hides which arm
    each rule was actually buying."""
    print('ABLATION -- one rule removed at a time, measured PER FIXTURE')
    print('criteria %s' % CRITERIA_VERSION)
    print('')
    base = {}
    for name, src, want in F:
        base[name] = census(src)
    for label, rules in (('R1 span-bounded-at-next-fetch', Rules(r1=False)),
                         ('R2 guard-binds-to-own-variable', Rules(r2=False)),
                         ('R3 follow-caller-through-assignments', Rules(r3=False))):
        broke = []
        for name, src, want in F:
            rows = census(src, rules)
            a, b = base[name], rows
            same = (len(a) == len(b)
                    and all(x.get('method') == y.get('method')
                            and x.get('influence') == y.get('influence')
                            and x.get('state') == y.get('state')
                            for x, y in zip(a, b)))
            if not same:
                got = (b[0]['state'] + '/' + str(b[0].get('method')) + '/'
                       + str(b[0].get('influence'))) if b else 'NO ROW'
                broke.append((name, got))
        print('  WITHOUT %-38s %d fixture(s) change' % (label, len(broke)))
        for n, g in broke:
            print('      %-60s -> %s' % (n[:60], g))
        if not broke:
            print('      NONE -- THIS RULE IS NOT LOAD-BEARING ON ANY FIXTURE,')
            print('      which is a finding about the fixtures, not a pass.')
    print('')


def main(argv):
    if '--selftest' in argv:
        return 1 if selftest() else 0
    if '--ablate' in argv:
        bad = selftest()
        print('')
        if bad:
            print('COULD NOT RUN: the fixtures failed, so an ablation over them')
            print('would measure a broken classifier. Nothing was ablated.')
            return 2
        ablate()
        return 0
    bad = selftest()
    print('')
    if bad:
        print('COULD NOT RUN: %d fixture(s) failed, so NO CENSUS IS REPORTED.' % bad)
        print('A classifier that cannot pass its own locked criteria produces a')
        print('number nobody can use. This is exit 2, not a census with a caveat.')
        return 2
    src = src_path()
    if not os.path.isfile(src):
        print('COULD NOT RUN: %s does not exist. Nothing was measured.' % src)
        return 2
    text = io.open(src, encoding='utf-8').read()
    lines = text.split('\n')
    rows = census(text)
    from collections import Counter
    print('SOURCE api/sd-data.js, %d lines (split on newline)' % len(lines))
    print('GUARDS MATCHING (\\w+).status === 404 || \\1.status === 400 : %d'
          % len(rows))
    print('')
    for k, v in sorted(Counter(r['shape'] for r in rows).items()):
        print('  shape %-14s %d' % (k, v))
    print('')
    for shape in ('B-inline-503', 'C-200-empty', 'A-helper', 'other'):
        sub = [r for r in rows if r['shape'] == shape]
        if not sub:
            continue
        wr = [r for r in sub if r['state'] == 'OK' and r['method'] != 'GET']
        gd = [r for r in sub if r['state'] == 'OK' and r['method'] == 'GET']
        unk = [r for r in sub if r['state'] != 'OK']
        print('%s -- %d branch(es)' % (shape, len(sub)))
        print('  WRITE-guarded (POST/PATCH/DELETE) -> can receive a 23xxx : %d'
              % len(wr))
        if wr:
            print('     lines: %s' % ', '.join(':%d' % r['line'] for r in wr))
        print('  GET-guarded                                             : %d'
              % len(gd))
        for kind in ('CALLER', 'SESSION', 'UNRESOLVED', 'SERVER-ONLY'):
            k = [r for r in gd if r['influence'] == kind]
            print('     URL influence %-12s : %d' % (kind, len(k)))
            if k and kind in ('CALLER', 'UNRESOLVED'):
                print('       lines: %s' % ', '.join(':%d' % r['line'] for r in k))
        print('  UNCLASSIFIED (no fetch bound to this guard)              : %d'
              % len(unk))
        if unk:
            print('     lines: %s' % ', '.join(':%d' % r['line'] for r in unk))
        print('')
    print('UNRESOLVED IS NOT SERVER-ONLY, and that is the whole point of R3:')
    print('an identifier this walk cannot trace is reported as its own state')
    print('rather than defaulting into "the caller cannot reach it", which is')
    print('what made the CALLER figure a lower bound in b23.')
    print('')
    print('INTRA-PROCEDURAL. A function PARAMETER resolves to UNRESOLVED, which')
    print('is correct and is not CALLER -- and some of those ARE caller-reached')
    print('once the call sites are followed. fourth b26 resolved one by hand:')
    print('api/sd-data.js:10556 is CALLER via rfJobGate() at :10612 and :10746.')
    print('The inter-procedural walk is fourth b27 work, not installed here.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
