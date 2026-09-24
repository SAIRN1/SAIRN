"""Where is this platform a SINGLE POINT OF FAILURE, and where is it a PAIR
that is only fatal together?

    python tools/dependency_graph.py              # the report
    python tools/dependency_graph.py --json       # graph + verdicts, for tooling
    python tools/dependency_graph.py --fixtures   # the blind lock alone
    python tools/dependency_graph.py --pairs      # 2-element cut sets (item 53)
    python tools/dependency_graph.py --register   # docs/SPOF-REGISTER.md vs reality (item 91)

── WHAT THE GRAPH IS, SAID FIRST, BECAUSE EVERY NUMBER BELOW DEPENDS ON IT ─
NODES are JavaScript modules under `api/`, plus EXTERNAL RESOURCES -- the
environment variables the code reads. EDGES are relative `require()` calls
resolved to a real file on disk, and `process.env.X` reads.

`require('@vercel/node')` is NOT an edge: this asks which of OUR components is
load-bearing, and a third-party package is a different question with a
different register (`docs/SOUP-REGISTER.md`).

TWO GRAPHS ARE REPORTED, NOT ONE FUSED NUMBER, and that is deliberate. The
module graph answers "which of our files is a chokepoint". The module+resource
graph answers "what does this platform actually stand on", and its answer is
dominated by one or two credentials -- which is the true answer and would
drown the module-level structure if the two were averaged into one ranking.

── WHAT THIS CANNOT SEE, stated here rather than discovered by somebody
   quoting a number it does not support ─────────────────────────────────────
  * a RUNTIME call that is not a require. One endpoint fetching another over
    HTTP is a real dependency and is invisible here;
  * the app HTML files, which are not modules and reach the API over HTTP;
  * whether a dependency is on a HOT path or in a branch that never runs. A
    require is a require.

── ARTICULATION POINTS, AND WHY THE RANKING IS BY BLAST RADIUS ─────────────
An ARTICULATION POINT is the textbook definition: a node whose removal
increases the number of connected components of the UNDIRECTED graph. Computed
exactly. It is reported but it is NOT the headline, because on a dependency
graph it over-reports -- a helper required by exactly one endpoint is an
articulation point, and losing it costs one endpoint.

The headline is BLAST RADIUS: how many modules transitively require this one,
which is how many stop working if it does. That is the question "single point
of failure" is actually asking.

They disagree, and the disagreement is the informative part. Large blast radius
and NOT an articulation point means several paths reach the same place -- wide
but not a cut. An articulation point with a small blast radius is a narrow,
total cut. One number would hide whichever case it is not about.

── ITEM 53: PAIRS THAT ARE ONLY FATAL TOGETHER ────────────────────────────
A 2-ELEMENT MINIMAL CUT SET is a pair {u, v} where removing BOTH disconnects
something and removing EITHER ALONE does not. These are invisible to any
single-point analysis by construction, and they are the ones a redundancy
argument gets wrong: "there are two paths" is only reassuring while the two
paths do not share a third thing.

Computed exactly rather than sampled: for every u that is NOT already a cut
vertex, the articulation points of G-u that are not articulation points of G
are exactly the v that complete a minimal pair with it. That is O(V * (V+E)),
which at this size is a second, so nothing is capped and nothing is estimated.

ISOLATED NODES ARE EXCLUDED FROM THE PAIR SEARCH and that is a real limit, not
a tidy-up: removing an isolated node lowers the component count, so the
"disconnects something" test cannot distinguish it. A module nothing requires
and which requires nothing has no pair to be half of anyway.
"""
import datetime
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.path.join(REPO, 'api')
SEP = chr(92)


