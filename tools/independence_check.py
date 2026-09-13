"""Is a claimed "independent review" actually independent, or the same method twice?

    python tools/independence_check.py --fixtures    # the blind lock alone
    python tools/independence_check.py
    python tools/independence_check.py --json

── THE CARRIED QUESTION, NOW ANSWERED FROM THE RECORD ────────────────────
It was left open whether this platform's Tier A independence bar means a
STRUCTURALLY DIFFERENT method -- a different tool, code path or evidence source
-- or two passes through the same method by different agents.

MEASURED, not decided. 18 index rows carry an independence claim in their STATUS
cell, and by the criteria below: 8 name a DIFFERENT METHOD, 4 name only a second
READER, and 6 name NO METHOD AT ALL. So the answer to the carried question is
that this platform has used BOTH bars and has not been distinguishing them --
and the largest single group, the 6 UNSTATED, claims independence while naming
nothing a reader could check.

Those figures moved twice while this tool was being written, and both moves were
the tool being wrong rather than the index changing. The first filter matched
"independent" ANYWHERE in a row and returned 56 -- every narrative cell that
mentions the idea in passing. The first classifier then read the WHOLE row, so a
"live-verified" written about something else entirely promoted a plain
read-through to DIFFERENT-METHOD and reported 11. Both now read the STATUS cell
only, which is where a claim actually lives.

THAT MATTERS BECAUSE THE WEAK VERSION CANNOT CATCH A SHARED BLIND SPOT. Two
agents reading the same source with the same assumptions share the assumptions.
docs/2026-09-13-cross-domain-disciplines.md item 7 is the sharpest statement of
why: two identical redundant units running the same correct software failed
identically on Ariane 5, because a second copy is not a second opinion. A second
READ is the same shape.

── THE LADDER, BY TIER ───────────────────────────────────────────────────
  TIER C  none required. Cosmetic, device state, preference.
  TIER B  a second-agent read-through. Different eyes, same method, and that is
          proportionate: the consequence of being wrong is operational, not
          money or a regulated record.
  TIER A  a DIFFERENT METHOD, plus live verification, plus mutation-tested
          proof. Three things, because each answers a question the others
          cannot: a different method breaks a shared blind spot, live
          verification proves the deployed thing behaves, and a mutation
          control proves the test would have noticed.

── WHAT THIS CAN AND CANNOT MEASURE, SAID PLAINLY ────────────────────────
It reads the REVIEW CLAIM and classifies the method it names. It cannot tell
whether the review was any good. A row saying "live-verified against production"
is classified DIFFERENT-METHOD whether or not the probe was well chosen.

AND THE MEASUREMENT MICHAEL ASKED FOR -- what fraction of real defects the
independent step catches versus the author's own testing -- IS BLOCKED, which is
the honest headline. docs/defect-density-register.json records
`detection_method` and exactly ONE of 52 records says `independent-review`,
while the index describes at least six independent reviews that found real
defects. The data to answer the question is not being captured. Until it is,
this ships as an ACCUMULATING OBSERVATION LOG that says so, rather than a
statistic computed on n=1.

Exit 0 when every Tier A claim names a different method, 1 when one does not,
2 when the fixtures fail -- which means nothing real was classified.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')
REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')
CRITERIA_VERSION = '2026-09-13.1'

# ── THE CRITERIA, decided before the index was read for content ───────────
# A phrase that names a SECOND, STRUCTURALLY DIFFERENT source of evidence.
# Each of these is a different way of being wrong from "somebody read it".
DIFFERENT_METHOD = (
    'live-verified', 'live verified', 'live-confirmed', 'live confirmed',
    'against production', 'on production', 'live probe', 'live check',
    'fault-injection', 'fault injection', 'mutation control', 'mutation-tested',
    'negative control', 'property test', 'schema snapshot', 'live read',
    'independently measured', '503', 'two sources',
)
# A phrase that names a second READER and nothing else. Different eyes, same
# method -- the shape that cannot break a shared assumption.
SAME_METHOD = (
    'reviewed', 'review done', 'read-through', 'read through', 'questions answered',
    'items answered', 'no findings', 'independently reviewed', 'second pair of eyes',
)


def classify(text):
    t = re.sub(r'[*`~]', '', text or '').lower()
    if any(p in t for p in DIFFERENT_METHOD):
        return 'DIFFERENT-METHOD'
    if any(p in t for p in SAME_METHOD):
        return 'SAME-METHOD'
    return 'UNSTATED'


# Hand-decided BEFORE the index was read for content. The controls matter: a
# classifier that answered DIFFERENT-METHOD to everything would satisfy the
# positive arms alone.
FIXTURES = [
    ('a live probe against production is a different method',
     'FIXED and live-confirmed on production', 'DIFFERENT-METHOD'),
    ('a fault-injection run is a different method',
     'found by the first fault-injection run this platform has done', 'DIFFERENT-METHOD'),
    ('a mutation control is a different method',
     'eight mutation controls all bite', 'DIFFERENT-METHOD'),
    ('two sources sharing no mechanism is the strongest form',
     'confirmed by two sources that do not share a mechanism', 'DIFFERENT-METHOD'),
    ('CONTROL: a second agent reading it is SAME-METHOD',
     'REVIEW DONE 2026-09-08 (CC), not Hank. All six items answered', 'SAME-METHOD'),
    ('CONTROL: "no findings" from a reader is SAME-METHOD',
     'INDEPENDENTLY REVIEWED 2026-09-10 (Hank) -- no findings', 'SAME-METHOD'),
    ('CONTROL: a claim naming no method at all is UNSTATED',
     'CLOSED 2026-09-04, and it is done', 'UNSTATED'),
    ('a row naming BOTH counts as the stronger one',
     'INDEPENDENTLY REVIEWED and live-verified on production', 'DIFFERENT-METHOD'),
]


def run_fixtures():
    return [(n, w, classify(t)) for n, t, w in FIXTURES if classify(t) != w]


def rows():
    """Every index row claiming an independent review, with its tier if named."""
    out = []
    if not os.path.exists(INDEX):
        return out
    for line in io.open(INDEX, encoding='utf-8'):
        if not line.startswith('|'):
            continue
        cells = line.split('|')
        if len(cells) < 4:
            continue
        # THE CLAIM LIVES IN THE STATUS CELL, not anywhere in the row. The first
        # version matched the word "independent" ANYWHERE in the line and
        # returned 56 rows against 11 real claims -- every narrative cell that
        # merely mentions independence in passing. A row that discusses the idea
        # is not a row claiming a review was done.
        status = re.sub(r'\s+', ' ', cells[3]).strip()
        if 'independent' not in status.lower():
            continue
        app = re.sub(r'[*`]', '', cells[1]).strip()
        # Classified on the STATUS CELL, for the same reason it is filtered on
        # it. Classifying the whole line let a narrative cell elsewhere in the
        # row -- "live-verified" mentioned about something else entirely --
        # promote a plain read-through to DIFFERENT-METHOD.
        out.append({'app': app, 'status': status[:160],
                    'method': classify(status)})
    return out


def register_capture():
    """Is detection_method capturing independent review at all?"""
    try:
        recs = json.load(io.open(REGISTER, encoding='utf-8')).get('records', [])
    except Exception:
        return None
    ind = [r for r in recs if str(r.get('detection_method', '')).startswith('independent')]
    return {'records': len(recs), 'independent_review': len(ind),
            'has_rules_field': sum(1 for r in recs if r.get('rules'))}


def main(argv):
    bad = run_fixtures()
    print('INDEPENDENCE CHECK -- criteria %s, report only' % CRITERIA_VERSION)
    if bad:
        print('  !! THE CRITERIA FAILED THEIR OWN FIXTURES. NOTHING REAL WAS CLASSIFIED.')
        for n, w, g in bad:
            print('     expected %-18s got %-18s %s' % (w, g, n))
        return 2
    print('  blind lock: %d/%d fixtures correct, run before the index was read.'
          % (len(FIXTURES), len(FIXTURES)))
    if '--fixtures' in argv:
        return 0

    rs = rows()
    counts = {}
    for r in rs:
        counts[r['method']] = counts.get(r['method'], 0) + 1
    cap = register_capture()

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'rows': rs,
                          'counts': counts, 'register_capture': cap}, indent=1))
        return 1 if counts.get('SAME-METHOD') or counts.get('UNSTATED') else 0

    print('  rows claiming an independent review: %d' % len(rs))
    for k in ('DIFFERENT-METHOD', 'SAME-METHOD', 'UNSTATED'):
        note = {'DIFFERENT-METHOD': '  <- a second EVIDENCE SOURCE',
                'SAME-METHOD': '  <- a second READER. Cannot break a shared blind spot',
                'UNSTATED': '  <- claims independence and names no method'}[k]
        print('    %-18s %2d%s' % (k, counts.get(k, 0), note))
    print('')
    print('  THE LADDER, BY TIER: C none; B a second-agent read-through; A a')
    print('  DIFFERENT METHOD plus live verification plus a mutation-tested proof.')
    print('  A Tier A row classified SAME-METHOD has met the Tier B bar, not the A one.')
    for r in rs:
        if r['method'] != 'DIFFERENT-METHOD':
            print('')
            print('    %-18s %s' % (r['method'], r['app'][:40]))
            print('      %s' % r['status'][:120])

    print('')
    print('  ── THE MEASUREMENT MICHAEL ASKED FOR IS BLOCKED, AND THAT IS THE')
    print('  ── HEADLINE, NOT A FOOTNOTE ─────────────────────────────────────')
    if cap:
        print('  docs/defect-density-register.json: %d records, %d with'
              % (cap['records'], cap['independent_review']))
        print('  detection_method = independent-review. The index above describes')
        print('  %d independent reviews, several of which FOUND REAL DEFECTS.' % len(rs))
        print('  The data needed to answer "what fraction does the independent step')
        print('  catch" IS NOT BEING CAPTURED. A rate computed on %d record(s) would'
              % cap['independent_review'])
        print('  be a number, not evidence -- so none is offered.')
        print('')
        print('  THE FIX IS SMALL AND CONCRETE: record detection_method =')
        print('  independent-review when a review finds a defect, and backfill the')
        print('  known ones. Same shape as the FMEA scorer being blocked on a')
        print('  rules-citation field: the tool is ready, the input is not.')
    else:
        print('  the register could not be read -- NOT a pass.')
    return 1 if (counts.get('SAME-METHOD') or counts.get('UNSTATED')) else 0


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1:]))
