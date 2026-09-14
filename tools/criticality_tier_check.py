"""Every registered resource in a re-tiered app must carry a criticality tier.

    python tools/criticality_tier_check.py            # report, exit 1 on drift
    python tools/criticality_tier_check.py --quiet    # exit code only

WHY THIS EXISTS. `docs/CRITICALITY-TIERS.md` states, for each RESOURCE, the worst
consequence of it being wrong, and cites something already recorded in this repo
as the evidence. Third of the three standing disciplines for vertical work,
alongside the SOUP register and the traceability matrix.

── IT USED TO CHECK APPS, AND THAT WAS THE DEFECT (2026-09-10) ─────────────
The register tiered whole apps. Measuring the eight Tier B apps moved every one
of them to A -- their B rested on an absence of RECORDING, not a measured
absence -- and 21 of 22 verticals became Tier A, at which point the register had
stopped discriminating. The measurement was honest; the GRANULARITY was wrong.
A roofing app's invoicing panel and its colour-theme settings do not carry the
same consequence, and one label per app forces them into one answer.

The unit is now `api/_resources/<app>.js`, the same unit the SOUP register and
the traceability matrix already use.

IT REPORTS AND NEVER REWRITES, deliberately. The tier and its sentence are a
JUDGEMENT; a tool that regenerated this file would delete exactly the part that
matters and leave a table that looks authoritative because a machine made it.

WHAT IT CAN AND CANNOT SEE, said plainly because a checker that overstates its
reach is worse than none:

  IT CAN SEE    an app with no rollup line; a re-tiered app whose rows and
                registry disagree in either direction; a rollup count that does
                not match the rows under it; a tier outside A/B/C; a Tier A row
                with no evidence; resource rows under an app that claims not to
                be re-tiered yet.

  IT CANNOT SEE whether a tier is RIGHT. Nothing mechanical can. That is what
                the evidence column is for.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
RESOURCES = os.path.join(REPO, 'api', '_resources')
VALID_TIERS = ('A', 'B', 'C')


def cells(line):
    """Split a markdown row, honouring an escaped pipe as CONTENT -- this repo
    has a standing rule about it, and this file's own index row tripped it."""
    out, cur, i, bs = [], '', 0, chr(92)
    while i < len(line):
        if line[i] == bs and i + 1 < len(line) and line[i + 1] == '|':
            cur += '|'
            i += 2
            continue
        if line[i] == '|':
            out.append(cur.strip())
            cur = ''
            i += 1
            continue
        cur += line[i]
        i += 1
    out.append(cur.strip())
    return out[1:-1] if len(out) >= 2 else []


def apps_with_registries():
    out = {}
    if not os.path.isdir(RESOURCES):
        return out
    for f in sorted(os.listdir(RESOURCES)):
        if not f.endswith('.js') or f.endswith('.test.js'):
            continue
        app = f[:-3]
        if app in ('index', 'shared'):
            continue
        names, err = resource_names(os.path.join(RESOURCES, f))
        if err:
            # A FILE WHOSE SHAPE IS NOT RECOGNISED IS AN ERROR, NOT AN EMPTY
            # APP. Returning an empty set would make every resource in it
            # vanish from the register check and the app would read CLEAN --
            # which is the fail-open direction and the worst possible answer
            # from a completeness checker.
            out[app] = SHAPE_ERROR(err)
            continue
        out[app] = names
    return out


class SHAPE_ERROR(str):
    """A file this reader could not parse. Truthy and NOT a set, so any use of
    it as a name collection fails loudly instead of contributing zero names."""


