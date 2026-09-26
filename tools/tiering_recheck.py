"""tools/tiering_recheck.py -- methodology item 26, phase 2: which tier assignments
has the platform's own review history earned the right to doubt?

    python tools/tiering_recheck.py
    python tools/tiering_recheck.py --candidates   # the proposal list alone

── WHY THIS COULD NOT BE BUILT UNTIL NOW, AND WHAT CHANGED ─────────────────
Item 26 was gated on Batch 3 -- the standing rule that a DIFFERENT agent reviews
another's Tier A work, recorded with a detection_method. The gate was not a
technical dependency: a tiering re-check driven by review history is worthless
until there IS review history, and a tool built early would have correlated
nothing and reported confidence it had not earned.

There is history now, and it is not thin: 167 records in
docs/tier-a-reviews.json across 245 distinct resources, and 74 of the 304
records in docs/defect-density-register.json carry
`detection_method: independent-review` -- a quarter of every defect this platform
has recorded was found by one agent reading another's work.

── THE QUESTION IT ASKS, WHICH IS NOT "IS THIS TIER RIGHT" ─────────────────
Nothing here judges a tier. A tier is a judgement about consequence and this
tool has no access to consequence. What it has is EVIDENCE OF SURPRISE: places
where independent review kept finding real defects. A resource whose area keeps
surprising reviewers is a resource whose tier was set with less information than
exists now -- in either direction.

  * a B resource in an app where independent review has found HIGH or CRITICAL
    defects is a RECHECK CANDIDATE: the reviews found things the tier did not
    anticipate
  * an A resource with many reviews and no independent-review defects is
    EVIDENCE THE TIER IS EARNING ITS COST, reported so the list is not only
    bad news
  * a resource with NO review and NO defect data is UNEXAMINED, which is a
    third state and is never folded into either of the others

── IT PROPOSES AND IT MAY NEVER APPLY (cross-domain disciplines, item 11) ───
This tool does not edit docs/CRITICALITY-TIERS.md and must not be given the
ability to. A detector that blesses its own re-tier is the defect that
discipline names, one step later -- and a tier promotion here is not even a cell
edit: SC_TIER_A_SOFT_DELETE_ONLY and the write gates DERIVE from the Tier A
list, so an A withdraws a resource's `delete` verb and moves its client remove
path. Every output below is a sentence for the register owner to act on or
reject.

── WHAT IT CANNOT SEE, STATED RATHER THAN DISCOVERED ───────────────────────
THE LINK IS PER APP, NOT PER RESOURCE, and that is the biggest limit. Defect
records carry `app` and `files`, not resource names, so a defect found in
sairncode is attributed to every sairncode resource. That OVER-attributes: one
defect in one branch raises the signal for every resource in the app. The
per-resource half is recoverable only from the review records' own `resources`
lists, which is why both signals are reported separately and never summed into
one score. A single number here would be exactly the fabricated-metric shape
this platform polices hardest.

It also cannot see reviews that found nothing and were never recorded, cannot
weight a defect by how close it came to shipping, and has no opinion on
confidentiality at all -- every signal it carries is about integrity surprise.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIERS = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
REVIEWS = os.path.join(REPO, 'docs', 'tier-a-reviews.json')
DEFECTS = os.path.join(REPO, 'docs', 'defect-density-register.json')

SEVERE = ('critical', 'high')


class CouldNotTell(Exception):
    pass


def _load(path, what):
    if not os.path.isfile(path):
        raise CouldNotTell('%s does not exist, so %s could not be read -- nothing '
                           'was correlated' % (os.path.relpath(path, REPO), what))
    try:
        return json.load(io.open(path, encoding='utf-8'))
    except ValueError as e:
        raise CouldNotTell('%s will not parse (%s), so %s could not be read'
                           % (os.path.relpath(path, REPO), e, what))


def read_tiers():
    """{resource: (integrity, confidentiality)} from the register's own row anchor."""
    if not os.path.isfile(TIERS):
        raise CouldNotTell('docs/CRITICALITY-TIERS.md does not exist')
    out = {}
    src = io.open(TIERS, encoding='utf-8', errors='replace').read()
    for line in src.split('\n'):
        m = re.match(r'^\| `([a-z0-9_]+)` \| \*\*([ABC])\*\* \| \*\*([ABC])\*\* \|', line)
        if m:
            out[m.group(1)] = (m.group(2), m.group(3))
    if not out:
        raise CouldNotTell('no resource row matched the register\'s row anchor -- '
                           'the format moved and NOTHING was correlated. This is '
                           'not "no resources".')
    return out


