#!/usr/bin/env python3
"""SAIRNlaw deadline-rule coverage gaps, per seeded jurisdiction.

    python tools/sairnlaw_deadline_coverage_gap.py            # the table, oldest gap first
    python tools/sairnlaw_deadline_coverage_gap.py --json
    python tools/sairnlaw_deadline_coverage_gap.py --fixtures # criteria lock only

Exit 0 every jurisdiction has an isolation test AND a mutation test; 1 at least
one gap; 2 COULD NOT RUN (no seed files, an unreadable seed, git unreadable).

WHAT COUNTS, so that the table cannot pass on a word match:
  JURISDICTION  every distinct `jurisdiction` value across
                sql/sairnlaw_deadline_seed_*.json (the seeds the loader reads).
  ISOLATION     a test file that (1) requires the real deadline-engine, (2)
                reads one of THIS jurisdiction's seed files BY NAME, and (3)
                either that seed holds no other jurisdiction or the test names
                the jurisdiction code as a quoted literal. A suite that walks
                every seed with readdirSync is CROSS-CUTTING. It is reported in
                its own column and is NOT isolation, because a rule that is
                wrong in a way every jurisdiction shares passes it.
  MUTATION      an isolation test that also carries a mutation, sabotage or
                ablation arm (MUTATION_RX), or a tests/*.py probe with a
                MUTATIONS list that names one of this jurisdiction's isolation
                tests or seed files. A test with no arm proving it can fail is
                a test nobody has seen fail.
  AGE           the date the jurisdiction's OLDEST seed file was first
                committed (git log --diff-filter=A). "Oldest-untested first"
                means the longest-standing rules with the gap come first.
"""
import glob
import json
import os
import re
import subprocess
import sys

CRITERIA_VERSION = '2026-10-23.1'
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_GLOB = 'sql/sairnlaw_deadline_seed_*.json'
TEST_GLOBS = ('api/_lib/deadline-*.test.js', 'api/*.test.js', 'tests/*.js')
PROBE_GLOB = 'tests/*.py'
MUTATION_RX = re.compile(r'MUTATION|\bmutant|\bmutat(?:e|ed|ion|ions)\b|sabotage|ablat|NEGATIVE CONTROL',
                         re.I)
ENGINE_RX = re.compile(r"require\([^)]*deadline-engine")


def seed_rows(path):
    d = json.load(open(path, encoding='utf-8'))
    rows = d if isinstance(d, list) else (d.get('rules') or d.get('rows') or [])
    if not isinstance(rows, list):
        raise ValueError('no row list in %s' % path)
    return [r for r in rows if isinstance(r, dict)]


def classify(code, seeds_of, seed_juris, tests, probes):
    """-> dict for one jurisdiction. Pure: every input is passed in.

    seeds_of[code] -> [seed basenames]; seed_juris[seed] -> {codes};
    tests -> {path: source}; probes -> {path: source}.
    """
    mine = seeds_of[code]
    iso, cross = [], []
    for p, src in tests.items():
        if not ENGINE_RX.search(src):
            continue
        if 'readdirSync' in src and not any(s in src for s in mine):
            cross.append(p)
            continue
        for s in mine:
            if s not in src:
                continue
            if len(seed_juris[s]) == 1 or re.search(r"['\"]%s['\"]" % re.escape(code), src):
                iso.append(p)
                break
    mut = [p for p in iso if MUTATION_RX.search(tests[p])]
    for p, src in probes.items():
        if 'MUTATIONS' not in src:
            continue
        names = [os.path.basename(t) for t in iso] + mine
        if any(n in src for n in names):
            mut.append(p)
    # DEDICATED vs INCIDENTAL. A NEIGHBOUR's suite that drives this
    # jurisdiction once as a contrast arm (West Virginia's suite computing one
    # Georgia deadline to show that the two differ) is real coverage of one
    # case. It is not a suite about this jurisdiction. "Dedicated" means the
    # test is named for one of this jurisdiction's own single-jurisdiction
    # seeds.
    alnum = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())          # noqa: E731
    stems = [alnum(s[len('sairnlaw_deadline_seed_'):-len('.json')]) for s in mine
             if len(seed_juris[s]) == 1]
    dedicated = [p for p in iso if any(st and st in alnum(os.path.basename(p)) for st in stems)]
    gap = []
    if not iso:
        gap.append('NO ISOLATION')
    elif not dedicated:
        gap.append('INCIDENTAL ONLY')
    if not mut:
        gap.append('NO MUTATION')
    return {'jurisdiction': code, 'seeds': mine, 'isolation': sorted(set(iso)),
            'dedicated': sorted(set(dedicated)),
            'mutation': sorted(set(mut)), 'cross_cutting': len(set(cross)), 'gap': gap}


