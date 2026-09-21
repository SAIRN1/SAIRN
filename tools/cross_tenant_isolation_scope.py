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

CRITERIA_VERSION = '2026-09-21.4'

# The one known-good instance, named rather than described, so --check can
# assert the grader still recognises it. A grader that stops recognising its
# own reference case is a grader whose criteria have drifted, and nothing else
# would announce that.
REFERENCE_TEST = 'api/sairndental/complaint-respond.test.js'
# ── THE SECOND REFERENCE, AND ADDING IT IS THE FIX FOR HOW THE FIRST
# ── INVERSION SHIPPED ────────────────────────────────────────────────────────
# The self-check was anchored on the file the criteria were DERIVED from, which
# is right, and on nothing else. The commit that introduced
# api/sd-data-cross-tenant-isolation.test.js named it the reference
# implementation in its own header and did not add it here -- so the guard went
# on reporting "the criteria still match what they were derived from" while the
# artefact they exist to measure graded WEAK. A guard anchored on one file
# checks one file. Every reference goes in this list.
REFERENCE_TESTS = (
    'api/sairndental/complaint-respond.test.js',   # SHAPE I -- id read, 404
    'api/sd-data-cross-tenant-isolation.test.js',  # SHAPE L + W -- list read, write
)


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
# ── "A REFUSAL" HAS THREE SPELLINGS AND THE FIRST VERSION KNEW TWO ───────────
# Found by CC's independent review of the reference implementation, and it is
# the SECOND inversion in this grader, in the same session, in the opposite
# direction to the first:
#
#   api/sd-data-cross-tenant-isolation.test.js -- the reference implementation,
#   whose own header says "the refusal is not a status code, it is an ABSENCE:
#   200 OK carrying only tenant A's rows. Assert the CONTENT of the array,
#   never its length alone" -- graded WEAK, because _REFUSAL could see a status
#   code and a bare length check and had NO EXPRESSION AT ALL for a content
#   assertion. So a transplant doing the thing the reference calls wrong scored
#   GENUINE, and the reference doing the thing it calls right scored WEAK. Every
#   one of the 48 planned units, done correctly, would have landed as WEAK and
#   the plan's own progress measure would have read zero while the work was
#   being done properly.
#
# THREE SHAPES, REPORTED SEPARATELY RATHER THAN MERGED, because which one a
# test uses is information a reader wants:
#   STATUS   -- a 4xx/5xx status or a named refusal code. The id-read shape.
#   CONTENT  -- an assertion about WHICH rows came back, or that a foreign
#               row/hash is absent or unchanged. The list-read shape, and the
#               only one that can catch a handler returning everybody's rows
#               with a 200.
#   LENGTH   -- `.length, 0`. A real refusal assertion for an id read and a
#               WEAK one for a list read, and nothing here can tell which. Kept
#               because removing it would lose real coverage, but NAMED in the
#               output so "length only" is visible rather than silently equal
#               to the other two.
_REFUSAL_STATUS = re.compile(
    r"""statusCode,\s*(40[0-9]|41[0-9]|5\d\d)|"""
    r"""code,\s*['"`](NOT_FOUND|FORBIDDEN|UNAUTHORIZED|DENIED)""")
_REFUSAL_LENGTH = re.compile(r"""\.length,\s*0\b""")
_REFUSAL_CONTENT = re.compile(
    # deepStrictEqual/deepEqual over a projection -- "exactly A's rows"
    r"""deep(?:Strict)?Equal\(|"""
    # an explicit assertion that the other tenant is absent or unchanged
    r"""assert\.ok\(\s*!\s*\w+[.\[]|"""
    r"""(?:notStrictEqual|strictEqual)\(\s*\w+(?:\.\w+|\[[^\]]*\])*\s*,\s*(?:undefined|null)\)|"""
    r"""\.(?:some|find|filter|includes|indexOf)\([^)]*\)[^;\n]{0,60}(?:false|=== *-1|, *0\))""")


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
    # 3. Is a refusal asserted, and in which of the three spellings?
    kinds = []
    if _REFUSAL_STATUS.search(body):
        kinds.append('status')
    if _REFUSAL_CONTENT.search(body):
        kinds.append('content')
    if _REFUSAL_LENGTH.search(body):
        kinds.append('length')
    refuses = bool(kinds)

    if filters_url and two_tenants and refuses:
        return 'GENUINE', ('url-filtering mock + %d distinct hashes + refusal asserted (%s)'
                           % (len(hashes), '+'.join(kinds)))
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


