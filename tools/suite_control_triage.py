"""Which of the uncontrolled suites to sabotage FIRST, ranked by what they guard.

    python tools/suite_control_triage.py
    python tools/suite_control_triage.py --fixtures
    python tools/suite_control_triage.py --tier A

`tools/suite_control_coverage.py` answers HOW MANY suites have ever been proven
to catch a real defect -- 7 of 154 when this was written. That is the census. It
deliberately does not say which of the other 147 matter, and the honest sentence
in its own output is why: *"THIS IS NOT A LIST OF BAD SUITES. A pure-function
unit test over a table of inputs has little to sabotage."* A flat list of 147 is
a number nobody can act on, and working down it alphabetically spends the first
hour on `ai_shortcuts_reach_the_chat.js`.

This ranks them by the CRITICALITY TIER of the resources each suite actually
names, so the work starts where being wrong costs the most.

── THE RANKING IS DERIVED FROM TWO EXISTING SOURCES, NOT INVENTED HERE ──────
  * the census comes from `suite_control_coverage.survey()`, imported rather
    than re-implemented -- a second copy of "which suites have a control" would
    be a second answer to a question that already has one, and the two would
    drift;
  * the tiers come from `docs/CRITICALITY-TIERS.md`, the hand-written register
    `tools/criticality_tier_check.py` already guards.

So this file owns exactly one new idea: the join between them.

── THE THIRD BUCKET IS THE POINT, AND IT IS NOT A LOW PRIORITY ──────────────
A suite that names no registered resource is reported UNCLASSIFIED, separately
from Tier C. It is NOT "safe to skip": `sd-data-session-gate.test.js` guards the
gate in front of every resource and names none of them. This tool cannot rank
those and says so rather than sorting them to the bottom, which would read as a
judgement it did not make. PR 1.11 in its ranking form -- "could not tell" is
not "low".

── WHAT A HIGH RANK DOES AND DOES NOT MEAN ──────────────────────────────────
It means: this suite is the only thing standing between a Tier A resource and a
silent regression, and nobody has ever seen it go red. It does NOT mean the
suite is weak -- that is unmeasured, which is the entire finding. Writing the
negative control is what converts the unknown into either answer.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import EXIT_CLEAN, EXIT_COULD_NOT_RUN, read   # noqa: E402
import suite_control_coverage                                  # noqa: E402

TIERS_DOC = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')

# `| `sb_payruns` | **A** | ... |` -- the per-resource rows in the app sections.
# Anchored to the start of a table row so the tier VOCABULARY table near the top
# ("| **A** | handles money ...") cannot be read as a resource named "**A**".
ROW = re.compile(r'^\|\s*`([A-Za-z0-9_]+)`\s*\|\s*\*\*([ABC])\*\*\s*\|', re.M)

RANK = {'A': 0, 'B': 1, 'C': 2}


def tier_map(doc_text):
    """{resource name: tier}. A resource listed twice at DIFFERENT tiers raises.

    Not defensive: `stonedesk` and the fifteen-app section are separate tables
    in one file, and a resource that appeared in both at different tiers would
    make every ranking below depend on which table was parsed last. That is the
    kind of disagreement a tool must refuse rather than resolve by ordering.
    """
    out = {}
    for name, tier in ROW.findall(doc_text):
        if name in out and out[name] != tier:
            raise ValueError('%s is tiered both %s and %s in %s -- the register '
                             'disagrees with itself and the ranking below would '
                             'depend on parse order'
                             % (name, out[name], tier, os.path.basename(TIERS_DOC)))
        out[name] = tier
    return out


def resources_named(src, tiers):
    """The tiered resources this suite source actually references.

    Word-boundary, because `dnt_ar` is a substring of `dnt_area` and a
    substring match would tier a suite by a resource it never touches. Comments
    are NOT stripped: a suite whose comment names the resource it covers is
    still evidence of what it covers, and the cost of a false positive here is
    a suite ranked too high, which wastes an hour rather than hiding a gap.
    That asymmetry is deliberate and is the opposite of the choice a detector
    would make.
    """
    return sorted(n for n in tiers
                  if re.search(r'\b' + re.escape(n) + r'\b', src))


def classify(suite_basename, src, tiers):
    """(bucket, [resources]) -- bucket is 'A', 'B', 'C' or 'UNCLASSIFIED'."""
    hits = resources_named(src, tiers)
    if not hits:
        return 'UNCLASSIFIED', []
    best = min(tiers[h] for h in hits)          # 'A' < 'B' < 'C' as strings
    return best, hits


def _suite_path(basename):
    for d in ('tests', 'api'):
        p = os.path.join(REPO, d, basename)
        if os.path.isfile(p):
            return p
    return None


# ── THE BLIND LOCK ───────────────────────────────────────────────────────────
# Criteria locked against synthetic sources before the tool is pointed at the
# real tree. The substring arm is the one that matters: it is the difference
# between ranking a suite by what it guards and ranking it by a coincidence of
# spelling.
FIXTURES = (
    ('names a Tier A resource',       "post('dnt_payments', row)",        'A', ['dnt_payments']),
    ('names a Tier B resource',       "get('sb_ap')",                     'B', ['sb_ap']),
    ('A wins when both appear',       "sb_ap; dnt_payments;",             'A', ['dnt_payments', 'sb_ap']),
    ('names nothing registered',      "assert(add(2,2) === 4)",  'UNCLASSIFIED', []),
    # Substring, both directions. `dnt_ar` must not be found inside `dnt_area`.
    ('substring is not a match',      "const dnt_area = 1;",     'UNCLASSIFIED', []),
    ('the real name still matches',   "const x = dnt_ar;",                'A', ['dnt_ar']),
    # A resource name inside a longer identifier, the other direction.
    ('prefixed identifier is not it', "legacy_sb_ap_old()",      'UNCLASSIFIED', []),
)

FIXTURE_TIERS = {'dnt_payments': 'A', 'dnt_ar': 'A', 'sb_ap': 'B', 'sdn_theme': 'C'}


def run_fixtures():
    wrong = []
    for label, src, want_bucket, want_hits in FIXTURES:
        bucket, hits = classify('<fixture>', src, FIXTURE_TIERS)
        if bucket != want_bucket or hits != want_hits:
            wrong.append('%-30s expected %s %s, got %s %s'
                         % (label, want_bucket, want_hits, bucket, hits))

    # And the register-disagrees-with-itself refusal, which is the arm that
    # cannot be checked by classifying anything.
    try:
        tier_map('| `x` | **A** | a | b |\n| `x` | **B** | a | b |\n')
        wrong.append('%-30s a self-contradicting register was ACCEPTED'
                     % 'duplicate at two tiers')
    except ValueError:
        pass
    # ...and that a resource repeated at the SAME tier is fine, or every app
    # section listing a shared resource would refuse.
    try:
        m = tier_map('| `x` | **A** | a | b |\n| `x` | **A** | a | b |\n')
        if m != {'x': 'A'}:
            wrong.append('%-30s got %r' % ('duplicate at same tier', m))
    except ValueError as e:
        wrong.append('%-30s refused a register that agrees with itself: %s'
                     % ('duplicate at same tier', e))
    # The vocabulary table at the top of the real document must not parse as a
    # resource. This is the arm that caught the first version.
    m = tier_map('| Tier | A resource qualifies when it... |\n'
                 '| **A** | handles **money** |\n')
    if m:
        wrong.append('%-30s the tier LEGEND parsed as a resource: %r'
                     % ('legend is not a resource', m))

    if wrong:
        print('REFUSING: the criteria do not classify their own fixtures.')
        for w in wrong:
            print('  ' + w)
        return EXIT_COULD_NOT_RUN
    print('  %d/%d fixtures correct, plus 4 register-parse arms.'
          % (len(FIXTURES), len(FIXTURES)))
    return EXIT_CLEAN


def main(argv):
    if '--fixtures' in argv:
        return run_fixtures()

    if not os.path.isfile(TIERS_DOC):
        print('COULD NOT RUN: %s is missing. The ranking has no tier source, '
              'and an unranked list of 147 is what this tool exists to replace.'
              % TIERS_DOC)
        return EXIT_COULD_NOT_RUN
    try:
        tiers = tier_map(read(TIERS_DOC))
    except ValueError as e:
        print('COULD NOT RUN: %s' % e)
        return EXIT_COULD_NOT_RUN
    if not tiers:
        print('COULD NOT RUN: parsed 0 resources out of %s. The row format '
              'changed and this tool would otherwise report every suite as '
              'UNCLASSIFIED -- which looks exactly like a clean answer.'
              % os.path.basename(TIERS_DOC))
        return EXIT_COULD_NOT_RUN

    # survey() gained a fourth return on 2026-09-17 -- the suites that mutate
    # their own source with no visible applied-check. Not used here (this file
    # ranks what is UNCONTROLLED, and those are already uncontrolled), but it is
    # unpacked by name rather than swallowed so the next reader can see it
    # exists rather than discovering it through a tuple-length crash, which is
    # how this line was found.
    (suites, controllers, unreadable,
     _inline_unverified) = suite_control_coverage.survey()
    uncontrolled = [s for s in suites if s not in controllers]

    buckets = {'A': [], 'B': [], 'C': [], 'UNCLASSIFIED': []}
    could_not_read = []
    for b in uncontrolled:
        p = _suite_path(b)
        if p is None:
            could_not_read.append((b, 'not found under tests/ or api/'))
            continue
        try:
            src = io.open(p, encoding='utf-8', errors='replace').read()
        except OSError as e:                                    # noqa: BLE001
            could_not_read.append((b, repr(e)))
            continue
        bucket, hits = classify(b, src, tiers)
        buckets[bucket].append((b, hits))

    want = None
    if '--tier' in argv:
        want = argv[argv.index('--tier') + 1].upper()

    print('UNCONTROLLED SUITE TRIAGE -- report only, nothing gates on this')
    print('  %d suite(s); %d have a negative control; %d do not.'
          % (len(suites), len(controllers), len(uncontrolled)))
    print('  %d tiered resources read from %s'
          % (len(tiers), os.path.basename(TIERS_DOC)))
    print('')
    print('  TIER A         %3d   money or a regulated record. START HERE.'
          % len(buckets['A']))
    print('  TIER B         %3d   employee-gated operational data' % len(buckets['B']))
    print('  TIER C         %3d   cosmetic, device state, preference' % len(buckets['C']))
    print('  UNCLASSIFIED   %3d   names no registered resource -- NOT low, unranked'
          % len(buckets['UNCLASSIFIED']))
    print('')

    for key in ('A', 'B', 'C', 'UNCLASSIFIED'):
        if want and key != want:
            continue
        rows = sorted(buckets[key])
        if not rows:
            continue
        # ASCII on purpose. A box-drawing character here raised
        # UnicodeEncodeError under cp1252 the first time this was piped, which
        # killed the run AFTER the summary had already printed -- a truncated
        # report that looks like a complete one.
        print('  -- %s (%d) ' % (key, len(rows)) + '-' * max(0, 48 - len(key)))
        for b, hits in rows:
            shown = ', '.join(hits[:4]) + ('  +%d more' % (len(hits) - 4)
                                           if len(hits) > 4 else '')
            print('    %-46s %s' % (b, shown))
        print('')

    if unreadable:
        print('  PROBES THAT COULD NOT BE PARSED (%d) -- a control may exist and '
              'not be credited:' % len(unreadable))
        for n, why in unreadable:
            print('    %-44s %s' % (n, why))
    if could_not_read:
        print('  SUITES THAT COULD NOT BE READ (%d) -- unranked, and that is not '
              'the same as Tier C:' % len(could_not_read))
        for n, why in could_not_read:
            print('    %-44s %s' % (n, why))

    print('  A HIGH RANK IS NOT A CLAIM THAT THE SUITE IS WEAK. It is a claim')
    print('  that its strength is UNMEASURED while the thing it guards is the')
    print('  most expensive kind to get wrong. Writing the control is what')
    print('  turns that into either answer.')
    return EXIT_COULD_NOT_RUN if (unreadable or could_not_read) else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
