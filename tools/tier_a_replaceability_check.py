"""Is a Tier A resource the irreplaceable artifact, or can it be destroyed?

    python tools/tier_a_replaceability_check.py
    python tools/tier_a_replaceability_check.py --json

ITEM 97 -- THE HALF THE TIER RUBRIC DOES NOT ASK. `docs/CRITICALITY-TIERS.md`
assigns a tier from "the worst consequence of that resource being WRONG". That
is one of the two questions aerospace asks of a serial number. The other is
whether the thing in front of you is the article that flies or a stand-in built
to look like it -- a boilerplate capsule, a mass simulator, a pathfinder. Both
look identical on a bench. Only one of them is unrecoverable if it is lost, and
applying flight rigour to the wrong one is not the expensive mistake; it is the
cheap one. The expensive mistake is the reverse.

SO THIS TOOL ASKS THE SECOND QUESTION AND ONLY THE SECOND. For every Tier A
resource it crosses the register against the LIVE verb grants in
`api/_resources/`, and reports which Tier A artifacts a caller can DESTROY
rather than hide.

WHAT IT MEASURES, and each is a fact from a file rather than a judgement:

  HARD DELETE  the resource grants the `delete` verb -- the row is gone
  SOFT ONLY    it grants `soft_delete` -- marked and hidden, the row survives
  NO DELETE    no delete verb of either kind is reachable at all

AND ONE LANGUAGE MEASUREMENT, REPORTED SEPARATELY BECAUSE IT IS WEAKER. The
register's own rule is that every Tier A row cites something real. This counts
how many of those evidence cells say anything about RECOVERABILITY -- backup,
soft-delete, append-only, only-copy. It reads language, not intent, so a row
that establishes replaceability in words this does not match is a false hit.
It is printed as a documentation coverage figure and never as a defect count.

WHAT IT CANNOT SEE, said plainly:

  * WHETHER A TIER IS RIGHT. criticality_tier_check.py already says nothing
    mechanical can, and that is still true. This adds one axis, not a verdict.
  * THE UNDER-ASSIGNMENT DIRECTION, which is the dangerous one. A Tier B or C
    resource that is in fact the only copy of something irreplaceable is
    exactly what item 97 is about and this tool does NOT sweep for it. Naming
    the gap rather than implying coverage.
  * WHETHER A BACKUP EXISTS. It reads no infrastructure. As of 2026-09-14
    `docs/2026-09-14-nightly-backup-design.md` records that the nightly backup
    has NEVER RUN and Supabase is on a free tier with no automated backups, so
    a hard delete today is unrecoverable -- but that is a dated statement from
    a document, not something this tool checked. Re-read it before quoting it.

REPORT ONLY. Nothing is blocked and nothing should be: a hard delete verb is
not a defect, it is a decision, and this platform has made it deliberately in
both directions (`sv_controlled` has no delete verb ON PURPOSE; SAIRNdental
chose `soft_delete` and its registry says "not 'delete'"). What the tool
surfaces is a Tier A resource whose delete grant was never a per-resource
decision at all.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import criticality_tier_check as ctc                             # noqa: E402

REGISTER = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')

# Deliberately generous: a false HIT here understates the gap, which is the
# safe direction for a figure reported as "documentation coverage".
RECOVERABILITY = re.compile(
    r'soft.?delete|backup|backed up|recover|restore|only record|only copy|'
    r'irreplace|append-only|additive-only|immutab|cannot be deleted|no delete',
    re.I)


def tier_rows(text):
    """(resource, tier, evidence) for every row that states a tier."""
    out = []
    for line in text.split('\n'):
        if not line.startswith('|'):
            continue
        cells = ctc.cells(line)
        if len(cells) < 4:
            continue
        tier = cells[1].replace('*', '').strip()
        if tier in ('A', 'B', 'C'):
            out.append((cells[0].strip('` '), tier, cells[3]))
    return out


def extra_actions():
    """The LIVE verb grants, read by running the registry rather than by
    re-parsing it. index.js composes eighteen modules and one of them builds
    its grants with a reduce() -- a regex over the source would miss exactly
    the case this tool exists to report."""
    src = ('const i=require("./api/_resources/index.js");'
           'process.stdout.write(JSON.stringify({e:i.EXTRA_ACTIONS,'
           'o:i.OWNER_BY_RESOURCE,n:i.RESOURCE_NAMES}));')
    try:
        r = subprocess.run(['node', '-e', src], cwd=REPO,
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        sys.stderr.write('COULD NOT RUN -- node is required to read the live '
                         'registry: %s: %s\n' % (type(e).__name__, e))
        sys.exit(2)
    if r.returncode != 0:
        sys.stderr.write('COULD NOT RUN -- the resource registry did not load. '
                         'That is a finding about api/_resources/, not a pass '
                         'for this check:\n' + (r.stderr or '')[:800] + '\n')
        sys.exit(2)
    return json.loads(r.stdout)


def main():
    reg = extra_actions()
    verbs, owner, names = reg['e'], reg['o'], reg['n']
    rows = tier_rows(io.open(REGISTER, encoding='utf-8').read())
    tier_a = [r for r in rows if r[1] == 'A']

    # A register row naming a resource the registry does not have would make
    # every count below meaningless. criticality_tier_check owns that check;
    # this refuses rather than quietly measuring a subset.
    unknown = [r[0] for r in tier_a if r[0] not in names]
    if unknown:
        sys.stderr.write('COULD NOT MEASURE -- %d Tier A row(s) name a resource '
                         'the live registry does not have: %s\nRun '
                         'criticality_tier_check.py; this tool will not report a '
                         'number over a subset it cannot explain.\n'
                         % (len(unknown), ', '.join(sorted(unknown))))
        sys.exit(2)

    def grants(name):
        return verbs.get(name) or []

    hard = [r for r in tier_a if 'delete' in grants(r[0])]
    soft = [r for r in tier_a if 'soft_delete' in grants(r[0])
            and 'delete' not in grants(r[0])]
    none = [r for r in tier_a if not any(v.endswith('delete') for v in grants(r[0]))]
    silent = [r for r in tier_a if not RECOVERABILITY.search(r[2])]

    if '--json' in sys.argv:
        print(json.dumps({
            'tier_a': len(tier_a),
            'hard_delete': sorted((r[0], owner.get(r[0])) for r in hard),
            'soft_delete_only': sorted(r[0] for r in soft),
            'no_delete_verb': sorted(r[0] for r in none),
            'evidence_silent_on_recoverability': sorted(r[0] for r in silent),
        }, indent=2))
        return 0

    say = print
    say('TIER A REPLACEABILITY -- item 97, report only, nothing is blocked')
    say('  Tier A resources              : %d' % len(tier_a))
    say('  can be HARD DELETED           : %d' % len(hard))
    say('  soft_delete only (row survives): %d' % len(soft))
    say('  no delete verb reachable      : %d' % len(none))
    say('')
    if hard:
        by_app = {}
        for r in hard:
            by_app.setdefault(owner.get(r[0]) or '?', []).append(r[0])
        say('  A TIER A ARTIFACT THAT CAN BE DESTROYED RATHER THAN HIDDEN:')
        for app in sorted(by_app):
            say('    %-14s %s' % (app, ', '.join(sorted(by_app[app]))))
        say('')
        if len(by_app) == 1:
            say('  ALL OF THEM ARE IN ONE APP, which is the finding rather than')
            say('  the total: every other Tier A resource on this platform either')
            say('  hides the row or cannot delete it at all. Check whether that')
            say('  grant was a per-RESOURCE decision or a set-level one.')
            say('')
    say('  DOCUMENTATION COVERAGE, weaker and separate -- this reads LANGUAGE:')
    say('    Tier A rows whose evidence mentions recoverability : %d'
        % (len(tier_a) - len(silent)))
    say('    Tier A rows silent on it                           : %d' % len(silent))
    say('  The register asks for the worst consequence of being WRONG and gets')
    say('  it. Replaceability is a different question and mostly unrecorded.')
    say('  A row that establishes it in words this pattern does not match is a')
    say('  FALSE HIT, so treat this as coverage and never as a defect count.')
    say('')
    say('  NOT SWEPT HERE, and it is the dangerous direction: a Tier B or C')
    say('  resource that is in fact the only copy of something irreplaceable.')
    say('  Over-tiering costs rigour; under-tiering is the accident.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