# ── A FILE WHOSE SUBJECT IS THIS GRADER IS NOT PLATFORM COVERAGE ────────────
# tests/run_cross_tenant_scope_probe.py contains seven FIXTURE bodies written
# to grade GENUINE, and those fixtures name real resources. So the grader's own
# negative control graded GENUINE and credited `law_trusttx` with a genuine
# cross-tenant isolation test -- on the strength of a string inside a fixture.
# Found by CC's review. Two of the three reported GENUINEs were one real file
# and this; the tool was counting itself.
#
# NAMED AND DISCLOSED rather than silently dropped, because an exclusion nobody
# can see is how a coverage number starts lying in the other direction.
SELF_EXCLUDED = (
    'tests/run_cross_tenant_scope_probe.py',
    # Fourth's review of this grader. Same reason: its subject IS this tool, so
    # the prose in it discusses declarations and resource names, and the parser
    # read the word `declaration` out of a sentence as a resource. A file whose
    # subject is the measurer is not a measurement.
    'tests/cross_tenant_scope_grader_review_probe.py',
)

# ── WHICH RESOURCES A GENUINE FILE COVERS IS DECLARED, NOT GUESSED ──────────
# A file-level grade is not a per-resource grade, and this tool REPORTS and
# PLANS in resources. api/dnt-bi.test.js earns GENUINE on an arm about
# sairndental_bi_tokens and was crediting dnt_charges and dnt_patients purely
# because their names appear somewhere in it (CC's finding 4).
#
# TWO HEURISTICS WERE TRIED AND BOTH INVERTED, WHICH IS WHY THIS IS A
# DECLARATION INSTEAD. "The name appears within N lines of a license_hash
# mention" credited dnt_charges off an arm about UNREADABLE datasets.
# Tightening the anchor to "a SECOND tenant is in play nearby" then credited
# NOTHING from api/sd-data-cross-tenant-isolation.test.js -- because a
# well-structured parameterised test declares its resources in a table at the
# top and drives them in loops below, so the shared mock is nowhere near the
# names. That is the THIRD time in this tool that a heuristic has scored the
# better-structured artefact worse, and the lesson is not "tune the window".
# Static analysis cannot attribute a parameterised arm to its resources, and a
# coverage number built on a guess about that is not auditable.
#
# So a test file SAYS what its cross-tenant arms cover:
#
#     // CROSS-TENANT-ISOLATION: law_invoices, law_opaccounts, law_barcerts
#
# Same shape as the MUTATIONS blocks and GUARD_TESTS entries this platform
# already uses. The declaration is CROSS-CHECKED, never trusted alone: a file
# that declares coverage and does NOT grade GENUINE credits nothing and is
# reported, and a file that grades GENUINE with no declaration credits nothing
# and is ALSO reported -- an undeclared genuine test is real coverage the
# number cannot see, which is a gap worth naming rather than silently
# absorbing.
#
# `none` IS A DECLARATION, NOT AN ABSENCE, and it needs a reason. A genuine
# cross-tenant test can be about a resource that is not Tier A at all --
# complaint-respond covers dnt_complaints, dnt-bi's arm covers
# sairndental_bi_tokens -- and those files credit nothing here and are CORRECT
# to. Without a way to say so they would sit in the undeclared list forever,
# and a disclosure list that never empties is a disclosure list nobody reads,
# which is the failure this platform keeps recording. Same decision the defect
# register made for `--rule not-citable`: an escape hatch, with a sentence.
_DECLARES = re.compile(r'CROSS-TENANT-ISOLATION\s*:\s*([a-z0-9_, \t]+)')
_DECLARES_NONE = re.compile(r'CROSS-TENANT-ISOLATION\s*:\s*none\s*\(([^)\n]{10,})\)', re.I)


# ── WHAT A SUITE ACTUALLY DRIVES, READ FROM ITS OWN TABLE ───────────────────
# Fourth's review of the declaration mechanism, and it is finding 4 surviving in
# a new form. The three conditions for credit were: the name appears in the file
# as a whole word, the file grades GENUINE, and the name is in the declaration.
# CONDITION 1 IS SATISFIED BY THE DECLARATION ITSELF, because the declaration is
# a line in the file -- so the word-boundary check added to close finding 4 was
# a restatement of condition 3, not independent corroboration of it. Driven by
# fourth and reproduced here: adding `sv_controlled` to the reference file's
# declaration line and NOTHING ELSE takes GENUINE from 3 to 4, with no test
# behind it, and every arm of the control stays green.
#
# The declaration replaced a GUESSED distribution of a file-level grade with an
# ASSERTED one. That is better -- a person can be held to a declaration and a
# regex cannot -- but it is still not a CHECK, and the number the whole plan is
# read from moved on one comment line.
#
# SO THE DECLARATION IS NOW CHECKED AGAINST THE SUITE'S OWN DRIVING TABLE. The
# structure that defeats every proximity heuristic -- a table of resources plus
# a loop that iterates it -- is exactly the structure that makes the declaration
# verifiable, because the table is machine-readable and IS what the arms drive.
# A declared resource absent from it is credited to nothing and reported.
_TABLE = re.compile(
    r'^const\s+(?:[A-Z][A-Z0-9_]*)\s*=\s*\[(.*?)^\];', re.M | re.S)