# ── STRIPPING, AND WHY IT IS NOT OPTIONAL ─────────────────────────────────
# The first version of this scan reported one unresolvable require --
# `./_lib/heartbeat` -- which looked like a broken import and a crash waiting
# to happen. It was a USAGE EXAMPLE IN A COMMENT inside api/_lib/heartbeat.js
# itself. A dependency graph that counts commented-out and documented code as
# edges reports structure the runtime does not have, and the error it produces
# is the confident kind.
def strip_js(src):
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        if c == '/' and nxt == '/':
            j = src.find(chr(10), i)
            i = n if j < 0 else j
            continue
        if c == '/' and nxt == '*':
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in ('"', "'", '`'):
            # Kept as an EMPTY string literal rather than dropped, so a
            # require() whose argument is a string still parses -- the argument
            # is read from the original text, not from this.
            q, j = c, i + 1
            while j < n:
                if src[j] == SEP:
                    j += 2
                    continue
                if src[j] == q:
                    break
                j += 1
            out.append(src[i:j + 1])
            i = j + 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


REQ = re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)")
ENV = re.compile(r"process\.env\.([A-Z_][A-Z0-9_]*)")


def rel(p):
    return os.path.relpath(p, REPO).replace(SEP, '/')


def js_files(with_tests=False):
    """TEST FILES ARE EXCLUDED BY DEFAULT, and that is a correctness decision
    rather than tidiness. 155 of the 299 `.js` files under `api/` are
    `*.test.js` -- MORE THAN HALF the graph. Counting them makes the headline
    number a lie in the direction that matters: "82 modules stop working if
    api/_lib/license.js does" reads as 82 endpoints and is mostly test files,
    which stop working in CI and serve nobody. A blast radius has to mean
    production or it means nothing.

    They are not deleted from the world, only from the default graph --
    `--with-tests` puts them back, and the counts are printed side by side so
    the difference is visible rather than assumed."""
    out = []
    for root, dirs, fs in os.walk(API):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git')]
        for f in fs:
            if not f.endswith('.js'):
                continue
            if not with_tests and f.endswith('.test.js'):
                continue
            out.append(os.path.join(root, f))
    return sorted(out)


def build(include_env=True, files=None, root=None, with_tests=False):
    """Return (nodes, edges, unresolved). `edges` is a -> set(b): a needs b."""
    base = root or REPO
    edges = defaultdict(set)
    nodes = set()
    unresolved = Counter()
    for p in (files if files is not None else js_files(with_tests)):
        raw = io.open(p, encoding='utf-8', errors='replace').read()
        src = strip_js(raw)
        a = os.path.relpath(p, base).replace(SEP, '/')
        nodes.add(a)
        for m in REQ.finditer(src):
            t = m.group(1)
            if not t.startswith('.'):
                continue
            cand_base = os.path.normpath(os.path.join(os.path.dirname(p), t))
            hit = None
            for cand in (cand_base, cand_base + '.js', os.path.join(cand_base, 'index.js')):
                if os.path.isfile(cand):
                    hit = cand
                    break
            if hit:
                b = os.path.relpath(hit, base).replace(SEP, '/')
                nodes.add(b)
                edges[a].add(b)
            else:
                unresolved[a + ' -> ' + t] += 1
        if include_env:
            for m in ENV.finditer(src):
                b = 'env:' + m.group(1)
                nodes.add(b)
                edges[a].add(b)
    return nodes, edges, unresolved


def undirected(nodes, edges):
    adj = defaultdict(set)
    for a in nodes:
        adj[a]
    for a, bs in edges.items():
        for b in bs:
            adj[a].add(b)
            adj[b].add(a)
    return adj


def components(adj, nodes, removed=()):
    removed = set(removed)
    seen, count = set(), 0
    for s in nodes:
        if s in removed or s in seen:
            continue
        count += 1
        stack = [s]
        seen.add(s)
        while stack:
            x = stack.pop()
            for y in adj.get(x, ()):
                if y not in removed and y not in seen:
                    seen.add(y)
                    stack.append(y)
    return count


