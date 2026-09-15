"""A hand-written list that was supposed to match a pinned register, and nothing compared them.

    python tools/pinned_list_drift_check.py
    python tools/pinned_list_drift_check.py --json
    python tools/pinned_list_drift_check.py --all     # include the low-signal rows

Exit 0 always. REPORT-ONLY, and it is a READ-LIST rather than a score -- the
correct length of its output is NOT zero, for the same reason
accepted_risk_scan.py's is not. Most partial lists on this platform are partial
ON PURPOSE with a reason written beside them. What this tool does is put the
comparison in front of a person, because the two real defects below were both
found by a person happening to do that comparison by hand.

── THE DEFECT SHAPE, FOUND TWICE IN TWO DAYS ───────────────────────────────────
A literal list of resource names in one file, which is supposed to correspond to
a population defined in another file, with NOTHING anywhere comparing them.

  2026-09-14  SC_TIER_A_WRITE_GATED was a hand-written list of SIX while
              docs/CRITICALITY-TIERS.md said SEVEN sc_* resources are Tier A.
              sc_denial_events was the one missing. Measured against the
              DEPLOYED function on 2026-09-15: the other six answered 401
              NO_SESSION to a write carrying the licence key alone, and
              sc_denial_events answered 200. A Tier A medical-billing record
              took a write from anybody holding a string the app's own
              documentation says is not auth.

  2026-09-15  api/_resources/sairncode.js granted a destroying `delete` to all
              28 names with one reduce(), so the seven Tier A records inherited
              a destroy verb nobody chose for them -- item 97.

Both were the same shape one file apart, and in both cases every individual
piece was correct: the register was right, the list was right when written, and
the code did exactly what it said. The failure was that no third thing ever
asked whether the two agreed.

── WHAT IT REPORTS, AND WHAT IT REFUSES TO CALL A FINDING ──────────────────────
For every literal array of registered resource names it can find, it says which
app owns them, and how the list compares to two pinned populations: that app's
REGISTRY, and that app's TIER A set from docs/CRITICALITY-TIERS.md.

  PARTIAL-TIER-A   a proper subset of the app's Tier A set. THIS IS THE SHAPE
                   THAT BIT TWICE and is the only class printed by default.
  COVERS-TIER-A    equals the Tier A set. Read it anyway -- equal today is not
                   derived, and the next tier change is where it drifts.
  COVERS-REGISTRY  equals the whole registry for that app.
  MIXED            names from more than one app. Almost always a deliberate
                   cross-app list; reported under --all.
  OTHER            some other subset; reported under --all.

A DERIVED LIST IS NOT REPORTED AT ALL, and that is the point of the tool: the
fix for both real cases was to derive one list from the other, so a list that
already is derived has nothing to drift.

── WHAT IT CANNOT SEE, said plainly ───────────────────────────────────────────
  * WHETHER A PARTIAL LIST IS WRONG. Most are partial deliberately, with the
    reason written beside them -- SB_SYNCED excludes seven collections and
    names each one. It cannot read that reasoning and does not try.
  * A LIST BUILT AT RUNTIME from anything other than a plain literal --
    concatenations, spreads, values pulled from a config object.
  * A LIST OF SOMETHING ELSE PINNED. Roles, table names, verbs and file paths
    have the same failure shape and are NOT covered here. Named as a known
    hole rather than left as an apparent absence.
  * WHETHER ANYTHING ALREADY COMPARES THE TWO. A list with a test pinning it
    to the register looks identical to one with nothing. That is why this is a
    read-list: the tool narrows 400-odd resources to a handful of rows, and a
    person decides.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')

# A list has to be this long to be interesting. Two names is a pair, not a
# population, and pairs are everywhere.
MIN_MEMBERS = 3

SKIP_DIRS = ('docs/skill-backups/', 'docs/sources/', 'node_modules/', '.git/')


def sh(*args):
    # ENCODING IS EXPLICIT, AND THIS IS A REAL DEFECT THAT WAS HERE (2026-09-15).
    # `text=True` alone decodes with the LOCALE default, which is cp1252 on this
    # platform -- and this repo's diffs are full of box-drawing characters and
    # em-dashes. The reader thread raised UnicodeDecodeError, the exception was
    # printed by the threading machinery, and the call returned with stdout
    # TRUNCATED rather than failing. A diff-reading gate that silently gets a
    # short diff under-detects and reports clean, which is the worst direction
    # for this particular tool to be wrong in.
    r = subprocess.run(list(args), cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.stdout if r.returncode == 0 else ''


def registry():
    """resource -> owning app, read by RUNNING api/_resources/index.js. It
    composes eighteen modules and one of them builds its grants with a reduce();
    a regex over the sources would miss exactly the shapes this tool is about."""
    src = ('const i=require("./api/_resources/index.js");'
           'process.stdout.write(JSON.stringify({o:i.OWNER_BY_RESOURCE,'
           'n:i.RESOURCE_NAMES}));')
    r = subprocess.run(['node', '-e', src], cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=120)
    if r.returncode != 0:
        sys.stderr.write('COULD NOT RUN -- the resource registry did not load. '
                         'That is a finding about api/_resources/, not a clean '
                         'result here:\n' + (r.stderr or '')[:500] + '\n')
        sys.exit(2)
    d = json.loads(r.stdout)
    return d['o'], set(d['n'])


def tier_a_by_app(owner):
    """The Tier A set, per app, from the register. FAILS CLOSED on an empty
    parse -- an empty set would make every list look like a complete cover."""
    text = io.open(REGISTER, encoding='utf-8').read()
    names = set()
    for line in text.split('\n'):
        m = re.match(r'^\|\s*`([a-z0-9_]+)`\s*\|\s*\*\*A\*\*\s*\|', line)
        if m:
            names.add(m.group(1))
    if not names:
        sys.stderr.write('COULD NOT MEASURE -- docs/CRITICALITY-TIERS.md yielded '
                         'ZERO Tier A rows. An empty set would make every list '
                         'below look complete.\n')
        sys.exit(2)
    out = {}
    for n in names:
        out.setdefault(owner.get(n, '?'), set()).add(n)
    return out, names


# A literal array of quoted strings, on one line or several. Deliberately
# simple: anything cleverer starts matching code that only looks like a list.
ARRAY = re.compile(r"\[\s*((?:['\"][a-z0-9_]+['\"]\s*,\s*)+['\"][a-z0-9_]+['\"]\s*,?)\s*\]")
MEMBER = re.compile(r"['\"]([a-z0-9_]+)['\"]")
# The assignment that owns the array, so a row can name it.
NAME_BEFORE = re.compile(r"([A-Za-z_$][\w$.]*)\s*[:=]\s*$")


def tracked_files():
    out = []
    for rel in sh('git', 'ls-files').split('\n'):
        rel = rel.strip().replace('\\', '/')
        if not rel or any(rel.startswith(d) for d in SKIP_DIRS):
            continue
        if rel.endswith(('.js', '.py', '.html', '.json')):
            out.append(rel)
    return out


def scan_text(rel, body, resources, owner):
    """Split out from scan() so the probe can drive it with fixture STRINGS.
    A probe that had to write a file into this repo to test a scanner is a probe
    that can lose somebody else's work on a branch four sessions share."""
    rows = []
    for m in ARRAY.finditer(body):
        members = MEMBER.findall(m.group(1))
        known = [x for x in members if x in resources]
        if len(known) < MIN_MEMBERS or len(known) != len(members):
            # A list that is only PARTLY resource names is something else -- a
            # mixed list of verbs and names, a config block. Requiring every
            # member to be registered keeps this narrow on purpose.
            continue
        line = body.count('\n', 0, m.start()) + 1
        head = body[:m.start()].rsplit('\n', 1)[-1]
        nm = NAME_BEFORE.search(head.rstrip())
        apps = set(owner.get(x, '?') for x in known)
        rows.append({
            'file': rel, 'line': line,
            'name': nm.group(1) if nm else '(unnamed)',
            'members': sorted(set(known)),
            'apps': sorted(apps),
        })
    return rows


