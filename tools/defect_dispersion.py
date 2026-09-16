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
import math
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


def dispersion(counts_by_unit, population):
    """Is this count distribution OVER-DISPERSED, or just sparse?

    Returns (index_of_dispersion, nb_k, verdict, why) -- any of which may be
    None, and None is never folded into a number.

    ── WHY A GINI IS NOT AN ANSWER TO ITEM 59 ──────────────────────────────
    77 defects over 1232 commits gives a Gini of 0.97 over the population. So
    does a PERFECTLY POISSON process at the same rate: with a mean of 0.06
    defects per commit, almost every commit has zero and a handful have one,
    which is maximally "unequal" by any concentration index and is not
    superspreading. **A concentration index measures sparseness at these rates,
    not clustering.** Quoting one as evidence of a few bad apples is the same
    error as quoting an accuracy figure built from false positives.

    THE TEST THAT DOES ANSWER IT is the variance relative to the mean.
      * Poisson (pure chance):        variance == mean, index == 1
      * over-dispersed (clustered):   variance >  mean, index >  1
      * under-dispersed (regular):    variance <  mean, index <  1
    The index is computed OVER THE POPULATION -- zeros included -- because the
    zeros are most of the distribution and the whole question is their shape.

    AND THE NEGATIVE-BINOMIAL k IS THE EPIDEMIOLOGICAL FORM of the same thing,
    which is where item 59's framing comes from: k = mean^2 / (variance - mean).
    Small k means heavy clustering (superspreading); large k approaches Poisson.
    It is only defined when variance > mean, and it is NOT computed otherwise
    rather than being clamped -- a clamped k reads as a measurement.

    ── AND THE UNCERTAINTY, WHICH IS THE POINT ─────────────────────────────
    At these counts the index is NOISE-DOMINATED. The standard error of the
    index of dispersion for a Poisson sample of n units is approximately
    sqrt(2/(n-1)), so a spread of a few percent around 1 is indistinguishable
    from chance. The verdict below is deliberately three-valued and the
    inconclusive band is wide.
    """
    if population is None:
        return None, None, 'NOT TESTED', \
            'the population is unknown, so the zeros cannot be counted and the ' \
            'variance cannot be computed over the real distribution'
    affected = list(counts_by_unit.values())
    n = population
    if n < 2:
        return None, None, 'NOT TESTED', 'fewer than two units'
    zeros = max(0, n - len(affected))
    vals = affected + [0] * zeros
    total = sum(vals)
    mean = total / float(n)
    if mean <= 0:
        return None, None, 'NOT TESTED', 'no defects, so there is no rate to test'
    var = sum((v - mean) ** 2 for v in vals) / float(n - 1)
    index = var / mean
    # Standard error of the index under the Poisson null.
    se = math.sqrt(2.0 / (n - 1))
    # ── NB k IS ONLY EMITTED WHEN OVER-DISPERSION IS ESTABLISHED ─────────
    # FOUND BY tests/run_dispersion_probe.py, and it is exactly the fabrication
    # this file was written to avoid. A PURE POISSON sample whose sample
    # variance lands a hair above the mean yields k = mean^2/(var-mean) = 0.87 --
    # which in epidemiological terms reads as heavy superspreading, from pure
    # chance. As (var - mean) approaches zero the expression explodes or
    # collapses on noise alone.
    #
    # So k is computed BELOW, after the verdict, and only when the verdict is
    # OVER-DISPERSED. A k without an established over-dispersion is not a small
    # number, it is a meaningless one, and this platform's own history says a
    # meaningless number gets quoted.
    # ── UNDERPOWERED IS NOT "INDISTINGUISHABLE" ──────────────────────────
    # With 3 units, 2*SE is 2.0, so the index would have to exceed 3.0 to
    # register -- a test that can only ever answer "indistinguishable" is not a
    # test, and reporting its answer as a finding about the data would be
    # exactly the vacuous pass this platform keeps removing. When the band is
    # wider than the null value it is testing against, say so instead.
    if 2 * se >= 1.0:
        return index, None, 'NOT TESTED -- UNDERPOWERED', (
            'index %.3f, but 2 SE is %.3f on only %d units: the band is wider '
            'than the value being tested against, so this test could only ever '
            'answer "indistinguishable". That is a fact about the number of '
            'units, not about the defects.' % (index, 2 * se, n))
    # THE BAND IS 2 STANDARD ERRORS AND IS DELIBERATELY WIDE. A narrower band
    # on counts this small would turn noise into a finding, which is the exact
    # thing this function exists to stop the Gini column doing.
    k = None
    if index > 1 + 2 * se:
        verdict = 'OVER-DISPERSED'
        k = (mean * mean) / (var - mean) if var > mean else None
        why = ('variance exceeds the mean by more than 2 standard errors '
               '(index %.3f, SE %.3f) -- clustering beyond chance' % (index, se))
    elif index < 1 - 2 * se:
        verdict = 'UNDER-DISPERSED'
        why = ('variance is BELOW the mean by more than 2 SE (index %.3f, '
               'SE %.3f) -- more regular than chance, which is not a defect '
               'pattern anybody expects and is worth reading twice'
               % (index, se))
    else:
        verdict = 'INDISTINGUISHABLE FROM POISSON'
        why = ('index %.3f is within 2 SE (%.3f) of 1, so the spread is what '
               'pure chance at this rate produces. THE GINI COLUMN IS HIGH '
               'BECAUSE THE DATA IS SPARSE, NOT BECAUSE IT IS CLUSTERED.'
               % (index, se))
    return index, k, verdict, why


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
    # THE DISPERSION TEST IS THE ANSWER TO ITEM 59; the Gini columns are
    # context. Reported for every dimension including the ones whose population
    # is unknown, where it says NOT TESTED rather than producing a figure.
    idx, k, verdict, why = dispersion(counts_by_unit, population)
    row['dispersion_index'] = idx
    row['nb_k'] = k
    row['dispersion_verdict'] = verdict
    row['dispersion_why'] = why
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


