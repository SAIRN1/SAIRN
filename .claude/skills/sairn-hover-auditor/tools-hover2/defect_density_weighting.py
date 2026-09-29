#!/usr/bin/env python
"""defect_density_weighting.py (hover2's own independent build, 2026-09-27)
-- empirically-derived, real-finding-history rotation weighting, closing the
capability gap this role's own self-audit named (seq 252): the static
SENSITIVITY_RE substring heuristic hover_cold_scan_pool.py used until now
does not learn from where real findings have actually landed.

SAME COORDINATOR-DIRECTED POLICY AS SKILL.md'S ROTATION SECTION DESCRIBES
FOR H1'S TOOL (fourth rotation axis, 2026-09-16; combined draw score,
2026-09-25/27) -- EMPIRICAL, DIFFERENT CODE. Never copied from H1's source
(never read it, never had access to it); built from the policy's own stated
CONTRACT the way hover_editor_review.py was built from a validated
contract, not a pasted implementation. One deliberate attribution
divergence, named because it matters: H1's tool resolves a finding's files
via git commit-sha diff-tree, crediting every file a commit touched. This
tool instead reads the RESOURCE NAME(S) directly out of the finding's own
structured `target` field -- hover2's log already carries that field on
every entry, and it names what a finding is actually ABOUT rather than
everything a commit happened to touch (H1's own docstring discloses the
noise this avoids: "a regenerated MASTER-PLAN.md alongside a real fix"
gets over-credited by sha-based attribution; target-based attribution does
not have that failure mode, at the cost of depending on hover2's own
target-field discipline being followed).

ATTRIBUTION, precisely. A finding's `target` field is comma-split into
tokens. Each token is looked up against the resource->app map derived from
api/_resources/*.js (every app's own registry file, GENERATED lookup never
a hand map -- same "app-map lesson" SKILL.md already names). A token that
resolves is credited to that app once per finding (a finding naming two
resources in the same app is not double-counted for that app). A token
that resolves to NO app (a commit sha, an agent name like 'hank', the
literal 'self') is UNMAPPED and credited to nothing -- it must sink, never
inflate any app's score. type == 'check' entries NEVER count (Safe
Harbor: a thoroughly-verified-clean file must not rank as though findings
happened there).

METRIC: density(app) = real findings attributed to app / resources
registered for that app in api/_resources/<app>.js. A ratio, not a raw
count, so a large app with one finding does not outrank a small app whose
one finding is a larger fraction of its own surface -- and named as MY OWN
metric, not claimed identical to H1's "module_density", since the two
tools derive it by different paths and comparing the numbers across
instances would be comparing different things wearing the same name.

FAIL-CLOSED, both directions (PR SS1.11): log unreadable/empty ->
COULD-NOT-RUN (exit 2). Zero apps derivable from api/_resources/*.js ->
COULD-NOT-RUN -- a missing instrument is never scored as all-zero risk.

BLIND LOCK (discipline 1): 7 synthetic fixtures classify first, in
isolation, every invocation; any miss refuses the real run.

Run:
  python defect_density_weighting.py [--repo PATH] [--json]
  python defect_density_weighting.py --selftest
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, 'hover-audit-log.jsonl')
DEFAULT_REPO = 'C:/Users/marsh/Documents/SAIRN-hover2'
RESOURCES_SKIP = {'index.js'}
APP_RE = re.compile(r"app:\s*'([^']+)'")
RESOURCE_TOKEN_RE = re.compile(r"'([a-z][a-z0-9_]*)'")


def read_entries(path):
    try:
        out = []
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out, None
    except (OSError, ValueError) as e:
        return None, str(e)


LINE_COMMENT_RE = re.compile(r"//.*")


def _strip_line_comments(text):
    """FOUND ON THIS TOOL'S OWN FIRST REAL RUN, not assumed safe: a bare
    non-greedy `\\[(.*?)\\]` match stops at the FIRST ']' in the file,
    including one written in PROSE inside a // comment ('a [resource,
    storage-key] PAIR list', api/_resources/sairnmechanical.js:59) that
    sits before the array's real close -- silently truncating the resource
    list to whatever came before that comment (confirmed: mech_docs and
    mech_takeoffs, declared AFTER the comment, were dropped; only 3 of 5
    real resources survived). Stripping '//' to end-of-line before parsing
    removes the false bracket. Safe for this specific, checked corpus: none
    of these registry files' comments or resource names contain '//' as
    literal content (verified: no 'http://' or similar appears in any
    api/_resources/*.js resources array or its surrounding comments)."""
    return '\n'.join(LINE_COMMENT_RE.sub('', ln) for ln in text.split('\n'))


CONFLICT_MARKER_RE = re.compile(r'^(<{7}|={7}|>{7})', re.M)
CONFLICT_SENTINEL = '__UNRESOLVED_MERGE_CONFLICT__'


def parse_resource_registry(text):
    """-> (app_name, [resource,...]) or (None, None) if the shape isn't
    recognised. -> (CONFLICT_SENTINEL, None) if the text carries unresolved
    git conflict markers (the REALISTIC bad state a botched rebase leaves,
    not an arbitrary injected one -- checked FIRST, before any other
    parsing, because a conflicted file can otherwise still coincidentally
    match app:/resources: on one side of the conflict and get silently,
    WRONGLY parsed: confirmed by driving a real conflict-shaped fixture
    through this function before this check existed -- it returned
    resources from BOTH sides of the conflict, duplicated, with no signal
    anything was wrong. Regex-based on purpose, own pattern, not a
    require() of the real JS module (this tool has no JS runtime and
    should not need one for a static list of quoted strings)."""
    if CONFLICT_MARKER_RE.search(text):
        return CONFLICT_SENTINEL, None
    text = _strip_line_comments(text)
    am = APP_RE.search(text)
    if not am:
        return None, None
    rm = re.search(r"resources:\s*\[(.*?)\]", text, re.S)
    if not rm:
        return None, None
    resources = RESOURCE_TOKEN_RE.findall(rm.group(1))
    return am.group(1), resources


def load_app_registry(repo, resources_dir='api/_resources'):
    """-> ({resource: app}, {app: resource_count}, err). err is set (and the
    two dicts empty) when NOTHING could be derived at all, OR when ANY
    registry file carries unresolved conflict markers -- a corrupted file
    silently excluded would under-count exactly that app's real resource
    total and skew every OTHER app's ratio unfairly relative to it, which
    is a different and worse failure than 'missing = zero risk'; this
    fails the WHOLE call closed instead, naming the file."""
    d = os.path.join(repo, resources_dir)
    try:
        files = sorted(f for f in os.listdir(d)
                       if f.endswith('.js') and f not in RESOURCES_SKIP
                       and not f.endswith('.test.js'))
    except OSError as e:
        return {}, {}, str(e)
    resource_to_app = {}
    app_resource_count = {}
    for fn in files:
        try:
            with open(os.path.join(d, fn), encoding='utf-8', errors='replace') as f:
                text = f.read()
        except OSError:
            continue
        app, resources = parse_resource_registry(text)
        if app == CONFLICT_SENTINEL:
            return {}, {}, ('%s carries unresolved git conflict markers -- '
                            'refusing to parse a corrupted registry rather '
                            'than silently under-counting or double-counting '
                            'its app' % os.path.join(d, fn))
        if not app:
            continue
        app_resource_count[app] = len(resources)
        for r in resources:
            resource_to_app[r] = app
    if not app_resource_count:
        return {}, {}, 'zero apps derived from %s -- registry files missing or unparseable' % d
    return resource_to_app, app_resource_count, None


def density(entries, resource_to_app, app_resource_count):
    """Pure core. -> {'ranking': [(app, density, finding_count), ...] desc,
    'unmapped_findings': n, 'total_findings': n}."""
    finding_count = {}
    unmapped = 0
    total = 0
    for e in entries:
        if e.get('type') != 'finding':
            continue
        total += 1
        target = e.get('target')
        if not isinstance(target, str):
            unmapped += 1
            continue
        apps_hit = set()
        for tok in (p.strip() for p in target.split(',')):
            app = resource_to_app.get(tok)
            if app:
                apps_hit.add(app)
        if not apps_hit:
            unmapped += 1
            continue
        for app in apps_hit:
            finding_count[app] = finding_count.get(app, 0) + 1
    ranking = []
    for app, n_resources in app_resource_count.items():
        n_findings = finding_count.get(app, 0)
        d = (n_findings / n_resources) if n_resources else 0.0
        ranking.append((app, d, n_findings))
    ranking.sort(key=lambda t: (-t[1], t[0]))
    return {'ranking': ranking, 'unmapped_findings': unmapped,
            'total_findings': total}


def _selftest():
    fails = []

    def chk(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            fails.append(label)

    mk = lambda typ, target: {'type': typ, 'target': target}

    # REALISTIC-TRANSITION REGRESSION, per direct instruction (2026-09-27):
    # a bad state reached via a transition a real session would produce --
    # a botched rebase leaving unresolved conflict markers in a registry
    # file -- not one injected directly as already-final garbage. FOUND FOR
    # REAL by driving this before the CONFLICT_MARKER_RE check existed: the
    # file below parsed as if clean, returning ['fk_one','fk_two','fk_one',
    # 'fk_three'] -- both sides of the conflict, duplicated, no signal
    # anything was wrong.
    conflicted_registry = (
        "module.exports = {\n"
        "  app: 'fakeapp',\n"
        "<<<<<<< HEAD\n"
        "  resources: [\n"
        "    'fk_one',\n"
        "    'fk_two',\n"
        "=======\n"
        "  resources: [\n"
        "    'fk_one',\n"
        "    'fk_three',\n"
        ">>>>>>> branch\n"
        "  ],\n"
        "};\n")
    app, resources = parse_resource_registry(conflicted_registry)
    chk('a file with unresolved git conflict markers is flagged, never '
        'silently parsed as a clean registry',
        app == CONFLICT_SENTINEL and resources is None)

    # REGRESSION for this build's own first real-run defect: a bracket
    # written in PROSE inside a // comment, before the array's real close,
    # must not truncate the resource list.
    fake_registry = (
        "module.exports = {\n"
        "  app: 'fakeapp',\n"
        "  resources: [\n"
        "    'fk_one',\n"
        "    // this comment describes a [pair] shape, a false bracket\n"
        "    'fk_two',\n"
        "    'fk_three',\n"
        "  ],\n"
        "};\n")
    app, resources = parse_resource_registry(fake_registry)
    chk("a bracket inside a // comment does not truncate the resources array",
        app == 'fakeapp' and resources == ['fk_one', 'fk_two', 'fk_three'])

    # basic ranking: app A (1 finding / 2 resources = .5) outranks
    # app B (1 finding / 10 resources = .1)
    entries = [mk('finding', 'res_a1'), mk('finding', 'res_b1')]
    r2a = {'res_a1': 'appA', 'res_b1': 'appB'}
    counts = {'appA': 2, 'appB': 10}
    r = density(entries, r2a, counts)
    chk('higher finding-per-resource ratio ranks first',
        r['ranking'][0][0] == 'appA' and abs(r['ranking'][0][1] - 0.5) < 1e-9
        and abs(r['ranking'][1][1] - 0.1) < 1e-9)

    # Safe Harbor: type=check never counts, even naming a real resource
    entries = [mk('check', 'res_a1'), mk('check', 'res_a1'), mk('check', 'res_a1')]
    r = density(entries, r2a, counts)
    chk("type='check' entries never count toward density (Safe Harbor)",
        r['ranking'][0][1] == 0.0 and r['ranking'][1][1] == 0.0
        and r['total_findings'] == 0)

    # unmapped token sinks, never inflates any app, never crashes
    entries = [mk('finding', 'not_a_real_resource'), mk('finding', 'hank'),
              mk('finding', 'res_a1')]
    r = density(entries, r2a, counts)
    chk('unmapped tokens sink to zero and do not inflate any app',
        r['unmapped_findings'] == 2 and r['ranking'][0][0] == 'appA'
        and r['ranking'][0][2] == 1)

    # multi-resource target crossing two apps credits both once each
    entries = [mk('finding', 'res_a1,res_b1')]
    r = density(entries, r2a, counts)
    by_app = {a: n for a, _d, n in r['ranking']}
    chk('a finding naming resources in two apps credits both, once each',
        by_app['appA'] == 1 and by_app['appB'] == 1)

    # a finding naming TWO resources in the SAME app is not double-counted
    r2b = dict(r2a); r2b['res_a2'] = 'appA'
    entries = [mk('finding', 'res_a1,res_a2')]
    r = density(entries, r2b, counts)
    by_app = {a: n for a, _d, n in r['ranking']}
    chk('two resources in the same app, one finding, counts once',
        by_app['appA'] == 1)

    # apps with zero registered resources never divide by zero
    counts0 = dict(counts); counts0['appC'] = 0
    entries = [mk('finding', 'res_a1')]
    r = density(entries, r2a, counts0)
    by_density = {a: d for a, d, _n in r['ranking']}
    chk('an app with zero registered resources scores 0.0, never crashes',
        by_density.get('appC') == 0.0)

    # load_app_registry() fails the WHOLE call closed on a real conflicted
    # file, not just that one app -- driven against real files on disk.
    import tempfile
    tmpdir = tempfile.mkdtemp()
    resdir = os.path.join(tmpdir, 'api', '_resources')
    os.makedirs(resdir)
    with open(os.path.join(resdir, 'good.js'), 'w', encoding='utf-8') as f:
        f.write("module.exports = {\n  app: 'goodapp',\n  resources: [\n    'g_one',\n  ],\n};\n")
    with open(os.path.join(resdir, 'bad.js'), 'w', encoding='utf-8') as f:
        f.write(conflicted_registry)
    r2app, r2cnt, r2err = load_app_registry(tmpdir)
    chk('load_app_registry() refuses the WHOLE call when ANY registry file '
        'in the directory has unresolved conflict markers, not just that '
        "one app's count",
        r2app == {} and r2cnt == {} and r2err and 'conflict' in r2err.lower())

    print()
    if fails:
        print('%d SELFTEST FAILURE(S): %s' % (len(fails), fails))
        return 1
    print('ALL SELFTEST CASES PASS')
    return 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=DEFAULT_REPO)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)

    if not _selftest_quiet_ok():
        print('REFUSED: fixture lock failed -- criteria judged nothing '
              'real (exit 2).')
        return 2
    if a.selftest:
        return _selftest()

    entries, err = read_entries(LOG)
    if entries is None or not entries:
        print('COULD NOT RUN: log unreadable or empty (%s). (exit 2)' % err)
        return 2
    resource_to_app, app_resource_count, rerr = load_app_registry(a.repo)
    if rerr:
        print('COULD NOT RUN: %s. A missing instrument is never scored as '
              'all-zero risk. (exit 2)' % rerr)
        return 2

    r = density(entries, resource_to_app, app_resource_count)
    if a.json:
        print(json.dumps({app: d for app, d, _n in r['ranking']},
                         sort_keys=True))
        return 0
    print('DEFECT DENSITY (real findings only, Safe Harbor -- never a clean '
          'check) -- %d real finding(s), %d unmapped (no resolvable app '
          'in target, sink to nothing):'
          % (r['total_findings'], r['unmapped_findings']))
    for app, d, n in r['ranking']:
        print('  %-16s density %.3f  (%d finding(s) / %d resources)'
              % (app, d, n, app_resource_count[app]))
    return 0


def _selftest_quiet_ok():
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = _selftest()
    return rc == 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
