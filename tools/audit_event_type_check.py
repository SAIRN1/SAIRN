#!/usr/bin/env python
# OWNER: hank
"""audit_event_type_check.py -- does every event_type the code EMITS appear in
the CHECK constraint on the audit table it writes to?

    python tools/audit_event_type_check.py             # report
    python tools/audit_event_type_check.py --json
    python tools/audit_event_type_check.py --selftest  # fixtures, both directions

EXIT 0 every emitted value is allowed. EXIT 1 at least one is REJECTED
(report-only convention: findings). EXIT 2 COULD NOT RUN -- never folded into 0.

── THE DEFECT THIS EXISTS FOR, AND IT WAS MINE ─────────────────────────────
On 2026-10-06 I added audit calls to four endpoints so that granting access
would be attributable. `tests/provisioning_attribution.js` went green: 10 arms,
three runs, and every arm asserted the POST the handler ISSUED to the audit
table -- which is correct, and is exactly what sairn-api-tester section 7 asks
for.

FOUR OF THE EVENT TYPES THAT CODE EMITS ARE REJECTED BY THE CHECK CONSTRAINT ON
THE TABLE. The insert fails, `writeAuditLog` returns false, the response says
`attributed:false`, and SIX MANAGEMENT-WRITE PATHS RECORD NOTHING. The suite
stayed green for a whole day.

A STUBBED `fetch` CANNOT REFUSE A ROW. That is the whole of it. The test
replaced the one layer that would have said no, so the stronger the mock, the
more completely it hid the defect. No amount of care inside the handler's own
contract reaches this: the constraint lives one boundary further out.

── WHY A STATIC CHECK AND NOT A BETTER TEST ────────────────────────────────
The honest alternative is a live round trip, and that needs a database. This
runs with no network, on any clone, in under a second, and answers the one
question a mock structurally cannot: is this string in that column's CHECK list.

It does NOT replace the live round trip and does not claim to. It closes the
specific gap where the answer was knowable from two files that were both sitting
in the repo.

── MEASURED ON ITS FIRST LIVE RUN, 2026-10-07, at HEAD 4fd3b94f ────────────
3 of 3 audit-log tables carrying an event_type CHECK had at least one emitted
value their CHECK rejects -- TWELVE distinct values across SEVEN api/ files.
`sv_audit_log` carries no event_type CHECK at all, so it cannot be violated and
is reported separately rather than counted as clean.

── WHAT IT CANNOT SEE, printed on every run rather than filed ──────────────
Both halves are LEXICAL. An `event_type` built from a variable, and a target
table reached through a helper, are invisible -- so the error direction is a
MISS, not a false accusation. A CLEAN ROW IS WEAKER EVIDENCE THAN A DIRTY ONE,
and that asymmetry is stated because the opposite assumption is what a green bar
invites.
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRITERIA_VERSION = '2026-10-07.1'

# Both spellings the platform uses for an emitted event, plus the ternary form.
EV_DIRECT = re.compile(r"event_type:\s*'([a-z0-9_]+)'")
EV_HELPER = re.compile(r"\baudit\(\s*'([a-z0-9_]+)'")
EV_TERNARY = re.compile(r"event_type:\s*[^,']*\?\s*'([a-z0-9_]+)'\s*:\s*'([a-z0-9_]+)'")
TBL_CONST = re.compile(r"AUDIT_TABLE\s*=\s*'(\w+)'")
TBL_LITERAL = re.compile(r"table:\s*'(\w+_audit_log)'")
DDL = re.compile(r'create table if not exists (?:public\.)?(\w*audit_log)\b')
CHK = re.compile(r'event_type[^,]*?check\s*\(\s*event_type\s+in\s*\(([^)]*)\)',
                 re.S | re.I)


def emitted_in(src):
    ev = set(EV_DIRECT.findall(src)) | set(EV_HELPER.findall(src))
    for a, b in EV_TERNARY.findall(src):
        ev.add(a)
        ev.add(b)
    return ev


def default_table(api_dir):
    """The table a writeAuditLog call with no `table:` argument lands in.

    RESOLVED, NOT REPORTED AS UNKNOWN, and the first version of this sweep got
    that wrong: it bucketed four files as "target could not be resolved" and left
    them out of the comparison. api/_lib/audit.js reads
    `const target = table || DEFAULT_AUDIT_TABLE`, so the answer was never
    unknown -- and resolving it took the finding from 2 tables to 3 and from 6
    rejected values to 12. A could-not-tell that is really a known answer hides
    exactly as much as a wrong one.
    """
    p = os.path.join(api_dir, '_lib', 'audit.js')
    if not os.path.isfile(p):
        return None, 'api/_lib/audit.js is absent'
    s = io.open(p, encoding='utf-8', errors='replace').read()
    m = re.search(r"DEFAULT_AUDIT_TABLE\s*=\s*'(\w+)'", s)
    if not m:
        return None, 'DEFAULT_AUDIT_TABLE not found in api/_lib/audit.js'
    return m.group(1), None


def scan(repo):
    """(tables, emits, problem). `problem` is the THIRD STATE and is not
    foldable into "no findings"."""
    sql_dir = os.path.join(repo, 'sql')
    api_dir = os.path.join(repo, 'api')
    for d in (sql_dir, api_dir):
        if not os.path.isdir(d):
            return None, None, '%s is not a directory' % d
    dflt, why = default_table(api_dir)
    if dflt is None:
        return None, None, why

    tables = {}
    for f in sorted(os.listdir(sql_dir)):
        if not f.endswith('.sql'):
            continue
        s = io.open(os.path.join(sql_dir, f), encoding='utf-8',
                    errors='replace').read()
        for m in DDL.finditer(s):
            tail = s[m.end():m.end() + 4000]
            cm = CHK.search(tail)
            tables[m.group(1)] = {
                'ddl': f,
                'allowed': sorted(set(re.findall(r"'([a-z0-9_]+)'", cm.group(1))))
                if cm else None,
            }
    if not tables:
        return None, None, ('no `create table ... audit_log` found anywhere in '
                            'sql/. Zero tables is not a clean verdict -- the '
                            'population this check compares against is empty.')

    emits = {}
    for root, _dirs, files in os.walk(api_dir):
        if 'node_modules' in root:
            continue
        for f in sorted(files):
            if not f.endswith('.js') or f.endswith('.test.js'):
                continue
            p = os.path.join(root, f)
            s = io.open(p, encoding='utf-8', errors='replace').read()
            if 'writeAuditLog' not in s:
                continue
            ev = emitted_in(s)
            if not ev:
                continue
            tgt = set(TBL_CONST.findall(s)) | set(TBL_LITERAL.findall(s))
            if not tgt:
                tgt = {dflt}
            rel = os.path.relpath(p, repo).replace('\\', '/')
            for t in tgt:
                emits.setdefault(t, {}).setdefault(rel, set()).update(ev)
    return tables, emits, None


def findings(tables, emits):
    out = []
    for t in sorted(tables):
        allowed = tables[t]['allowed']
        if allowed is None:
            continue
        files = emits.get(t, {})
        got = set()
        for v in files.values():
            got |= v
        rejected = sorted(got - set(allowed))
        if rejected:
            out.append({'table': t, 'rejected': rejected,
                        'emitted_by': sorted(files),
                        'allowed': allowed})
    return out


def _limits():
    print('LIMITS, on every run rather than in a document nobody opens:')
    print('  * BOTH HALVES ARE LEXICAL. An event_type built from a variable,')
    print('    and a target table reached through a helper, are invisible.')
    print('    The error direction is a MISS, not a false accusation.')
    print('  * A CLEAN ROW IS WEAKER EVIDENCE THAN A DIRTY ONE. Said out loud')
    print('    because a green bar invites the opposite assumption.')
    print('  * It does NOT replace a live round trip and does not claim to. It')
    print('    closes the case where the answer was knowable from two files')
    print('    already sitting in the repo.')
    print('  * A table with NO event_type CHECK cannot be violated and is')
    print('    listed separately, never counted as clean.')


def selftest():
    """Both directions, on fixtures, before the live tree is read.

    NEITHER ARM IS WORTH ANYTHING ALONE. An arm that only proved the dirty pair
    flags would pass on a function returning a finding for everything; an arm
    that only proved the clean pair passes would pass on one that returned
    nothing. That is the same both-ways discipline the sabotage controls use.
    """
    print('audit_event_type_check selftest -- criteria %s\n' % CRITERIA_VERSION)
    npass = nfail = 0

    def ck(label, cond, extra=''):
        nonlocal npass, nfail
        if cond:
            npass += 1
            print('  ok   ' + label)
        else:
            nfail += 1
            print('  FAIL ' + label)
            if extra:
                print('       ' + str(extra)[:300])

    DIRTY_SQL = """
    create table if not exists public.zz_fixture_audit_log (
      id uuid primary key,
      event_type text not null check (event_type in (
        'allowed_one',
        'allowed_two'
      )),
      detail jsonb
    );
    """
    DIRTY_JS = """
    const { writeAuditLog } = require('./_lib/audit');
    const AUDIT_TABLE = 'zz_fixture_audit_log';
    await writeAuditLog(U, K, { event_type: 'allowed_one', table: AUDIT_TABLE });
    await writeAuditLog(U, K, { event_type: 'not_in_the_check', table: AUDIT_TABLE });
    """
    CLEAN_JS = DIRTY_JS.replace("'not_in_the_check'", "'allowed_two'")

    tl = {'zz_fixture_audit_log': {
        'ddl': 'fixture.sql',
        'allowed': sorted(set(re.findall(r"'([a-z0-9_]+)'",
                                         CHK.search(DIRTY_SQL).group(1))))}}

    def run(js):
        return findings(tl, {'zz_fixture_audit_log': {'fixture.js': emitted_in(js)}})

    f = run(DIRTY_JS)
    ck('A1. a value OUTSIDE the CHECK list is FLAGGED, and the finding names it',
       len(f) == 1 and f[0]['rejected'] == ['not_in_the_check'], f)
    f2 = run(CLEAN_JS)
    ck('A2. ...and the SAME pair with every value inside the list is NOT '
       'flagged. WITHOUT THIS ARM a function returning a finding for '
       'everything would satisfy A1', not f2, f2)
    ck('B1. the ternary spelling is read -- `event_type: x ? \'a\' : \'b\'` '
       'yields BOTH values, because api/sc-auth.js writes its credential '
       'events that way and reading only one would miss half of them',
       emitted_in("event_type: next ? 'reactivated' : 'deactivated',")
       == {'reactivated', 'deactivated'})
    ck('B2. the helper spelling is read -- `audit(\'pin_setup\', ...)` -- '
       'because api/law-auth.js and api/sc-auth.js wrap writeAuditLog in a '
       'local `audit()` and a direct-only match sees nothing in either',
       'pin_setup' in emitted_in("await audit('pin_setup', { x: 1 });"))
    ck('C1. a table with NO event_type CHECK yields NO finding -- it cannot be '
       'violated, and treating absence as a violation would make sv_audit_log '
       'a permanent false positive',
       not findings({'zz_no_check': {'ddl': 'f.sql', 'allowed': None}},
                    {'zz_no_check': {'f.js': {'anything_at_all'}}}))
    ck('C2. ...and an emitted value with NO table resolved at all still lands '
       'somewhere rather than vanishing: emitted_in finds it, and scan() '
       'routes it to DEFAULT_AUDIT_TABLE',
       emitted_in("event_type: 'orphan_event'") == {'orphan_event'})
    print('\n%d passed, %d failed' % (npass, nfail))
    return 1 if nfail else 0


def main(argv):
    if '--selftest' in argv:
        return selftest()
    tables, emits, problem = scan(REPO)
    if problem:
        print('COULD NOT RUN: %s' % problem)
        print('This is NOT "every event type is allowed". Nothing was compared.')
        return 2
    fs = findings(tables, emits)
    checked = [t for t in tables if tables[t]['allowed'] is not None]
    nochk = [t for t in tables if tables[t]['allowed'] is None]
    if '--json' in argv:
        print(json.dumps({'criteria': CRITERIA_VERSION,
                          'tables_with_check': sorted(checked),
                          'tables_without_check': sorted(nochk),
                          'findings': fs}, indent=1))
        return 1 if fs else 0

    print('AUDIT event_type vs its CHECK CONSTRAINT -- criteria %s'
          % CRITERIA_VERSION)
    print('FILES READ (printed because a silent universe reports clean for a '
          'file it never opened):')
    print('    sql/*.sql                     -- %d audit-log table(s) found'
          % len(tables))
    print('    api/**/*.js                   -- %d file(s) calling writeAuditLog'
          % len({f for d in emits.values() for f in d}))
    print('  tables WITH an event_type CHECK : %d' % len(checked))
    print('  tables WITHOUT one              : %d  %s'
          % (len(nochk), ', '.join(sorted(nochk))))
    print('')
    if not fs:
        print('Every event_type emitted to a table with a CHECK constraint '
              'appears in that constraint.')
        print('')
        _limits()
        return 0
    for f in fs:
        print('! %s  %d value(s) its CHECK REJECTS:' % (f['table'], len(f['rejected'])))
        for v in f['rejected']:
            print('      %s' % v)
        print('    emitted by : %s' % ', '.join(f['emitted_by']))
        print('    CHECK allows: %s' % ', '.join(f['allowed']))
        print('')
    print('%d of %d table(s) with a CHECK reject at least one emitted value. '
          '%d distinct value(s) in total.'
          % (len(fs), len(checked), len({v for f in fs for v in f['rejected']})))
    print('EVERY ONE OF THESE IS A WRITE THAT FAILS AT THE DATABASE. '
          'writeAuditLog is non-fatal and returns false, so the calling code '
          'carries on and the row is simply absent.')
    print('')
    _limits()
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
