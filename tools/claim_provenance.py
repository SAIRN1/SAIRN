#!/usr/bin/env python
"""claim_provenance.py -- record HOW a Tier A claim was established.

    python tools/claim_provenance.py scope
    python tools/claim_provenance.py types
    python tools/claim_provenance.py list [--subject X]
    python tools/claim_provenance.py add --subject sv_controlled \\
        --type live-schema --claim "the table exists on the live database" \\
        --method measured --observed 2026-09-14T12:00:00Z \\
        --by fourth --how "python tools/schema_snapshot_freshness.py"

THE RECORDING SIDE OF ITEM 23, AND ONLY THAT. The design
(docs/2026-09-13-claim-provenance-chain-design.md) recommends recording first
and checking second, for a reason it states plainly:

    "A provenance chain built before claims carry provenance would be the
     third tool waiting on an input nobody is producing."

Items 2/24 and 4 both shipped able to judge and had nothing to judge. THIS TOOL
DELIBERATELY DOES NOT JUDGE. It stores what a later checker will need and
refuses a record that could not be checked; deciding whether a claim has gone
stale is a separate build, after the chain has accumulated.

── WHAT EVERY RECORD MUST CARRY, AND WHY EACH ONE ──────────────────────────
  subject   a Tier A resource, DERIVED from docs/CRITICALITY-TIERS.md rather
            than a second list -- promoting a resource to Tier A brings it into
            scope automatically, with nothing to keep in step.
  type      what KIND of claim it is. The freshness interval belongs to the
            type, not to the clock: a live-schema claim is stale in hours and a
            criticality-tier claim is good for weeks. A single threshold would
            call a two-day-old snapshot live, which is exactly the error that
            produced a wrong 89-table never-run verdict.
  observed  WHEN THE MEASUREMENT WAS TAKEN. Stored separately from when it was
            recorded, and this is the field the design says bites:
            gate_column_check.py read the git COMMIT date and reported a capture
            as 25 hours old when it was 43.3 -- an 18.7-hour understatement, in
            the direction that makes stale data look current.
  method    measured | attested | derived.
  how       the reproduction path. A tool and its arguments for `measured`; for
            `attested`, HOW SOMEBODY ELSE COULD REDO IT. An attestation with no
            reproduction path is an assertion with a name attached, and this
            refuses to store one.

── THE ATTESTATION GUARD, WHICH IS THE MOST ABUSABLE PART ──────────────────
A human-attested link is unavoidable: the schema snapshot cannot be derived by
anything in this repo -- a person runs the query in the Supabase editor and
saves the result, and EVERY schema claim on this platform rests on that link. A
chain that could not represent it would either omit its own foundation or
present a human attestation as machine-derived, and the second is a fabrication.

But the premortem is the obvious one: if a tool-derived link is harder to
produce than typing a sentence, THE CHAIN FILLS WITH SENTENCES. So an attested
claim whose TYPE has a tool that could have produced it is stored with
`weaker_than_available` and the tool's name -- recorded as a downgrade at the
moment it is written, not discovered later.

Exit 0 on success, 1 on a refused record, 2 could not run.
"""
import io
import json
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(REPO, 'docs', 'claim-provenance.json')
TIERS = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
EXIT_CLEAN, EXIT_REFUSED, EXIT_COULD_NOT_RUN = 0, 1, 2

ISO = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
METHODS = ('measured', 'attested', 'derived')

# ── THE FRESHNESS TABLE, PER TYPE ──────────────────────────────────────────
# Intervals are NOT used by this tool -- it does not judge. They are stored here
# because the checker that comes later needs one source for them, and because a
# type with no row is the case that matters: AN UNCLASSIFIED TYPE IS NOT LIVE.
# Failing closed there is the point -- a claim whose subject nobody has
# classified is a claim nobody has thought about, and calling it live by default
# is the fail-open shape PR 1.11 names.
#
# `tool` names the thing that COULD produce this type. It is what makes the
# attestation downgrade mechanical rather than a judgement call.
TYPES = {
    'live-schema': {
        'live_for_hours': 12,
        'tool': 'tools/schema_snapshot_freshness.py',
        'why': 'a human runs a migration unannounced; a 43.3-hour-old snapshot '
               'was already wrong about five tables'
    },
    'deployed-code': {
        'live_for_hours': 1,
        'tool': 'tools/deploy_verify_notify.py',
        'why': 'changes on every push, several times an hour'
    },
    'criticality-tier': {
        'live_for_hours': 24 * 21,
        'tool': 'tools/criticality_tier_check.py',
        'why': 'a deliberate judgement, rarely revisited'
    },
    'grant-state': {
        'live_for_hours': 24 * 7,
        'tool': None,
        'why': 'changes only when somebody runs SQL, but nothing in this repo '
               'can read it without a live connection'
    },
    'removal-path': {
        'live_for_hours': 24 * 7,
        'tool': 'tools/removal_path_check.py',
        'why': 'derived from the code, so it moves when the code does'
    },
    'migration-run': {
        'live_for_hours': 12,
        'tool': None,
        'why': 'THE HUMAN-ATTESTED FOUNDATION. No clone can see whether a '
               'migration ran; somebody has to look and say so.'
    },
}


