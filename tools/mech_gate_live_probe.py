"""LIVE verification of the SAIRNmechanical MECH_RECORDS gate boundary, with the
residue it creates RECORDED AND PRINTED rather than discovered afterwards.

    python tools/mech_gate_live_probe.py                  # audit licence, default
    python tools/mech_gate_live_probe.py --key MECH-AUDIT-2026
    python tools/mech_gate_live_probe.py --selftest       # no network

── WHY THIS EXISTS AS A TOOL AND NOT AS A SCRATCHPAD SCRIPT ────────────────
On 2026-09-29 the mech_docs write gate was verified live by an ad-hoc script in a
temp directory. It worked -- 403 on the keyless write, 200 on the read and on the
three sibling writes -- and it left TWO ROWS on MECH-PINNACLE-2026, a
DEMO-FACING licence, on tables whose `service_role` has no DELETE grant. They
needed Michael in the SQL editor.

THE GUARD THAT WOULD HAVE STOPPED IT ALREADY EXISTED AND WAS NOT IMPORTED.
`tools/audit_licence.py:require_audit_licence` refuses a non-audit key outright,
and MECH-AUDIT-2026 is in its known list. An uncommitted script imports nothing
and is invisible to `tools/live_probe_residue_audit.py`, whose universe is tracked
files under tools/ tests/ scripts/ -- so the one mechanism that enforces the rule
could not see the one run that broke it.

**THE FIX IS THE FILE'S EXISTENCE, not a new rule.** Being here, tracked, with a
declared class and the audit guard called on the path that writes, is what makes
the existing auditor able to judge it.

── WHAT THIS ADDS ON TOP OF THE FOUR STANDING OBLIGATIONS ──────────────────
`tools/live_probe_residue_audit.py` already requires a declared class, an audit
licence, a named residue and a run that fails when residue remains. It checks that
a residue path is NAMED. It cannot check that the rows are ENUMERATED, because
nothing enumerated them.

So every write this probe performs goes through `_write()`, which RECORDS the
(table, id column, id value) it created before it reports success, and `finish()`:

  (a) writes a DATED residue record to docs/live-residue/<date>-<tool>.json
      listing every row by table and id, and
  (b) PRINTS the select / delete / confirm SQL block for those exact rows, with
      the licence hash DERIVED in SQL rather than pasted.

THE RECORDER'S CLAIM IS CHECKED AGAINST AN INDEPENDENT COUNT. `finish()` takes
the number of writes the ENDPOINT observed and refuses -- exit 2 COULD NOT RUN --
when the recorder saw fewer. A recorder that counts only its own calls cannot
detect a write that bypassed it, which is the whole failure being closed.
`tests/run_mech_gate_live_probe_probe.py` drives exactly that against a mock.
"""
import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_licence                                           # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESIDUE_DIR = os.path.join(REPO, 'docs', 'live-residue')
URL = 'https://sairn.vercel.app/api/sd-data'
APP = 'sairnmechanical'

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

LIVE_PROBE_CLASS = 'VERIFICATION'
LIVE_PROBE_RESIDUE = ('one row per sibling table written (mech_checks, '
                      'mech_takeoffs), id ZZ-MECH-GATE-<run>, on the audit '
                      'licence only; enumerated by table and id in '
                      'docs/live-residue/<date>-mech_gate_live_probe.json and '
                      'removable with the SQL this tool prints at the end of '
                      'every run')

# The id column each MECH_RECORDS table actually uses. NOT entry_id -- the rest of
# this platform's blob tables use entry_id and these four do not, which is the
# defect that made a pushed removal script name a column that does not exist.
# Taken from sql/sairnmechanical_records_schema.sql's unique constraints.
ID_COL = {'mech_quotes': 'quote_id', 'mech_checks': 'check_id',
          'mech_docs': 'doc_id', 'mech_takeoffs': 'takeoff_id'}


