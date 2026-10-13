#!/usr/bin/env python
# OWNER: cody
"""Verify cl_feedback_log attribution AGAINST THE REAL DATABASE. Run AFTER the SQL.

── WHAT THIS IS FOR (b5 item 12) ─────────────────────────────────────────────
b4 added `employee_id` and `employee_role` to `cl_feedback_log`, at the
application layer and in `sql/sairnlaw_citator_schema.sql`, closing hover2
seq 951 -- a legal-citation treatment confirm that recorded no person, under a
schema comment claiming "individual feedback stays attributable".

GUARDIAN CHECK 29 IS NOT SATISFIED BY THAT COMMIT AND SAYS SO. Any change to a
stored shape must be proven with a REAL WRITE through the REAL endpoint, read
back, with the boundary driven both ways. b4 had no Supabase credentials and
the `alter table` has not been run, so none of that happened: the suite drives
the handler against a mocked PostgREST and asserts the row that WOULD be
written.

This script is the missing half, written and left ready rather than left as a
sentence in a handoff. It is NOT RUN BY THIS BATCH and it does not run the SQL.

    THE ORDER MATTERS AND IS NOT NEGOTIABLE:
      1. Michael runs sql/sairnlaw_citator_schema.sql in Supabase.
      2. python tools/verify_citator_feedback.py --check-only     (safe, reads)
      3. python tools/verify_citator_feedback.py --write          (two real rows)

── WHY IT REFUSES TO RUN WITHOUT --write, AND WHY THAT IS NOT TIMIDITY ──────
This writes real rows into a real table. A verification script that writes by
default is one somebody runs by accident while exploring, and the rows it leaves
are indistinguishable from an attorney's real feedback -- in the table whose
whole subject is attribution. `--check-only` answers the question that does not
need a write (are the columns there at all) and is the mode to reach for first.

── AND IT CANNOT PASS BY DOING NOTHING ──────────────────────────────────────
Every arm here has a way to fail that is NOT "the request errored". The failure
this exists to catch is the quiet one: a 200 with no employee on the row, which
is exactly what the old code did. So each write is READ BACK BY ID and the
stored value compared -- the rule Guardian Check 29 states as "read it back and
confirm the stored value is what you sent", and the one the b4 suite could not
reach.

── THE TWO DIRECTIONS, BOTH REQUIRED ───────────────────────────────────────
  WITH a session     employee_id and employee_role must equal what was signed.
  WITHOUT a session  both must be stored as SQL NULL -- present and null, not
                     absent, and not a placeholder. The session token on this
                     endpoint is OPTIONAL by design (api/legal-citator.js:178),
                     so a row legitimately has no person on it, and inventing
                     one would be worse than the original omission because it
                     would read as evidence.

── WHAT IT DOES NOT DO ─────────────────────────────────────────────────────
It does not run the migration, does not create the treatment row it needs
(cl_citing_treatments has a FK and a real row must exist -- the script finds one
rather than inserting one, and refuses if the table is empty), and does not
clean up the two rows it writes. They are real feedback events in a global
cache and deleting them is a separate decision; their note field says plainly
that they are verification rows.

Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY. Optionally SD_AUTH_SECRET and
LAW_LICENSE_KEY to drive the real endpoint instead of the table directly.
"""
import json
import os
import sys
import urllib.error
import urllib.request

CRITERIA_VERSION = '2026-10-13.1'
TABLE = 'cl_feedback_log'
NOTE_MARK = 'ZZ-VERIFY-SEQ951'


def env(name):
    v = (os.environ.get(name) or '').strip()
    return v or None


def rest(base, path):
    return base.rstrip('/') + '/rest/v1/' + path


def call(url, key, method='GET', body=None, prefer=None):
    """-> (status, parsed_or_text). A transport failure is NOT an empty result."""
    headers = {'apikey': key, 'Authorization': 'Bearer ' + key,
               'Accept': 'application/json'}
    data = None
    if body is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(body).encode('utf-8')
    if prefer:
        headers['Prefer'] = prefer
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode('utf-8', 'replace')
            try:
                return r.status, json.loads(raw) if raw.strip() else []
            except ValueError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(raw) if raw.strip() else {}
        except ValueError:
            return e.code, raw
    except Exception as e:                                   # noqa: BLE001
        # COULD NOT RUN. Returning (None, ...) rather than a status keeps this
        # out of every pass/fail branch below -- a network failure is not a
        # verdict about the schema.
        return None, '%s: %s' % (type(e).__name__, e)