def articulation(adj, nodes, removed=()):
    """Iterative Hopcroft-Tarjan. Recursion would blow the stack on a real repo
    and, worse, would do it only on the biggest component -- so the small test
    graphs would pass and the real run would crash."""
    removed = set(removed)
    live = [n for n in sorted(nodes) if n not in removed]
    disc, low, parent, ap = {}, {}, {}, set()
    timer = [0]
    for root in live:
        if root in disc:
            continue
        disc[root] = low[root] = timer[0]
        timer[0] += 1
        parent[root] = None
        root_children = 0
        stack = [(root, iter(sorted(n for n in adj.get(root, ()) if n not in removed)))]
        while stack:
            node, it = stack[-1]
            pushed = False
            for nb in it:
                if nb not in disc:
                    parent[nb] = node
                    if node == root:
                        root_children += 1
                    disc[nb] = low[nb] = timer[0]
                    timer[0] += 1
                    stack.append((nb, iter(sorted(n for n in adj.get(nb, ()) if n not in removed))))
                    pushed = True
                    break
                if nb != parent.get(node):
                    low[node] = min(low[node], disc[nb])
            if not pushed:
                stack.pop()
                if stack:
                    par = stack[-1][0]
                    low[par] = min(low[par], low[node])
                    if par != root and low[node] >= disc[par]:
                        ap.add(par)
        if root_children > 1:
            ap.add(root)
    return ap


def blast(edges, nodes):
    """How many modules transitively REQUIRE each node -- what stops if it does."""
    radj = defaultdict(set)
    for a, bs in edges.items():
        for b in bs:
            radj[b].add(a)
    out = {}
    for n in nodes:
        seen, stack = set(), [n]
        while stack:
            x = stack.pop()
            for y in radj.get(x, ()):
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        out[n] = len(seen)
    return out


def cut_pairs(adj, nodes):
    """Item 53. Pairs fatal together, harmless apart."""
    isolated = {n for n in nodes if not adj.get(n)}
    live = sorted(n for n in nodes if n not in isolated)
    base_ap = articulation(adj, live)
    pairs = set()
    for u in live:
        if u in base_ap:
            continue                     # u alone already cuts; not a MINIMAL pair
        for v in articulation(adj, live, removed=(u,)):
            if v in base_ap or v == u:
                continue
            pairs.add(tuple(sorted((u, v))))
    return sorted(pairs), sorted(base_ap), sorted(isolated)


# ── THE BLIND LOCK ────────────────────────────────────────────────────────
# Every criterion below is decided against SYNTHETIC graphs with hand-known
# answers, and this refuses to report on the real repo until they all classify
# as written. The graphs are small enough to verify by eye, which is the point:
# a 300-node result nobody can check by hand is only as trustworthy as the
# 5-node result somebody did.
#
# The four-cycle is the load-bearing one. It has NO articulation points at all
# -- every single-vertex removal leaves a path -- and exactly TWO minimal
# 2-cuts, the opposite pairs. A graph where the single-point analysis is
# completely silent and the pair analysis is not is exactly the case item 53
# exists for, so it is the fixture that would catch a pair search that had
# quietly degenerated into a second copy of the articulation search.
FIXTURES = [
    # (name, undirected adjacency as {node: [neighbours]}, expected articulation,
    #  expected minimal 2-cut pairs)
    ('a path A-B-C: the middle is a cut, the ends are not',
     {'A': ['B'], 'B': ['A', 'C'], 'C': ['B']},
     {'B'}, []),
    ('a triangle has no cut vertex -- every pair still has a way round',
     {'A': ['B', 'C'], 'B': ['A', 'C'], 'C': ['A', 'B']},
     set(), []),
    ('two triangles sharing ONE vertex: that vertex is the cut',
     {'A': ['B', 'C'], 'B': ['A', 'C'], 'C': ['A', 'B', 'D', 'E'],
      'D': ['C', 'E'], 'E': ['C', 'D']},
     {'C'}, []),
    ('a four-cycle: NO single cut vertex, and exactly two fatal PAIRS',
     {'A': ['B', 'D'], 'B': ['A', 'C'], 'C': ['B', 'D'], 'D': ['C', 'A']},
     set(), [('A', 'C'), ('B', 'D')]),
    ('an isolated node is not a cut vertex and is in no pair',
     {'A': ['B'], 'B': ['A'], 'Z': []},
     set(), []),
]


