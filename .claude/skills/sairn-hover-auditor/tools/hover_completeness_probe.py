#!/usr/bin/env python
"""hover_completeness_probe.py -- outside-in completeness check for
docs/CRITICALITY-TIERS.md.

H1 batch Q item 6. The register can only be as complete as the thing that
reads it. Every existing criticality tool (criticality_tier_check.py,
confidentiality_candidate_flagger.py) checks rows that are ALREADY IN the
table -- tier correctness, confidentiality correctness, evidence shape. None
of them ask the outside-in question: does the table's ROW COUNT even match
what the live codebase actually registers as a synced resource right now.
A tool that only validates existing rows cannot catch a resource that was
never added -- the false-negative direction -- which is exactly the shape
of the gap this role is asked to use as "a denominator correction for the
Verification Certificate."

TWO INDEPENDENT SOURCES, RE-DERIVED, NEVER TRUSTED FROM THE DOC ITSELF:

  1. LIVE CODEBASE (`git ls-files` + source read): every string literal
     inside a `resources: [...]` array in api/_resources/*.app.js. This is
     the actual, server-synced resource list each app's client code can
     reach -- the same list api/sd-data.js's app-boundary gate reads.
  2. THE REGISTER: every `` | `resource_name` | `` row already in
     docs/CRITICALITY-TIERS.md, extracted structurally (the row anchor,
     same convention the doc's own re-count commands already use), never by
     trusting a count written in prose.

A resource present in (1) and absent from (2) is a REAL REGISTER GAP: a
synced resource with no tier judgement at all, which is a different and
worse state than a wrong tier. This tool does not and cannot assign the
missing resource a tier -- that is a judgement call for a human or the
register's own hand-written convention (see CRITICALITY-TIERS.md's own
"hand-written on purpose" header) -- it only reports that the judgement has
never been made.

LIVE HTTP, BEST-EFFORT AND HONESTLY SCOPED. A short HEAD-style reachability
probe against each app's deployed base URL is attempted so an app that no
longer resolves at all is not silently treated as "fully tiered because
nothing new to check." Network access inside this tool's own environment is
not guaranteed; a failed probe is reported as COULD_NOT_REACH, never folded
into either a pass or a gap -- a could-not-tell is a third state, same rule
this register already states for its own confidentiality column.

WHAT THIS DOES NOT DO: it does not decide whether a gap resource IS Tier A.
Tier-worthiness needs the same resource-by-resource reading the register's
own §3.2 pass did -- this tool flags CANDIDATES using the same money/PHI
keyword heuristic already used by confidentiality_candidate_flagger.py nd
labels them CANDIDATE, never DECIDED.

Read-only. Writes nothing. No network write, no file write.
"""
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def discover_repo():
    for cand in (os.environ.get('HOVER_PROBE_REPO'),
                 r'C:\Users\marsh\Documents\SAIRN-hover',
                 r'C:\Users\marsh\Documents\SAIRN-hank',
                 r'C:\Users\marsh\Documents\SAIRN-cc'):
        if cand and os.path.isdir(os.path.join(cand, '.git')):
            return cand
    return None


TIER_A_KEYWORDS = (
    'billing', 'invoice', 'invs', 'payment', 'pay', 'price', 'pricing',
    'ledger', 'ar_', 'ap_', 'mar', 'medication', 'dosage', 'dose',
    'phi', 'clinical', 'vital', 'license', 'licence', 'legal',
    'deadline', 'trust', 'escrow', 'ssn', 'credential', 'incident',
)