def scan(paths, resources, owner, tier_a):
    rows = []
    for rel in paths:
        try:
            body = io.open(os.path.join(REPO, rel), encoding='utf-8',
                           errors='replace').read()
        except OSError:
            continue
        rows.extend(scan_text(rel, body, resources, owner))
    return rows


def classify(row, by_app, registry_names, owner):
    got = set(row['members'])
    if len(row['apps']) != 1:
        return 'MIXED', []
    app = row['apps'][0]
    ta = by_app.get(app, set())
    reg = set(n for n in registry_names if owner.get(n) == app)
    if ta and got == ta:
        return 'COVERS-TIER-A', []
    if reg and got == reg:
        return 'COVERS-REGISTRY', []
    if ta and got < ta:
        return 'PARTIAL-TIER-A', sorted(ta - got)
    if ta and got & ta and not got >= ta:
        # Touches Tier A without covering it -- the same question, one step
        # weaker, because the list is not purely a Tier A list.
        return 'PARTIAL-TIER-A', sorted(ta - got)
    return 'OTHER', []


def main():
    owner, resources = registry()
    by_app, all_tier_a = tier_a_by_app(owner)
    rows = scan(tracked_files(), resources, owner, by_app)
    for r in rows:
        r['class'], r['missing'] = classify(r, by_app, resources, owner)

    if '--json' in sys.argv:
        print(json.dumps(rows, indent=2))
        return 0

    interesting = [r for r in rows if r['class'] == 'PARTIAL-TIER-A']
    others = [r for r in rows if r['class'] != 'PARTIAL-TIER-A']

    print('HAND-WRITTEN LISTS OF RESOURCE NAMES -- report only, nothing is blocked')
    print('  literal lists found            : %d' % len(rows))
    print('  Tier A resources in the register: %d' % len(all_tier_a))
    print('')
    print('  PARTIAL-TIER-A -- a list that names Tier A resources and does NOT')
    print('  name all of that app\'s. This is the shape that bit twice: a gate')
    print('  list of six beside a register that said seven, and nothing')
    print('  comparing them. IT IS NOT A FINDING BY ITSELF -- most partial')
    print('  lists here are partial on purpose. Read the reason beside each.')
    print('')
    if not interesting:
        print('    none.')
    for r in sorted(interesting, key=lambda x: (x['file'], x['line'])):
        print('  %s:%d  %s  [%s]' % (r['file'], r['line'], r['name'], r['apps'][0]))
        print('      has %d: %s' % (len(r['members']), ', '.join(r['members'])[:100]))
        print('      Tier A NOT in it: %s' % (', '.join(r['missing'])[:100] or 'none'))
    print('')
    counts = {}
    for r in others:
        counts[r['class']] = counts.get(r['class'], 0) + 1
    print('  Other classes (--all to list): '
          + (', '.join('%s %d' % (k, v) for k, v in sorted(counts.items())) or 'none'))
    if '--all' in sys.argv:
        for r in sorted(others, key=lambda x: (x['class'], x['file'], x['line'])):
            print('  [%-15s] %s:%d %s -- %d name(s)'
                  % (r['class'], r['file'], r['line'], r['name'], len(r['members'])))
    print('')
    print('  A DERIVED LIST IS NOT HERE AT ALL, and that is the fix both real')
    print('  cases got: derive one list from the other and there is nothing to')
    print('  drift. What this cannot see is whether a test already pins a list')
    print('  to its register -- so this is a read-list, not a score, and its')
    print('  correct length is not zero.')
    print('  NOT COVERED, named rather than implied: lists of ROLES, TABLE')
    print('  NAMES, VERBS or FILE PATHS have the same failure shape and are')
    print('  outside this tool.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