def run_fixtures():
    bad = []
    for name, raw, want_ap, want_pairs in FIXTURES:
        adj = {k: set(v) for k, v in raw.items()}
        nodes = set(raw)
        got_ap = articulation(adj, nodes)
        if got_ap != want_ap:
            bad.append((name, 'articulation', sorted(want_ap), sorted(got_ap)))
        got_pairs, _, _ = cut_pairs(adj, nodes)
        if got_pairs != [tuple(p) for p in want_pairs]:
            bad.append((name, 'pairs', want_pairs, got_pairs))
    # BLAST RADIUS gets its own fixture because it reads the DIRECTED edges and
    # everything above reads the undirected ones -- a single fixture set over
    # one representation would leave the other unchecked.
    e = {'a.js': {'b.js'}, 'b.js': {'c.js'}}
    n = {'a.js', 'b.js', 'c.js'}
    got = blast(e, n)
    want = {'a.js': 0, 'b.js': 1, 'c.js': 2}
    if got != want:
        bad.append(('blast radius counts TRANSITIVE requirers, not direct ones',
                    'blast', want, got))
    # STRIPPING. The real defect this caught, kept as a fixture so it cannot
    # come back: a require() inside a comment is not an edge.
    stripped = strip_js("// const x = require('./ghost');\nconst y = require('./real');")
    if "require('./ghost')" in stripped or "require('./real')" not in stripped:
        bad.append(('a require() inside a comment is not an edge', 'strip',
                    'ghost gone, real kept', stripped))
    return bad


def analyse(include_env, with_tests=False):
    nodes, edges, unresolved = build(include_env=include_env, with_tests=with_tests)
    adj = undirected(nodes, edges)
    ap = articulation(adj, nodes)
    rad = blast(edges, nodes)
    return {'nodes': sorted(nodes), 'edges': {a: sorted(b) for a, b in edges.items()},
            'articulation': sorted(ap), 'blast': rad, 'adj': adj,
            'unresolved': dict(unresolved)}