def resource_app():
    """{resource: app} by RUNNING the registry, never by parsing it.

    api/_resources/index.js owns OWNER_BY_RESOURCE and is the only thing that
    knows. A regex over the directory would be a second copy of that map, which
    is the drift api/_resources exists to prevent.
    """
    src = ('process.stdout.write(JSON.stringify('
           'require("./api/_resources").OWNER_BY_RESOURCE || {}));')
    try:
        r = subprocess.run(['node', '-e', src], cwd=REPO, capture_output=True,
                           text=True, encoding='utf-8', errors='replace', timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise CouldNotTell('could not run the resource registry (%s: %s), so no '
                           'resource could be attributed to an app'
                           % (type(e).__name__, e))
    if r.returncode != 0:
        raise CouldNotTell('the resource registry exited %d: %s'
                           % (r.returncode, (r.stderr or '')[:200]))
    try:
        m = json.loads(r.stdout)
    except ValueError as e:
        raise CouldNotTell('the resource registry returned unreadable JSON: %s' % e)
    if not m:
        raise CouldNotTell('OWNER_BY_RESOURCE is empty -- every resource would be '
                           'unattributed and every signal would read as zero')
    return m


def collect():
    tiers = read_tiers()
    owner = resource_app()
    reviews = _load(REVIEWS, 'the review history')['records']
    defects = _load(DEFECTS, 'the defect register')['records']

    # PER-RESOURCE: how often has independent review looked directly at this row?
    #
    # THE TOTAL OF THESE COUNTS IS PAIRS, NOT RECORDS, and saying otherwise was
    # this tool's own first wrong number. One review record naming twelve
    # resources contributes twelve. The file holds 167 records and this sums to
    # 789 -- reporting 789 as "review records" inflates the corpus 4.7x in the
    # one direction that flatters the tool, which is the fabricated-metric shape
    # this platform polices hardest. Both are carried and both are labelled.
    reviewed = {}
    for rec in reviews:
        for n in (rec.get('resources') or []):
            reviewed.setdefault(n, {'total': 0, 'discharged': 0})
            reviewed[n]['total'] += 1
            if (rec.get('verdict') or '').strip():
                reviewed[n]['discharged'] += 1

    # PER APP: what did independent review actually FIND? Kept apart from the
    # per-resource count on purpose -- see the module docstring.
    app_found = {}
    for rec in defects:
        if rec.get('detection_method') != 'independent-review':
            continue
        app = (rec.get('app') or '').strip()
        if not app:
            continue
        a = app_found.setdefault(app, {'n': 0, 'severe': 0, 'examples': []})
        a['n'] += 1
        if (rec.get('severity') or '').lower() in SEVERE:
            a['severe'] += 1
            if len(a['examples']) < 3:
                a['examples'].append('%s: %s' % (rec.get('severity'),
                                                 (rec.get('summary') or '')[:90]))
    return tiers, owner, reviewed, app_found, len(reviews)


def classify(res, tiers, owner, reviewed, app_found):
    integ = tiers[res][0]
    app = owner.get(res)
    seen = reviewed.get(res, {'total': 0, 'discharged': 0})
    found = app_found.get(app, {'n': 0, 'severe': 0, 'examples': []})
    if app is None:
        return 'UNATTRIBUTED', app, seen, found
    if not seen['total'] and not found['n']:
        return 'UNEXAMINED', app, seen, found
    # ── THE FIRST CRITERION WAS TOO WIDE AND ITS OWN OUTPUT SAID SO ─────────
    # It read `integ in ('B','C') and found['severe']` -- app signal alone -- and
    # returned 95 candidates, every B row in any app with a severe finding, all
    # of them `reviews=0`. 95 undifferentiated lines is furniture, and a report
    # nobody reads is worse than none.
    #
    # THE CLAIM IS "the reviews found something the tier did not anticipate", and
    # that requires the reviews to have LOOKED AT THIS ROW. A row nobody has
    # reviewed carries no review evidence about itself, whatever its neighbours
    # did -- so it is a different finding and gets its own bucket below rather
    # than being folded in to make this list look thorough.
    if integ in ('B', 'C') and found['severe'] and seen['total']:
        return 'RECHECK', app, seen, found
    # A REVIEW-SCHEDULING SIGNAL, NOT A TIER ONE, and worth naming precisely
    # because it is the larger population: this app has surprised reviewers and
    # nobody has looked at this row yet.
    if integ in ('B', 'C') and found['severe']:
        return 'UNREVIEWED-IN-SURPRISING-APP', app, seen, found
    if integ == 'A' and seen['total'] >= 2 and not found['severe']:
        return 'EARNING', app, seen, found
    return 'NO-SIGNAL', app, seen, found


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidates', action='store_true',
                    help='print only the recheck candidates')
    args = ap.parse_args(argv)
    try:
        tiers, owner, reviewed, app_found, n_records = collect()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- %s\n' % e)
        sys.stderr.write('This is the THIRD STATE and is NOT a clean run.\n')
        return 2

    buckets = {}
    for res in sorted(tiers):
        kind, app, seen, found = classify(res, tiers, owner, reviewed, app_found)
        buckets.setdefault(kind, []).append((res, app, seen, found))

    if not args.candidates:
        print('TIERING RE-CHECK -- methodology item 26 phase 2')
        print('Correlating %d review record(s) -- %d record-resource pair(s) '
              'across %d resource(s), NOT %d reviews -- and %d '
              'independent-review defect(s) against %d tiered resource(s).'
              % (n_records, sum(v['total'] for v in reviewed.values()),
                 len(reviewed), sum(v['total'] for v in reviewed.values()),
                 sum(v['n'] for v in app_found.values()), len(tiers)))
        print('')
        print('IT PROPOSES AND NEVER RE-TIERS. Every line below is a sentence for')
        print('the register owner; nothing here edits docs/CRITICALITY-TIERS.md.')
        print('')

    # ── THE STRUCTURAL FINDING, PRINTED BEFORE THE EMPTY LIST IT EXPLAINS ──
    # An empty RECHECK list would read as "nothing to do". It is not: it is a
    # measurement of what this corpus CANNOT answer, and the number is the point.
    a_rows = [r for r in tiers if tiers[r][0] == 'A']
    bc_rows = [r for r in tiers if tiers[r][0] in ('B', 'C')]
    a_seen = [r for r in a_rows if reviewed.get(r)]
    bc_seen = [r for r in bc_rows if reviewed.get(r)]
    if not args.candidates:
        print('THE REVIEW CORPUS IS BLIND IN THE DIRECTION A RE-CHECK MOST NEEDS,')
        print('and that is the headline of this pass rather than a caveat on it:')
        print('   Tier A rows  %3d, reviewed %3d  -> %.1f%%'
              % (len(a_rows), len(a_seen),
                 100.0 * len(a_seen) / len(a_rows) if a_rows else 0))
        print('   Tier B/C     %3d, reviewed %3d  -> %.1f%%'
              % (len(bc_rows), len(bc_seen),
                 100.0 * len(bc_seen) / len(bc_rows) if bc_rows else 0))
        print('The review gate opens an obligation when TIER A CODE changes, so a')
        print('row left at B is never reviewed and no review can ever surprise')
        print('anybody about it. UNDER-tiering is the error this mechanism cannot')
        print('see, and under-tiering is the direction that leaves a real record')
        print('under-protected. Review history can confirm an A is earning its cost')
        print('and can RANK which B/C rows to read first -- it cannot tell you a B')
        print('is wrong. That needs a read, which is what the ranking below is for.')
        print('')

    cand = buckets.get('RECHECK', [])
    print('RECHECK CANDIDATES: %d%s' % (len(cand),
          '   (structurally reachable only once a B/C row has been reviewed -- '
          'see above)' if not cand else ''))
    print('A B-or-C row in an app where independent review has found a HIGH or')
    print('CRITICAL defect. The reviews found something the tier did not expect.')
    for res, app, seen, found in sorted(cand, key=lambda x: (-x[3]['severe'], x[0])):
        print('   %-26s %-14s tier I=%s  reviews=%d  app severe finds=%d'
              % (res, app, tiers[res][0], seen['total'], found['severe']))
    if cand and not args.candidates:
        print('')
        print('   what those reviews actually found, per app:')
        for app in sorted({a for _, a, _, _ in cand}):
            for ex in app_found.get(app, {}).get('examples', []):
                print('     %-14s %s' % (app, ex))

    if args.candidates:
        return 1 if cand else 0

    unrev = buckets.get('UNREVIEWED-IN-SURPRISING-APP', [])
    print('')
    print('UNREVIEWED IN A SURPRISING APP: %d' % len(unrev))
    print('B-or-C rows in an app where independent review HAS found a HIGH or')
    print('CRITICAL defect, and which no review has looked at. This is a REVIEW')
    print('SCHEDULING signal, not a tier one -- there is no review evidence about')
    print('these rows, only about their neighbours. Grouped by app, worst first.')
    by_app = {}
    for res, app, seen, found in unrev:
        by_app.setdefault(app, {'n': 0, 'severe': found['severe']})
        by_app[app]['n'] += 1
    for app in sorted(by_app, key=lambda a: -by_app[a]['severe']):
        print('   %-14s %3d unreviewed B/C row(s), %d severe find(s) in the app'
              % (app, by_app[app]['n'], by_app[app]['severe']))

    print('')
    print('EARNING ITS COST: %d' % len(buckets.get('EARNING', [])))
    print('Tier A, reviewed two or more times, and independent review has found no')
    print('HIGH/CRITICAL defect in the app. Reported so this is not only bad news.')
    for res, app, seen, found in sorted(buckets.get('EARNING', []))[:12]:
        print('   %-26s %-14s reviews=%d' % (res, app, seen['total']))
    if len(buckets.get('EARNING', [])) > 12:
        print('   ... and %d more' % (len(buckets['EARNING']) - 12))

    print('')
    print('UNEXAMINED: %d -- no review record and no independent-review defect in'
          % len(buckets.get('UNEXAMINED', [])))
    print('their app. A THIRD STATE: not evidence the tier is right, and not')
    print('evidence it is wrong. Nobody has looked.')

    unatt = buckets.get('UNATTRIBUTED', [])
    print('')
    print('UNATTRIBUTED: %d -- tiered but absent from OWNER_BY_RESOURCE, so no app'
          % len(unatt))
    print('signal can reach them. That is a registry gap, not a tier finding.')
    for res, _app, _s, _f in sorted(unatt)[:8]:
        print('   %s' % res)
    if len(unatt) > 8:
        print('   ... and %d more' % (len(unatt) - 8))

    print('')
    print('NO-SIGNAL: %d' % len(buckets.get('NO-SIGNAL', [])))
    print('')
    print('THE LINK IS PER APP, NOT PER RESOURCE. A defect found anywhere in an')
    print('app raises the signal for every resource in it, so a candidate is a')
    print('QUESTION about a row, never a verdict on it. The two signals are')
    print('printed apart and are never summed -- a single score here would be the')
    print('fabricated-metric shape this platform polices hardest.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