def resource_names(path):
    """Names inside the `resources: [...]` array ONLY.

    ── WHY THIS IS NOT "any line that looks like a quoted string" ────────────
    It was, until 2026-09-14, and the answer depended on WHERE SOMEBODY PUT A
    COMMENT. api/_resources/sairnvet.js declares three local-only keys together
    in `notSynced`:

        'sv_examrooms_turnover',  // NOT RECORDS -- a flat array of NUMBERS
        'sv_settings',            // device configuration
        ...
        'sv_audit_backed',

    The old rule required the line to END in `',` with exactly two quotes. The
    first two carry trailing comments and so were invisible; the third has its
    comment on the lines ABOVE and so was scraped as a server resource. The
    checker then reported `sairnvet/sv_audit_backed is registered and has no
    row` -- a finding produced entirely by comment placement, about a key that
    is DECLARED LOCAL-ONLY and correctly has no tier row.

    `notSynced` is the opposite of registered: it is the list of things that
    deliberately never reach a server. Counting it was always wrong; the
    comment style merely decided which of the three got noticed.
    """
    try:
        lines = io.open(path, encoding='utf-8').read().splitlines()
    except Exception as e:
        return None, 'could not read (%s)' % type(e).__name__
    # THREE SHAPES EXIST IN api/_resources/ AND ALL THREE ARE REAL. The first
    # version of this reader knew only the first and reported the other two as
    # a changed file shape -- which was loud and wrong, and is why it is worth
    # enumerating them here rather than widening a regex until nothing
    # complains.
    #
    #   resources: [            multi-line array          (13 files)
    #   resources: [],          explicitly EMPTY          (sairncash)
    #   resources: RESOURCES,   a reference to a const    (sairncode)
    start = None
    for i, l in enumerate(lines):
        # An explicitly empty array is a real answer, not a parse failure: the
        # app owns no resources of its own and the master plan already says so.
        if re.match(r'^\s*resources:\s*\[\s*\]\s*,?\s*$', l):
            return set(), None
        if re.match(r'^\s*resources:\s*\[\s*$', l):
            start = i + 1
            break
        m = re.match(r'^\s*resources:\s*([A-Z_][A-Z0-9_]*)\s*,\s*$', l)
        if m:
            # Follow the reference to `const NAME = [`. One hop only -- a chain
            # is a shape nobody has written and guessing at it would be the
            # widening this comment warns against.
            for j, l2 in enumerate(lines):
                if re.match(r'^\s*const\s+' + re.escape(m.group(1)) + r'\s*=\s*\[\s*$', l2):
                    start = j + 1
                    break
            if start is None:
                return None, ('resources references %s and no `const %s = [` was '
                              'found' % (m.group(1), m.group(1)))
            break
    if start is None:
        return None, 'no `resources:` array or reference found -- the file shape changed'
    names = set()
    for l in lines[start:]:
        # Another TOP-LEVEL key (two-space indent) ends the array. That is what
        # `notSynced:` and `extraActions:` are, and stopping here is the whole
        # fix.
        if re.match(r'^  \w+:', l) or re.match(r'^\};', l) or re.match(r'^\s*\]\s*;?\s*$', l):
            break
        m = re.match(r"^\s*'([\w.-]+)'\s*,", l)
        if m:
            names.add(m.group(1))
    if not names:
        return None, 'the `resources: [` array parsed to ZERO names -- that is a '                     'broken reader, not an app with no resources'
    return names, None


def parse():
    """(rollup, resource_rows). Rollup rows have 6 cells and a backticked app in
    cell 0; resource rows have 4 and a backticked name. Anchored on shape AND on
    the backtick so the TIER LEGEND above -- same column count -- is not read as
    data. Counting columns alone would have swallowed it."""
    src = io.open(REGISTER, encoding='utf-8').read()
    rollup, rows = {}, []
    for line in src.split('\n'):
        if not line.startswith('|'):
            continue
        c = cells(line)
        if len(c) == 6:
            m = re.match(r'^`([\w.-]+)`$', c[0])
            if m:
                rollup[m.group(1)] = {
                    'n': c[1], 'a': c[2], 'b': c[3], 'c': c[4], 'status': c[5]}
        elif len(c) == 4:
            m = re.match(r'^`([\w.-]+)`$', c[0])
            if m:
                rows.append((m.group(1), re.sub(r'[*`]', '', c[1]).strip(), c[2], c[3]))
    return rollup, rows