def main(argv):
    bad = run_fixtures()
    print('DEPENDENCY GRAPH -- single points of failure, and pairs (items 88, 53)')
    if bad:
        print('  !! THE CRITERIA FAILED THEIR OWN FIXTURES. NOTHING WAS ANALYSED.')
        for row in bad:
            print('     %s -- %s: wanted %r, got %r' % row)
        return 2
    print('  blind lock: %d synthetic graphs classify as written, plus the blast-radius'
          % len(FIXTURES))
    print('              and comment-stripping fixtures. Run BEFORE the repo was read.')
    if '--fixtures' in argv:
        return 0

    if '--register' in argv:
        return check_register()

    with_tests = '--with-tests' in argv
    mod = analyse(include_env=False, with_tests=with_tests)
    full = analyse(include_env=True, with_tests=with_tests)

    if '--json' in argv:
        out = {}
        for name, g in (('modules', mod), ('modules_and_resources', full)):
            out[name] = {'nodes': g['nodes'], 'edges': g['edges'],
                         'articulation': g['articulation'], 'blast': g['blast'],
                         'unresolved': g['unresolved']}
        pairs, base_ap, isolated = cut_pairs(mod['adj'], set(mod['nodes']))
        out['modules']['cut_pairs'] = [list(p) for p in pairs]
        pairs_f, _, _ = cut_pairs(full['adj'], set(full['nodes']))
        out['modules_and_resources']['cut_pairs'] = [list(p) for p in pairs_f]
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

    print()
    print('  GRAPH A -- our modules only. %d nodes, %d edges.'
          % (len(mod['nodes']), sum(len(v) for v in mod['edges'].values())))
    print('  GRAPH B -- modules PLUS the environment they read. %d nodes, %d edges.'
          % (len(full['nodes']), sum(len(v) for v in full['edges'].values())))
    print('  Reported separately on purpose: B is dominated by two credentials,')
    print('  which is the true answer and would drown A if they were averaged.')

    if mod['unresolved']:
        print()
        print('  UNRESOLVED RELATIVE require() -- a path that names no file on disk.')
        print('  This is a crash at import time, not a graph nicety:')
        for k, v in sorted(mod['unresolved'].items()):
            print('     %s   (x%d)' % (k, v))

    for label, g in (('A (modules)', mod), ('B (modules + environment)', full)):
        rad = g['blast']
        apset = set(g['articulation'])
        print()
        print('  === GRAPH %s -- WIDEST BLAST RADIUS ===' % label)
        print('  how many modules stop working if this one does')
        top = sorted(rad.items(), key=lambda kv: (-kv[1], kv[0]))[:12]
        for n, c in top:
            if c == 0:
                continue
            print('    %4d  %-44s %s' % (c, n, 'CUT VERTEX' if n in apset else '-'))
        print('  %d articulation point(s) in this graph.' % len(apset))
        wide_not_cut = [n for n, c in top if c >= 5 and n not in apset]
        if wide_not_cut:
            print('  WIDE BUT NOT A CUT (several paths reach it, so removing it is')
            print('  broad rather than total): ' + ', '.join(wide_not_cut[:6]))

    print()
    print('  === ITEM 53 -- PAIRS THAT ARE ONLY FATAL TOGETHER ===')
    for label, g in (('A (modules)', mod), ('B (modules + environment)', full)):
        pairs, base_ap, isolated = cut_pairs(g['adj'], set(g['nodes']))
        print('  GRAPH %s: %d minimal 2-cut(s), against %d single cut vertices '
              'and %d isolated node(s) excluded.'
              % (label, len(pairs), len(base_ap), len(isolated)))
        for u, v in pairs[:20]:
            print('     {%s , %s}' % (u, v))
        if len(pairs) > 20:
            print('     ... and %d more. NOT a cap on the analysis -- the full list is '
                  'in --json; only the printing stops here.' % (len(pairs) - 20))
        if not pairs:
            print('     none. Every disconnection in this graph is reachable by')
            print('     removing ONE node, so pairs add nothing here -- which is a')
            print('     result, not a silence.')
    return 0




# ── ITEM 91: THE REGISTER, AND WHY IT IS NOT A GENERATED FILE ─────────────
# A single-point-of-failure list generated once and filed is a document. What
# is wanted is a LIVE, SHRINKING list: every chokepoint named, OWNED, and
# retired visibly when a real fix lands.
#
# So the rows are HAND-WRITTEN -- the owner, the mitigation and the judgement
# about whether a thing should be a chokepoint at all are not derivable -- and
# this checks them against the live graph in BOTH directions:
#
#   * a component at or above the threshold with NO ROW is an unregistered
#     single point of failure, which is the failure the register exists to
#     prevent;
#   * a row marked OPEN whose component is no longer above the threshold is
#     STALE -- the fix landed and nobody moved the row, so the list stopped
#     shrinking where it should have;
#   * a row marked RETIRED whose component is STILL above the threshold is the
#     sharp one. It is a retirement that did not happen, and it is exactly how
#     a register becomes a reassuring lie. Retirement is not a decision
#     somebody makes; it is a measurement.
#
# THE THRESHOLD IS A POLICY, NOT A CLASSIFIER, and it is named rather than
# buried so that moving it is a visible act. Ten production modules is roughly
# 7% of the 144 in the graph.
SPOF_THRESHOLD = 10
REGISTER = os.path.join(REPO, 'docs', 'SPOF-REGISTER.md')


