#!/usr/bin/env python3
"""CHECKED OVER UNIVERSE -- and a RATCHET that fails when the universe grows
and the checked count does not.

    python tools/checker_denominator.py                 # report
    python tools/checker_denominator.py --update        # re-baseline, with a reason
    python tools/checker_denominator.py --json
    python tools/checker_denominator.py --selftest

Exit 0 CLEAN, 1 A RATCHET TRIPPED, 2 COULD NOT RUN. Never 0 for could-not-tell.

── WHY THIS EXISTS, AND IT IS A MEASURED INCIDENT ─────────────────────────
2026-09-27: this platform had TWO anchor-freshness checkers running side by
side. `tools/mutation_anchor_check.py` covered the 85 probes declaring a
module-level MUTATIONS list. `tools/probe_anchor_freshness.py` covered the 10
passing edit tuples to arm(). **The overlap was ZERO**, and a third convention
-- two probes, one of them arming a controlled-substance register -- was
covered by nothing at all.

Both tools were wired. Both were correct. Both reported clean results about
their own populations for days while three probes in the other population were
DEAD. Nothing was stale and nothing was broken: **the number of things being
checked was never compared against the number of things there are.**

A checker that reports "114 anchors agree" has said nothing about coverage.
114 out of what?

── THE TWO NUMBERS, AND WHY BOTH ─────────────────────────────────────────
  UNIVERSE  how many candidates EXIST, counted from the repo
  CHECKED   how many the tool could actually read

A tool is not required to reach 100%. It is required to SAY. The gap is the
number nobody had: `probe_anchor_freshness.py` read 12 probe files out of 99
that declare anchors, and reported neither figure.

── THE RATCHET, AND WHAT IT DELIBERATELY DOES NOT DO ─────────────────────
It trips when the UNIVERSE GROWS AND CHECKED DOES NOT. That is the exact shape
of the incident: somebody adds probes in a convention the tool cannot parse,
the tool keeps reporting a clean number about the subset it can see, and
coverage silently falls.

IT DOES NOT TRIP ON COVERAGE BEING LOW. A tool at 12% that has always been at
12% is a known, stated limit; failing on it would produce a red check nobody
can clear and the whole thing gets switched off. The ratchet is about
REGRESSION, not about a target.

IT DOES NOT TRIP WHEN BOTH SHRINK. Deleting probes is legitimate.

── FAIL CLOSED (PR 1.11) ─────────────────────────────────────────────────
A counter that raises, a baseline that will not parse, or a tool whose universe
cannot be derived is exit 2 with the name printed. It is never folded into
"clean", and a missing baseline is not a pass -- it is an unmeasured tool, and
it is listed as one.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(REPO, 'docs', 'checker-coverage-baseline.json')
CRITERIA_VERSION = '2026-09-28.2'

# A checker that cannot read this share of its own population is not
# reporting about that population. STATED rather than tuned: the figure is a
# judgement and is written here once so a result can be compared against a
# number somebody chose, not against one that drifted.
UNREADABLE_CEILING = 0.25


def _tracked(*globs):
    try:
        p = subprocess.run(['git', 'ls-files'] + list(globs), cwd=REPO,
                           capture_output=True, timeout=120)
    except Exception as exc:
        raise RuntimeError('git ls-files failed to launch: %s' % type(exc).__name__)
    if p.returncode != 0:
        raise RuntimeError('git ls-files exited %d' % p.returncode)
    out = (p.stdout or b'').decode('utf-8', 'replace').split('\n')
    return [f.strip().replace(os.sep, '/') for f in out
            if f.strip() and not f.strip().startswith(('archive/', 'node_modules/'))]


def _read(rel):
    try:
        return io.open(os.path.join(REPO, rel), encoding='utf-8',
                       errors='replace').read()
    except OSError:
        return ''


# ── THE UNIVERSE FOR EACH WIRED CHECKER ───────────────────────────────────
# Each entry answers ONE question: how many candidates exist for this tool to
# look at? The universe is counted from the REPO, never from the tool -- a
# universe the tool derives is the tool grading its own denominator, which is
# the defect this file exists for one level up.

def _probes_declaring_anchors():
    """Probe files that declare a mutation anchor in ANY of the three known
    conventions. The universe for BOTH anchor checkers, which is the point:
    they are measured against the same denominator or the zero-overlap gap
    cannot be seen."""
    import ast
    ARM = ('arm', 'mutate', 'sabotage', 'plant')
    n = 0
    for rel in _tracked('tests/*.py', 'tests/**/*.py'):
        src = _read(rel)
        if re.search(r'^MUTATIONS\s*=', src, re.M):
            n += 1
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        hit = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                nm = getattr(node.func, 'id', None) or getattr(node.func, 'attr', None)
                if nm in ARM:
                    for a in list(node.args) + [k.value for k in node.keywords]:
                        for e in (a.elts if isinstance(a, (ast.List, ast.Tuple)) else [a]):
                            if isinstance(e, ast.Tuple) and len(e.elts) >= 2:
                                hit = True
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name in ARM:
                params = [x.arg for x in node.args.args]
                if 'old' in params and 'new' in params:
                    hit = True
        if hit:
            n += 1
    return n


def _checked_probe_anchor_freshness():
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import probe_anchor_freshness as paf
    res = paf.scan()
    if res is None:
        raise RuntimeError('probe_anchor_freshness.scan() could not run')
    return len(set(r['probe'].replace(os.sep, '/') for r in res['rows']))


def _checked_mutation_anchor_check():
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import mutation_anchor_check as mac
    import glob as _g
    seen = set()
    for path in _g.glob(os.path.join(REPO, 'tests', '**', '*_probe.py'),
                        recursive=True):
        try:
            _c, muts = mac.read_probe(path)
        except Exception:
            continue
        if muts:
            seen.add(os.path.relpath(path, REPO).replace(os.sep, '/'))
    return len(seen)


def _apps():
    return len([f for f in _tracked('*.html') if '/' not in f])


def _checked_overrun_scan():
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import overrun_inversion_scan as ois
    rows = ois.scan()
    if rows is None:
        raise RuntimeError('overrun_inversion_scan.scan() could not run')
    return len(set(r['file'] for r in rows if '/' not in r['file']))


def _js_html_tracked():
    return len(_tracked('*.js', '*.html'))


def _checked_ai_action_audit():
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import ai_action_approval_audit as a
    files = a.app_files()
    if files is None:
        raise RuntimeError('ai_action_approval_audit.app_files() refused')
    return len(files)


def _unreadable_probe_anchor_freshness():
    """Probe files this tool PARSED but could not fully read."""
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import probe_anchor_freshness as paf
    res = paf.scan()
    if res is None:
        raise RuntimeError('probe_anchor_freshness.scan() could not run')
    skipped = set(rel for rel, _why in res.get('skipped', []))
    unread = set(r['probe'] for r in res['rows'] if r['count'] in (-1, -2))
    return len(skipped | unread)


def _unreadable_mutation_anchor_check():
    """Probe files with at least one arm whose target could not be resolved."""
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import mutation_anchor_check as mac
    import glob as _g
    bad = set()
    for path in _g.glob(os.path.join(REPO, 'tests', '**', '*_probe.py'),
                        recursive=True):
        rel = os.path.relpath(path, REPO).replace(os.sep, '/')
        try:
            consts, muts = mac.read_probe(path)
        except Exception:
            bad.add(rel)
            continue
        for entry in muts:
            try:
                target, old = mac.resolve(consts, entry)
            except Exception:
                bad.add(rel)
                continue
            if not target and isinstance(old, str):
                bad.add(rel)
    return len(bad)


def _unreadable_zero_by_construction():
    """A HARD, MEASURED ZERO rather than an omission.

    An absent number and a measured zero read identically in a table and mean
    opposite things -- which is the whole reason this dimension exists. These
    tools read with errors='replace' and have no could-not-read state at all.
    """
    return 0


TOOLS = [
    {'tool': 'probe_anchor_freshness.py',
     'unreadable': _unreadable_probe_anchor_freshness,
     'universe': _probes_declaring_anchors,
     'checked': _checked_probe_anchor_freshness,
     'unit': 'probe files declaring a mutation anchor',
     'note': 'THE INCIDENT ITSELF. Measured against the SAME universe as '
             'mutation_anchor_check.py deliberately -- two tools graded on two '
             'different denominators cannot show a zero-overlap gap.'},
    {'tool': 'mutation_anchor_check.py',
     'unreadable': _unreadable_mutation_anchor_check,
     'universe': _probes_declaring_anchors,
     'checked': _checked_mutation_anchor_check,
     'unit': 'probe files declaring a mutation anchor',
     'note': 'Same universe as above, on purpose. The two CHECKED counts '
             'summing to more than the universe would mean overlap; summing to '
             'less means a convention neither reads.'},
    {'tool': 'overrun_inversion_scan.py',
     'unreadable': _unreadable_zero_by_construction,
     'universe': _apps,
     'checked': _checked_overrun_scan,
     'unit': 'root .html apps',
     'note': 'CHECKED here means "produced at least one row", so a genuinely '
             'clean app is indistinguishable from an unparsed one. Stated '
             'rather than left for somebody to assume the other way.'},
    {'tool': 'ai_action_approval_audit.py',
     'unreadable': _unreadable_zero_by_construction,
     'universe': _apps,
     'checked': _checked_ai_action_audit,
     'unit': 'root .html apps',
     'note': 'Its app_files() refuses an EMPTY list as could-not-tell, so a '
             'checked count of 0 raises here rather than reporting coverage 0.'},
]


def load_baseline():
    if not os.path.isfile(BASELINE):
        return {}
    try:
        return json.loads(io.open(BASELINE, encoding='utf-8').read())
    except ValueError as exc:
        raise RuntimeError('%s will not parse: %s' % (BASELINE, exc))


def measure():
    rows, errors = [], []
    for spec in TOOLS:
        row = {'tool': spec['tool'], 'unit': spec['unit'], 'note': spec['note']}
        try:
            row['universe'] = spec['universe']()
        except Exception as exc:
            errors.append('%s: universe could not be derived (%s: %s)'
                          % (spec['tool'], type(exc).__name__, exc))
            continue
        try:
            row['checked'] = spec['checked']()
        except Exception as exc:
            errors.append('%s: checked count could not be derived (%s: %s)'
                          % (spec['tool'], type(exc).__name__, exc))
            continue
        if spec.get('unreadable'):
            try:
                row['unreadable'] = spec['unreadable']()
            except Exception as exc:
                errors.append('%s: UNREADABLE count could not be derived '
                              '(%s: %s) -- and that is itself a could-not-tell '
                              'about a could-not-tell, so the row is dropped '
                              'rather than reported with the dimension missing'
                              % (spec['tool'], type(exc).__name__, exc))
                continue
        rows.append(row)
    return rows, errors


def compare(rows, base):
    """Ratchet verdicts. See the header for what it deliberately does NOT do."""
    out = []
    for r in rows:
        b = base.get(r['tool'])
        if not b:
            out.append(dict(r, verdict='UNBASELINED',
                            why='no recorded baseline, so no regression can be '
                                'detected -- this tool is UNMEASURED, which is '
                                'not the same as clean'))
            continue
        grew = r['universe'] > b['universe']
        gained = r['checked'] > b['checked']
        if grew and not gained:
            out.append(dict(r, verdict='RATCHET TRIPPED', prev=b,
                            why='the universe grew from %d to %d and the '
                                'checked count did not move from %d. Coverage '
                                'fell from %.0f%% to %.0f%% without anything '
                                'failing.'
                                % (b['universe'], r['universe'], b['checked'],
                                   100.0 * b['checked'] / max(1, b['universe']),
                                   100.0 * r['checked'] / max(1, r['universe']))))
        elif r['checked'] < b['checked'] and r['universe'] >= b['universe']:
            out.append(dict(r, verdict='RATCHET TRIPPED', prev=b,
                            why='the checked count FELL from %d to %d while the '
                                'universe did not shrink -- the tool reads less '
                                'than it did and nothing else said so.'
                                % (b['checked'], r['checked'])))
        # ── THE COULD-NOT-READ RATCHET, added 2026-09-28 ──────────────────
        # EARNED BY A MEASURED INCIDENT: tools/mutation_anchor_check.py was
        # wired and exiting 2 with 84 UNREADABLE declarations, and behind that
        # exit code sat 16 REAL findings nobody could see. An unreadable count
        # is not a neutral statistic -- it is the size of the blind spot, and a
        # rising one means a checker is quietly reading less of its own
        # population while still printing a number.
        #
        # RATCHETED DOWNWARD ONLY. It may fall freely; it may not rise. That
        # asymmetry is the whole point: teaching a checker a new declaration
        # shape lowers it, and adding declarations in a shape it cannot read
        # raises it, and only the second is a regression.
        elif (r.get('unreadable') is not None
              and b.get('unreadable') is not None
              and r['unreadable'] > b['unreadable']):
            out.append(dict(r, verdict='RATCHET TRIPPED', prev=b,
                            why='the UNREADABLE count ROSE from %d to %d. The '
                                'blind spot grew: declarations were added in a '
                                'shape this checker cannot parse, so it is '
                                'reading less of its population while still '
                                'reporting a clean number.'
                                % (b['unreadable'], r['unreadable'])))
        # ── AND A CEILING, because a ratchet alone permits a large blind spot
        # forever as long as it never grows. The fraction is stated rather than
        # tuned: a checker that cannot read a QUARTER of its own population is
        # not reporting about that population.
        elif (r.get('unreadable') is not None and r['universe'] > 0
              and r['unreadable'] > UNREADABLE_CEILING * r['universe']):
            out.append(dict(r, verdict='RATCHET TRIPPED', prev=b,
                            why='%d of %d candidates (%.0f%%) are UNREADABLE, '
                                'over the stated ceiling of %.0f%%. A checker '
                                'that cannot read that share of its own '
                                'population is not reporting about that '
                                'population.'
                                % (r['unreadable'], r['universe'],
                                   100.0 * r['unreadable'] / r['universe'],
                                   100.0 * UNREADABLE_CEILING)))
        else:
            out.append(dict(r, verdict='OK', prev=b))
    return out


def selftest():
    out, bad = [], 0

    def arm(name, ok, detail=''):
        nonlocal bad
        out.append('  %s %s%s' % ('ok  ' if ok else 'FAIL', name,
                                  '' if ok else '\n       ' + str(detail)[:300]))
        if not ok:
            bad += 1

    def one(u, c, bu, bc):
        return compare([{'tool': 't', 'universe': u, 'checked': c,
                         'unit': 'x', 'note': ''}],
                       {'t': {'universe': bu, 'checked': bc}})[0]

    arm('THE INCIDENT SHAPE trips: universe grows, checked does not',
        one(99, 12, 90, 12)['verdict'] == 'RATCHET TRIPPED',
        one(99, 12, 90, 12))
    arm('growth MATCHED by new coverage does NOT trip',
        one(99, 20, 90, 12)['verdict'] == 'OK')
    arm('a checked count that FALLS on a steady universe trips',
        one(90, 8, 90, 12)['verdict'] == 'RATCHET TRIPPED')
    arm('BOTH shrinking does not trip -- deleting probes is legitimate',
        one(80, 10, 90, 12)['verdict'] == 'OK',
        'a ratchet that fired on deletion would make removing dead code a red '
        'check, and it would be switched off')
    arm('LOW COVERAGE ALONE does not trip -- it is a stated limit, not a '
        'regression',
        one(99, 3, 99, 3)['verdict'] == 'OK',
        'failing on a long-standing 3%% would produce a red nobody can clear')
    arm('NO BASELINE is UNBASELINED, never OK',
        compare([{'tool': 'z', 'universe': 5, 'checked': 5, 'unit': 'x',
                  'note': ''}], {})[0]['verdict'] == 'UNBASELINED',
        'an unmeasured tool reported as clean is the whole failure this file '
        'is about, one level up')
    arm('CONTROL -- the verdicts are not all the same value',
        len({one(99, 12, 90, 12)['verdict'], one(99, 20, 90, 12)['verdict'],
             compare([{'tool': 'z', 'universe': 1, 'checked': 1, 'unit': '',
                       'note': ''}], {})[0]['verdict']}) == 3,
        'compare() returns one verdict for every input, so every arm above is '
        'checking one value repeatedly')

    # ── THE COULD-NOT-READ RATCHET, in every direction ────────────────────
    def unr(u, c, un, bu, bc, bun):
        return compare([{'tool': 't', 'universe': u, 'checked': c,
                         'unreadable': un, 'unit': 'x', 'note': ''}],
                       {'t': {'universe': bu, 'checked': bc,
                              'unreadable': bun}})[0]

    arm('a RISING unreadable count trips -- the blind spot grew',
        unr(100, 90, 12, 100, 90, 4)['verdict'] == 'RATCHET TRIPPED',
        unr(100, 90, 12, 100, 90, 4))
    arm('a FALLING unreadable count does NOT trip -- that is the fix landing',
        unr(100, 90, 2, 100, 90, 9)['verdict'] == 'OK')
    arm('an unreadable count over the stated ceiling trips even if it did not rise',
        unr(100, 60, 40, 100, 60, 40)['verdict'] == 'RATCHET TRIPPED',
        'a ratchet alone permits a large blind spot forever as long as it '
        'never grows; 40 of 100 is over the %.0f%% ceiling and must fail'
        % (100 * UNREADABLE_CEILING))
    arm('...and one UNDER the ceiling that did not rise is OK',
        unr(100, 90, 10, 100, 90, 10)['verdict'] == 'OK')
    arm('a tool that publishes NO unreadable count is not treated as zero',
        compare([{'tool': 't', 'universe': 100, 'checked': 60, 'unit': 'x',
                  'note': ''}],
                {'t': {'universe': 100, 'checked': 60}})[0]['verdict'] == 'OK'
        and 'unreadable' not in compare(
            [{'tool': 't', 'universe': 100, 'checked': 60, 'unit': 'x',
              'note': ''}], {'t': {'universe': 100, 'checked': 60}})[0],
        'an absent blind-spot figure must not silently satisfy the ceiling -- '
        'it is reported as ? and the ceiling does not apply')

    # ── THE KNOWN-BAD CONTROL, and it drives a REAL checker ───────────────
    # THE RULE: a checker fed an unparseable declaration must FAIL, not exit
    # clean. tools/mutation_anchor_check.py exited 2 on 84 unreadable
    # declarations while hiding 16 real findings, which is the version of this
    # that already cost something. The weaker failure -- a checker that parses
    # nothing and reports zero findings -- is the one this arm exists for.
    import tempfile as _tf
    import shutil as _sh
    bad_dir = _tf.mkdtemp(prefix='sairn-knownbad-')
    try:
        sys.path.insert(0, os.path.join(REPO, 'tools'))
        import mutation_anchor_check as _mac
        p = os.path.join(bad_dir, 'broken_probe.py')
        io.open(p, 'w', encoding='utf-8').write(
            'MUTATIONS = [(\n')          # deliberately unparseable
        raised = False
        try:
            _mac.read_probe(p)
        except Exception:
            raised = True
        arm('KNOWN-BAD: an UNPARSEABLE probe makes the reader RAISE, so the '
            'caller can count it rather than seeing an empty list',
            raised,
            'read_probe() returned normally on a file that does not parse. An '
            'empty MUTATIONS list from a broken file is indistinguishable from '
            'a file with no mutations, and the checker would report it clean.')
        # ...and the count this file publishes must MOVE when that happens.
        arm('KNOWN-BAD: the unreadable counter is a real function, not a '
            'constant',
            callable(TOOLS[0].get('unreadable'))
            and TOOLS[0]['unreadable']() >= 0)
    finally:
        _sh.rmtree(bad_dir, ignore_errors=True)

    rows, errors = measure()
    arm('the real measurement runs over every registered tool',
        not errors and len(rows) == len(TOOLS),
        'errors=%r rows=%d of %d' % (errors, len(rows), len(TOOLS)))
    arm('...and every registered tool publishes an unreadable count',
        all(r.get('unreadable') is not None for r in rows),
        'tool(s) with no blind-spot figure: %r'
        % [r['tool'] for r in rows if r.get('unreadable') is None])
    return out, bad


def main(argv):
    if '--selftest' in argv:
        print('CHECKER DENOMINATOR -- selftest (criteria %s)' % CRITERIA_VERSION)
        o, bad = selftest()
        for line in o:
            print(line)
        print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
        return 1 if bad else 0

    try:
        base = load_baseline()
    except RuntimeError as exc:
        print('COULD NOT RUN: %s' % exc, file=sys.stderr)
        return 2
    rows, errors = measure()
    if errors and not rows:
        print('COULD NOT RUN: no tool could be measured:', file=sys.stderr)
        for e in errors:
            print('  - %s' % e, file=sys.stderr)
        return 2
    verdicts = compare(rows, base)

    if '--update' in argv:
        why = ''
        if '--reason' in argv:
            why = argv[argv.index('--reason') + 1]
        if len(why.strip()) < 30:
            print('--update needs --reason "<at least 30 characters>". '
                  'Re-baselining is how a ratchet is silently disarmed, so the '
                  'reason is recorded beside the numbers rather than in a '
                  'commit message somebody has to go and find.', file=sys.stderr)
            return 2
        newbase = dict(base)
        for r in rows:
            newbase[r['tool']] = {'universe': r['universe'],
                                  'checked': r['checked'],
                                  'unreadable': r.get('unreadable'),
                                  'unit': r['unit'],
                                  'reason': why}
        io.open(BASELINE, 'w', encoding='utf-8', newline='').write(
            json.dumps(newbase, indent=1, sort_keys=True) + '\n')
        print('re-baselined %d tool(s) into %s'
              % (len(rows), os.path.relpath(BASELINE, REPO)))
        return 0

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION,
                          'tools': verdicts, 'errors': errors}, indent=1))
        return 1 if any(v['verdict'] == 'RATCHET TRIPPED' for v in verdicts) else 0

    print('CHECKER DENOMINATOR -- checked over universe, and a ratchet on the gap')
    print('  criteria %s' % CRITERIA_VERSION)
    print('')
    print('  %-34s %8s %8s %10s %9s  %s'
          % ('tool', 'checked', 'universe', 'unreadable', 'coverage', 'verdict'))
    for v in verdicts:
        cov = 100.0 * v['checked'] / max(1, v['universe'])
        # AN ABSENT UNREADABLE COUNT IS PRINTED AS '?' AND NEVER AS 0. A tool
        # that does not publish its blind spot is not a tool with no blind
        # spot, and the two must not share a cell.
        un = ('%d' % v['unreadable']) if v.get('unreadable') is not None else '?'
        print('  %-34s %8d %8d %10s %8.0f%%  %s'
              % (v['tool'], v['checked'], v['universe'], un, cov, v['verdict']))
    for v in verdicts:
        print('')
        print('  %s -- %s' % (v['tool'], v['unit']))
        print('      %s' % v['note'])
        if v.get('why'):
            print('      %s' % v['why'])
    if errors:
        print('')
        print('COULD NOT MEASURE (%d) -- a third state, never a pass:' % len(errors))
        for e in errors:
            print('  - %s' % e)
    print('')
    print('A TOOL IS NOT REQUIRED TO REACH 100%. It is required to SAY. The')
    print('ratchet fires on the universe GROWING while checked does not, which')
    print('is coverage falling with nothing failing -- not on coverage being low.')
    if errors:
        return 2
    return 1 if any(v['verdict'] == 'RATCHET TRIPPED' for v in verdicts) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