class Residue(object):
    """Every row this run created, by table and id, plus the SQL that removes it."""

    def __init__(self, tool, key):
        self.tool = tool
        self.key = key
        self.rows = []

    def created(self, table, id_value):
        col = ID_COL.get(table)
        if not col:
            raise KeyError('no id column known for %r -- refusing to record a row '
                           'whose removal SQL would name the wrong column' % table)
        self.rows.append({'table': table, 'id_column': col, 'id': id_value})

    def record_path(self, today):
        return os.path.join(RESIDUE_DIR, '%s-%s.json' % (today, self.tool))

    def write_record(self, today):
        if not os.path.isdir(RESIDUE_DIR):
            os.makedirs(RESIDUE_DIR)
        p = self.record_path(today)
        io.open(p, 'w', encoding='utf-8', newline='\n').write(json.dumps({
            '_what': 'Rows created on a live licence by %s. Written by the tool '
                     'itself at the end of its run, so the rows are enumerated '
                     'rather than discovered later. The SQL that removes them is '
                     'printed by the same run and reproduced below.' % self.tool,
            'tool': self.tool,
            'licence_key': self.key,
            'date': today,
            'rows': self.rows,
            'removal_sql': self.sql(),
        }, indent=2, sort_keys=True) + '\n')
        return p

    def sql(self):
        """select / delete / confirm, hash DERIVED, one statement per element."""
        if not self.rows:
            return ['-- No rows were created by this run, so there is nothing to '
                    'remove. This is not the same as "the run did not write" -- '
                    'see the observed-write cross-check in finish().']
        h = ("encode(digest('%s', 'sha256'), 'hex')" % self.key)
        out = ['create extension if not exists pgcrypto;',
               "select %s as derived_license_hash;" % h]
        for r in self.rows:
            out.append(
                "select '%(t)s' as tbl, %(c)s as row_key, license_hash, created_at\n"
                "  from public.%(t)s\n where license_hash = %(h)s\n   and %(c)s = '%(i)s';"
                % {'t': r['table'], 'c': r['id_column'], 'i': r['id'], 'h': h})
        for r in self.rows:
            out.append(
                "delete from public.%(t)s\n where license_hash = %(h)s\n"
                "   and %(c)s = '%(i)s';"
                % {'t': r['table'], 'c': r['id_column'], 'i': r['id'], 'h': h})
        for r in self.rows:
            out.append(
                "select '%(t)s' as tbl, count(*) as remaining\n  from public.%(t)s\n"
                " where license_hash = %(h)s\n   and %(c)s = '%(i)s';"
                % {'t': r['table'], 'c': r['id_column'], 'i': r['id'], 'h': h})
        return out

    def finish(self, today, observed_writes):
        """Write the record, print the SQL, and REFUSE on an unrecorded write.

        `observed_writes` comes from whatever actually issued the requests, not
        from this object. A recorder that counts its own calls cannot detect a
        write that went around it, and that is the entire failure being closed.
        """
        print('')
        print('RESIDUE THIS RUN CREATED: %d row(s)' % len(self.rows))
        for r in self.rows:
            print('  %-16s %s = %s' % (r['table'], r['id_column'], r['id']))
        if observed_writes is not None and observed_writes > len(self.rows):
            sys.stderr.write(
                'COULD NOT RUN -- %d write(s) reached the endpoint and only %d '
                'were RECORDED.\n'
                'A write that bypassed the recorder leaves a row nothing will '
                'ever name, which is exactly the 2026-09-29 residue. The removal '
                'SQL below would be INCOMPLETE, so it is not trusted and this run '
                'reports COULD NOT RUN rather than printing it as if it covered '
                'everything.\n' % (observed_writes, len(self.rows)))
            return EXIT_COULD_NOT_RUN
        p = self.write_record(today)
        print('  recorded in %s' % os.path.relpath(p, REPO))
        print('')
        print('REMOVAL SQL -- run the selects first and read the counts. '
              'This tool runs no delete.')
        for stmt in self.sql():
            print('')
            print(stmt)
        return EXIT_CLEAN