FIXTURES = [
    ('a dedicated state test with a mutation arm closes both gaps',
     ('zz', {'zz': ['sairnlaw_deadline_seed_zzland.json']}, {'sairnlaw_deadline_seed_zzland.json': {'zz'}},
      {'api/_lib/deadline-zzland.test.js':
       "require('./deadline-engine.js'); read('sairnlaw_deadline_seed_zzland.json'); // MUTATION arm"}, {}), []),
    ("a NEIGHBOUR's suite driving it once is INCIDENTAL, not dedicated",
     ('zz', {'zz': ['sairnlaw_deadline_seed_zzland.json']}, {'sairnlaw_deadline_seed_zzland.json': {'zz'}},
      {'api/_lib/deadline-otherland.test.js':
       "require('./deadline-engine.js'); read('sairnlaw_deadline_seed_zzland.json')"}, {}),
     ['INCIDENTAL ONLY', 'NO MUTATION']),
    ('a test that only walks every seed with readdirSync is NOT isolation',
     ('zz', {'zz': ['s_zz.json']}, {'s_zz.json': {'zz'}},
      {'t.js': "require('./deadline-engine'); fs.readdirSync(SQL)"}, {}), ['NO ISOLATION', 'NO MUTATION']),
    ('a multi-state seed read WITHOUT naming the code is not isolation for that code',
     ('mi', {'mi': ['multi.json']}, {'multi.json': {'mi', 'pa'}},
      {'t.js': "require('./deadline-engine'); read('multi.json'); jurisdiction==='pa'"}, {}),
     ['NO ISOLATION', 'NO MUTATION']),
    ('...naming the code makes it isolation, but only INCIDENTAL without a test named for the state',
     ('mi', {'mi': ['multi.json']}, {'multi.json': {'mi', 'pa'}},
      {'t.js': "require('./deadline-engine'); read('multi.json'); jurisdiction==='mi'"}, {}),
     ['INCIDENTAL ONLY', 'NO MUTATION']),
    ('a test that never requires the engine does not count',
     ('zz', {'zz': ['s_zz.json']}, {'s_zz.json': {'zz'}}, {'t.js': "read('s_zz.json')"}, {}),
     ['NO ISOLATION', 'NO MUTATION']),
    ('a probe with MUTATIONS naming the isolation test closes the mutation gap',
     ('zz', {'zz': ['sairnlaw_deadline_seed_zz.json']}, {'sairnlaw_deadline_seed_zz.json': {'zz'}},
      {'api/_lib/deadline-zz.test.js': "require('./deadline-engine'); read('sairnlaw_deadline_seed_zz.json')"},
      {'tests/p.py': "MUTATIONS = [('deadline-zz.test.js', ...)]"}), []),
    ('the word "mutation" in a file with no isolation does not count as a mutation test',
     ('zz', {'zz': ['s_zz.json']}, {'s_zz.json': {'zz'}},
      {'t.js': "// MUTATION of something else"}, {}), ['NO ISOLATION', 'NO MUTATION']),
]


def run_fixtures():
    bad = []
    for why, args, want in FIXTURES:
        got = classify(*args)['gap']
        if got != want:
            bad.append('EXPECTED %r, got %r -- %s' % (want, got, why))
    return bad


def first_commit(path):
    r = subprocess.run(['git', 'log', '--diff-filter=A', '--follow', '--format=%cI', '--', path],
                       capture_output=True, text=True, cwd=REPO)
    if r.returncode != 0:
        raise RuntimeError('git log failed for %s: %s' % (path, r.stderr.strip()))
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    return lines[-1][:10] if lines else None