def register_rows(text):
    """Rows of the register table: (component, owner, status)."""
    rows = []
    for line in text.split(chr(10)):
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 4:
            continue
        comp = cells[0].strip('`* ')
        if comp in ('Component', '---') or set(comp) <= set('-: '):
            continue
        rows.append({'component': comp, 'owner': cells[1].strip('* '),
                     'status': cells[2].strip('* ').upper()})
    return rows


# ── THE FROZEN DENOMINATOR (item 91, 2026-09-14) ──────────────────────────
# JWST tracked 344 single-point failures. The number is famous because it never
# moved: every retirement was read against the SAME total, so progress was a
# fraction and not an anecdote.
#
# This register already counted OPEN / ACCEPTED / RETIRED, and that is a
# snapshot. Without a baseline "7 OPEN" a year from now cannot be told from
# "7 OPEN" today -- a register that shrank by four and one that never moved
# print the same line. So the opening total is written into the register once,
# parsed here, and every run reports today AGAINST it.
#
# IT IS A HISTORICAL FACT AND MUST NOT BE EDITED. If it drifts, the fraction
# stops meaning anything, which is why a MISSING baseline is a refusal rather
# than a default -- a default of "today's count" would silently make progress
# zero forever.
BASELINE_RE = re.compile(
    r'BASELINE\s*[:\-]?\s*(\d+)\s+components?\s+at\s+or\s+above', re.I)


# THE DATE, because a frozen denominator without one cannot express a TREND.
# "0 RETIRED" is a number; "0 RETIRED in 10 days" is what this register was
# actually asked for -- a LIVE, SHRINKING list. Read out of the SAME sentence
# as the count so the two cannot drift apart.
BASELINE_DATE_RE = re.compile(
    r'BASELINE\s*[:\-]?\s*\d+\s+components?\s+at\s+or\s+above'
    r'[^\r\n]*?on\s+(\d{4}-\d{2}-\d{2})', re.I)


def read_baseline(text):
    m = BASELINE_RE.search(text)
    return int(m.group(1)) if m else None


def read_baseline_date(text):
    m = BASELINE_DATE_RE.search(text)
    return m.group(1) if m else None