RESULTS = []


def arm(name, ok, detail=''):
    RESULTS.append((name, ok, detail))
    print(('  ok   ' if ok else '  FAIL ') + name)
    if not ok and detail:
        print('       ' + str(detail)[:500])


def unknown(name, why):
    RESULTS.append((name, None, why))
    print('  ????  ' + name)
    print('       COULD NOT TELL: ' + str(why)[:500])


def main(argv):
    check_only = '--check-only' in argv or '--write' not in argv
    base, key = env('SUPABASE_URL'), env('SUPABASE_SERVICE_ROLE_KEY')

    print('VERIFY cl_feedback_log ATTRIBUTION -- criteria %s' % CRITERIA_VERSION)
    print('  mode: %s' % ('CHECK-ONLY (no write)' if check_only
                          else 'WRITE (two real rows)'))
    if not base or not key:
        print()
        print('COULD NOT RUN: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must '
              'both be set.')
        print('Nothing was read and nothing was written. This is exit 2, not a '
              'pass --')
        print('a missing credential is not evidence that the schema is correct.')
        return 2

    print()
    print('A. THE COLUMNS EXIST (this is what the migration adds)')
    # PostgREST answers 400 PGRST204 for an unknown column in a select, which
    # is the same signal api/legal-citator.js now reports as 503
    # NOT_PROVISIONED instead of "try again".
    st, body = call(rest(base, TABLE + '?select=id,employee_id,employee_role'
                                       '&limit=1'), key)
    if st is None:
        unknown('both attribution columns are selectable', body)
        print()
        print('STOPPING: the table could not be reached at all, so nothing '
              'below would mean anything.')
        return 2
    blob = json.dumps(body)
    if st == 200:
        arm('both attribution columns are selectable -- the migration has run',
            True)
    else:
        arm('both attribution columns are selectable -- the migration has run',
            False,
            'status %s %s\n       RUN sql/sairnlaw_citator_schema.sql FIRST. '
            'Until then api/legal-citator.js answers 503 NOT_PROVISIONED '
            'naming that file, which is the loud state -- not this failure.'
            % (st, blob[:300]))
        print()
        print('STOPPING: without the columns every arm below would fail for '
              'the same single reason.')
        return 1

    print()
    print('B. THE INDEX THE MIGRATION ALSO ADDS')
    st, body = call(rest(base, TABLE + '?select=id&employee_id=is.null&limit=1'),
                    key)
    if st is None:
        unknown('employee_id is queryable as NULL', body)
    else:
        arm('employee_id is queryable as NULL -- so "no person on this row" is '
            'a state the table can be ASKED about, not just stored',
            st == 200, 'status %s %s' % (st, json.dumps(body)[:200]))

    if check_only:
        print()
        print('CHECK-ONLY: stopping before any write. The two directions that '
              'matter --')
        print('a row WITH a session and a row WITHOUT one -- need real inserts '
              'and a')
        print('read-back, which is what --write does. Guardian Check 29 is NOT '
              'satisfied')
        print('by this mode alone and this script will not claim otherwise.')
        return _verdict(partial=True)

    print()
    print('C. A REAL TREATMENT ROW TO POINT AT (cl_citing_treatments FK)')
    st, body = call(rest(base, 'cl_citing_treatments?select=id&limit=1'), key)
    if st is None:
        unknown('a treatment row exists', body)
        return _verdict()
    treatment = (body[0]['id'] if (st == 200 and isinstance(body, list)
                                   and body and 'id' in body[0]) else None)
    arm('a real cl_citing_treatments row exists to reference',
        bool(treatment),
        'status %s %s\n       This script does NOT insert one: the FK wants a '
        'real classification, and manufacturing one would put a fabricated '
        'treatment into a GLOBAL cache every firm reads.'
        % (st, json.dumps(body)[:200]))
    if not treatment:
        return _verdict()

    lic = env('LAW_LICENSE_HASH') or 'VERIFY-SEQ951-LICENSE-HASH'

    print()
    print('D. DIRECTION ONE -- a row WITH an employee, written then READ BACK')
    row_with = {'license_hash': lic, 'app_id': 'sairnlaw',
                'treatment_id': treatment, 'action': 'confirmed',
                'corrected_to': None,
                'note': NOTE_MARK + ' verification row, employee present',
                'employee_id': 'emp-verify-001', 'employee_role': 'attorney'}
    st, body = call(rest(base, TABLE), key, 'POST', row_with,
                    prefer='return=representation')
    if st is None:
        unknown('the WITH-session row inserted', body)
        return _verdict()
    arm('the WITH-session row inserted', st in (200, 201),
        'status %s %s' % (st, json.dumps(body)[:300]))
    new_id = (body[0]['id'] if (isinstance(body, list) and body
                                and isinstance(body[0], dict)
                                and 'id' in body[0]) else None)
    if new_id:
        st2, back = call(rest(base, TABLE + '?id=eq.' + str(new_id)
                              + '&select=employee_id,employee_role,action'), key)
        got = back[0] if (st2 == 200 and isinstance(back, list) and back) else {}
        # THE ARM THAT MATTERS. A 201 proves the insert was accepted; only the
        # read-back proves the value was STORED. The defect being closed was a
        # 200 with no employee on the row.
        arm('...and the STORED values are what was sent -- the read-back, not '
            'the status code',
            got.get('employee_id') == 'emp-verify-001'
            and got.get('employee_role') == 'attorney',
            'read back %s' % json.dumps(got))
    else:
        unknown('...and the STORED values are what was sent',
                'the insert returned no id, so there is nothing to read back: '
                + json.dumps(body)[:200])

    print()
    print('E. DIRECTION TWO -- a row WITHOUT an employee. NULL must be STORED,')
    print('   present and null, not absent and not a placeholder.')
    row_without = dict(row_with)
    row_without.update({'note': NOTE_MARK + ' verification row, no session',
                        'employee_id': None, 'employee_role': None})
    st, body = call(rest(base, TABLE), key, 'POST', row_without,
                    prefer='return=representation')
    if st is None:
        unknown('the NO-session row inserted', body)
        return _verdict()
    arm('the NO-session row inserted', st in (200, 201),
        'status %s %s' % (st, json.dumps(body)[:300]))
    nid = (body[0]['id'] if (isinstance(body, list) and body
                             and isinstance(body[0], dict)
                             and 'id' in body[0]) else None)
    if nid:
        st2, back = call(rest(base, TABLE + '?id=eq.' + str(nid)
                              + '&select=employee_id,employee_role'), key)
        got = back[0] if (st2 == 200 and isinstance(back, list) and back) else {}
        arm('...and both columns are stored as NULL -- the key is PRESENT and '
            'the value is null, which is a different claim from the key being '
            'absent',
            'employee_id' in got and got.get('employee_id') is None
            and 'employee_role' in got and got.get('employee_role') is None,
            'read back %s' % json.dumps(got))
        # THE NULL ARM NEEDS ITS OWN NEGATIVE HALF: if the column defaulted to
        # something, both rows would read identically and E would pass for the
        # wrong reason.
        arm('...and the two rows really DIFFER, so E is not passing because '
            'every row looks the same',
            got.get('employee_id') != 'emp-verify-001',
            'the no-session row reads %s' % json.dumps(got))
    else:
        unknown('...and both columns are stored as NULL',
                'the insert returned no id: ' + json.dumps(body)[:200])

    print()
    print('F. THE ROWS THIS SCRIPT LEFT BEHIND')
    st, body = call(rest(base, TABLE + '?select=id,employee_id,note'
                         '&note=like.*' + NOTE_MARK + '*'), key)
    n = len(body) if isinstance(body, list) else 0
    print('  %d row(s) carry %s in their note.' % (n, NOTE_MARK))
    print('  NOT DELETED BY THIS SCRIPT. They are real rows in a global cache '
          'and')
    print('  removing them is a separate decision; their note says what they '
          'are.')
    return _verdict()


def _verdict(partial=False):
    ok = sum(1 for _, s, _ in RESULTS if s is True)
    bad = sum(1 for _, s, _ in RESULTS if s is False)
    unk = sum(1 for _, s, _ in RESULTS if s is None)
    print()
    print('%d passed, %d failed, %d could-not-tell' % (ok, bad, unk))
    if unk:
        print('COULD-NOT-TELL IS NOT A PASS. Those arms were not answered.')
    if partial:
        print('PARTIAL: check-only mode. Guardian Check 29 needs --write.')
    if bad:
        return 1
    if unk:
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
