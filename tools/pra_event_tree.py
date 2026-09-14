"""Item 84 -- probabilistic risk assessment: the EVENT TREE, and the number it
refuses to invent.

    python tools/pra_event_tree.py            # the trees
    python tools/pra_event_tree.py --json
    python tools/pra_event_tree.py --fixtures # the blind lock alone

── WHY THIS IS NOT THE FMEA, and the difference is the whole reason it exists ─
`tools/fmea_draft.py` is BOTTOM-UP and PER-FILE: given this file, what can fail
in it, seeded from what has already failed here. It answers "what is wrong with
this component".

This is TOP-DOWN and PER-SYSTEM: given that a component HAS failed, what
sequence of things decides how bad that is, and which end states are reachable.
Different unit, different direction, and neither substitutes for the other --
an FMEA cannot tell you that two independently-fine components share a third
one, and an event tree cannot tell you which line of a file is wrong.

── THE NUMBER THIS REFUSES TO PRODUCE, SAID FIRST ──────────────────────────
A probabilistic risk assessment classically multiplies a FREQUENCY by a
CONSEQUENCE and reports one risk score. THIS TOOL DOES NOT, and the refusal is
the most important thing in it.

There is no frequency here that anybody can defend. The obvious candidate --
docs/defect-density-register.json, 68 confirmed defects -- is a record of
DEFECTS FOUND IN CODE over six days. That is a different population from
COMPONENT FAILURES IN PRODUCTION, it is bounded by how hard anyone looked, and
six days is not a rate. Multiplying it by a consequence tier would produce a
confident number nobody could check, which is this platform's most-recorded
failure shape: a figure no measurement stands behind.

So the output is an END STATE and a CONSEQUENCE TIER, reported separately and
never fused. Where a frequency would go, it says UNKNOWN and says why.

── THE THREE BRANCH POINTS, EACH DERIVED RATHER THAN ASSERTED ──────────────
Every branch is a binary whose answer comes from something already maintained
for its own reasons, so this file invents no facts:

  FAILS CLOSED?   For an environment value: docs/SECRETS-INVENTORY.md's absence
                  column, which is itself measured by tools/secrets_inventory.py.
                  For a MODULE: a require that cannot resolve is a crash at
                  import, so a module's absence fails closed BY CONSTRUCTION --
                  which is a real asymmetry between the two kinds of node and
                  is the reason they are not treated alike.

  ANNOUNCED?      Does the failure produce a distinguishable error, or a
                  plausible wrong answer? A guarded env value refuses with a
                  message; an unguarded one carries on with undefined. A module
                  crash is announced by definition.

  RECOVERABLE?    Is the affected data reconstructible afterwards? Read from
                  the audit-checkpoint table list (api/audit-checkpoint.js) --
                  the only independently-computed fingerprint of history this
                  platform has -- and from the standing fact, recorded in
                  docs/2026-09-14-backup-restorability-scoping.md, that NOTHING
                  in this repo takes or restores a backup.

── WHAT IT CANNOT SEE ──────────────────────────────────────────────────────
  * anything the dependency graph cannot see: a runtime HTTP call between two
    endpoints is a real dependency and is invisible to both;
  * a failure MODE other than "the component is unavailable". A component that
    is present and WRONG is the FMEA's question, not this one;
  * whether an end state has ever actually occurred. This enumerates what is
    REACHABLE, which is a statement about structure, not about history.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import dependency_graph as G                                     # noqa: E402
import secrets_inventory as S                                    # noqa: E402

TIERS = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
SPOF = os.path.join(REPO, 'docs', 'SPOF-REGISTER.md')

# The three audit tables are the only history on this platform with an
# independently recomputable fingerprint, so they are the only data a restore
# could be CHECKED against rather than merely attempted. Read from the handler
# rather than restated, so the two cannot drift.
AUDIT_TABLES_SRC = os.path.join(REPO, 'api', 'audit-checkpoint.js')


def audit_tables():
    src = io.open(AUDIT_TABLES_SRC, encoding='utf-8').read()
    m = re.search(r"const TABLES = \[([^\]]*)\]", src)
    return set(re.findall(r"'([a-z_]+)'", m.group(1))) if m else set()


def tiers():
    out = {}
    for name, tier in re.findall(r'^\|\s*`([a-z_0-9]+)`\s*\|\s*\*\*([ABC])\*\*\s*\|',
                                 io.open(TIERS, encoding='utf-8').read(), re.M):
        out[name] = tier
    return out


def spof_components():
    rows = G.register_rows(io.open(SPOF, encoding='utf-8').read())
    return [r for r in rows if r['component']]


# ── THE END STATES ────────────────────────────────────────────────────────
# Eight reachable combinations of three binaries. They are NAMED rather than
# numbered, because "state 6" tells a reader nothing and the whole value of an
# event tree is that somebody can argue with the end state.
#
# THE ORDERING IS NOT BY COUNT OF FAILED BRANCHES, and that is deliberate: the
# worst state here is not the one where the most things go wrong. It is
# SILENT AND UNRECOVERABLE -- the system carries on, produces plausible wrong
# answers, and there is nothing to reconstruct the truth from afterwards. A
# loud total failure is recoverable by definition; nobody acts on it.
END_STATES = {
    (True, True, True): ('REFUSED AND RECONSTRUCTIBLE',
                         'the component is unavailable, the call refuses, the refusal is '
                         'visible, and history can be checked afterwards. This is the '
                         'good outcome and it is still an outage'),
    (True, True, False): ('REFUSED, NOTHING TO RECONSTRUCT',
                          'it refuses loudly and nobody loses data because nothing was '
                          'written -- but if anything WAS mid-flight there is no '
                          'independent record to check it against'),
    (True, False, True): ('REFUSED QUIETLY',
                          'it fails closed but says nothing distinguishable, so the '
                          'symptom is "the feature stopped working" with no cause '
                          'attached. Recoverable, and expensive to diagnose'),
    (True, False, False): ('REFUSED QUIETLY, NOTHING TO RECONSTRUCT',
                           'fails closed, says nothing useful, and no independent record'),
    (False, True, True): ('CARRIES ON, LOUDLY, CHECKABLE',
                          'it does NOT fail closed -- work proceeds on a missing or '
                          'wrong value -- but the error is visible and history can be '
                          'checked afterwards'),
    (False, True, False): ('CARRIES ON, LOUDLY, UNCHECKABLE',
                           'work proceeds wrongly, the error is visible, and there is no '
                           'independent record of what was written while it was wrong'),
    (False, False, True): ('SILENT WRONG ANSWER, CHECKABLE',
                           'work proceeds on a missing value, nothing announces it, and '
                           'the only reason it is survivable is that an independent '
                           'fingerprint of history exists to find the damage later'),
    (False, False, False): ('SILENT AND UNRECOVERABLE',
                            'THE WORST REACHABLE STATE, and not because the most branches '
                            'failed. Work proceeds on a missing value, nothing announces '
                            'it, and nothing can reconstruct what was true. A loud total '
                            'failure is recoverable by definition; this one is acted on'),
}


def classify(component, secrets_rows, audit, tier_map, reach):
    """The three branches, for one initiating event."""
    if component.startswith('env:'):
        name = component[4:]
        row = secrets_rows.get(name)
        # FAILS CLOSED: measured by tools/secrets_inventory.py, not asserted
        # here. A value with a guard that refuses fails closed; one with NO
        # GUARD FOUND carries on with undefined.
        closed = bool(row and (row['guarded'] or row['guarded_via']))
        announced = closed         # a guard that refuses does so with a message
        kind = 'environment value'
        basis_closed = ('docs/SECRETS-INVENTORY.md: %s'
                        % ('a guard refuses' if closed else 'NO GUARD FOUND in any reader '
                           'or in any module they require'))
    else:
        # A require that cannot resolve throws at import. There is no quiet
        # version of a missing module, which is a REAL asymmetry between the two
        # kinds of node and the reason they are not treated alike.
        closed = True
        announced = True
        kind = 'module'
        basis_closed = 'a require that cannot resolve throws at import -- by construction'

    # RECOVERABLE: is there an independently recomputable record of what was
    # true? Only the three audit tables have one. Nothing in this repo takes or
    # restores a backup -- docs/2026-09-14-backup-restorability-scoping.md.
    touched = sorted(r for r in reach if r in tier_map)
    recoverable = bool(audit & set(touched))
    worst = 'C'
    for r in touched:
        t = tier_map[r]
        if t == 'A':
            worst = 'A'
            break
        if t == 'B' and worst != 'A':
            worst = 'B'
    if not touched:
        worst = None
    key = (closed, announced, recoverable)
    state, prose = END_STATES[key]
    return {
        'component': component, 'kind': kind,
        'fails_closed': closed, 'announced': announced, 'recoverable': recoverable,
        'basis_fails_closed': basis_closed,
        'basis_recoverable': ('an audit-checkpoint table is in reach: %s'
                              % ', '.join(sorted(audit & set(touched)))) if recoverable
                             else ('no audit-checkpoint table is in reach, and nothing in '
                                   'this repo takes or restores a backup'),
        'end_state': state, 'end_state_prose': prose,
        'worst_tier': worst, 'resources_in_reach': len(touched),
        # THE KIND MATTERS AND OMITTING IT WOULD MISLEAD. A TUNING value with a
        # documented default reaching SILENT AND UNRECOVERABLE is usually the
        # default working as intended -- a Firebase project id is not a
        # credential and its absence is a misconfiguration, not a breach. A
        # CREDENTIAL or a limit in the same state is a different sentence. The
        # classification comes from docs/SECRETS-INVENTORY.md's hand-written
        # half rather than being re-derived here.
        'secret_kind': (secrets_rows.get(component[4:], {}) or {}).get('kind')
                       if component.startswith('env:') else None,
        # THE NUMBER THIS REFUSES TO INVENT.
        'frequency': None,
        'frequency_note': 'UNKNOWN. The only candidate is the defect register, which '
                          'counts DEFECTS FOUND IN CODE over six days -- a different '
                          'population from component failures in production, bounded by '
                          'how hard anyone looked. Six days is not a rate.',
    }


def resources_reachable(component, edges, nodes):
    """Which registered resources sit downstream of this component.

    Approximated from the MODULE that names them: a resource name appearing as a
    string literal in a module that transitively requires the component. Stated
    as an approximation because it is one -- a module can name a resource it
    does not touch, and a resource can be reached through a runtime call this
    graph cannot see. It is used only to pick the WORST TIER in reach, which is
    a ceiling rather than a count.
    """
    radj = {}
    for a, bs in edges.items():
        for b in bs:
            radj.setdefault(b, set()).add(a)
    seen, stack = {component}, [component]
    while stack:
        x = stack.pop()
        for y in radj.get(x, ()):
            if y not in seen:
                seen.add(y)
                stack.append(y)
    names = set()
    for f in seen:
        if f.startswith('env:'):
            continue
        p = os.path.join(REPO, f)
        if not os.path.isfile(p):
            continue
        body = io.open(p, encoding='utf-8', errors='replace').read()
        names.update(re.findall(r"'([a-z][a-z0-9_]{3,})'", body))
    return names


# ── THE BLIND LOCK ────────────────────────────────────────────────────────
# The classifier is decided against synthetic inputs before any real component
# is read. The arm that matters is the ORDERING claim: this tool asserts that
# the worst end state is not the one with the most failed branches, and a
# fixture pins it so nobody "fixes" the table into a severity ladder.
FIXTURES = [
    ('a guarded env value that refuses, with an audit table in reach',
     (True, True, True), 'REFUSED AND RECONSTRUCTIBLE'),
    ('an unguarded env value, nothing announced, nothing to reconstruct',
     (False, False, False), 'SILENT AND UNRECOVERABLE'),
    ('CONTROL: three failed branches and two failed branches are DIFFERENT '
     'states, so the table is not a severity ladder in disguise',
     (False, True, False), 'CARRIES ON, LOUDLY, UNCHECKABLE'),
    ('a module: fails closed and announced by construction',
     (True, True, False), 'REFUSED, NOTHING TO RECONSTRUCT'),
]


def run_fixtures():
    bad = []
    for label, key, want in FIXTURES:
        got = END_STATES[key][0]
        if got != want:
            bad.append((label, want, got))
    # THE ORDERING CLAIM, asserted rather than left in prose: the all-false
    # state must be the one the header calls the worst, and it must NOT be
    # reachable by simply counting failed branches -- (False, True, False) has
    # two failures and is explicitly not the worst.
    if 'WORST REACHABLE STATE' not in END_STATES[(False, False, False)][1]:
        bad.append(('the all-silent state is named the worst', True, False))
    if 'WORST' in END_STATES[(False, True, False)][1]:
        bad.append(('a two-failure state is NOT named the worst', True, False))
    if len(END_STATES) != 8:
        bad.append(('every combination of three binaries has a named end state',
                    8, len(END_STATES)))
    return bad


def main(argv):
    # UNDER --json THE BANNER GOES TO STDERR. A consumer piping this to jq must
    # receive JSON and nothing else -- the probe caught exactly that, failing to
    # parse its own tool's output. The blind-lock result is NOT suppressed, only
    # redirected: a lock whose verdict is invisible is a lock nobody ran.
    out = sys.stderr if '--json' in argv else sys.stdout

    def say(*a):
        print(*a, file=out)

    bad = run_fixtures()
    say('PRA EVENT TREE -- item 84')
    if bad:
        print('  !! THE END-STATE TABLE FAILED ITS OWN FIXTURES. NOTHING WAS ANALYSED.')
        for row in bad:
            print('     %s -- wanted %r, got %r' % row)
        return 2
    say('  blind lock: %d end-state fixtures plus the ordering claim, decided'
          % len(FIXTURES))
    say('              before any real component was read.')
    if '--fixtures' in argv:
        return 0

    nodes, edges, _ = G.build(include_env=True, with_tests=False)
    tier_map = tiers()
    audit = audit_tables()
    secrets_rows = {r['name']: r for r in S.analyse()}
    comps = spof_components()
    # ── THE SECOND SOURCE OF INITIATING EVENTS, AND IT IS THE ONE THAT MAKES
    # THE TREE DISCRIMINATE. The SPOF register holds the components with the
    # widest REACH, and every one of them happens to be guarded -- so on that
    # set alone the fails-closed branch is constant and the tree collapses to a
    # single end state. An analysis where every input produces the same output
    # is not discriminating, whatever it says about the world.
    #
    # The components the secrets inventory found with NO GUARD FOUND are
    # exactly the ones that do NOT fail closed. They are narrow, which is why
    # they are not in the SPOF register -- and they are the half of the tree
    # that the wide components cannot populate.
    seen_c = {c['component'] for c in comps}
    for name, row in sorted(secrets_rows.items()):
        if row['guarded'] or row['guarded_via']:
            continue
        node = 'env:' + name
        if node in seen_c:
            continue
        comps.append({'component': node, 'owner': 'unassigned',
                      'status': 'not in the SPOF register -- narrow reach, no guard found'})

    trees = []
    for c in comps:
        reach = resources_reachable(c['component'], edges, nodes)
        t = classify(c['component'], secrets_rows, audit, tier_map, reach)
        t['owner'] = c['owner']
        t['register_status'] = c['status']
        trees.append(t)

    if '--json' in argv:
        print(json.dumps({'initiating_events': trees,
                          'frequency': None,
                          'frequency_note': trees[0]['frequency_note'] if trees else ''},
                         indent=2, sort_keys=True))
        return 0

    print()
    n_reg = len([t for t in trees if t['register_status'] != 'not in the SPOF register -- '
                 'narrow reach, no guard found'])
    say('  INITIATING EVENTS: %d -- %d from docs/SPOF-REGISTER.md (the widest reach) '
          'and' % (len(trees), n_reg))
    say('  %d from docs/SECRETS-INVENTORY.md with NO GUARD FOUND (narrow reach, and the'
          % (len(trees) - n_reg))
    say('  only ones that do not fail closed).')
    say('  Each is the event "this component is unavailable". A component that is')
    say('  PRESENT AND WRONG is the FMEA\'s question, not this one.')
    print()
    by_state = {}
    for t in trees:
        by_state.setdefault(t['end_state'], []).append(t)
    for state in sorted(by_state, key=lambda s: -len(by_state[s])):
        rows = by_state[state]
        print('  %s  (%d)' % (state, len(rows)))
        print('     %s' % END_STATES[[k for k, v in END_STATES.items()
                                      if v[0] == state][0]][1])
        for t in rows:
            print('       %-38s %-11s tier %-5s owner %-10s %s'
                  % (t['component'], t['secret_kind'] or 'module',
                     t['worst_tier'] or 'n/a', t['owner'],
                     'recoverable' if t['recoverable'] else 'NO independent record'))
            print('          fails closed: %s' % t['basis_fails_closed'])
            print('          recoverable : %s' % t['basis_recoverable'])
        # A BRANCH THAT DID NOT DISCRIMINATE IS REPORTED AS SUCH. An event tree
    # whose branches all resolve the same way still prints eight end states and
    # occupies one, and a reader who does not notice reads structure that is
    # not there.
    # READ THE KIND BEFORE READING THE END STATE. Said here rather than left
    # to be worked out, because the worst-state list is dominated by TUNING
    # values whose default is the intended behaviour.
    tune = [t for t in trees if t['secret_kind'] == 'TUNING'
            and t['end_state'] == 'SILENT AND UNRECOVERABLE']
    if tune:
        print('  READ THE KIND COLUMN BEFORE THE END STATE. %d of the worst-state rows'
              % len(tune))
        print('  are TUNING values, where carrying on with a documented default is the')
        print('  INTENDED behaviour and not a finding -- a Firebase project id is not a')
        print('  credential. What is worth reading in that state is a CREDENTIAL, or a')
        print('  LIMIT whose default IS the policy: SAIRN_AI_DAILY_LIMIT and')
        print('  SAIRN_ANON_INVALID_LIMIT are both in it, and an unbounded default on a')
        print('  BILLED AI ceiling is a different sentence from a missing analytics id.')
        print()
    say('  BRANCHES THAT DID NOT DISCRIMINATE ON THIS INPUT SET:')
    flat = []
    for field, label in (('fails_closed', 'FAILS CLOSED'), ('announced', 'ANNOUNCED'),
                         ('recoverable', 'RECOVERABLE')):
        vals = {t[field] for t in trees}
        if len(vals) == 1:
            flat.append('%s is %s for every one of the %d initiating events'
                        % (label, list(vals)[0], len(trees)))
    if flat:
        for f in flat:
            print('     ' + f)
        print('     That is a fact about the platform, not a bug in the tree -- but a')
        print('     branch with one value carries no information, and saying so is the')
        print('     difference between a result and a shape.')
    else:
        print('     none -- all three branches took both values.')
    print()
    say('  FREQUENCY: UNKNOWN, and deliberately not estimated.')
    say('  %s' % (trees[0]['frequency_note'] if trees else ''))
    say('  The end state and the consequence tier are reported SEPARATELY and')
    say('  never multiplied. A risk score nobody can check is worse than none.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
