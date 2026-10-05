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
    registry against itself would prove nothing about the migration.

    ── THE `public.` PREFIX WAS REQUIRED AND 28 TABLES WERE INVISIBLE ────────
    (2026-10-05.) The pattern was `create table if not exists public\\.(\\w+)`
    and 25 files in `sql/` write the unqualified form -- `create table if not
    exists sd_employee_auth (`. Measured over the whole directory: **442 tables
    with the prefix required, 470 with it optional, so 28 were never read.**
    Almost all are the `*_employee_auth` and `*_audit_log` families, which is
    the worst possible set to be blind to: they are the tables an app's sign-in
    depends on.

    HOW IT WAS FOUND, because it says something about the failure mode. Not by
    review and not by a test -- by following ONE register cell.
    `supplier_lead_times` is recorded as not provisioned, and when that was
    re-driven today the table was not in the Gate-1 missing list OR in the
    sweep at all. Pulling that thread found an app-prefix glob reading 113
    schema files of 147, and pulling it again found this.

    AND THE SILENT HALF IS WORSE THAN THE COUNT. A file whose every table is
    unqualified returned an EMPTY LIST, and the caller then reported
    `schema declares : 0`, `PROVISIONED : 0`, `MISSING : 0` and exited **0**.
    `sql/stonedesk_audit_log_schema.sql` did exactly that in the 2026-10-05
    sweep -- one declared table, read as none, reported clean. "Nothing to
    check" and "everything checked out" printed the same, which is why
    `main()` now refuses a schema file that declares nothing (PR 1.11).

    AND COMMENTS ARE STRIPPED, BECAUSE MAKING THE PREFIX OPTIONAL MADE THEM
    REACHABLE -- same change, caught by its own new arm. With `public.`
    required a comment had to name a qualified table to produce a false hit,
    which no file did. Optional, the phrase alone is enough: the probe's prose
    fixture -- a comment reading "see create table if not exists in the other
    file" -- yielded the table name `in`. A widening that reaches into comments
    is the defect this platform records most often (PR 1.2: grep cannot tell
    code from text that describes code), so the widening and the stripper land
    together rather than one at a time.
    """
    src = open(schema, encoding='utf-8', errors='replace').read()
    # Line comments only, which is what SQL files here use for prose. Block
    # comments are not stripped and no file in sql/ uses one around a CREATE.
    code = '\n'.join(l for l in src.split('\n')
                     if not l.lstrip().startswith('--'))
    return sorted(set(re.findall(
        r'create\s+table\s+if\s+not\s+exists\s+(?:public\.)?(\w+)', code,
        re.I)))


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


# ── SIGNING IN, BECAUSE A LICENCE KEY ANSWERS 37% OF THE QUESTION ──────────
# (2026-10-05.) Driven over every app with a demo key on 2026-10-05: 402
# declared tables across 113 (app, schema) pairs, 148 confirmed PROVISIONED,
# 2 confirmed MISSING -- and **216 REFUSED**, every one of them because the
# resource is behind the employee session gate and this check presented a
# licence key and nothing else. Per app: sairnvet 42, sairnlegacy 36,
# sairnroofing 25, sairndental 24, sairnlaw 19, sairnfreedom 17, sairnsenior 15,
# sairncare 14, sairnbiz 13, sairndesign 10, stonedesk 5, sairnmechanical 3,
# sairnscape 2, sairnbuild 1.
#
# So Gate 1 -- the one gate in docs/MASTER-PLAN.md with a live dependency --
# was UNANSWERABLE for more than half of what it covers, and the file already
# said what to do about it: "Re-run with a session."
#
# THE AUTH ENDPOINT IS NOT DERIVED FROM THE APP NAME, deliberately, and this
# file's own header gives the reason for the schema argument and it applies
# twice over here: `sairncare` signs in at `/api/alf-auth`, `sairnfreedom` at
# `/api/sf-auth`, `sairndesign` at `/api/sdn-auth`. There is no rule. A guess
# would sign in to the WRONG APP and -- since f27a9cd5 -- get a 403
# LICENSE_WRONG_APP that reads like a gate result. Passed explicitly or not at
# all.
#
# A FAILED SIGN-IN IS EXIT 2 AND NEVER A SILENT FALLBACK to the unauthenticated
# run. Falling back would answer a DIFFERENT question under the flag that asked
# not to -- the same rule control_char_check's --rev follows.
# ── GIT BASH REWRITES AN ARGUMENT THAT LOOKS LIKE A UNIX PATH ──────────────
# `--auth /api/scp-auth` arrives as `C:/Program Files/Git/api/scp-auth`. MSYS
# path conversion, and it is not optional on this platform: CLAUDE.md names Git
# Bash as the shell. The first live run of this flag died on
# `InvalidURL: URL can't contain control characters` naming a Program Files
# path, which is a confusing way to learn that the shell edited your argument.
#
# So the ENDPOINT NAME is the accepted form -- `--auth scp-auth` -- and a
# leading-slash path is still taken when it survives. A value that has clearly
# been rewritten is REFUSED BY NAME rather than sent: a mangled endpoint would
# otherwise produce a sign-in failure that reads like a dead credential.
def normalise_auth(raw):
    """('api/<name>', None) or (None, why it cannot be used)."""
    v = (raw or '').strip().replace('\\', '/')
    if not v:
        return None, 'empty'
    if re.match(r'^[A-Za-z]:/', v) or 'Program Files' in v:
        tail = v.rsplit('/', 1)[-1]
        return None, ('the shell rewrote this argument into a Windows path '
                      '(%r). Git Bash converts an argument beginning with `/` '
                      'into a filesystem path. Pass it WITHOUT the leading '
                      'slash: --auth %s' % (v, tail))
    v = v.lstrip('/')
    if v.startswith('api/'):
        v = v[4:]
    if '/' in v:
        return None, ('%r is not an endpoint name. Pass the name alone, e.g. '
                      '--auth scp-auth' % raw)
    return 'api/' + v, None


def sign_in(auth_path, key, employee, pin):
    """(token, None) or (None, why). Never raises, never falls back."""
    url = URL.rsplit('/api/', 1)[0] + '/' + auth_path
    body = json.dumps({'action': 'login', 'employee_id': employee,
                       'pin': pin}).encode('utf-8')
    try:
        r = sairn_http.fetch(url, method='POST', data=body, headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + key})
        status, raw = r.status, r.body
    except sairn_http.Challenged as e:
        return None, 'the sign-in was CHALLENGED by Vercel (%s)' % e
    except Exception as e:                                      # noqa: BLE001
        status = getattr(e, 'code', None)
        try:
            raw = e.read()
        except Exception:                                       # noqa: BLE001
            return None, '%s: %s' % (type(e).__name__, e)
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', 'replace')
    try:
        d = json.loads(raw)
    except Exception:                                           # noqa: BLE001
        return None, 'sign-in returned unreadable body: %s' % raw[:160]
    tok = d.get('token') if isinstance(d, dict) else None
    if status == 200 and tok:
        return tok, None
    return None, 'sign-in returned %s %s' % (status, json.dumps(d)[:200])


def probe(resource, key, app, token=None):
    body = json.dumps({'action': 'read', 'resource': resource,
                       'app_id': app, 'payload': {}}).encode('utf-8')
    hdrs = {'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + key}
    if token:
        hdrs['X-SD-Auth'] = token
    try:
        r = sairn_http.fetch(URL, method='POST', data=body, headers=hdrs)
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

    # ── THE SESSION, IF ONE WAS ASKED FOR ──────────────────────────────────
    pin = opt(argv, '--pin') or os.environ.get('SAIRN_DEMO_PIN')
    employee = opt(argv, '--employee') or 'sairn-demo-owner'
    auth_path = opt(argv, '--auth')
    token = None
    if auth_path:
        auth_path, why = normalise_auth(auth_path)
        if auth_path is None:
            sys.stderr.write('--auth cannot be used: %s\nExit 3.\n' % why)
            return 3
    if pin and not auth_path:
        sys.stderr.write(
            '--pin needs --auth <name>, and the name is NOT derived from the\n'
            'app name because there is no rule: sairncare signs in at\n'
            '/api/alf-auth, sairnfreedom at /api/sf-auth, sairndesign at\n'
            '/api/sdn-auth. A guess would sign in to the WRONG APP and get a\n'
            '403 LICENSE_WRONG_APP that reads like a gate result.\n'
            'The endpoints are listed in docs/2026-09-03-demo-credentials.md.\n')
        return 3
    if auth_path and not pin:
        sys.stderr.write('--auth needs --pin (or SAIRN_DEMO_PIN).\n')
        return 3
    if pin:
        token, why = sign_in(auth_path, key, employee, pin)
        if token is None:
            # EXIT 2, NOT A FALLBACK. An unauthenticated run would answer a
            # different question under the flag that asked for a session, and
            # its REFUSED list would look exactly like today's.
            sys.stderr.write(
                'COULD NOT SIGN IN, so the session-gated resources CANNOT be\n'
                'checked and this run is NOT falling back to an\n'
                'unauthenticated one -- that would answer a different question\n'
                'and its REFUSED list would be indistinguishable from a real\n'
                'result.\n\n  %s\n  employee: %s   endpoint: %s\n'
                'Exit 2, not a pass.\n' % (why, employee, auth_path))
            return 2

    tables = declared_tables(schema)
    # ── A SCHEMA FILE THAT DECLARES NOTHING IS NOT A CLEAN ONE (PR 1.11) ───
    # This fell straight through: zero declared meant zero checkable, zero
    # provisioned, zero missing and exit 0, printed in the same shape as a
    # fully-migrated app. `sql/stonedesk_audit_log_schema.sql` was reported as
    # `schema declares : 0 ... MISSING : 0`, exit 0, on 2026-10-05, while
    # declaring one table the prefix-requiring regex above could not see.
    #
    # EITHER CAUSE IS A REFUSAL, and the message names both rather than
    # guessing: the file may genuinely create no table (a grant-only or
    # query-only file, of which sql/ has 13), or it may create one in a shape
    # this reader cannot parse. The caller must not be told "clean" for either.
    if not tables:
        sys.stderr.write(
            'COULD NOT RUN: %s declares NO table this reader can see, so\n'
            'nothing below would be checked -- and zero tables checked is not\n'
            'zero tables missing.\n\n'
            'Two causes and this tool cannot tell them apart:\n'
            '  (a) the file genuinely creates no table -- a grant-only, '
            'policy-only or\n      query-only file. 13 files in sql/ are like '
            'that.\n'
            '  (b) it creates one in a shape this reader cannot parse. The '
            'prefix was\n      REQUIRED until 2026-10-05 and 28 tables in 25 '
            'files were invisible for it.\n\n'
            'Exit 2, not a pass.\n' % os.path.relpath(schema, REPO)
            .replace(os.sep, '/'))
        return 2
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
        results[t] = probe(asked, key, app, token)
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
        # THE SESSION IS DISCLOSED ON EVERY RUN, present or absent. A reader
        # comparing two runs of this tool has to be able to tell which question
        # each one answered: the unauthenticated run's REFUSED list and the
        # signed-in run's are the same shape and mean different things.
        print('  session         : %s'
              % ('SIGNED IN as %s at %s' % (employee, auth_path) if token
                 else 'NONE -- licence key only, so every session-gated '
                      'resource below is UNANSWERABLE rather than broken'))
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