def load_tier_a():
    """The Tier A subjects, DERIVED from the register. No second list."""
    try:
        lines = io.open(TIERS, encoding='utf-8').read().split('\n')
    except Exception as e:
        return None, 'could not read %s (%s)' % (os.path.relpath(TIERS, REPO), type(e).__name__)
    out = set()
    for l in lines:
        if not l.startswith('|') or l.startswith('|---'):
            continue
        c = [x.strip() for x in l.split('|')]
        if len(c) < 4:
            continue
        name = c[1].strip('` *')
        tier = c[2].strip('* ')
        if tier == 'A' and re.match(r'^[a-z][a-z0-9_]*$', name):
            out.add(name)
    if not out:
        # A ZERO HERE IS A BROKEN READER, NOT AN EMPTY REGISTER. Returning an
        # empty scope would make every `add` refuse with "not Tier A", which
        # reads as a rule working and is a parser that stopped matching.
        return None, ('parsed %s and found NO Tier A resources -- that is a '
                      'broken reader, not an empty register' % os.path.relpath(TIERS, REPO))
    return out, None


def load_ledger():
    if not os.path.exists(LEDGER):
        return {'_what_this_is': (
            'Item 23, the RECORDING side. How each Tier A claim was established: '
            'what was observed, WHEN it was observed (not when it was typed), by '
            'what method, and how somebody else could redo it. Nothing judges '
            'staleness yet -- see the design document for why recording comes '
            'first.'),
            '_scope': 'Tier A only, derived from docs/CRITICALITY-TIERS.md',
            '_freshness': 'per TYPE, not per clock; an unclassified type is NOT LIVE',
            'records': []}
    try:
        d = json.loads(io.open(LEDGER, encoding='utf-8').read())
    except Exception as e:
        return {'_error': '%s: %s' % (type(e).__name__, e)}
    if 'records' not in d:
        d['records'] = []
    return d


def save_ledger(d):
    io.open(LEDGER, 'w', encoding='utf-8', newline='').write(
        json.dumps(d, indent=2, ensure_ascii=False) + '\n')


def cmd_scope(argv):
    subs, err = load_tier_a()
    if err:
        print('COULD NOT RUN: ' + err)
        return EXIT_COULD_NOT_RUN
    print('TIER A SUBJECTS IN SCOPE: %d' % len(subs))
    print('  derived from %s -- promoting a resource to Tier A brings it into'
          % os.path.relpath(TIERS, REPO))
    print('  scope automatically, with no second list to keep in step.')
    for s in sorted(subs)[:20]:
        print('    ' + s)
    if len(subs) > 20:
        print('    ... and %d more' % (len(subs) - 20))
    return EXIT_CLEAN


def cmd_types(argv):
    print('CLAIM TYPES AND THEIR FRESHNESS INTERVALS')
    print('  The interval belongs to the TYPE, not to the clock. Stored for the')
    print('  checker that comes later; NOTHING here judges staleness yet.')
    print('')
    for t in sorted(TYPES):
        r = TYPES[t]
        print('  %-18s live for %5dh   tool: %s' %
              (t, r['live_for_hours'], r['tool'] or '(none -- human-attested)'))
        print('  %-18s %s' % ('', r['why']))
    print('')
    print('  A TYPE NOT LISTED HERE IS NOT LIVE. That is the fail-closed half:')
    print('  a claim whose subject nobody has classified is a claim nobody has')
    print('  thought about.')
    return EXIT_CLEAN


def arg(argv, name, dflt=None):
    if '--' + name in argv:
        i = argv.index('--' + name)
        if i + 1 < len(argv) and not argv[i + 1].startswith('--'):
            return argv[i + 1]
    return dflt