# A row's FIRST string literal is the resource: ['law_invoices', 'invoice_id'],
# { map: ..., members: [['dnt_ar', 'ar_id'], ...] } -- both yield the name.
_ROW_NAME = re.compile(r"\[\s*'([a-z][a-z0-9_]*)'")


def driven_resources(body):
    """Resource names the file's own table(s) carry, or None when it has none.

    None and empty are different: a suite with no table cannot be cross-checked
    and says so, rather than having every declaration silently rejected.
    """
    found = set()
    tables = 0
    for m in _TABLE.finditer(body):
        rows = _ROW_NAME.findall(m.group(1))
        if rows:
            tables += 1
            found.update(rows)
    return found if tables else None


def declared_coverage(body):
    """(resources, none_reason). A `none` declaration returns an empty set and
    a reason; an absent declaration returns an empty set and None, and the two
    are not the same thing."""
    m = _DECLARES_NONE.search(body)
    if m:
        return set(), m.group(1).strip()
    out = set()
    for d in _DECLARES.finditer(body):
        # ── THE DECLARATION MAY WRAP, and the first version could not read a
        # wrapped one. A 46-resource declaration does not fit on one line, so
        # the dispatcher suite declared 46 and the tool read 4 -- an
        # UNDER-count, which is the safe direction and was still wrong.
        # Continuation lines are comment lines carrying nothing but resource
        # names and commas; the first line that is anything else ends it.
        text = d.group(1)
        rest_of = body[d.end():].split('\n')
        # the first fragment is the tail of the line the match ended on, which
        # is empty -- dropping it is what lets the loop see the NEXT line
        if rest_of and not rest_of[0].strip():
            rest_of = rest_of[1:]
        if text.rstrip().endswith(','):
            for line in rest_of:
                s = line.strip()
                if not s.startswith('//') and not s.startswith('#'):
                    break
                s = s.lstrip('/#').strip()
                if not s or not re.match(r'^[a-z0-9_]+(\s*,\s*[a-z0-9_]+)*,?$', s):
                    break
                text += ' ' + s
                if not s.rstrip().endswith(','):
                    break
        for part in text.replace('\t', ' ').split(','):
            part = part.strip()
            if part and part != 'none':
                out.add(part)
    return out, None


UNDECLARED = []


