"""Is every table a schema file declares ACTUALLY there, in the live database?

WHY THIS EXISTS. A 35-table migration is 35 chances for one statement to fail
while the other 34 succeed, and nothing about that is loud. api/sd-data.js
answers a read against a missing table with `{ok:true, data:[], provisioned:
false}` -- deliberately, so an un-migrated table is distinguishable from an
empty one -- but the CLIENT treats provisioned:false as "nothing to hydrate"
and carries on. So a partially-run migration looks, from inside the app, exactly
like a practice that has not entered any data yet: no error, no warning, and
every write to the missing table answering 503 into a console nobody is reading.

READ-ONLY, ON PURPOSE, AND THE FILE SAYS SO RATHER THAN THE COMMIT MESSAGE.
Every request here is action:'read'. Nothing is written, so this cannot leave a
row behind in a licence it has no way to clean up -- api/sd-data.js has no
delete path outside the sc_* family, and sf_* declares no soft_delete. Proving
the WRITE path end to end needs a row that would then be permanent, which is a
decision for whoever owns the licence, not a side effect of a check.

WHAT A PASS HERE DOES AND DOES NOT MEAN:
  DOES  -- the table exists, the resource is registered, the handler branch is
           reached, and the licence resolves.
  DOES NOT -- that a write succeeds, that the id column matches what the client
           sends, or that a row comes back. Those need a real write.
           tools/write_without_readback_check.py and the app's own probe cover
           the code side; the live side is stated as unverified rather than
           implied.

WRITTEN FOR SAIRNfreedom AND GENERALISED IN THE SAME PASS, because the
question is not SAIRNfreedom's. Every app on this platform is one hand-run
migration away from the same partial state, and three schema files were waiting
to be run on the night this was written.

Usage:
    python tools/schema_provisioning_check.py --app sairnfreedom \
        --schema sql/sairnfreedom_data_schema.sql --key SF-PINNACLE-2026
    python tools/schema_provisioning_check.py --app sairnvet \
        --schema sql/sairnvet_data_schema.sql --key SV-PINNACLE-2026 --json

THE APP AND THE SCHEMA ARE BOTH REQUIRED AND NEITHER IS GUESSED. Schema
filenames do not follow one rule (sairnvet_data_schema.sql,
sairndental_vendor_schema.sql, sairnlaw_data_extended_schema.sql), and deriving
one from the app name would silently check the wrong file -- or nothing.

Exits 1 if any declared table is missing, 2 if the licence or the endpoint
could not be reached at all -- which is NOT a pass and says so.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sairn_http  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'https://sairn.vercel.app/api/sd-data'


def declared_tables(schema):
    """Table names the SCHEMA FILE creates -- the source of truth for what the
    migration was supposed to produce. Read from the file rather than from the
    registry, deliberately: the registry says what the app is allowed to ask
    for, and the schema says what the database was told to build. Checking the
    registry against itself would prove nothing about the migration."""
    src = open(schema, encoding='utf-8', errors='replace').read()
    return sorted(set(re.findall(r'create table if not exists public\.(\w+)', src)))


def registered(app):
    src = open(os.path.join(REPO, 'api', '_resources', app + '.js'),
               encoding='utf-8', errors='replace').read()
    src = '\n'.join(l for l in src.split('\n') if not l.strip().startswith('//'))
    m = re.search(r'resources\s*:\s*\[', src)
    if not m:
        return set()
    i = src.index('[', m.start())
    depth = 0
    for j in range(i, len(src)):
        if src[j] == '[':
            depth += 1
        elif src[j] == ']':
            depth -= 1
            if depth == 0:
                break
    return set(re.findall(r"'([\w.-]+)'", src[i:j + 1]))


def probe(resource, key, app):
    body = json.dumps({'action': 'read', 'resource': resource,
                       'app_id': app, 'payload': {}}).encode('utf-8')
    try:
        r = sairn_http.fetch(URL, method='POST', data=body, headers={
            'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
        status, raw = r.status, r.body
    except sairn_http.Challenged as e:
        return 'CHALLENGED', str(e)
    except Exception as e:
        status = getattr(e, 'code', None)
        try:
            raw = e.read()
        except Exception:
            raw = str(e).encode()
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', 'replace')
    try:
        d = json.loads(raw)
    except Exception:
        return 'UNREADABLE', raw[:120]
    if status == 200 and d.get('ok'):
        return ('PROVISIONED' if d.get('provisioned') else 'MISSING'), ''
    err = (d.get('error') or {})
    return 'REFUSED', '%s %s' % (status, err.get('code') or err.get('message') or '')


def opt(argv, name):
    if name not in argv:
        return None
    i = argv.index(name)
    if i + 1 >= len(argv):
        sys.stderr.write('%s needs a value\n' % name)
        raise SystemExit(3)
    return argv[i + 1]


def main(argv):
    app = opt(argv, '--app')
    schema = opt(argv, '--schema')
    key = opt(argv, '--key') or os.environ.get('SAIRN_LICENSE_KEY')
    if not app or not schema:
        sys.stderr.write('--app and --schema are both required, and neither is\n'
                         'guessed from the other -- schema filenames do not follow\n'
                         'one rule, so a guess would check the wrong file.\n')
        return 3
    if not os.path.isabs(schema):
        schema = os.path.join(REPO, schema)
    if not os.path.isfile(schema):
        sys.stderr.write('No such schema file: %s\n' % schema)
        return 3
    if not os.path.isfile(os.path.join(REPO, 'api', '_resources', app + '.js')):
        sys.stderr.write('No registry for app %r -- an unregistered app cannot be\n'
                         'checked, and that absence is itself a finding.\n' % app)
        return 3
    if not key:
        sys.stderr.write('No licence key. Pass --key or set SAIRN_LICENSE_KEY.\n'
                         'WITHOUT ONE NOTHING IS CHECKED -- this is not a pass.\n')
        return 2

    tables = declared_tables(schema)
    reg = registered(app)
    # A table the schema creates but the registry does not name can never be
    # reached through the endpoint, so a live probe cannot see it either. That
    # is a finding about the REPO, reported separately from the migration.
    unreachable = [t for t in tables if t not in reg]
    checkable = [t for t in tables if t in reg]

    results = {}
    for t in checkable:
        results[t] = probe(t, key, app)

    missing = sorted(t for t, (s, _) in results.items() if s == 'MISSING')
    refused = sorted(t for t, (s, _) in results.items() if s in ('REFUSED', 'UNREADABLE'))
    blocked = sorted(t for t, (s, _) in results.items() if s == 'CHALLENGED')
    ok = sorted(t for t, (s, _) in results.items() if s == 'PROVISIONED')

    if '--json' in argv:
        print(json.dumps({'declared': tables, 'unreachable': unreachable,
                          'provisioned': ok, 'missing': missing,
                          'refused': refused, 'challenged': blocked}, indent=1))
    else:
        print('%s live provisioning -- READ ONLY, nothing was written' % app)
        print('  schema          : %s' % os.path.relpath(schema, REPO).replace(os.sep, '/'))
        print('  schema declares : %d table(s)' % len(tables))
        print('  registered      : %d checkable' % len(checkable))
        print('  PROVISIONED     : %d' % len(ok))
        print('  MISSING         : %d' % len(missing))
        for t in missing:
            print('      %s -- the table does not exist; every write to it answers 503' % t)
        if unreachable:
            print('  NOT REGISTERED  : %d (the schema builds these and no code can ask for them)'
                  % len(unreachable))
            for t in unreachable:
                print('      %s' % t)
        if refused:
            print('  REFUSED         : %d -- NOT a pass, the check did not run for these' % len(refused))
            for t in refused:
                print('      %-28s %s' % (t, results[t][1]))
        if blocked:
            print('  CHALLENGED      : %d -- bot mitigation, UNVERIFIED not verified-good' % len(blocked))
        if not missing and not refused and not blocked and not unreachable:
            print('\nAll %d declared tables exist. Reads only -- a WRITE has still never been'
                  ' exercised against this licence, and that is stated rather than implied.' % len(ok))

    if blocked or refused:
        return 2
    return 1 if (missing or unreachable) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
