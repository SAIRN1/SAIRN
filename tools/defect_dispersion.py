"""Is defect causation concentrated in a few places, or spread evenly?

    python tools/defect_dispersion.py
    python tools/defect_dispersion.py --json
    python tools/defect_dispersion.py --quiet

Exit 0 always unless something could not be computed. REPORT ONLY: this is a
description of where defects have been FOUND, and nothing gates on it.

── THE QUESTION, AND THE TRAP INSIDE IT ────────────────────────────────────
"Are most defects caused by a few commits / files / sessions?" is worth asking:
if causation is concentrated, effort goes to the few; if it is uniform, it does
not, and a hunt for the bad apple is wasted.

THE TRAP IS THE DENOMINATOR, and it is the whole reason this file is careful.
docs/defect-density-register.json contains only units that HAVE a defect. A
Gini coefficient computed over that set alone answers "among the commits that
produced a defect, how unevenly are defects spread" -- which is a different and
much less interesting question, and it will always look more uniform than
reality because every zero is missing.

So EVERY figure here is reported TWICE:

  AMONG THE AFFECTED   over the units present in the register. Never quoted on
                       its own; it is the smaller, flattering number.
  OVER THE POPULATION  with every commit, file or session that produced NO
                       defect included at zero. This is the honest one, and it
                       is where concentration actually shows.

The two differ enormously, and the difference IS the finding.

── WHAT A GINI OF 0.9 DOES AND DOES NOT MEAN ───────────────────────────────
Over the full population it will always be high, because most commits touch
nothing that was ever swept and most files have never been looked at. **A high
concentration here is at least as much a statement about COVERAGE as about
causation** -- the register is a record of what has been FOUND, and finding is
not uniform either. That caveat is printed with the number rather than left for
a reader to remember, because a Gini quoted bare reads as a fact about quality.

── THE SESSION DIMENSION IS A PROXY AND IS LABELLED AS ONE ─────────────────
Every commit carries a `Claude-Session` trailer, so defects can be grouped by
the session that produced the commit. That is NOT an agent: four clones run many
sessions each, sessions are re-used across subjects, and a defect recorded
against a commit was not necessarily introduced by the session that landed it --
a fix commit often carries the record of the defect it fixed. Reported because
it is the only real unit available, labelled so nobody reads it as a scorecard.
"""
import argparse
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_COULD_NOT_RUN, finish                # noqa: E402

REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')


