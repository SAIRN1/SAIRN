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


CONTROLLED_BY = ['tests/run_schema_provisioning_probe.py']


def registered_from_source(src):
    """The resource names a registry module EXPORTS, or None if it declares none.

    ── NONE AND EMPTY ARE DIFFERENT AND THE DIFFERENCE WAS THE DEFECT ────────
    The first version searched for the literal `resources: [` and returned an
    EMPTY SET when it found nothing. api/_resources/sairncode.js declares
    `const RESOURCES = [...]` and exports it as
    `module.exports = { resources: RESOURCES }`, so that spelling never matched
    -- and the tool printed "registered: 0 checkable" followed by
    "NOT REGISTERED: 15 (no code can ask for them)" FOR AN APP WITH TWENTY-EIGHT
    REGISTERED RESOURCES. The two halves contradicted each other, neither was
    flagged, and the 15-table finding was DERIVED FROM THE EMPTY READ.

    So: None means COULD NOT READ and the caller must refuse. An empty set means
    the registry really admits nothing, which is a different fact.
    """
    src = '\n'.join(l for l in src.split('\n') if not l.strip().startswith('//'))
    # Either spelling: `resources: [ ... ]`, or `NAME = [ ... ]` exported as
    # `resources: NAME`.
    m = re.search(r'resources\s*:\s*\[', src)
    if not m:
        ex = re.search(r'resources\s*:\s*([A-Z_][A-Z0-9_]*)', src)
        if ex:
            m = re.search(r'\b%s\s*=\s*\[' % re.escape(ex.group(1)), src)
    if not m:
        return None
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


def registered(app):
    """registered_from_source for one app, or None when the file is unreadable."""
    p = os.path.join(REPO, 'api', '_resources', app + '.js')
    try:
        src = open(p, encoding='utf-8', errors='replace').read()
    except OSError:
        return None
    return registered_from_source(src)


# ── A TABLE NAME IS NOT A RESOURCE NAME, AND SEVEN LIVE TABLES PAID FOR IT ───
# SAIRNgrounds and SAIRNscape map one to the other ON PURPOSE: resource
# `properties` reaches table `grd_properties`, `customers` reaches
# `scp_customers`, and five more. The handler builds the PostgREST path from the
# prefixed name while the registry admits the bare one. Comparing the two sets
# directly reported every one of those tables as something "no code can ask
# for", while code asks for them on every page load.
#
# The prefix is taken from the table itself rather than from a per-app list: a
# leading `<letters>_` is stripped and the remainder tried. That is narrow
# enough to keep an orphan table orphaned -- `zz_orphan_table` does not resolve
# against a registry of `properties` -- which is the half that keeps the finding
# able to fire at all.
_PREFIX = re.compile(r'^[a-z]{2,6}_')


def resolves(table, reg):
    """Is `table` reachable through some resource name in `reg`?"""
    if not reg:
        return False
    if table in reg:
        return True
    bare = _PREFIX.sub('', table, count=1)
    return bare != table and bare in reg


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
    code = err.get('code') or ''
    msg = err.get('message') or ''
    # SAY WHICH KIND OF REFUSAL (2026-09-30). `403 FORBIDDEN` alone cannot be
    # acted on: it reads the same whether the resource is deliberately behind an
    # employee sign-in or the licence has lost its access. Diagnosed 2026-09-30
    # for scp_invoices and scp_quotes -- both are in SD_SESSION_GATED at
    # api/sd-data.js:817, so an unauthenticated run CANNOT complete the check for
    # them and the honest report says so rather than implying something is broken.
    why = code or msg
    if status == 403 and ('sign in' in msg.lower() or 'session' in msg.lower()):
        why = ('%s -- SESSION-GATED, not broken. This resource requires an '
               'employee sign-in; an unauthenticated run cannot check it. Re-run '
               'with a session.' % (code or 'FORBIDDEN'))
    return 'REFUSED', '%s %s' % (status, why)


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
    # AN UNREADABLE REGISTRY IS COULD NOT RUN, NEVER ZERO. Deriving a
    # NOT-REGISTERED finding from a read that returned nothing is the
    # zero-item-corpus failure, and this tool shipped it.
    if reg is None:
        sys.stderr.write(
            'COULD NOT READ the resource registry for %r. api/_resources/%s.js\n'
            'exists but no resource list could be parsed out of it, so NOTHING\n'
            'below could be judged -- and a NOT-REGISTERED finding derived from\n'
            'an empty read is exactly the defect this tool looks for. Exit 2.\n'
            % (app, app))
        return 2
    # A table the schema creates but the registry does not name can never be
    # reached through the endpoint, so a live probe cannot see it either. That
    # is a finding about the REPO, reported separately from the migration.
    unreachable = [t for t in tables if not resolves(t, reg)]
    checkable = [t for t in tables if resolves(t, reg)]

    results = {}
    asked_as = {}
    for t in checkable:
        # ASK FOR THE RESOURCE, NOT THE TABLE. `grd_properties` is not a
        # resource the dispatch has ever seen; `properties` is.
        asked = t if t in reg else _PREFIX.sub('', t, count=1)
        results[t] = probe(asked, key, app)
        # RECORD WHAT WAS ACTUALLY ASKED FOR when it differs from the table.
        # A verdict about `scp_invoices` that came from asking for `invoices`
        # cannot be reconciled with the endpoint's own answer unless the report
        # says so -- and a reader chasing a 403 on scp_invoices will look for a
        # branch that does not exist under that name.
        if asked != t:
            asked_as[t] = asked

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
                if t in asked_as:
                    print('        (asked for the RESOURCE %r, not the table name)'
                          % asked_as[t])
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