def main(argv):
    as_json = '--json' in argv
    bad = run_fixtures()
    if bad:
        print('CRITERIA LOCK FAILED -- nothing real was judged:')
        for b in bad:
            print('  ! ' + b)
        return 2
    if not as_json:
        print('SAIRNLAW DEADLINE COVERAGE GAP -- criteria lock %s: %d/%d fixtures classify correctly'
              % (CRITERIA_VERSION, len(FIXTURES), len(FIXTURES)))
    if '--fixtures' in argv:
        return 0
    seeds = sorted(glob.glob(os.path.join(REPO, SEED_GLOB)))
    if not seeds:
        print('COULD NOT RUN: no %s found.' % SEED_GLOB)
        return 2
    seeds_of, seed_juris, ages = {}, {}, {}
    try:
        for p in seeds:
            b = os.path.basename(p)
            codes = {r.get('jurisdiction') for r in seed_rows(p) if r.get('jurisdiction')}
            seed_juris[b] = codes
            ages[b] = first_commit(os.path.relpath(p, REPO).replace('\\', '/'))
            for c in codes:
                seeds_of.setdefault(c, []).append(b)
    except Exception as e:                                       # noqa: BLE001
        print('COULD NOT RUN: %s: %s' % (type(e).__name__, e))
        return 2
    tests = {}
    for g in TEST_GLOBS:
        for p in glob.glob(os.path.join(REPO, g)):
            rel = os.path.relpath(p, REPO).replace('\\', '/')
            tests[rel] = open(p, encoding='utf-8', errors='replace').read()
    probes = {os.path.relpath(p, REPO).replace('\\', '/'): open(p, encoding='utf-8', errors='replace').read()
              for p in glob.glob(os.path.join(REPO, PROBE_GLOB))}
    rows = []
    for code in sorted(seeds_of):
        row = classify(code, seeds_of, seed_juris, tests, probes)
        dated = [ages[s] for s in row['seeds'] if ages[s]]
        row['oldest_seed_commit'] = min(dated) if dated else None
        row['rules'] = sum(1 for s in row['seeds'] for r in seed_rows(os.path.join(REPO, 'sql', s))
                           if r.get('jurisdiction') == code)
        rows.append(row)
    gaps = [r for r in rows if r['gap']]
    gaps.sort(key=lambda r: (r['oldest_seed_commit'] or '9999', r['jurisdiction']))
    ok = [r for r in rows if not r['gap']]
    if as_json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'jurisdictions': len(rows),
                          'gaps_oldest_first': gaps, 'covered': ok,
                          'exit': 1 if gaps else 0}, indent=1))
        return 1 if gaps else 0
    print('%d seeded jurisdictions across %d seed files.' % (len(rows), len(seeds)))
    print('')
    print('GAPS, OLDEST-UNTESTED FIRST (age = first commit of the jurisdiction\'s oldest seed):')
    print('  %-11s %-10s %5s  %-26s %-5s %s' % ('juris', 'since', 'rules', 'gap', 'cross', 'isolation tests'))
    for r in gaps:
        print('  %-11s %-10s %5d  %-26s %-5d %s'
              % (r['jurisdiction'], r['oldest_seed_commit'], r['rules'], ' + '.join(r['gap']),
                 r['cross_cutting'], ', '.join(os.path.basename(t) for t in r['isolation']) or '-'))
    print('')
    print('COVERED BOTH WAYS: %s' % (', '.join(r['jurisdiction'] for r in ok) or 'none'))
    print('')
    n_iso = sum(1 for r in gaps if 'NO ISOLATION' in r['gap'])
    n_mut = sum(1 for r in gaps if 'NO MUTATION' in r['gap'])
    n_inc = sum(1 for r in gaps if 'INCIDENTAL ONLY' in r['gap'])
    print('%d of %d jurisdictions have a gap: %d with NO ISOLATION test, %d covered only '
          'INCIDENTALLY by a neighbour\'s suite, %d with NO MUTATION test.'
          % (len(gaps), len(rows), n_iso, n_inc, n_mut))
    print('A test with no mutation arm has never been seen to fail. That is the column this '
          'report exists for.')
    return 1 if gaps else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