def git(*a):
    return subprocess.run(['git'] + list(a), cwd=REPO, capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout


def gini(values):
    """Gini over a list of counts. 0 = perfectly even, 1 = all in one unit."""
    xs = sorted(float(v) for v in values)
    n = len(xs)
    if n == 0:
        return None
    total = sum(xs)
    if total == 0:
        return 0.0
    cum = 0.0
    for i, x in enumerate(xs, 1):
        cum += i * x
    return (2.0 * cum) / (n * total) - (n + 1.0) / n


def top_share(counts, frac=0.20):
    """What share of defects sit in the top `frac` of units, by count."""
    xs = sorted(counts, reverse=True)
    if not xs or sum(xs) == 0:
        return None
    k = max(1, int(round(len(xs) * frac)))
    return sum(xs[:k]) / float(sum(xs))


def dimension(name, counts_by_unit, population, note):
    """counts_by_unit: {unit: n}. population: total units INCLUDING zeros."""
    affected = list(counts_by_unit.values())
    row = {'dimension': name, 'note': note,
           'defects': sum(affected), 'affected_units': len(affected),
           'population': population}
    row['gini_among_affected'] = gini(affected)
    row['top20_among_affected'] = top_share(affected)
    if population is None:
        # A POPULATION NOBODY COUNTED IS NOT A POPULATION OF ONE. Reported as
        # unknown rather than defaulted, because defaulting it would silently
        # turn the honest figure into the flattering one.
        row['gini_over_population'] = None
        row['top20_over_population'] = None
        row['population_note'] = 'NOT COUNTED -- the over-population figures ' \
                                 'cannot be computed and are not guessed'
    else:
        zeros = max(0, population - len(affected))
        full = affected + [0] * zeros
        row['gini_over_population'] = gini(full)
        row['top20_over_population'] = top_share(full)
        row['zero_units'] = zeros
    return row


def collect():
    with io.open(REGISTER, encoding='utf-8') as fh:
        recs = json.load(fh)['records']

    start = min(r.get('date') or '9999' for r in recs)

    # ── the populations, each derived and each named ─────────────────────────
    # COMMITS: every commit on main since the register opened. The register is
    # explicit that it is NOT backfilled beyond its start date, so counting all
    # of history would invent a denominator the numerator cannot reach.
    since = '--since=' + start
    commit_lines = [l for l in git('log', since, '--format=%H').split('\n') if l.strip()]
    commit_pop = len(commit_lines) or None

    # SESSIONS: the distinct Claude-Session trailers on those commits.
    sess_out = git('log', since, '--format=%H%x1f%(trailers:key=Claude-Session,valueonly)')
    sess_by_commit = {}
    for line in sess_out.split('\n'):
        if '\x1f' not in line:
            continue
        sha, sess = line.split('\x1f', 1)
        sess = sess.strip().split('\n')[0].strip()
        if sha:
            sess_by_commit[sha[:12]] = sess or '(no session trailer)'
    session_pop = len(set(v for v in sess_by_commit.values() if v)) or None

    # FILES: files actually TOUCHED in the window. Using every tracked file
    # would count 900-odd files nobody has edited since the register opened,
    # which inflates the zero bucket with units that were never at risk.
    touched = set()
    for f in git('log', since, '--name-only', '--format=').split('\n'):
        f = f.strip()
        if f:
            touched.add(f)
    file_pop = len(touched) or None

    # APPS: the app files that exist. A defect is filed against an app or
    # against PLATFORM; the app population is the real app count plus one for
    # PLATFORM, which is not a file and is named as such in the output.
    apps = [f for f in git('ls-files', '*.html').split('\n') if f.strip() and '/' not in f]
    app_pop = (len(apps) + 1) if apps else None

    def tally(key):
        out = {}
        for r in recs:
            k = key(r)
            if isinstance(k, list):
                for x in k:
                    out[x] = out.get(x, 0) + 1
            elif k:
                out[k] = out.get(k, 0) + 1
        return out

    dims = [
        dimension('originating commit', tally(lambda r: r['commit']), commit_pop,
                  'one record per confirmed defect; a commit can carry several'),
        dimension('file', tally(lambda r: [f for f in (r.get('files') or [])]), file_pop,
                  'a defect is counted against EVERY file in its commit, so this '
                  'over-attributes: a one-line fix that also touched three docs '
                  'credits all four'),
        dimension('app', tally(lambda r: r.get('app')), app_pop,
                  'PLATFORM is not a file and is one unit of the population'),
        dimension('session', tally(lambda r: sess_by_commit.get(r['commit'], '(unknown)')),
                  session_pop,
                  'A PROXY, NOT AN AGENT: sessions are reused across subjects and '
                  'a fix commit often carries the record of the defect it fixed, '
                  'so the session that LANDED a record is not necessarily the one '
                  'that introduced the defect'),
        dimension('layer', tally(lambda r: r.get('layer')), 3,
                  'product / tooling / test -- the whole population is three'),
        dimension('detection method', tally(lambda r: r.get('detection_method')), None,
                  'the population is the METHODS THAT EXIST, which is a judgement '
                  'rather than a count, so the over-population figures are refused'),
    ]
    return recs, start, dims, sess_by_commit


def fmt(v):
    return '  --  ' if v is None else '%6.3f' % v


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args(argv)

    try:
        recs, start, dims, _s = collect()
    except Exception as e:                                   # noqa: BLE001
        print('could not compute: %s: %s' % (type(e).__name__, e))
        return EXIT_COULD_NOT_RUN

    cnr = [d['dimension'] + ': ' + d['population_note']
           for d in dims if d.get('population_note')]

    if args.json:
        print(json.dumps({'records': len(recs), 'since': start,
                          'dimensions': dims, 'could_not_run': cnr}, indent=1))
        return EXIT_COULD_NOT_RUN if cnr else 0

    if not args.quiet:
        print('DEFECT DISPERSION -- report only, nothing gates on this')
        print('  %d confirmed defects, register opens %s' % (len(recs), start))
        print('')
        print('  %-20s %7s %7s | %-14s %-14s | %-14s %-14s'
              % ('dimension', 'defects', 'units', 'GINI affected',
                 'GINI population', 'top20 affected', 'top20 population'))
        for d in dims:
            print('  %-20s %7d %7s | %-14s %-14s | %-14s %-14s'
                  % (d['dimension'], d['defects'],
                     '%d/%s' % (d['affected_units'],
                                d['population'] if d['population'] else '?'),
                     fmt(d['gini_among_affected']), fmt(d['gini_over_population']),
                     fmt(d['top20_among_affected']), fmt(d['top20_over_population'])))
        print('')
        print('  READ THE TWO GINI COLUMNS TOGETHER OR NEITHER.')
        print('  AFFECTED is computed over the units that already have a defect,')
        print('  so every zero is missing and it always looks more uniform than')
        print('  reality. POPULATION includes them and is the honest one.')
        print('')
        print('  AND A HIGH POPULATION FIGURE IS AT LEAST AS MUCH ABOUT COVERAGE')
        print('  AS ABOUT CAUSATION: this register records what has been FOUND,')
        print('  and finding is not uniform either. Most files have never been')
        print('  swept by anything, and a file nobody looked at contributes a')
        print('  zero that is indistinguishable from a file that is clean.')
        for d in dims:
            print('')
            print('  %s -- %s' % (d['dimension'], d['note']))
        # PRINTED UNCONDITIONALLY, and the probe is why. This line used to live
        # in the clean_line, which only prints when there are no findings and
        # nothing could-not-run -- so the one caveat that stops the whole table
        # being read as a verdict appeared exactly when it was least needed, and
        # never on the real run, which exits 2 because one population is
        # deliberately uncounted.
        print('')
        print('  THIS IS A DESCRIPTION, NOT A VERDICT. No threshold is applied,')
        print('  nothing is flagged, and no number here says anybody did')
        print('  anything wrong.')

    return finish([], cnr, quiet=args.quiet,
                  clean_line='\n  Computed.')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
