"""Which Tier A resources have a GENUINE cross-tenant isolation test, and what
would it cost to give one to the rest.

    python tools/cross_tenant_isolation_scope.py              # the table
    python tools/cross_tenant_isolation_scope.py --plan       # + the phasing
    python tools/cross_tenant_isolation_scope.py --resource X # one resource

Exit 0 clean, 1 a finding, 2 COULD NOT TELL -- never folded into either of the
other two (PR 1.11).

── WHY THIS EXISTS ─────────────────────────────────────────────────────────────
The hover auditor's finding #269 swept `license_hash` FILTERING to 84/84 Tier A
resources: every one of them scopes its query by tenant. Findings #276/#278 are
the other half of that sentence and it is the half that decays -- that filtering
is asserted by ALMOST NOTHING. A filter nothing tests is a filter the next
refactor can drop, and the failure is silent in the worst direction: tenant A
reads tenant B's row and the response looks perfectly normal.

The work was flagged as too large for one dispatch, which is correct. This tool
exists so the SCOPING is measured rather than estimated -- 84 resources is a
number to phase, not a number to start at the top of.

── WHAT "GENUINE" MEANS, AND WHY THE WEAK SHAPE IS THE DANGEROUS ONE ──────────
The one working pattern on this platform is
api/sairndental/complaint-respond.test.js:100-137. Its load-bearing property is
in its own comment: the fetch mock FILTERS ON WHICHEVER `eq.` CLAUSES ARE
ACTUALLY PRESENT IN THE URL, mirroring PostgREST. Two rows are seeded under two
different license_hash values, the caller authenticates as tenant A, asks for
tenant B's id, and must be refused.

That mock is the whole test. Remove `license_hash=eq.` from the handler and the
mock matches on the id alone, returns tenant B's row, and the assertion fails.

THE SHAPE THAT LOOKS LIKE IT AND IS NOT: a mock that returns a fixed array
regardless of the URL, with an assertion that the URL CONTAINS
`license_hash=eq.`. That is a string check wearing a behaviour check. It passes
when the filter is present but ANDed wrong, when it is present but the handler
ignores the returned rows, and when a second query on the same path lacks it.
This tool grades those apart, because counting them together would report
coverage this platform does not have -- and an overstated coverage number on
exactly this control is worse than a zero, which at least prompts the work.

── THE THIRD STATE IS REAL HERE ───────────────────────────────────────────────
A resource whose serving code this tool cannot locate is UNLOCATED, not
untested. It is reported in its own column and never folded into either
"covered" or "uncovered", because a session sent to write a test against a
branch that is not there reports a failure of the wrong thing.

THE COLUMN READS 0 TODAY AND THAT IS THE MEASUREMENT, NOT A DEFAULT. It read 57
on the first version, then 22, then 8, then 0, as each of four distinct serving
shapes was added -- named branch, generic dispatcher, compound-action branch,
and a predicate dispatcher over an external registry module. Every one of those
was a parser limit reported as a platform gap. Do not read a 0 here as "the
parser is finished"; read it as "no fifth shape has been introduced yet."
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

CRITERIA_VERSION = '2026-09-21.2'

# The one known-good instance, named rather than described, so --check can
# assert the grader still recognises it. A grader that stops recognising its
# own reference case is a grader whose criteria have drifted, and nothing else
# would announce that.
REFERENCE_TEST = 'api/sairndental/complaint-respond.test.js'


class CouldNotTell(Exception):
    pass


def read(rel):
    try:
        return io.open(os.path.join(REPO, rel), encoding='utf-8', errors='replace').read()
    except OSError as e:
        raise CouldNotTell('%s could not be read: %s' % (rel, e))


def tier_a():
    """Straight from the register the tier decision already lives in. Never a
    second copy -- see tier_a_review_gate.tier_a_resources(), whose failure
    mode this shares deliberately: zero rows is COULD NOT TELL, never an empty
    set that would make everything look covered."""
    text = read('docs/CRITICALITY-TIERS.md')
    names = set()
    for line in text.split('\n'):
        m = re.match(r'^\|\s*`([a-z0-9_]+)`\s*\|\s*\*\*A\*\*\s*\|', line)
        if m:
            names.add(m.group(1))
    if not names:
        raise CouldNotTell(
            'docs/CRITICALITY-TIERS.md yielded ZERO Tier A rows -- a parse '
            'failure or a lost table. An empty set would report the whole '
            'platform as covered.')
    return names


def all_files(exts, roots=('api', 'tests')):
    out = []
    for root in roots:
        base = os.path.join(REPO, root)
        for dirpath, _dirs, files in os.walk(base):
            for f in files:
                if f.endswith(exts):
                    p = os.path.join(dirpath, f)
                    out.append(os.path.relpath(p, REPO).replace('\\', '/'))
    return sorted(out)


def is_test(rel):
    b = rel.rsplit('/', 1)[-1]
    return b.endswith('.test.js') or rel.startswith('tests/')


# ── WHERE A RESOURCE IS SERVED ────────────────────────────────────────────────
# THREE shapes, and the third is the one that changes the size of this job.
#   * a NAMED BRANCH in api/sd-data.js -- `resource === 'x' && action === 'read'`
#   * a GENERIC DISPATCHER -- `const SV_RESOURCES = { sv_billing: 'billing_id',
#     ... }` followed by `if (SV_RESOURCES[resource] && action === 'read')`. One
#     query-building code path serves every member of the map.
#   * a DEDICATED endpoint -- api/<thing>.js, its own handler
# A resource matching none of the three is UNLOCATED and says so.
#
# ── THE FIRST VERSION OF THIS FUNCTION KNEW ONLY THE FIRST AND THIRD SHAPES ───
# and reported 57 of 84 as UNLOCATED, including dnt_charges, which is plainly
# served. Worth recording because the wrong answer was the ACTIONABLE-looking
# one: it would have sent a session to write 84 separate tests, when the
# dispatchers mean a single parameterised test over one map covers every
# resource in it. The measurement was not just incomplete, it pointed the plan
# in the wrong direction.
BRANCH = re.compile(r"resource === '([a-z0-9_]+)'\s*&&\s*\(?\s*action === '([a-z_]+)'",
                    re.S)
# A SECOND named-branch spelling, and missing it cost 4 more false UNLOCATEDs:
# `resource === 'sen_claims' && (action === 'read' || action === 'write')`.
# Every extra action in the parenthesised group is picked up by BRANCH_ALT.
BRANCH_ALT = re.compile(r"resource === '([a-z0-9_]+)'\s*&&\s*\(([^)]*action === '[^)]*)\)",
                        re.S)
_ACTIONS = re.compile(r"action === '([a-z_]+)'")
# The map NAME is not a reliable marker -- SD_HR and MECH_RECORDS are
# dispatchers and neither ends in RESOURCES. What makes a map a dispatcher is
# that it is SUBSCRIPTED BY `resource` in a branch condition, which is a
# property of the use, not of the name.
DISPATCH_MAP = re.compile(r"const ([A-Z][A-Za-z0-9_]*)\s*=\s*\{")
DISPATCH_USE = re.compile(r"if \(([A-Z][A-Za-z0-9_]*)\[resource\]")


def _offset_of_line(src, n):
    off = 0
    for _ in range(n - 1):
        off = src.index('\n', off) + 1
    return off


def _block_after(src, off):
    """The `{ ... }` block that opens at or after `off`, brace-matched.

    ── WHY BRACE MATCHING AND NOT A LINE WINDOW ───────────────────────────────
    The first version looked 40 lines ahead for a `rest(` and reported
    DNT_FINANCIAL_RESOURCES -- a role gate whose entire body is a 403 -- as a
    serving site for eight resources, because the gate is NESTED INSIDE the
    dental read branch and the query forty lines later belongs to the enclosing
    block, not to it. A window cannot tell "inside this branch" from "after
    this branch", and on a 12,582-line file with branches nested five deep that
    distinction is the whole measurement.
    """
    start = src.find('{', off)
    if start < 0:
        return ''
    depth, i = 0, start
    while i < len(src):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    return src[start:]


def dispatcher_members(src, names):
    """map name -> (declaration line, [member resources], {action: line}).

    Only maps that are actually USED as `MAP[resource] && action === ...` are
    dispatchers. DNT_FINANCIAL_RESOURCES is a ROLE GATE with the same shape and
    is deliberately not counted as a serving site: it decides who may call, not
    where the query is built, and scoring it as a serving site would double-count
    every dental resource."""
    lines = src.split('\n')
    used = {}
    for i, line in enumerate(lines, 1):
        for m in DISPATCH_USE.finditer(line):
            # ── A GATE IS NOT A SERVING SITE, and conflating them inflates the
            # plan. `if (DNT_FINANCIAL_RESOURCES[resource] && !ROLES[role])
            # { 403 }` decides WHO MAY CALL; it builds no query and there is no
            # tenant filter in it to test. Only a branch that actually
            # constructs a PostgREST request is a place the filter lives.
            # Measured by looking forward from the branch for a `rest(`/`fetch(`
            # before the block plausibly ends -- crude, and deliberately
            # generous in the direction of counting a site, because missing a
            # real serving site is the failure that loses coverage.
            if 'rest(' not in _block_after(src, _offset_of_line(src, i)):
                continue
            acts = _ACTIONS.findall(line) or ['any']
            for a in acts:
                used.setdefault(m.group(1), {})[a] = i
    out = {}
    for i, line in enumerate(lines, 1):
        m = DISPATCH_MAP.search(line)
        if not m or m.group(1) not in used:
            continue
        # the literal runs to the first line that closes it at this indent
        body, j = [], i
        while j < len(lines):
            body.append(lines[j - 1])
            if re.match(r'^\s*\};?\s*$', lines[j - 1]) and j > i:
                break
            j += 1
        members = [k for k in re.findall(r"^\s*([a-z][a-z0-9_]*)\s*:", '\n'.join(body),
                                         re.M)
                   if k in names]
        members += [k for k in re.findall(r",\s*([a-z][a-z0-9_]*)\s*:", '\n'.join(body))
                    if k in names]
        members = sorted(set(members))
        if not members:
            continue
        out[m.group(1)] = (i, members, used[m.group(1)])
    return out


def serving_sites(names):
    src = read('api/sd-data.js')
    lines = src.split('\n')
    sites = {n: [] for n in names}
    # WHOLE-TEXT, NOT LINE-BY-LINE. `resource === 'mech_credentials' &&\n
    # (action === 'read' || ...)` is one condition across two lines and a
    # per-line scan cannot see it -- it was the last false UNLOCATED that was
    # actually a parser limit rather than a real gap.
    def lineno(off):
        return src.count('\n', 0, off) + 1
    for m in BRANCH.finditer(src):
        if m.group(1) in sites:
            sites[m.group(1)].append(('api/sd-data.js', lineno(m.start()), m.group(2)))
    for m in BRANCH_ALT.finditer(src):
        if m.group(1) in sites:
            for a in _ACTIONS.findall(m.group(2)):
                sites[m.group(1)].append(('api/sd-data.js', lineno(m.start()), a))
    # ── A FOURTH SHAPE: a PREDICATE dispatcher over an external registry ──────
    # `const SC_RESOURCES = require('./_resources/sairncode').resources` ->
    # `function isSc(resource){...}` -> `if (isScResource) {`. The membership
    # list is in another FILE, so nothing in sd-data.js names sc_claims on a
    # serving line at all. Detected from the require + the branch, and the
    # members come from the registry module -- never from a second copy here.
    for m in re.finditer(
            r"const\s+([A-Z][A-Za-z0-9_]*)\s*=\s*require\('\./_resources/([a-z]+)'\)\.resources",
            src):
        const, mod = m.group(1), m.group(2)
        pred = re.search(r"function\s+(\w+)\s*\(resource\)\s*\{\s*return\s+%s\.indexOf"
                         % re.escape(const), src)
        if not pred:
            continue
        # every `if (<something derived from the predicate>)` branch in the file
        holders = set(re.findall(r"const\s+(\w+)\s*=\s*%s\(resource\)" % re.escape(pred.group(1)), src))
        holders.add(pred.group(1) + '(resource)')
        branch_lines = []
        for h in holders:
            for bm in re.finditer(r"if \(%s\)\s*\{" % re.escape(h), src):
                branch_lines.append(lineno(bm.start()))
        if not branch_lines:
            continue
        try:
            reg = read('api/_resources/%s.js' % mod)
        except CouldNotTell:
            continue
        members = [n for n in names if re.search(r"'%s'" % re.escape(n), reg)]
        for n in members:
            for ln in sorted(set(branch_lines)):
                sites[n].append(('api/sd-data.js[%s via _resources/%s.js]' % (const, mod),
                                 ln, 'any'))
    for mapname, (_decl, members, actions) in dispatcher_members(src, names).items():
        for n in members:
            for action, ln in sorted(actions.items()):
                sites[n].append(('api/sd-data.js[%s]' % mapname, ln, action))
    # Dedicated endpoints: a non-test api file whose CODE (not comments) names
    # the resource as a PostgREST path or table.
    for rel in all_files(('.js',), roots=('api',)):
        if is_test(rel) or rel.endswith('/index.js'):
            continue
        if rel == 'api/sd-data.js':
            continue
        try:
            body = read(rel)
        except CouldNotTell:
            continue
        for n in names:
            if re.search(r"""['"`]%s\?""" % re.escape(n), body) or \
               re.search(r"""from\(['"`]%s['"`]\)""" % re.escape(n), body):
                sites[n].append((rel, 0, 'endpoint'))
    return sites


# ── DOES A TEST ACTUALLY EXERCISE TWO TENANTS ─────────────────────────────────
# Graded, not counted. The three grades are the three things a session needs to
# know before it picks up a resource, and collapsing them would hide the one
# that matters.
#
#   GENUINE  -- a URL-FILTERING mock (it reads eq. clauses out of the query and
#               honours them) AND two distinct license_hash values AND a
#               refusal assertion. Drop the filter in the handler and it fails.
#   WEAK     -- two tenants appear, or license_hash=eq. is asserted as a
#               substring, but the mock does not filter. Passes a handler whose
#               filter is present and wrong.
#   NONE     -- the resource is named by a test that does neither.
# ── THE FIRST VERSION COULD ONLY SEE HASHES AND CLAUSES SPELLED ONE WAY ──────
# and that is the eighth cross-domain discipline arriving on schedule: the
# criteria were derived from ONE file, so they encoded that file's spelling
# rather than the property. api/sd-data-cross-tenant-isolation.test.js parses
# the query generically (`/^([a-z0-9_]+)=eq\.(.*)$/`) and binds its two tenants
# to CONSTANTS (`const HASH_A = 'tenant-A-hash'`), and the grader scored it WEAK
# -- a test that did the more general thing scored worse, the same inversion
# sabotage_control_check.py recorded about its UNIQUENESS guard. Widened to the
# property: does the mock read an `=eq.` clause out of the URL at all, and are
# there two distinct tenant identifiers in the file by any spelling.
_EQ_READ = re.compile(
    r"""match\([^)]{0,40}=eq\\?\.|"""          # u.match(/license_hash=eq\.../), any prefix
    r"""=eq\\?\.\(?\[?\^?&""")                 # a generic `<col>=eq.(...)` parser
_EQ_READ2 = re.compile(r"""(?:searchParams|URLSearchParams|split\(['"]&)""")
_HASH_LITERALS = re.compile(r"""license_hash\s*[:=]\s*['"`]([^'"`]+)['"`]""")
_HASH_RETURNED = re.compile(r"""license_hash:\s*['"`]([^'"`]+)['"`]""")
# A tenant bound to a CONSTANT and used as `license_hash: HASH_A`. Counted only
# when the constant is actually used in a license_hash position somewhere,
# so an unrelated `const HASH = ...` does not inflate the count.
_HASH_CONST = re.compile(r"""const\s+([A-Z][A-Z0-9_]*)\s*=\s*['"`]([^'"`]+)['"`]""")
_HASH_USE = re.compile(r"""license_hash\s*[:=]\s*([A-Z][A-Z0-9_]*)\b""")
_REFUSAL = re.compile(
    r"""statusCode,\s*(40[0-9]|41[0-9]|5\d\d)|"""
    r"""\.length,\s*0\b|"""
    r"""code,\s*['"`](NOT_FOUND|FORBIDDEN|UNAUTHORIZED|DENIED)""")


def grade(body):
    """Grade one test file. Returns (grade, why)."""
    # 1. Does the fetch mock READ the query and filter on it?
    filters_url = bool(_EQ_READ.search(body)) or (
        bool(_EQ_READ2.search(body)) and 'license_hash' in body)
    # 2. Are there two DISTINCT license_hash values anywhere in it?
    hashes = set(_HASH_LITERALS.findall(body)) | set(_HASH_RETURNED.findall(body))
    consts = dict(_HASH_CONST.findall(body))
    for name in set(_HASH_USE.findall(body)):
        if name in consts:
            hashes.add(consts[name])
    two_tenants = len(hashes) >= 2
    # 3. Is a refusal asserted?
    refuses = bool(_REFUSAL.search(body))

    if filters_url and two_tenants and refuses:
        return 'GENUINE', 'url-filtering mock + %d distinct hashes + refusal asserted' % len(hashes)
    # ── WEAK MUST BE ABOUT THE TENANT BOUNDARY, NOT ABOUT REFUSALS ────────────
    # The first version graded WEAK on "asserts a refusal" alone, which every
    # serious test file on this platform does -- 67 of 84 came back WEAK and the
    # grade carried no information. WEAK now requires at least one TENANT-SHAPED
    # signal: two distinct license_hash values, a literal eq.-clause assertion,
    # or a mock that reads the query. A refusal assertion with none of those is
    # a test about something else that happens to name the resource, and calling
    # it partial coverage would be the overstatement this tool exists to avoid.
    bits = []
    if two_tenants:
        bits.append('%d distinct license_hash values' % len(hashes))
    if 'license_hash=eq.' in body:
        bits.append('asserts the eq. clause as a substring')
    if filters_url:
        bits.append('mock reads the query')
    if bits:
        if refuses:
            bits.append('asserts a refusal')
        missing = []
        if not filters_url:
            missing.append('the mock does NOT filter on the query')
        if not two_tenants:
            missing.append('only one tenant appears')
        if not refuses:
            missing.append('no refusal is asserted')
        return 'WEAK', '; '.join(bits) + ' -- but ' + '; '.join(missing)
    return 'NONE', 'names the resource but exercises no tenant boundary'


def tests_naming(names):
    """resource -> [(test file, grade, why)]. A test NAMES a resource when the
    string appears in it at all -- deliberately loose, because the question
    here is 'is there anything to build on', and a false 'yes' is corrected by
    the grade beside it."""
    hits = {n: [] for n in names}
    for rel in all_files(('.js', '.py')):
        if not is_test(rel):
            continue
        try:
            body = read(rel)
        except CouldNotTell:
            continue
        g, why = grade(body)
        for n in names:
            if n in body:
                hits[n].append((rel, g, why))
    return hits


# ── RISK RANK ─────────────────────────────────────────────────────────────────
# NOT a score invented here. Three inputs, each already recorded somewhere on
# this platform, and each named so a reader can disagree with one of them
# rather than with an opaque number:
#
#   BLAST   the tier register's own one-line harm sentence, read for the words
#           that distinguish "money moves" and "a person is harmed" from "a
#           report is wrong". This is the register's judgement, not a new one.
#   REACH   how many serving branches the resource has. A resource served at
#           six branches has six places the filter can be dropped.
#   EXPOSED whether a dedicated endpoint serves it. A dedicated endpoint is
#           reachable without sd-data.js's shared preamble, so it does not
#           inherit whatever that preamble checks.
#
# THE RANK IS ORDINAL AND SAYS SO. It orders work; it is not a probability and
# must never be quoted as one.
_HARM_MONEY = re.compile(
    r'money|paid|payment|invoice|billed|billing|charge|price|pricing|quote|'
    r'payroll|trust|ledger|account|ar\b|revenue|cost|bid', re.I)
_HARM_PERSON = re.compile(
    r'patient|resident|client|medication|controlled|clinical|incident|'
    r'credential|licence|license|cert|safety|harm|care|deadline|claim', re.I)


def harm_words(register_text, name):
    for line in register_text.split('\n'):
        if re.match(r'^\|\s*`%s`\s*\|' % re.escape(name), line):
            cells = line.split('|')
            return ' '.join(cells[3:])[:400]
    return ''


def rank(name, sites, hits, register_text):
    harm = harm_words(register_text, name)
    blast = 0
    if _HARM_MONEY.search(harm):
        blast += 2
    if _HARM_PERSON.search(harm):
        blast += 2
    reach = len([s for s in sites if s[1]])
    exposed = 2 if any(s[2] == 'endpoint' for s in sites) else 0
    best = 'NONE'
    for _f, g, _w in hits:
        if g == 'GENUINE':
            best = 'GENUINE'
            break
        if g == 'WEAK':
            best = 'WEAK'
    gap = {'GENUINE': 0, 'WEAK': 2, 'NONE': 3}[best]
    return {'resource': name, 'harm': harm, 'blast': blast, 'reach': reach,
            'exposed': exposed, 'coverage': best,
            'score': blast * 2 + min(reach, 4) + exposed + gap,
            'sites': sites, 'tests': hits}


def build():
    names = tier_a()
    register_text = read('docs/CRITICALITY-TIERS.md')
    sites = serving_sites(names)
    hits = tests_naming(names)
    rows = [rank(n, sites[n], hits[n], register_text) for n in sorted(names)]
    rows.sort(key=lambda r: (-r['score'], r['resource']))
    return rows


def self_check(rows):
    """The grader must still recognise its own reference case. A criteria set
    that stops matching the one instance it was derived FROM has drifted, and
    nothing else on this platform would announce that -- see the eighth
    cross-domain discipline."""
    body = read(REFERENCE_TEST)
    g, why = grade(body)
    if g != 'GENUINE':
        raise CouldNotTell(
            'THE GRADER NO LONGER RECOGNISES ITS OWN REFERENCE CASE.\n'
            '  %s graded %s (%s)\n'
            'The criteria were derived from that file. If it does not grade '
            'GENUINE, every other verdict in this run is untrustworthy and '
            'none of them are printed.' % (REFERENCE_TEST, g, why))
    return g


def main(argv):
    try:
        rows = build()
        self_check(rows)
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL: %s\n' % e)
        return 2

    one = None
    if '--resource' in argv:
        one = argv[argv.index('--resource') + 1]
        rows = [r for r in rows if r['resource'] == one]
        if not rows:
            sys.stderr.write('no such Tier A resource: %s\n' % one)
            return 2

    genuine = [r for r in rows if r['coverage'] == 'GENUINE']
    weak = [r for r in rows if r['coverage'] == 'WEAK']
    none = [r for r in rows if r['coverage'] == 'NONE']
    unlocated = [r for r in rows if not r['sites']]

    print('CROSS-TENANT ISOLATION COVERAGE -- Tier A, criteria %s' % CRITERIA_VERSION)
    print('reference case %s grades GENUINE, so the criteria still match what '
          'they were derived from' % REFERENCE_TEST)
    print('')
    print('  Tier A resources        %3d' % len(rows))
    print('  GENUINE isolation test  %3d' % len(genuine))
    print('  WEAK -- looks like one  %3d   <- graded apart deliberately; see the header'
          % len(weak))
    print('  NONE                    %3d' % len(none))
    print('  serving code UNLOCATED  %3d   <- a THIRD state, in neither column above'
          % len(unlocated))
    print('')

    if '--json' in argv:
        print(json.dumps(rows, indent=2))
        return 0

    print_codepaths(rows)
    print('')
    print('%-28s %-8s %5s %5s %4s  %s' % ('resource', 'coverage', 'score', 'reach', 'endp', 'where it is served'))
    print('-' * 118)
    for r in rows:
        where = ', '.join(sorted(set(
            '%s%s' % (s[0], (':%d' % s[1]) if s[1] else '') for s in r['sites']))) or '** UNLOCATED **'
        print('%-28s %-8s %5d %5d %4s  %s'
              % (r['resource'], r['coverage'], r['score'], r['reach'],
                 'yes' if r['exposed'] else '-', where[:60]))
        if one:
            print('    harm : %s' % r['harm'][:300])
            for t, g, why in r['tests']:
                print('    test : %-8s %s -- %s' % (g, t, why))

    if '--plan' in argv:
        print_plan(rows)

    # A finding, not a pass: the whole point is that this number is not 84.
    return 1 if len(genuine) < len(rows) else 0


def codepaths(rows):
    """84 resources, but FAR FEWER places the tenant filter is actually built.

    ── THIS IS THE NUMBER THE PLAN IS SIZED FROM, and it is why "84 tests" was
    the wrong unit. A generic dispatcher builds ONE query for every member of
    its map: `rest(resource + '?license_hash=eq.' + enc(licHash) + ...)`. One
    parameterised isolation test over that dispatcher, driven once per member,
    covers all of them -- and more importantly, deleting the filter breaks it
    once for all of them, which is the property that matters.

    A resource with its OWN named branch is its own code path and has to be
    paid for individually. Those are the expensive ones and they are a minority.
    """
    groups = {}
    for r in rows:
        for f, _ln, _a in r['sites']:
            # A DISPATCHER IS ONE UNIT regardless of how many action branches it
            # has, because all of them build the query the same way from the
            # same map. A resource with its OWN named branches is one unit too:
            # read and write are separate lines but a single test file drives
            # both, and that file is what a session is dispatched to write.
            key = f if '[' in f else ('%s :: %s' % (f, r['resource']))
            groups.setdefault(key, set()).add(r['resource'])
    return groups


def print_codepaths(rows):
    groups = codepaths(rows)
    shared = {k: v for k, v in groups.items() if len(v) > 1}
    solo = {k: v for k, v in groups.items() if len(v) == 1}
    covered_by_shared = set().union(*shared.values()) if shared else set()
    print('THE UNIT THIS PLAN IS SIZED IN -- and it is NOT 84')
    print('  A generic dispatcher builds ONE query for every resource in its map')
    print('  (rest(resource + \'?license_hash=eq.\' + enc(licHash) + ...)), so one')
    print('  parameterised test covers the whole map AND breaks once for all of')
    print('  them if the filter is ever dropped. That is the property worth having.')
    print('')
    print('  TEST UNITS                    %3d   <- the real size of the job' % len(groups))
    print('    shared dispatchers          %3d   covering %d of the 84 resources'
          % (len(shared), len(covered_by_shared)))
    print('    own-branch resources        %3d   one test file each, paid individually'
          % len(solo))
    print('')
    for k, v in sorted(shared.items(), key=lambda kv: -len(kv[1])):
        print('    %-52s %2d resources' % (k[:52], len(v)))


def print_plan(rows):
    """Phased by TEST UNIT, not by resource.

    ── WHY NOT BY RESOURCE, which is how this was first written ───────────────
    A per-resource list is a list of 84 things to do and it is wrong in the
    expensive direction: it puts `dnt_ar` and `dnt_charges` in different phases
    when ONE test over DNT_RESOURCES covers both and cannot cover one without
    the other. A session dispatched per resource would write the same
    dispatcher test nine times, or worse, write it once and mark eight
    resources done on a test that never names them.

    A unit is dispatched WHOLE. Its rank is the rank of its highest-risk member,
    because that is the member whose isolation failure costs the most, and the
    rest come along at no extra cost.
    """
    by_resource = {r['resource']: r for r in rows}
    groups = codepaths(rows)
    units = []
    for key, members in groups.items():
        best = max(by_resource[m]['score'] for m in members)
        worst_harm = max(by_resource[m]['blast'] for m in members)
        cov = 'GENUINE' if any(by_resource[m]['coverage'] == 'GENUINE' for m in members) \
            else ('WEAK' if any(by_resource[m]['coverage'] == 'WEAK' for m in members) else 'NONE')
        units.append({'key': key, 'members': sorted(members), 'score': best,
                      'blast': worst_harm, 'coverage': cov,
                      'shared': len(members) > 1})
    units.sort(key=lambda u: (-u['score'], -len(u['members']), u['key']))

    print('')
    print('=' * 118)
    print('PHASING -- by TEST UNIT, ordinal, derived from the table rather than chosen')
    print('=' * 118)
    print('A unit is one dispatchable piece of work: either a generic dispatcher')
    print('(one parameterised test, every member covered) or one resource with its')
    print('own branches (one test file). Rank is the highest-risk MEMBER\'s rank --')
    print('the rest come along at no extra cost, which is the whole argument for')
    print('doing the dispatchers first.')

    bands = [
        ('PHASE 1 -- money or a person, and a shared dispatcher (best ratio on the board)',
         lambda u: u['shared'] and u['blast'] >= 4),
        ('PHASE 2 -- the remaining shared dispatchers',
         lambda u: u['shared']),
        ('PHASE 3 -- own-branch resources where BOTH money and a person are at stake',
         lambda u: u['blast'] >= 4),
        ('PHASE 4 -- own-branch resources, one harm class',
         lambda u: u['blast'] >= 2),
        ('PHASE 5 -- the remainder',
         lambda u: True),
    ]
    seen = set()
    for label, pred in bands:
        band = [u for u in units if pred(u) and u['key'] not in seen]
        seen.update(u['key'] for u in band)
        if not band:
            continue
        covered = sum(len(u['members']) for u in band)
        print('')
        print('%s' % label)
        print('    %d unit(s), %d resource(s)' % (len(band), covered))
        for u in band:
            name = u['key'].split(' :: ')[-1] if ' :: ' in u['key'] else u['key']
            if u['shared']:
                print('    %-46s rank %2d  %-7s  %d resources: %s'
                      % (name[:46], u['score'], u['coverage'], len(u['members']),
                         ', '.join(u['members'])[:70]))
            else:
                print('    %-46s rank %2d  %-7s' % (name[:46], u['score'], u['coverage']))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