def main(argv):
    quiet = '--quiet' in argv
    problems = []

    if not os.path.isfile(REGISTER):
        print('docs/CRITICALITY-TIERS.md is missing -- that is the finding, not a '
              'reason to pass.')
        return 1

    rollup, rows = parse()
    reg = apps_with_registries()
    by_name = {r[0]: r for r in rows}

    for app in sorted(reg):
        if app not in rollup:
            problems.append('NO ROLLUP    %s has a resource registry and no rollup line. '
                            'An app nobody has even said "not yet" about is invisible.'
                            % app)
    for app in sorted(set(rollup) - set(reg)):
        problems.append('GONE         %s has a rollup line and no resource registry.' % app)

    for app in sorted(set(rollup) & set(reg)):
        retiered = 'NOT YET RE-TIERED' not in rollup[app]['status']
        names = reg[app]
        present = {n for n in names if n in by_name}
        if retiered:
            for n in sorted(names - present):
                problems.append('NO TIER      %s/%s is registered and has no row.' % (app, n))
            counts = {'A': 0, 'B': 0, 'C': 0}
            for n in sorted(present):
                t = by_name[n][1]
                if t in counts:
                    counts[t] += 1
            for key, label in (('a', 'A'), ('b', 'B'), ('c', 'C')):
                want = rollup[app][key]
                got = str(counts[label])
                if re.sub(r'[^0-9]', '', want) != got:
                    problems.append('COUNT        %s rollup says %s=%s, the rows say %s. '
                                    'A summary that disagrees with its own detail is worse '
                                    'than no summary.' % (app, label, want, got))
        else:
            for n in sorted(present):
                problems.append('HALF DONE    %s/%s has a resource row while the rollup '
                                'says NOT YET RE-TIERED. One of the two is wrong, and a '
                                'half-tiered app reads as an untiered one.' % (app, n))

    all_registered = set()
    for names in reg.values():
        all_registered |= names
    for name, tier, worst, ev in rows:
        if name not in all_registered:
            problems.append('NOT A RESOURCE  %s has a row and is not registered in any '
                            'api/_resources/*.js. The unit of this table is the registry.'
                            % name)
        if tier not in VALID_TIERS:
            problems.append('BAD TIER     %s has tier %r, not one of %s'
                            % (name, tier, '/'.join(VALID_TIERS)))
        if not worst:
            problems.append('NO WORST CASE  %s states no consequence' % name)
        # A TIER A ROW MUST CARRY ITS OWN EVIDENCE. This is the line that stops
        # the A tier degrading into rule-guessing: B and C are classified by the
        # stated rule, A is hand-verified, and the difference has to be
        # enforceable rather than promised.
        if tier == 'A' and not ev:
            problems.append('NO EVIDENCE  %s is Tier A with an empty evidence cell -- '
                            'that is a label, not a tier.' % name)

    if not quiet:
        for p in problems:
            print(p)
        print('')
        print('APPS_WITH_REGISTRIES:%d' % len(reg))
        print('RESOURCES_REGISTERED:%d' % len(all_registered))
        print('RESOURCE_ROWS:%d' % len(rows))
        print('RETIERED_APPS:%d' % sum(
            1 for a in rollup if 'NOT YET RE-TIERED' not in rollup[a]['status']))
        print('TIER_A:%d' % sum(1 for r in rows if r[1] == 'A'))
        print('PROBLEMS:%d' % len(problems))
        if not problems:
            print('')
            print('NOTE: this says every registered resource in a RE-TIERED app has a '
                  'tier, and that every Tier A carries evidence. It does not say the '
                  'tier is right -- nothing mechanical can.')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