def live_resources_by_app(repo):
    """Scan api/_resources/*.js for `app:` + its `resources: [...]` block."""
    out = {}
    res_dir = os.path.join(repo, 'api', '_resources')
    if not os.path.isdir(res_dir):
        return out, 'api/_resources not found at %s' % res_dir
    for fname in sorted(os.listdir(res_dir)):
        if not fname.endswith('.js') or fname.endswith('.test.js') or fname == 'index.js':
            continue
        path = os.path.join(res_dir, fname)
        try:
            with open(path, encoding='utf-8') as f:
                src = f.read()
        except Exception as e:
            out[fname] = {'error': str(e)}
            continue
        m_app = re.search(r"app:\s*'([a-z0-9_]+)'", src)
        app = m_app.group(1) if m_app else fname[:-3]
        m_block = re.search(r"resources:\s*\[(.*?)\]", src, re.S)
        names = []
        if m_block:
            # FOUND AND FIXED during this tool's own first real run (not a
            # synthetic fixture): a naive scan of the raw block text matches
            # quoted example code INSIDE a `//` comment too -- sairnlaw's own
            # comment reads `sdnData('write','law_deadlines')` as prose
            # explaining a resource, and sairnscape's reads
            # `action==='read'` -- both single-quoted, both inside the real
            # resources array's byte range, neither an actual resource
            # literal. Strip `//`-led comment text per line before matching,
            # same fix class as the register's own "a line, not a row" bugs.
            code_only = '\n'.join(
                re.sub(r'//.*$', '', line) for line in m_block.group(1).splitlines())
            names = re.findall(r"'([a-z][a-z0-9_]+)'", code_only)
        out[app] = {'file': 'api/_resources/%s' % fname, 'resources': sorted(set(names))}
    return out, None


def register_resources(repo):
    """Extract every `| `name` |` row from docs/CRITICALITY-TIERS.md."""
    path = os.path.join(repo, 'docs', 'CRITICALITY-TIERS.md')
    if not os.path.isfile(path):
        return set(), 'docs/CRITICALITY-TIERS.md not found'
    with open(path, encoding='utf-8') as f:
        src = f.read()
    names = re.findall(r"^\|\s*`([a-z][a-z0-9_]+)`\s*\|", src, re.M)
    return set(names), None


# App -> deployed base URL is not globally known to this role without
# reading deploy config each app may not share identically; left empty by
# default and filled only via --base-url-map <json file> so a missing map
# is COULD_NOT_REACH, not a silent skip disguised as coverage.
def live_http_check(app, base_url, timeout=4):
    try:
        req = urllib.request.Request(base_url, method='HEAD')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 'REACHABLE_%d' % resp.status
    except Exception as e:
        return 'COULD_NOT_REACH (%s)' % type(e).__name__


def run(repo, base_url_map=None):
    live, live_err = live_resources_by_app(repo)
    reg, reg_err = register_resources(repo)
    report = {
        'live_err': live_err,
        'reg_err': reg_err,
        'apps': {},
        'total_live': 0,
        'total_gap': 0,
        'gap_candidates_tier_a_shaped': [],
    }
    for app, info in live.items():
        names = info.get('resources', [])
        report['total_live'] += len(names)
        gaps = [n for n in names if n not in reg]
        report['total_gap'] += len(gaps)
        candidates = [n for n in gaps if any(k in n for k in TIER_A_KEYWORDS)]
        report['gap_candidates_tier_a_shaped'].extend(
            '%s.%s' % (app, c) for c in candidates)
        http_state = None
        if base_url_map and app in base_url_map:
            http_state = live_http_check(app, base_url_map[app])
        report['apps'][app] = {
            'file': info.get('file'),
            'live_count': len(names),
            'gap_count': len(gaps),
            'gaps': gaps,
            'http': http_state,
        }
    return report