def tests_naming(names):
    """resource -> [(test file, grade, why)].

    ── THE FILE-LEVEL GRADE IS NOT A PER-RESOURCE GRADE, and conflating them
    was a false GENUINE on two Tier A resources. api/dnt-bi.test.js earns
    GENUINE at the file level -- it has a real cross-tenant arm about
    sairndental_bi_tokens -- and it was crediting dnt_charges and dnt_patients
    purely because their names appear somewhere in it. The scanner REPORTS and
    PLANS in resources, so the unit it uses has to be the unit it checks.

    A GENUINE file now credits a resource only when the resource is NAMED NEAR
    a tenant-isolation signal. A resource named far from every such signal is
    downgraded to WEAK for that resource, with the reason said out loud -- not
    dropped, because the file may well be the right place to add the arm.
    """
    hits = {n: [] for n in names}
    del UNDECLARED[:]
    for rel in all_files(('.js', '.py')):
        if not is_test(rel):
            continue
        if rel in SELF_EXCLUDED:
            continue
        try:
            body = read(rel)
        except CouldNotTell:
            continue
        g, why = grade(body)
        declared, none_reason = declared_coverage(body)
        if declared and g != 'GENUINE':
            UNDECLARED.append((rel, 'DECLARES coverage but grades ' + g, sorted(declared)))
        if g == 'GENUINE' and not declared and none_reason is None:
            UNDECLARED.append((rel, 'grades GENUINE but DECLARES nothing', []))
        # ── THE DECLARATION IS CHECKED AGAINST THE TABLE THE ARMS DRIVE ─────
        # A name in the declaration and nowhere else credits nothing. Reported
        # rather than dropped: a declaration that outruns the table is either a
        # test somebody meant to write or a claim somebody should withdraw, and
        # both need saying.
        driven = driven_resources(body)
        if declared and driven is not None:
            undriven = declared - driven
            if undriven:
                UNDECLARED.append((rel, 'DECLARES what its own table does not drive',
                                   sorted(undriven)))
                declared = declared & driven
        elif declared and driven is None:
            # No table to check against. NOT silently trusted and NOT silently
            # refused -- the third state, said out loud, because a suite written
            # without a table would otherwise lose every credit it has earned.
            UNDECLARED.append((rel, 'DECLARES coverage and carries no table to '
                               'cross-check it against -- credited on the '
                               'declaration alone', sorted(declared)))
        for n in names:
            # WORD BOUNDARIES, not `in`. `'invoices' in body` is true of any
            # file naming `law_invoices` or `sdn_invoices`, so the bare Tier A
            # resources `invoices` and `quotes` were credited by every file
            # mentioning a prefixed sibling -- a coverage claim manufactured by
            # a substring. Same trap the platform records for the `sd` vs `sd_`
            # storage prefix, in a different tool.
            if not re.search(r'(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])' % re.escape(n), body):
                continue
            if g == 'GENUINE' and n in declared:
                hits[n].append((rel, 'GENUINE', why + '; DECLARED'))
            elif g == 'GENUINE':
                hits[n].append((rel, 'WEAK',
                                'the FILE has a genuine cross-tenant arm but does not '
                                'DECLARE %s -- add it to the file\'s '
                                'CROSS-TENANT-ISOLATION: line if an arm really covers it'
                                % n))
            else:
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
    """EVERY reference case must still grade GENUINE, not just the first one.

    A criteria set that stops matching an instance it was derived FROM has
    drifted, and nothing else on this platform would announce that -- the
    eighth cross-domain discipline. Anchored on REFERENCE_TESTS rather than a
    single file because a guard anchored on one file checks one file: the
    reference implementation added on 2026-09-21 graded WEAK for a full
    session while this function reported the criteria as still matching.
    """
    bad = []
    for ref in REFERENCE_TESTS:
        g, why = grade(read(ref))
        if g != 'GENUINE':
            bad.append((ref, g, why))
    if bad:
        raise CouldNotTell(
            'THE GRADER NO LONGER RECOGNISES %d OF ITS %d REFERENCE CASES.\n%s\n'
            'The criteria were derived from these files. If one does not grade '
            'GENUINE, every other verdict in this run is untrustworthy and none '
            'of them are printed.'
            % (len(bad), len(REFERENCE_TESTS),
               '\n'.join('  %s graded %s (%s)' % b for b in bad)))
    return 'GENUINE'


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
    print('all %d reference cases grade GENUINE, so the criteria still match what '
          'they were derived from:' % len(REFERENCE_TESTS))
    for ref in REFERENCE_TESTS:
        print('  ' + ref)
    print('%d file(s) EXCLUDED as the grader\'s own subject, not platform coverage: %s'
          % (len(SELF_EXCLUDED), ', '.join(SELF_EXCLUDED)))
    print('')
    print('  Tier A resources        %3d' % len(rows))
    print('  GENUINE isolation test  %3d' % len(genuine))
    print('  WEAK -- looks like one  %3d   <- graded apart deliberately; see the header'
          % len(weak))
    print('  NONE                    %3d' % len(none))
    print('  serving code UNLOCATED  %3d   <- a THIRD state, in neither column above'
          % len(unlocated))
    if UNDECLARED:
        print('')
        print('  DISCLOSED -- %d file(s) whose declaration and grade disagree. Coverage'
              % len(UNDECLARED))
        print('  the number below CANNOT see, named rather than silently absorbed:')
        for rel, what, res in UNDECLARED:
            print('    %-50s %s%s' % (rel[:50], what,
                                      (' [' + ', '.join(res) + ']') if res else ''))
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
    print('')
    print('** THE BAND IS AN UNMEASURED JUDGEMENT. ** `rank` and `reach` are derived')
    print('from the tier register and the source; WHICH BAND a unit falls in is an')
    print('ordinal a person chose, and nothing measures whether it is the right one.')
    print('Labelled here the way this platform labels a rule citation `arguable`')
    print('rather than `clean`, so a reader does not take the whole table as measured.')

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