def cmd_add(argv):
    subs, err = load_tier_a()
    if err:
        print('COULD NOT RUN: ' + err)
        return EXIT_COULD_NOT_RUN
    d = load_ledger()
    if '_error' in d:
        print('COULD NOT RUN: the ledger is unreadable (%s). Nothing was written '
              'and nothing was judged.' % d['_error'])
        return EXIT_COULD_NOT_RUN

    subject = arg(argv, 'subject')
    ctype = arg(argv, 'type')
    claim = arg(argv, 'claim')
    method = arg(argv, 'method')
    observed = arg(argv, 'observed')
    by = arg(argv, 'by')
    how = arg(argv, 'how')

    problems = []
    if not subject:
        problems.append('--subject is required')
    elif subject.startswith('migration:'):
        # ── A SECOND SUBJECT KIND, AND USING THE TOOL IS WHAT FOUND IT ───────
        # The very first real claim anybody tried to record was "this migration
        # was run and verified", and it HAD NO VALID SUBJECT: the Tier A scope
        # is derived from the RESOURCE register, and a migration is not a
        # resource. The type `migration-run` existed in the table below with
        # nothing it could legally be about -- an inconsistency in this file
        # that reading it would not have shown and running it exposed at once.
        #
        # The design's Q3 answer is Tier A ONLY and warns that widening dilutes,
        # so this does NOT widen to free text. A migration subject must name a
        # REAL FILE IN sql/, which is still derived from the repo and still has
        # no second list to keep in step.
        f = subject.split(':', 1)[1]
        if not re.match(r'^[A-Za-z0-9_.\-]+\.sql$', f) or \
                not os.path.isfile(os.path.join(REPO, 'sql', f)):
            problems.append('%r names no file in sql/. A migration subject must '
                            'be `migration:<file>.sql` and the file must exist, '
                            'because a claim about a migration nobody can find '
                            'is the assertion-with-a-name-attached this tool '
                            'refuses everywhere else.' % subject)
    elif subject not in subs:
        problems.append('%r is not Tier A in %s, and is not a `migration:<file>.sql` '
                        'subject. Scope is Tier A ONLY, and deliberately: a chain '
                        'covering everything gets skimmed.'
                        % (subject, os.path.relpath(TIERS, REPO)))
    if not ctype:
        problems.append('--type is required')
    elif ctype not in TYPES:
        problems.append('%r is not a known claim type. AN UNCLASSIFIED TYPE IS '
                        'NOT LIVE, so a record carrying one could never be '
                        'checked -- add it to TYPES with an interval and a '
                        'reason first. Known: %s'
                        % (ctype, ', '.join(sorted(TYPES))))
    if not claim:
        problems.append('--claim is required: what was actually established, in '
                        'words a reader can check')
    if method not in METHODS:
        problems.append('--method must be one of: ' + ', '.join(METHODS))
    if not observed or not ISO.match(observed):
        problems.append('--observed must be an ISO instant like '
                        '2026-09-14T12:00:00Z -- WHEN THE MEASUREMENT WAS TAKEN, '
                        'not when it was typed. Reading the recording time '
                        'instead is an 18.7-hour understatement on this '
                        'platform, in the direction that makes stale data look '
                        'current.')
    if not by:
        problems.append('--by is required')
    if not how:
        problems.append('--how is required: the reproduction path. For a '
                        'measurement, the tool and its arguments. For an '
                        'attestation, how somebody else could redo it -- an '
                        'attestation with no reproduction path is an assertion '
                        'with a name attached.')

    if problems:
        print('REFUSED -- nothing was written:')
        for p in problems:
            print('  x ' + p)
        return EXIT_REFUSED

    rec = {
        'subject': subject, 'type': ctype, 'claim': claim, 'method': method,
        'observed_at': observed,
        # BOTH INSTANTS, ALWAYS. The gap between them is itself information: a
        # record written three days after it was observed is a different thing
        # from one written the same minute.
        'recorded_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'by': by, 'how': how
    }

    # THE DOWNGRADE, APPLIED AT WRITE TIME. If a tool could have produced this
    # type and a human typed it instead, that is weaker evidence -- not equal
    # evidence -- and it is recorded as such rather than discovered later.
    tool = TYPES[ctype]['tool']
    if method == 'attested' and tool:
        rec['weaker_than_available'] = tool
        print('NOTE: %s could have produced a %r claim, so this attestation is '
              'recorded as WEAKER than a measurement, not equal to one.'
              % (tool, ctype))

    d['records'].append(rec)
    save_ledger(d)
    print('recorded: %s / %s / %s  observed %s, recorded %s'
          % (subject, ctype, method, rec['observed_at'], rec['recorded_at']))
    print('  ledger: %s  (%d record(s))'
          % (os.path.relpath(LEDGER, REPO), len(d['records'])))
    return EXIT_CLEAN


def cmd_list(argv):
    d = load_ledger()
    if '_error' in d:
        print('COULD NOT RUN: the ledger is unreadable (%s)' % d['_error'])
        return EXIT_COULD_NOT_RUN
    want = arg(argv, 'subject')
    rows = [r for r in d['records'] if not want or r.get('subject') == want]
    print('CLAIM PROVENANCE -- %d record(s)%s'
          % (len(rows), '' if not want else ' for ' + want))
    print('  NOTHING HERE IS JUDGED FOR STALENESS. This is the recording side;')
    print('  the checker is a separate build, deliberately after the chain has')
    print('  something in it.')
    for r in rows:
        print('')
        print('  %s  [%s]  %s' % (r.get('subject'), r.get('type'), r.get('method')))
        print('    claim    : %s' % r.get('claim'))
        print('    observed : %s   recorded: %s' % (r.get('observed_at'), r.get('recorded_at')))
        print('    by       : %s' % r.get('by'))
        print('    redo it  : %s' % r.get('how'))
        if r.get('weaker_than_available'):
            print('    DOWNGRADE: %s could have produced this -- attestation is '
                  'weaker evidence' % r['weaker_than_available'])
    return EXIT_CLEAN


def main(argv):
    cmds = {'scope': cmd_scope, 'types': cmd_types, 'add': cmd_add, 'list': cmd_list}
    if not argv or argv[0] not in cmds:
        print(__doc__.split('\n\n')[0])
        print('\ncommands: ' + ', '.join(sorted(cmds)))
        return EXIT_COULD_NOT_RUN
    return cmds[argv[0]](argv[1:])


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