def backward_trace(recs, top_n=3):
    """From the largest CLUSTERS, back to what they share. Not forward from
    every case.

    ── WHY BACKWARD, AND WHY IT IS NOT A STYLISTIC CHOICE ──────────────────
    Item 59's framing is epidemiological and so is this. Forward contact tracing
    -- take every case and follow it outward -- costs O(cases x contacts) and,
    in an over-dispersed process, spends almost all of that budget on cases that
    infected nobody. BACKWARD tracing starts from a KNOWN CLUSTER and asks what
    its members have in common, which in a superspreading regime finds the
    common source in one hop. The dispersion test above is what licenses it: on
    a Poisson-shaped distribution there are no clusters to trace back FROM, and
    doing it anyway would be reading a pattern into noise.
    77 records is also small enough that forward tracing every case would be
    affordable and still wrong -- the point is which question gets answered, not
    which is cheaper.

    ── WHAT A "COMMON ORIGIN" CAN AND CANNOT BE HERE ───────────────────────
    The register has no causal graph. What it has is attributes, so a shared
    attribute is a CANDIDATE origin and never a proven one. Each cluster is
    reported with the attributes its members share and how unusual that sharing
    is against the register as a whole -- because "all four are in stonedesk" is
    not informative if most records are.
    """
    from collections import Counter, defaultdict

    # Clusters are defined on the dimension whose over-dispersion is real AND
    # whose attribution is not inflated. `file` is excluded deliberately: the
    # tool counts a defect against EVERY file in its commit, so file counts are
    # correlated by construction and a "file cluster" can be one commit wearing
    # four hats.
    clusters = []
    by_commit = defaultdict(list)
    for r in recs:
        c = r.get('commit')
        if c:
            by_commit[c].append(r)
    multi = sorted([(len(v), k, v) for k, v in by_commit.items() if len(v) > 1],
                   reverse=True)[:top_n]

    # Base rates over the whole register, so "shared" can be judged against
    # "common". Without this a cluster that shares the most frequent value on
    # the platform reads as a finding.
    base = {}
    for field in ('app', 'layer', 'detection_method', 'injection_phase', 'severity'):
        base[field] = Counter(r.get(field) for r in recs)
    total = len(recs)

    for n, commit, members in multi:
        shared = []
        for field in ('app', 'layer', 'detection_method', 'injection_phase', 'severity'):
            vals = {m.get(field) for m in members}
            if len(vals) == 1:
                v = vals.pop()
                rate = base[field].get(v, 0) / float(total) if total else 0.0
                shared.append({
                    'field': field, 'value': v,
                    'register_rate': rate,
                    # A shared value is only INTERESTING if it is not the norm.
                    'informative': rate < 0.5,
                })
        # Files common to every member of the cluster -- the closest thing the
        # register has to a shared surface.
        filesets = [set(m.get('files') or []) for m in members]
        common_files = sorted(set.intersection(*filesets)) if filesets else []
        clusters.append({
            'commit': commit, 'size': n,
            'date': min((m.get('date') or '') for m in members),
            'subject': (members[0].get('subject') or '')[:90],
            'shared': shared,
            'common_files': common_files[:6],
            'summaries': [(m.get('summary') or '')[:70] for m in members],
        })
    return clusters


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
                          'dimensions': dims,
                          'clusters': backward_trace(recs),
                          'could_not_run': cnr}, indent=1))
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
        # ── THE DISPERSION TEST: THE COLUMN THAT ANSWERS ITEM 59 ──────────
        # The Gini columns above are context. This is the test.
        print('  dimension            disp.index    NB k     verdict')
        for d in dims:
            print('  %-20s %-13s %-8s %s'
                  % (d['dimension'], fmt(d.get('dispersion_index')),
                     fmt(d.get('nb_k')), d.get('dispersion_verdict') or '--'))
        print('')
        print('  A HIGH GINI IS NOT EVIDENCE OF CLUSTERING AT THESE RATES, and')
        print('  reading it as such is the trap this column exists to close.')
        print('  77 defects over 1232 commits gives a Gini near 1 under PURE')
        print('  CHANCE -- almost every commit has zero, which is maximally')
        print('  "unequal" and is not superspreading. The index is the test:')
        print('  1 is Poisson, above 1 is clustered, and the band is 2 standard')
        print('  errors wide because these counts are small. NB k is the')
        print('  epidemiological form -- small k is heavy clustering.')
        print('')
        for d in dims:
            if d.get('dispersion_why'):
                print('  %-20s %s' % (d['dimension'], d['dispersion_why']))
        print('')
        # ── BACKWARD TRACING, and only because the test licensed it ────────
        cl = backward_trace(recs)
        if not cl:
            print('  NO CLUSTER TO TRACE: no commit carries more than one')
            print('  confirmed defect, so there is no common origin to look for')
            print('  and none is invented.')
        else:
            print('  BACKWARD TRACE from the largest clusters. Backward, not')
            print('  forward: on an over-dispersed distribution almost every')
            print('  case infected nobody, so tracing outward from each spends')
            print('  the whole budget on the cases that do not matter.')
            print('  A SHARED ATTRIBUTE IS A CANDIDATE ORIGIN, NEVER A PROVEN')
            print('  ONE -- the register holds no causal graph. Each is scored')
            print('  against its rate in the register, because "all of them are')
            print('  in stonedesk" says nothing if most records are.')
            print('')
            for c in cl:
                print('  %s  %d defects  %s' % (c['commit'], c['size'], c['date']))
                print('      %s' % c['subject'])
                inf = [x for x in c['shared'] if x['informative']]
                dull = [x for x in c['shared'] if not x['informative']]
                for x in inf:
                    print('      SHARED  %-16s %-22s (%.0f%% of the register)'
                          % (x['field'], str(x['value'])[:22], 100 * x['register_rate']))
                if dull:
                    print('      shared but COMMON, so not informative: %s'
                          % ', '.join('%s=%s' % (x['field'], x['value']) for x in dull))
                if c['common_files']:
                    print('      files common to every member: %s'
                          % ', '.join(c['common_files']))
                for sm in c['summaries']:
                    print('        - %s' % sm)
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