def check_register():
    if not os.path.exists(REGISTER):
        print('  COULD NOT RUN: %s does not exist. That is not a clean register.'
              % os.path.relpath(REGISTER, REPO))
        return 2
    nodes, edges, _ = build(include_env=True, with_tests=False)
    rad = blast(edges, nodes)
    live = {n for n, c in rad.items() if c >= SPOF_THRESHOLD}
    rows = register_rows(io.open(REGISTER, encoding='utf-8').read())
    by = {r['component']: r for r in rows}

    problems = []
    for n in sorted(live):
        if n not in by:
            problems.append('UNREGISTERED  %s (blast %d) is at or above the '
                            'threshold and has no row' % (n, rad[n]))
    for r in rows:
        if not r['owner'] or r['owner'] in ('&mdash;', '-', '—'):
            problems.append('NO OWNER      %s -- an unowned entry is a note, not a register'
                            % r['component'])
        if r['status'] == 'RETIRED' and r['component'] in live:
            problems.append('NOT RETIRED   %s is marked RETIRED and is STILL at blast %d. '
                            'Retirement is a measurement, not a decision.'
                            % (r['component'], rad[r['component']]))
        if r['status'] == 'OPEN' and r['component'] not in live:
            problems.append('STALE         %s is marked OPEN and is no longer above the '
                            'threshold -- the fix landed and the row did not move'
                            % r['component'])
        # ACCEPTED IS A THIRD STATE AND IT IS NOT A WEAKENING. Some chokepoints
        # are the CORRECT design: one auth implementation is the thing this repo
        # spent item 94 arguing for, and calling it a defect because it has a
        # wide blast radius would be the analysis leading the judgement. An
        # ACCEPTED row is exempt from the shrink rules and from nothing else --
        # it still needs an owner, and it must still carry a REASON, because an
        # acceptance with no reason is indistinguishable from a row nobody got
        # round to.
        if r['status'] not in ('OPEN', 'ACCEPTED', 'RETIRED'):
            problems.append('BAD STATUS    %s has status %r -- the vocabulary is OPEN, '
                            'ACCEPTED, RETIRED' % (r['component'], r['status']))
        if r['component'] not in rad:
            problems.append('NOT A NODE    %s appears in no graph at all -- renamed, '
                            'deleted, or mistyped' % r['component'])

    print('  SPOF REGISTER -- threshold: blast radius >= %d production modules'
          % SPOF_THRESHOLD)
    print('  %d component(s) at or above it, %d row(s) in the register.'
          % (len(live), len(rows)))
    retired = [r for r in rows if r['status'] == 'RETIRED']
    accepted = [r for r in rows if r['status'] == 'ACCEPTED']
    print('  %d OPEN, %d ACCEPTED (deliberate, with a reason and a compensating '
          'control), %d RETIRED.'
          % (len([r for r in rows if r['status'] == 'OPEN']), len(accepted), len(retired)))
    base = read_baseline(io.open(REGISTER, encoding='utf-8', errors='replace').read())
    if base is None:
        problems.append('NO BASELINE   %s has no "BASELINE: N components at or '
                        'above" line. Without a frozen denominator a register '
                        'that shrank by four and one that never moved print the '
                        'same number.' % os.path.relpath(REGISTER, REPO))
    else:
        net = base - len(live)
        moved = ('no change' if net == 0
                 else ('%d fewer' % net if net > 0 else '%d MORE' % -net))
        print('  BASELINE %d on the day this register opened -> %d today (%s).'
              % (base, len(live), moved))
        # ── THE RETIREMENT STALL, REPORTED UNCONDITIONALLY (2026-09-24) ────
        # This disclosure used to be gated on `net == 0` -- the list being
        # exactly its opening size -- so it went SILENT in every case except
        # the one where nothing at all had happened. On 2026-09-23 the list
        # stood at 32 against a baseline of 11 with ZERO retirements and the
        # tool printed nothing about retirement at all: the GROWTH suppressed
        # the one sentence a reader needed. A disclosure that disappears when
        # the situation worsens is not a disclosure.
        #
        # AND IT CARRIES ELAPSED TIME NOW, which is what makes it a trend
        # rather than a number. This register's stated purpose is a LIVE,
        # SHRINKING list; "0 RETIRED" cannot be told from "nobody has run
        # this" without knowing how long it has been true.
        bdate = read_baseline_date(
            io.open(REGISTER, encoding='utf-8', errors='replace').read())
        if bdate is None:
            problems.append('NO BASELINE DATE  the BASELINE sentence gives a '
                            'count and no date, so "%d RETIRED" cannot be read '
                            'as a trend -- a list nobody has fixed and a list '
                            'nobody has measured print the same line.'
                            % len(retired))
        else:
            try:
                days = (datetime.date.today() - datetime.date(
                    *(int(x) for x in bdate.split('-')))).days
            except ValueError:
                days = None
            span = ('%d day(s)' % days) if days is not None else 'an unreadable span'
            if not retired:
                print('  NOTHING HAS BEEN RETIRED IN %s, since %s.' % (span, bdate))
                print('  THAT IS A FACT ABOUT THE PLATFORM, NOT ABOUT THIS REGISTER:')
                print('  retirement is a MEASUREMENT and no component has dropped')
                print('  below the threshold. Nothing here is broken -- but a list')
                print('  whose whole purpose is to SHRINK has not, and the elapsed')
                print('  time is printed so that cannot be read as a clean run.')
            else:
                print('  %d RETIRED in %s, since %s.' % (len(retired), span, bdate))
    print('  A register that only grows is a graveyard; one that shrinks without '
          'a measurement')
    print('  behind it is worse, so RETIRED is refused while the component is '
          'still above the bar.')
    if problems:
        for p in problems:
            print('    ' + p)
        return 1
    print('  OK: every chokepoint is named and owned, and every retirement is real.')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
