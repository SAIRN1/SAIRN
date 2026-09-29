#!/usr/bin/env python
"""scope_narrowing_check.py (hover2's own build) -- has this role's
attention quietly narrowed across the four build agents? Implemented from
hover_parity_specs.md #2 (H1, 2026-09-24), not H1's source.

For each build agent (hank, cc, fourth, cody): count real check/finding
entries logged SINCE that agent was last the SUBJECT of one -- read from
the structured `target` field only, never summary prose. An agent far past
the others is a computed drift-of-attention signal nobody decided on
purpose (the Boeing/ODA erosion shape: no single decision, just drift).

WHAT A HIT MEANS, stated in the output because the spec requires it: this
measures ATTENTION, not correctness or risk -- it cannot distinguish
"coverage narrowed" from "that agent had less real landed work to check in
the window". A stale agent is a CANDIDATE for the next targeted or
undirected pass, never a confirmed neglect finding.

TARGET MATCHING: an entry counts as being ABOUT an agent when the agent's
name appears as a comma-separated token of the structured target field.
Matching is exact-token, case-folded -- never substring, so target
'hank-probe.py' does not read as hank.

A REAL GAP THIS TOOL'S OWN FIRST RUN SURFACED, AND ITS FIX (2026-09-27,
direct instruction). The first real run reported all four agents "NEVER a
subject" -- true of the field, and misleading if read as "no agent's work
has ever been reviewed": every entry logged before seq
ATTRIBUTION_STARTS_AT_SEQ targeted resources or commit hashes, never an
agent name, because the CONVENTION of putting an agent's name in `target`
did not exist yet (confirmed: zero of 242 entries ever used one, checked
directly, not inferred). Same discipline as hover_log.py's own
`source_shas` field precedent ("this applies from THIS entry forward only,
not to the entries before it") -- historical entries are NOT rewritten
(append-only, hash-chained; rewriting would break the chain and violates
the AS-FOUND discipline), and this tool does not fabricate retroactive
attribution to make its own counters look populated. Instead this tool
now DISCLOSES the boundary explicitly: any FINDING whose evidence sits
entirely (or mostly) before the boundary is labelled a CONVENTION-GAP
READING, distinct from a POST-CONVENTION READING backed by real
post-fix data, and the two are never blended into one unqualified verdict.

VERDICTS, three, never two:
  PASS (0)          all four agents under the threshold; every count
                    printed anyway (the margin, discipline 4).
  FINDING (1)       any agent's since-last-subject count >= threshold.
                    Output states whether this is a CONVENTION-GAP READING
                    (little or no post-fix data yet) or a real signal.
  COULD-NOT-RUN (2) log unreadable / no parseable entries.

NARROWING_THRESHOLD = 60 real entries -- REASONED, not measured (H1's
starting number, kept for comparability); disclosed in every output.

Run:
  python scope_narrowing_check.py
  python scope_narrowing_check.py --selftest
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, 'hover-audit-log.jsonl')
AGENTS = ('hank', 'cc', 'fourth', 'cody')
NARROWING_THRESHOLD = 60  # REASONED, uncalibrated -- disclosed in output
REAL_TYPES = ('check', 'finding')
# The seq of the FIRST entry written under the new target-attribution
# convention (2026-09-27) -- computed as tip+1 at the moment of the fix,
# never adjusted after the fact. Entries below this seq structurally
# cannot carry an agent-name target; see module docstring.
ATTRIBUTION_STARTS_AT_SEQ = 243


def read_entries(path):
    try:
        out = []
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out, None
    except (OSError, ValueError) as e:
        return None, str(e)


def targets_of(entry):
    t = entry.get('target')
    if not isinstance(t, str):
        return set()
    return {p.strip().lower() for p in t.split(',') if p.strip()}


def narrowing(entries, agents=AGENTS, threshold=NARROWING_THRESHOLD,
              convention_since=ATTRIBUTION_STARTS_AT_SEQ):
    """Pure core. -> {agent: {'since': n, 'last_seq': seq-or-None,
    'since_post_convention': n}}, plus 'due', 'post_convention_real'
    (how much real fresh data exists at all, log-wide)."""
    per = {a: {'since': 0, 'since_post_convention': 0, 'last_seq': None,
               'counting': True} for a in agents}
    post_convention_real = 0
    for e in reversed(entries):
        real = e.get('type') in REAL_TYPES
        seq = e.get('seq')
        if real and isinstance(seq, int) and seq >= convention_since:
            post_convention_real += 1
        toks = targets_of(e) if real else set()
        for a in agents:
            d = per[a]
            if not d['counting']:
                continue
            if real and a in toks:
                d['last_seq'] = seq
                d['counting'] = False
            elif real:
                d['since'] += 1
                if isinstance(seq, int) and seq >= convention_since:
                    d['since_post_convention'] += 1
    for d in per.values():
        d.pop('counting')
    due = sorted(a for a, d in per.items() if d['since'] >= threshold)
    return {'per': per, 'due': due,
            'post_convention_real': post_convention_real}


def _selftest():
    fails = []

    def chk(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            fails.append(label)

    mk = lambda seq, typ, target: {'seq': seq, 'type': typ, 'target': target}
    T = NARROWING_THRESHOLD

    # negative control: hank last subject > threshold real entries ago,
    # every other agent recently a subject (so only hank can be due)
    es = [mk(1, 'check', 'hank')] + \
        [mk(i, 'check', 'cc,resource_x') for i in range(2, T + 3)] + \
        [mk(T + 3, 'check', 'fourth'), mk(T + 4, 'check', 'cody')]
    r = narrowing(es, convention_since=1)
    chk('one agent past threshold -> FINDING names exactly that agent',
        r['due'] == ['hank'] and r['per']['hank']['since'] >= T
        and r['per']['cc']['since'] == 2)

    # all-recent -> PASS
    es = [mk(i, 'check', a) for i, a in enumerate(AGENTS, 1)]
    r = narrowing(es, convention_since=1)
    chk('all four recently subjects -> PASS', r['due'] == [])

    # exact-token matching: a lookalike target must not count as the agent
    es = [mk(1, 'check', 'hank')] + \
        [mk(i, 'check', 'hank-probe.py') for i in range(2, T + 3)] + \
        [mk(T + 3, 'check', 'cc,fourth,cody')]
    r = narrowing(es, convention_since=1)
    chk("substring lookalike 'hank-probe.py' does not reset hank's counter",
        r['due'] == ['hank'] and r['per']['hank']['since'] >= T)

    # notes and non-real entries advance nothing
    es = [mk(1, 'check', 'cody')] + \
        [mk(i, 'note', 'x') for i in range(2, T + 20)]
    r = narrowing(es, convention_since=1)
    chk('non-real entries advance no counter',
        r['due'] == [] and r['per']['cody']['since'] == 0)

    # an agent NEVER a subject counts from genesis
    es = [mk(i, 'finding', 'cc') for i in range(1, T + 1)]
    r = narrowing(es, convention_since=1)
    chk('never-a-subject agents count from genesis',
        set(r['due']) == {'hank', 'fourth', 'cody'})

    # THE FIX ITSELF: entries entirely before the convention boundary
    # report due (honest -- it IS true of the field) but zero
    # since_post_convention and zero post_convention_real, so the caller
    # can label it a convention-gap reading rather than real drift.
    es = [mk(i, 'check', 'sb_vends') for i in range(1, T + 5)]
    r = narrowing(es, convention_since=T + 100)
    chk('all-pre-convention log -> due fires but post_convention_real is 0',
        set(r['due']) == set(AGENTS) and r['post_convention_real'] == 0
        and all(d['since_post_convention'] == 0 for d in r['per'].values()))

    # a real post-convention subject entry resets since_post_convention
    # to 0 for that agent even though 'since' (the honest total) does not
    # go negative or get erased -- last_seq becomes the post-convention seq
    es = [mk(i, 'check', 'sb_vends') for i in range(1, 30)] + \
        [mk(30, 'check', 'hank,sb_vends')] + \
        [mk(i, 'check', 'sb_vends') for i in range(31, 40)]
    r = narrowing(es, convention_since=25)
    chk('a real post-convention agent-subject entry is honored as last_seq',
        r['per']['hank']['last_seq'] == 30
        and r['per']['hank']['since'] == 9)

    print()
    if fails:
        print('%d SELFTEST FAILURE(S): %s' % (len(fails), fails))
        return 1
    print('ALL SELFTEST CASES PASS')
    return 0


def main(argv):
    if '--selftest' in argv:
        return _selftest()
    entries, err = read_entries(LOG)
    if entries is None or not entries:
        print('COULD NOT RUN: log unreadable or empty (%s). (exit 2)' % err)
        return 2
    r = narrowing(entries)
    print('SCOPE NARROWING -- real check/finding entries since each build '
          'agent was last the SUBJECT (structured target field, exact '
          'token; threshold %d, REASONED not measured; denominator excludes '
          'notes/no-reports). Attribution convention starts at seq %d -- '
          'see docstring for why entries before it carry no agent target '
          'by construction, not by neglect.'
          % (NARROWING_THRESHOLD, ATTRIBUTION_STARTS_AT_SEQ))
    for a in AGENTS:
        d = r['per'][a]
        last = ('last subject at seq %s' % d['last_seq']
                ) if d['last_seq'] is not None else 'NEVER a subject'
        print('  %-7s %4d real entries since (%s) -- %d of those postdate '
              'the attribution fix'
              % (a, d['since'], last, d['since_post_convention']))
    print('\n  %d real check/finding entries log-wide postdate the '
          'attribution fix (seq >= %d) -- this is how much FRESH, '
          'attribution-capable data exists at all right now.'
          % (r['post_convention_real'], ATTRIBUTION_STARTS_AT_SEQ))
    print()
    if r['due']:
        convention_gap = [a for a in r['due']
                          if r['per'][a]['since_post_convention'] == 0]
        real_signal = [a for a in r['due'] if a not in convention_gap]
        if convention_gap:
            print('CONVENTION-GAP READING (not evidence of neglect): %s '
                  'show zero post-fix entries in their "since" count -- '
                  'this reflects the historical absence of agent-name '
                  'targets before seq %d, not attention that has actually '
                  'narrowed. Re-run once real post-fix data accumulates.'
                  % (', '.join(convention_gap), ATTRIBUTION_STARTS_AT_SEQ))
        if real_signal:
            print('FINDING (ATTENTION-ONLY, backed by real post-fix data '
                  '-- still cannot distinguish "coverage narrowed" from '
                  '"that agent had less landed work to check"): %s past '
                  'the threshold with real post-convention entries in the '
                  'count. Each is a CANDIDATE for the next targeted or '
                  'undirected pass, not a confirmed neglect.'
                  % ', '.join(real_signal))
        return 1
    print('PASS: all four under the threshold; margins printed above.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
