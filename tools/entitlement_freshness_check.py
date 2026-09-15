"""Can anything in this repo ever REVOKE an entitlement it granted?

Run:  python tools/entitlement_freshness_check.py
      python tools/entitlement_freshness_check.py --json

ITEM 100 -- THE PRE-SIGNED-REMEDY QUESTION, ASKED MECHANICALLY
--------------------------------------------------------------
Lightning Network channels settle an unsolvable problem: you hand a counterparty
the ability to act, knowing you cannot force them to behave. The answer is not
to trust them and not to ask permission later. It is to PRE-SIGN THE REMEDY
BEFORE handing over control -- a penalty transaction that already exists, plus a
WATCHTOWER that watches for the cheat and can act WITHOUT the counterparty's
cooperation. The remedy must not depend on the party it is a remedy against.

A SaaS paywall is the same shape with the names changed. Stripe holds the truth
about whether somebody is still paying. The app hands out access. If the only
path from "they stopped paying" back to "access removed" runs through a webhook
Stripe has to deliver, or through a human noticing, THEN THE REMEDY DEPENDS ON
THE COUNTERPARTY and there is no watchtower.

WHAT THIS CHECKS, AND WHY IT IS NARROW
---------------------------------------
One question per entitlement field: **is there anything in this repo that can
ever change it?**

  readers  -- code that reads the field to decide access
  writers  -- code that can WRITE the field (POST/PATCH to its table)

A field with readers and NO writers is a MIRROR NOTHING MAINTAINS. Whatever it
said when a human last typed it, it still says. That is reported as UNREVOKABLE
-- not as a bug found in a line, but as a missing mechanism, which is the only
honest way to report an absence.

AND A SHARPER SUB-CASE, BECAUSE PRESENCE IS NOT STATE
------------------------------------------------------
`const isPaid = !!lic.stripe_subscription_id;` decides a paid tier from the mere
EXISTENCE of an external identifier. A cancelled subscription keeps its id
forever -- `sub_...` is the receipt that a subscription once existed, never
evidence that it exists now. Even a perfectly-reconciled mirror cannot fix this
expression, because it never asks the mirror anything. Reported separately.

WHAT THIS DOES NOT DO, STATED SO A CLEAN RUN IS NOT OVER-READ
--------------------------------------------------------------
  * It does not contact Stripe, or any provider. It reads this repo only.
  * It does not know whether a licence is CURRENTLY wrong. It reports whether a
    mechanism exists that could ever make it right.
  * A writer existing is not proof the writer is correct or ever runs. Presence
    of a mechanism is the floor this measures, not its quality.
  * SQL files are counted separately from code and NEVER as writers. A hand-run
    migration is a human remembering, which is precisely the thing a watchtower
    replaces. They are printed so a reader can see the field is set SOMEWHERE.

Exit codes:
  0  every entitlement field has at least one in-repo writer
  1  at least one is UNREVOKABLE, or decides access from an identifier's presence
  2  could not read a required source -- NOT a pass
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
LICENSE_LIB = os.path.join('api', '_lib', 'license.js')

# The authority module and the table it reads. Derived from the file rather than
# listed here: the fields come from what validateLicenseKey() actually maps out
# of the row, so a column added tomorrow is picked up without editing this tool.
TABLE = 'license_keys'

# Fields whose value is OWNED BY AN EXTERNAL PROVIDER and therefore can go stale
# without anything local happening. `app_id` and `customer_email` are local facts
# about the sale; they do not decay on their own and are not entitlement state.
EXTERNAL_OWNED = ('status', 'stripe_subscription_id', 'trial_ends_at', 'plan')

# `!!<anything>_subscription_id` and friends: a boolean derived from an
# identifier's PRESENCE. Deliberately not `\bsubscription\b` -- that matches
# prose, comments and a dozen unrelated variables.
#
# NARROWED TWICE ON 2026-09-15, both times against a real false positive the
# first version produced the moment the defect it names was actually FIXED.
#
#  1. ANCHORED AT THE START OF A LINE. Unanchored, it matched the FIX'S OWN
#     COMMENT -- `// This was `const isPaid = !!lic.stripe_subscription_id;`` --
#     so repairing the defect made the count go UP, from 3 to 6. A marker
#     search that cannot tell code from prose about code is the `esign`/`design`
#     trap in a new costume, and this repo has now been bitten by it twice in
#     one day (`api/license-trial-gate.test.js` hit the identical thing).
#
#  2. `ever...` IS EXCLUDED FROM THE NAME, because a name in the PAST TENSE is
#     the honest reading of an identifier. `const everSubscribed =
#     !!lic.stripe_subscription_id` is exactly right: an id proves a
#     subscription once existed, and that is what the name claims. The defect
#     is a boolean named for a CURRENT entitlement (`isPaid`, `entitled`)
#     derived from a fact about the past. The tense IS the bug, so the rule
#     keys on it -- and `isSubscribed` is still caught, which the control
#     asserts so this narrowing cannot quietly gut the check.
PRESENCE_GATE = re.compile(
    r'^[ \t]*(?:const|let|var)\s+(?!ever)(\w*(?:[Pp]aid|[Ee]ntitled|[Ss]ubscribed)\w*)\s*=\s*'
    r'!!\s*[\w.]*\.(\w*subscription_id|\w*customer_id)\b', re.M)


def fail(msg):
    print('COULD NOT RUN: ' + msg)
    print('Nothing was checked. This is exit 2, not a pass.')
    sys.exit(2)


def tracked(patterns):
    r = subprocess.run(['git', '-C', REPO, 'ls-files'] + list(patterns),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        fail('git ls-files failed: ' + (r.stderr or '')[:200])
    return [p for p in r.stdout.splitlines() if p.strip()]


def read(rel):
    try:
        return io.open(os.path.join(REPO, rel), encoding='utf-8',
                       errors='replace').read()
    except OSError as e:                                        # noqa: BLE001
        fail('could not read %s: %s' % (rel, e))


# ── 1. DERIVE THE FIELD LIST FROM THE AUTHORITY, DO NOT LIST IT ─────────────
# A hardcoded list is a list that goes stale silently. This reads the mapping
# block out of validateLicenseKey() itself, so the tool tracks the function it
# is asking about.
src = read(LICENSE_LIB)
mapped = re.findall(r'out\.\w+\s*=\s*(?:String\()?\s*row\.(\w+)', src)
if not mapped:
    fail('found no `out.x = row.y` mapping in %s -- the shape this tool '
         'depends on has changed, so it is reporting nothing rather than '
         'reporting zero' % LICENSE_LIB)
fields = [f for f in dict.fromkeys(mapped) if f in EXTERNAL_OWNED]
if not fields:
    fail('none of the mapped columns %s is externally owned -- either the '
         'schema moved or EXTERNAL_OWNED is stale' % sorted(set(mapped)))

print('ENTITLEMENT FRESHNESS -- item 100, the pre-signed-remedy question\n')
print('  authority : %s' % LICENSE_LIB.replace(os.sep, '/'))
print('  table     : %s' % TABLE)
print('  fields    : %s  (derived from the mapping block, not listed)\n'
      % ', '.join(fields))

# ── 2. WHO CAN WRITE THE TABLE AT ALL ───────────────────────────────────────
# A writer is a non-test .js under api/ or tools/ that issues a POST or PATCH
# whose URL names the table. Reading the table is not writing it, and a test
# fixture that returns a row is not a writer -- excluding *.test.js matters,
# because eleven of them mention `license_keys` and every one is a stub.
#
# THE PATHSPEC IS `api/` AND NOT `api/**/*.js`, AND THIS IS NOT A STYLE CHOICE.
# The first version of this tool used `api/**/*.js`. Git pathspecs match with
# FNM_PATHNAME, so `**` requires AT LEAST ONE directory level and
# `api/sd-data.js` DID NOT MATCH. It reported 4 readers where there are 27, and
# 1 presence-gate where there are 3 -- a clean-looking undercount with no error
# anywhere. Caught by a control that asserts a known file is in the list, which
# is now arm 1 of tests/entitlement_freshness_control.py. Directory pathspecs
# recurse; do not "tidy" these back into globs.
code = [p for p in tracked(['api/', 'tools/', 'scripts/'])
        if p.endswith('.js') and not p.endswith('.test.js')]
sql = [p for p in tracked(['sql/']) if p.endswith('.sql')]

writers, readers = [], []
for p in code:
    body = read(p)
    if TABLE not in body:
        continue
    readers.append(p)
    # POST/PATCH whose statement mentions the table within the same call.
    for m in re.finditer(r"method\s*:\s*'(POST|PATCH|PUT)'", body):
        window = body[max(0, m.start() - 600):m.start() + 600]
        if TABLE in window:
            writers.append((p, m.group(1)))
            break

# `public.license_keys` is the spelling the seeds actually use, so the schema
# qualifier has to be optional AND allow a dot -- `\w*\.?` does not match
# `public.`, which is how the first run reported 0 SQL writers next to a file
# literally named demo_license_keys_seed.sql.
SQL_WRITE = re.compile(r'(?:insert\s+into|update|upsert\s+into)\s+'
                       r'(?:[\w"]+\s*\.\s*)?"?' + TABLE, re.I)
sql_writers = [p for p in sql if SQL_WRITE.search(read(p))]

print('  in-repo CODE that reads %s : %d file(s)' % (TABLE, len(readers)))
print('  in-repo CODE that WRITES it : %d file(s)%s'
      % (len(writers), '' if writers else '   <-- nothing'))
print('  hand-run SQL that writes it : %d file(s)  (NOT counted as a writer)'
      % len(sql_writers))
for p in sql_writers[:6]:
    print('      ' + p)
if len(sql_writers) > 6:
    print('      ... and %d more' % (len(sql_writers) - 6))
print()

# ── 3. THE VERDICT PER FIELD ────────────────────────────────────────────────
problems = []
for f in fields:
    f_readers = [p for p in readers if re.search(r'\b' + f + r'\b', read(p))]
    if writers:
        print('  ok         %-24s %d reader(s), %d in-repo writer(s)'
              % (f, len(f_readers), len(writers)))
        continue
    print('  UNREVOKABLE %-23s %d reader(s), NO in-repo writer'
          % (f, len(f_readers)))
    problems.append((f, 'no in-repo writer', f_readers))

# ── 4. THE SHARPER SUB-CASE: A GATE ON AN IDENTIFIER'S PRESENCE ─────────────
print()
presence = []
for p in code:
    for m in PRESENCE_GATE.finditer(read(p)):
        line = read(p)[:m.start()].count('\n') + 1
        presence.append((p, line, m.group(1), m.group(2)))

if presence:
    print('  PRESENCE-GATED ENTITLEMENT -- %d site(s). An identifier existing is'
          % len(presence))
    print('  not a subscription being active; a cancelled sub keeps its id.')
    for p, line, var, field in presence:
        print('      %s:%d   %s = !!....%s' % (p, line, var, field))
    problems.append(('presence-gate', '%d site(s)' % len(presence),
                     ['%s:%d' % (p, l) for p, l, _v, _f in presence]))
else:
    print('  ok         no entitlement decided from an identifier\'s presence')

if '--json' in sys.argv:
    print('\n' + json.dumps({'fields': fields, 'writers': writers,
                             'sql_writers': sql_writers,
                             'presence_gates': presence}, indent=1))

print('\n%d finding(s)' % len(problems))
for f, why, where in problems:
    print('  - %-18s %s' % (f, why))
    for w in where[:4]:
        print('      ' + str(w))
sys.exit(1 if problems else 0)