def selftest():
    """No network. Drives the recorder and its refusal."""
    bad = []

    def ck(name, cond):
        print(('  ok   ' if cond else '  FAIL ') + name)
        if not cond:
            bad.append(name)

    r = Residue('selftest', 'MECH-AUDIT-2026')
    r.created('mech_checks', 'ZZ-MECH-GATE-T')
    ck('a recorded row carries the table\'s REAL id column (check_id, not entry_id)',
       r.rows[0]['id_column'] == 'check_id')
    try:
        r.created('not_a_mech_table', 'X')
        ck('an unknown table is REFUSED rather than recorded with a guessed column',
           False)
    except KeyError:
        ck('an unknown table is REFUSED rather than recorded with a guessed column',
           True)
    sql = '\n'.join(r.sql())
    ck('the SQL DERIVES the hash rather than pasting one',
       "digest('MECH-AUDIT-2026', 'sha256')" in sql)
    ck('...and names check_id, never entry_id', 'check_id' in sql
       and 'entry_id' not in sql)
    ck('the SQL has a select, a delete and a confirm',
       sql.count('select') >= 3 and sql.count('delete from') == 1)
    print('')
    return EXIT_FINDING if bad else EXIT_CLEAN


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--key', default='MECH-AUDIT-2026')
    ap.add_argument('--today', default=None,
                    help='date stamp for the residue record; defaults to UTC today')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)

    if args.selftest:
        print('mech_gate_live_probe --selftest (no network)\n')
        return selftest()

    # THE GUARD, ON THE PATH THAT WRITES, BEFORE ANY REQUEST IS MADE. This is the
    # line whose absence produced the 2026-09-29 residue.
    key = audit_licence.require_audit_licence(
        args.key, tool=__file__,
        writes='mech_checks and mech_takeoffs (the two sibling tables whose '
               'licence-only writes this probe asserts are UNCHANGED)')

    import datetime
    today = args.today or datetime.datetime.utcnow().strftime('%Y-%m-%d')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sairn_http

    res = Residue('mech_gate_live_probe', key)
    observed = {'writes': 0}
    run_id = today.replace('-', '')

    def call(action, resource, payload=None, token=None):
        body = {'action': action, 'resource': resource, 'app_id': APP}
        if payload is not None:
            body['payload'] = payload
        headers = {}
        if token:
            headers['x-sd-auth'] = token
        r = sairn_http.fetch_json(URL, payload=body, key=key, headers=headers)
        # OBSERVED INDEPENDENTLY OF THE RECORDER: counted here, at the request,
        # for every write that came back 200 -- whether or not anybody recorded it.
        if action == 'write' and r.status == 200:
            observed['writes'] += 1
        return r

    def write_sibling(resource):
        rid = 'ZZ-MECH-GATE-%s' % run_id
        r = call('write', resource, {'id': rid, 'text': 'gate boundary check'})
        if r.status == 200:
            res.created(resource, rid)
        return r

    bad = []

    def ck(name, cond, detail=''):
        print(('  ok   ' if cond else '  FAIL ') + name
              + ('' if cond else '\n         ' + str(detail)[:200]))
        if not cond:
            bad.append(name)

    print('MECH_RECORDS gate boundary, driven live on %s\n' % key)

    r = call('write', 'mech_docs', {'id': 'ZZ-MECH-GATE-%s' % run_id,
                                    'text': 'gate boundary check'})
    ck('mech_docs WRITE on the licence key alone is REFUSED',
       r.status in (401, 403), 'HTTP %s %s' % (r.status, r.body))

    r = call('read', 'mech_docs')
    ck('mech_docs READ still answers on the licence key alone -- the finding was '
       'the WRITE and the scope is held here, not just in the diff',
       r.status == 200, 'HTTP %s' % r.status)

    for sib in ('mech_checks', 'mech_takeoffs'):
        r = write_sibling(sib)
        ck('%s WRITE still answers on the licence key alone -- its own open-work '
           'row, not this one' % sib, r.status == 200, 'HTTP %s' % r.status)

    rc = res.finish(today, observed['writes'])
    if rc != EXIT_CLEAN:
        return rc
    return EXIT_FINDING if bad else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