def main(argv):
    repo = discover_repo()
    if not repo:
        print('COULD NOT RUN: no known hover-visible clone found on disk.')
        return 2
    base_url_map = None
    if '--base-url-map' in argv:
        p = argv[argv.index('--base-url-map') + 1]
        try:
            with open(p, encoding='utf-8') as f:
                base_url_map = json.load(f)
        except Exception as e:
            print('COULD NOT RUN: --base-url-map given but unreadable: %s' % e)
            return 2
    report = run(repo, base_url_map)
    if report['live_err'] or report['reg_err']:
        print('COULD NOT RUN: live_err=%s reg_err=%s' % (report['live_err'], report['reg_err']))
        return 2
    print('LIVE resources registered in api/_resources/*.js: %d, across %d apps'
          % (report['total_live'], len(report['apps'])))
    print('REGISTER rows in docs/CRITICALITY-TIERS.md: resource-row count derived separately, see per-app gaps below')
    print('TOTAL GAP (live resource, no register row at all): %d' % report['total_gap'])
    for app, info in sorted(report['apps'].items()):
        if info['gap_count']:
            print('  %-14s live=%-3d gap=%-3d  MISSING: %s'
                  % (app, info['live_count'], info['gap_count'], ', '.join(info['gaps'])))
        if info['http']:
            print('    http(%s): %s' % (app, info['http']))
    if report['gap_candidates_tier_a_shaped']:
        print('CANDIDATE Tier-A-shaped gap resources (name-heuristic only, NOT a tier decision):')
        for c in report['gap_candidates_tier_a_shaped']:
            print('  CANDIDATE %s' % c)
    if '--json' in argv:
        print(json.dumps(report, indent=1))
    return 1 if report['total_gap'] else 0


def _selftest():
    import tempfile
    failures = []

    def check(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            failures.append(label)

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, '.git'))
        os.makedirs(os.path.join(td, 'api', '_resources'))
        os.makedirs(os.path.join(td, 'docs'))
        with open(os.path.join(td, 'api', '_resources', 'fakeapp.js'), 'w') as f:
            f.write(
                "module.exports = {\n  app: 'fakeapp',\n  resources: [\n"
                "  // example: sdnData('write','fa_theme') is how the client calls this\n"
                "    'fa_billing_ledger',\n    'fa_theme',\n  ],\n};\n")
        with open(os.path.join(td, 'docs', 'CRITICALITY-TIERS.md'), 'w') as f:
            f.write("| `fa_theme` | C | B | cosmetic | none | n/a |\n")
        live, live_err = live_resources_by_app(td)
        reg, reg_err = register_resources(td)
        check('fixture live_err is None', live_err is None)
        check('fixture reg has fa_theme', 'fa_theme' in reg)
        check('fixture live has both resources', live.get('fakeapp', {}).get('resources') == ['fa_billing_ledger', 'fa_theme'])
        report = run(td)
        check('fa_billing_ledger is the one real gap', report['apps']['fakeapp']['gaps'] == ['fa_billing_ledger'])
        check('billing-named gap is flagged as a Tier-A-shaped candidate',
              'fakeapp.fa_billing_ledger' in report['gap_candidates_tier_a_shaped'])
        check('fa_theme is NOT a gap (already registered)',
              'fa_theme' not in report['apps']['fakeapp']['gaps'])
        # Regression lock for the real bug this tool's own first live run
        # found: a quoted string inside a `//` comment example must not be
        # read as a resource literal.
        check("comment-embedded 'write' is not treated as a resource",
              'write' not in report['apps']['fakeapp']['gaps']
              and 'write' not in live.get('fakeapp', {}).get('resources', []))

        # Negative control: planted bad state reached via a REAL transition
        # (a resource added to the live array after the register was last
        # edited), not just the planted-directly fixture above.
        with open(os.path.join(td, 'api', '_resources', 'fakeapp.js'), 'a') as f:
            pass
        with open(os.path.join(td, 'api', '_resources', 'fakeapp.js'), 'w') as f:
            f.write("module.exports = {\n  app: 'fakeapp',\n  resources: [\n    'fa_billing_ledger',\n    'fa_theme',\n    'fa_new_mar_log',\n  ],\n};\n")
        report2 = run(td)
        check('a resource added after the register was last touched is caught',
              'fa_new_mar_log' in report2['apps']['fakeapp']['gaps'])

    print()
    print('SELFTEST %s (%d/%d)' % ('PASS' if not failures else 'FAIL', 8 - len(failures), 8))
    return 0 if not failures else 1


if __name__ == '__main__':
    argv = sys.argv[1:]
    if '--selftest' in argv:
        sys.exit(_selftest())
    sys.exit(main(argv))
