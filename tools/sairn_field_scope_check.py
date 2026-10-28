#!/usr/bin/env python3
# OWNER: cc
"""Hold every endpoint's DECLARED field/row scope to what each role really gets back.

    python tools/sairn_field_scope_check.py               # coverage + every rule, working tree
    python tools/sairn_field_scope_check.py --ref <sha>   # the same, on the tree AT <sha>
    python tools/sairn_field_scope_check.py --sweep       # + an exposure matrix of every
                                                          #   role-scoped read nobody declared
    python tools/sairn_field_scope_check.py --live [--env-file F]   # every rule's live block, deployed
    python tools/sairn_field_scope_check.py --replay --handler-ref <sha> [--only <rule>]
                                                          # the SAME live path against the handler
                                                          #   at <sha>, served on 127.0.0.1
    python tools/sairn_field_scope_check.py --validate    # the registry's schema, nothing driven
    python tools/sairn_field_scope_check.py --fixtures    # the blind lock

THE CLASS (four confirmed instances by 2026-10-28, every one caught by an
auditor after it shipped): a field, role or tenant scope that was meant to
redact or refuse instead returns in full to an unprivileged caller --
sdn_pos's SDN_RESOURCES on the licence key alone; 16 Tier A sairncode
resources writable from the licence key alone; alf_mar's same id under a
different facility; sen_caregivers' name/phone/CPR/ids to every role after the
HR redaction (H1 #965). Each had a unit suite somewhere. None had a check that
asked every role, against the design, what it actually receives.

HOW. tools/field_scope_rules.json declares, per rule and per role, which seeded
fields that role MUST receive. Every other seeded field is a unique MARKER
string that must be absent from the whole serialised body, so the comparison
is closed-world and does not depend on the response's shape. The REAL handler
is driven by tools/field_scope_driver.js with a session token signed by the
real api/_lib/auth -- only the licence lookup and the database are stood in.

WHAT FAILS (exit 1):
  LEAK      a role received a marker its declaration does not allow
  MISSING   a role did not receive a marker it must -- an over-redaction, and
            the control that stops a handler returning nothing from passing
  FLAG      a declared response flag (hr_fields_visible ...) is wrong
  REFUSE    a role declared refused got a 2xx or any marker
  COVERAGE  a read branch in api/sd-data.js declares a field redaction or a
            scope flag and has NO rule here; a rule's anchor is not exactly
            once in the source; a rule omits or invents one of the app's roles
COULD NOT RUN (exit 2, and the push gate DENIES on it): node missing, the
driver crashed, a role's arm answered non-2xx where it must be served (the arm
never reached the scope code), the registry is unreadable, or --ref could not
be exported. "Could not run" is never folded into a pass (PR 1.11).

WHY PRE-PUSH IS HANDLER-LEVEL AND --live IS SEPARATE. A pre-push gate runs
before the deploy, so a live request there reads the PREVIOUS code: it would
refuse the push that fixes a leak and pass the push that adds one. The gate
therefore drives the code being pushed. --live reads the deployed endpoint per
role on an audit licence, read-only, and judges it with the SAME marker judge:
the licence holds the rule's own fixture rows, written from seed() (b63). It is
the post-push verification. Without role PINs in the environment it is COULD
NOT RUN, never a pass. --replay points that unchanged live path at a known-bad
handler, because a live check never seen to fail has proved nothing.

WHAT THIS CANNOT SEE: dispatch shapes other than `resource === 'x' && action
=== 'y'` in api/sd-data.js; writes (a refused write is a different check);
tenant scope across licences (the mock pins one licence_hash); any read whose
rule is not declared -- --sweep lists those rather than passing them.
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXIT_OK, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2
BRANCH_RE = re.compile(r"resource === '([a-z0-9_]+)' && action === '([a-z0-9_]+)'")
READ_ACTIONS = ('read', 'list', 'get')
LIVE_BASE = os.environ.get('SAIRN_LIVE_BASE', 'https://sairn.vercel.app')
AUDIT_KEY_RE = re.compile(r'^[A-Z]{2,6}-AUDIT-\d{4}$')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


class CouldNotRun(Exception):
    pass


# ── THE REGISTRY ───────────────────────────────────────────────────────────
def marker(rule_id, tag, field):
    return 'FSMK%sQ' % hashlib.sha1(('%s|%s|%s' % (rule_id, tag, field)).encode()).hexdigest()[:12]


def seed(rule):
    """(tables for the driver, {tag.field: marker})"""
    tables, markers = {}, {}
    for table, rows in rule['tables'].items():
        out = []
        for row in rows:
            tag, built = row['tag'], {}
            for k, v in row.items():
                if k == 'tag':
                    continue
                if k == 'data':
                    built['data'] = {f: _cell(rule, tag, f, fv, markers) for f, fv in v.items()}
                else:
                    built[k] = _cell(rule, tag, k, v, markers)
            out.append(built)
        tables[table] = out
    return tables, markers


def _cell(rule, tag, field, v, markers):
    """null -> a generated marker; {"marker": "<literal>"} -> that literal IS the
    marker (for a typed column, e.g. a timestamptz that cannot hold FSMK...);
    anything else is a literal and is not accounted."""
    if v is None:
        m = marker(rule['id'], tag, field)
    elif isinstance(v, dict) and set(v) == {'marker'}:
        m = str(v['marker'])
    else:
        return v
    if m in markers.values():
        raise CouldNotRun('rule %s: marker %r is used twice, so its presence cannot say which '
                          'field it came from' % (rule['id'], m))
    markers['%s.%s' % (tag, field)] = m
    return m


def substitute(tables, mapping):
    """The seeded tables with literal employee ids swapped for the live ones."""
    def sub(v):
        return mapping.get(v, v) if isinstance(v, str) else v
    return {t: [{k: ({f: sub(x) for f, x in v.items()} if k == 'data' else sub(v))
                 for k, v in row.items()} for row in rows] for t, rows in tables.items()}


RULE_KEYS = {'id', 'app', 'anchor', 'request', 'declared_from', 'caller', 'tables', 'sets', 'roles', 'live'}
SPEC_KEYS = {'see', 'refused', 'flags'}
LIVE_KEYS = {'licence_env', 'auth_path', 'creds', 'employees'}


def validate(rules):
    """Every way a declaration can be malformed, named by rule and key, before
    anything is driven. A typo'd key would otherwise be IGNORED: a "see_fields"
    the judge never reads is a role that is checked against nothing."""
    bad, ids = [], set()
    for n, r in enumerate(rules):
        start = len(bad)
        if not isinstance(r, dict):
            bad.append('rule #%d: is not an object' % n)
            continue
        where = 'rule %s' % (r.get('id') or '#%d' % n)
        for k in sorted(set(r) - RULE_KEYS):
            bad.append('%s: unknown key %r (allowed: %s)' % (where, k, ', '.join(sorted(RULE_KEYS))))
        for k in ('id', 'app', 'anchor', 'request', 'declared_from', 'tables', 'roles'):
            if k not in r:
                bad.append('%s: missing required key %r' % (where, k))
        if r.get('id') in ids:
            bad.append('%s: duplicate id' % where)
        ids.add(r.get('id'))
        req = r.get('request')
        if req is not None and not (isinstance(req, dict) and isinstance(req.get('resource'), str)
                                    and isinstance(req.get('action'), str)):
            bad.append('%s: request must be an object with string resource and action' % where)
        tags = set()
        tables = r.get('tables')
        if tables is not None and not isinstance(tables, dict):
            bad.append('%s: tables must be an object of table -> [rows]' % where)
            tables = {}
        for t, rows in (tables or {}).items():
            if not isinstance(rows, list) or not rows:
                bad.append('%s: table %r must be a non-empty list of rows' % (where, t))
                continue
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get('tag'), str):
                    bad.append('%s: every row in %r needs a string "tag"' % (where, t))
                    continue
                if row['tag'] in tags:
                    bad.append('%s: tag %r is used twice' % (where, row['tag']))
                tags.add(row['tag'])
                if 'data' in row and not isinstance(row['data'], dict):
                    bad.append('%s: %s.data must be an object' % (where, row['tag']))
        for sname, sv in (r.get('sets') or {}).items():
            if not isinstance(sv, list) or not all(isinstance(x, str) for x in sv):
                bad.append('%s: set %r must be a list of field names' % (where, sname))
        for role, spec in (r.get('roles') or {}).items():
            if not isinstance(spec, dict):
                bad.append('%s [%s]: spec must be an object' % (where, role))
                continue
            for k in sorted(set(spec) - SPEC_KEYS):
                bad.append('%s [%s]: unknown key %r (allowed: see, refused, flags)' % (where, role, k))
            if ('see' in spec) == bool(spec.get('refused')):
                bad.append('%s [%s]: needs exactly one of "see" (a list) or "refused": true' % (where, role))
            for item in spec.get('see') or []:
                tag, dot, field = str(item).partition('.')
                if not dot or tag not in tags or not field:
                    bad.append('%s [%s]: see entry %r is not <tag>.<field|*|@SET> for a declared tag'
                               % (where, role, item))
                elif field.startswith('@') and field[1:] not in (r.get('sets') or {}):
                    bad.append('%s [%s]: %r names an undeclared set' % (where, role, item))
            if 'flags' in spec and not isinstance(spec['flags'], dict):
                bad.append('%s [%s]: flags must be an object' % (where, role))
        live = r.get('live')
        if live is not None:
            for k in sorted(set(live) - LIVE_KEYS):
                bad.append('%s live: unknown key %r' % (where, k))
            for k in ('licence_env', 'auth_path', 'creds'):
                if k not in live:
                    bad.append('%s live: missing %r' % (where, k))
            for role, pair in (live.get('creds') or {}).items():
                if role not in (r.get('roles') or {}):
                    bad.append('%s live: creds for %r, which the rule does not declare' % (where, role))
                if not (isinstance(pair, list) and len(pair) == 2):
                    bad.append('%s live: creds[%r] must be [EMP_ENV, PIN_ENV]' % (where, role))
        if len(bad) > start:
            continue
        try:
            _t, mk = seed(r)
            for role, spec in r['roles'].items():
                if isinstance(spec.get('see'), list):
                    expand(r, spec['see'], mk)
        except CouldNotRun as e:
            bad.append(str(e))
        except Exception as e:                                  # noqa: BLE001
            bad.append('%s: could not be seeded (%s: %s)' % (where, type(e).__name__, e))
    return bad


def expand(rule, see, markers):
    want = set()
    for item in see:
        tag, _, field = item.partition('.')
        if field == '*':
            got = [k for k in markers if k.startswith(tag + '.')]
        elif field.startswith('@'):
            got = ['%s.%s' % (tag, f) for f in rule.get('sets', {}).get(field[1:], [None])]
        else:
            got = [item]
        for g in got:
            if g not in markers:
                raise CouldNotRun('rule %s: %r names %s, which is not a seeded marker'
                                  % (rule['id'], item, g))
            want.add(g)
    return want


# ── THE TREE BEING CHECKED ─────────────────────────────────────────────────
def export_ref(ref, paths=('api', 'tools/field_scope_rules.json')):
    d = tempfile.mkdtemp(prefix='field_scope_ref_')
    a = subprocess.run(['git', '-C', REPO, 'archive', '--format=tar', ref] + list(paths), capture_output=True)
    if a.returncode != 0:
        shutil.rmtree(d, ignore_errors=True)
        raise CouldNotRun('git archive %s failed: %s' % (ref, a.stderr.decode('utf-8', 'replace')[:300]))
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(a.stdout)) as t:
        t.extractall(d)
    return d


def node_json(script, stdin=None, timeout=600, env=None):
    if not shutil.which('node'):
        raise CouldNotRun('node is not on PATH, so no handler was driven')
    r = subprocess.run(['node'] + script, input=stdin, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=timeout,
                       env=dict(os.environ, **(env or {})))
    if r.returncode != 0:
        raise CouldNotRun('node %s exited %d: %s' % (script[0][:60], r.returncode, (r.stderr or r.stdout)[-500:]))
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise CouldNotRun('node %s printed no JSON: %s' % (script[0][:60], r.stdout[-300:]))


def app_roles(root):
    auth = os.path.join(root, 'api', '_lib', 'auth.js').replace('\\', '/')
    return node_json(['-e', 'process.stdout.write(JSON.stringify(require(%r).ROLES_BY_APP))' % auth])


def drive(root, cases, env=None):
    handler = os.path.join(root, 'api', 'sd-data.js')
    out = node_json([os.path.join(REPO, 'tools', 'field_scope_driver.js')],
                    stdin=json.dumps({'handler': handler, 'cases': cases}), env=env)
    if len(out.get('results', [])) != len(cases):
        raise CouldNotRun('driver returned %d results for %d cases'
                          % (len(out.get('results', [])), len(cases)))
    return out['results']


# ── COVERAGE: every declared redaction in the source has a rule ────────────
def discover(src):
    lines = src.split('\n')
    starts = [(i, m.group(1), m.group(2)) for i, l in enumerate(lines)
              for m in [BRANCH_RE.search(l)] if m and re.match(r'\s*(\}\s*else\s*)?if \(', l)]
    found = []
    for k, (i, res, act) in enumerate(starts):
        if act not in READ_ACTIONS:
            continue
        j = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        body = '\n'.join(lines[i:j])
        sig = []
        if re.search(r'session\.role|\[session\.role\]', body):
            sig.append('role')
        if re.search(r'\b[a-z_]+_(visible|scope)\s*:|\btiered\s*:', body):
            sig.append('flag')
        if re.search(r'delete out\[|_FIELDS\b', body):
            sig.append('fields')
        if sig:
            app = re.search(r"verifySessionToken\([^;]*?'([a-z]+)'\)", body)
            found.append({'resource': res, 'action': act, 'line': i + 1, 'signals': sig,
                          'app': app.group(1) if app else None, 'body': body})
    return found


def coverage(rules, src, roles_by_app):
    bad = []
    declared = {(r['request']['resource'], r['request']['action']) for r in rules}
    for b in discover(src):
        if ('flag' in b['signals'] or 'fields' in b['signals']) and \
                (b['resource'], b['action']) not in declared:
            bad.append('COVERAGE %s/%s (api/sd-data.js:%d) declares a field redaction or scope '
                       'flag and has no rule in tools/field_scope_rules.json, so nothing checks '
                       'what each role gets' % (b['resource'], b['action'], b['line']))
    for r in rules:
        n = src.count(r['anchor'])
        if n != 1:
            bad.append('COVERAGE rule %s: its anchor occurs %d times in api/sd-data.js, not once '
                       '-- the rule no longer points at one branch' % (r['id'], n))
        have, want = set(r['roles']), set(roles_by_app.get(r['app']) or [])
        if not want:
            bad.append('COVERAGE rule %s: app %r has no roles in ROLES_BY_APP' % (r['id'], r['app']))
        if want - have:
            bad.append('COVERAGE rule %s: role(s) %s exist in api/_lib/auth.js and are NOT declared '
                       '-- an undeclared role is an unchecked one' % (r['id'], sorted(want - have)))
        if have - want:
            bad.append('COVERAGE rule %s: declares role(s) %s the app does not have'
                       % (r['id'], sorted(have - want)))
    return bad


# ── ONE RULE, EVERY ROLE ───────────────────────────────────────────────────
def judge(rule, role, spec, result, markers):
    """-> (findings, could_not_run)"""
    if 'error' in result:
        return [], ['%s [%s]: the driver threw: %s' % (rule['id'], role, result['error'][:300])]
    status, body = result.get('status'), result.get('body')
    blob = json.dumps(body, ensure_ascii=False)
    present = {k for k, v in markers.items() if v in blob}
    if spec.get('refused'):
        if status in (401, 403) and not present:
            return [], []
        return ['REFUSE %s [%s]: declared refused, got %s with %d marker(s) %s'
                % (rule['id'], role, status, len(present), sorted(present)[:6])], []
    if status is None or not (200 <= int(status) < 300):
        return [], ['%s [%s]: answered %s %s -- the arm never reached the scope code, so it '
                    'proves nothing' % (rule['id'], role, status, blob[:200])]
    want = expand(rule, spec.get('see', []), markers)
    out = []
    leak, miss = sorted(present - want), sorted(want - present)
    if leak:
        out.append('LEAK %s [%s]: received %s, which its declaration does not allow'
                   % (rule['id'], role, leak))
    if miss:
        out.append('MISSING %s [%s]: did not receive %s, which it must -- an over-redaction, '
                   'or a handler returning nothing' % (rule['id'], role, miss))
    for k, v in (spec.get('flags') or {}).items():
        got = body.get(k) if isinstance(body, dict) else None
        if got != v:
            out.append('FLAG %s [%s]: %s is %r, declared %r' % (rule['id'], role, k, got, v))
    return out, []


def check_rules(root, rules, env=None):
    cases, index = [], []
    for r in rules:
        tables, markers = seed(r)
        for role, spec in sorted(r['roles'].items()):
            cases.append({'app': r['app'], 'role': role, 'employee_id': r.get('caller', 'emp-self'),
                          'body': r['request'], 'tables': tables})
            index.append((r, role, spec, markers))
    results = drive(root, cases, env=env)
    findings, cnr, ok = [], [], 0
    for (r, role, spec, markers), res in zip(index, results):
        f, c = judge(r, role, spec, res, markers)
        findings += f
        cnr += c
        ok += not f and not c
    return findings, cnr, ok, len(cases)


# ── THE SWEEP: every role-scoped read nobody declared, as an exposure matrix ─
OWNER_COL_RE = re.compile(r'employee_id|assigned|_by$|owner|user_id|staff_id')


def classify(matrix, nroles):
    """An exposure matrix {role: (status, own_markers, peer_markers)} -> (verdict, why)."""
    served = {ro: v for ro, v in matrix.items() if v[0] == 200}
    if not served:
        verdict, why = 'COULD NOT TELL', 'no role was served 200 (the read likely needs a payload)'
    elif not any(v[1] + v[2] for v in served.values()):
        verdict, why = 'COULD NOT TELL', 'served, but no seeded marker came back (unmodelled filter)'
    elif len(served) == nroles and len(set(v[1:] for v in served.values())) == 1 \
            and list(served.values())[0][2] > 0:
        # Identical AND peer rows included. Identical with no peer rows is
        # every role scoped to its own record, which is a scope (measured:
        # employee_profile/read, whose role only gates `all: true`).
        verdict, why = 'SUSPECT', ('the branch consults session.role, yet EVERY role receives '
                                   'the same rows and fields, peer rows included')
    elif len(set(v[1:] for v in served.values())) == 1:
        verdict, why = 'OWN-ROW ONLY', 'every served role gets its own row and no peer row'
    else:
        verdict, why = 'DIFFERENTIATED', 'roles receive different exposure; not checked against a design'
    return verdict, why


def sweep(root, src, rules, roles_by_app):
    declared = {(r['request']['resource'], r['request']['action']) for r in rules}
    rows_out = []
    for b in discover(src):
        if 'role' not in b['signals'] or (b['resource'], b['action']) in declared:
            continue
        app = b['app']
        roles = roles_by_app.get(app or '') or []
        m = re.search(r"rest\('([a-z0-9_]+)\?([^\n]*)", b['body'])
        sel = re.search(r'select=([a-z0-9_,*]+)', m.group(2)) if m else None
        if not app or not roles or not m:
            rows_out.append((b, 'COULD NOT TELL', 'no app, roles or first table read found', {}))
            continue
        table, cols = m.group(1), (sel.group(1).split(',') if sel else ['data'])
        rule = {'id': 'sweep:%s.%s' % (b['resource'], b['action']), 'tables': {table: []}}
        for tag, emp in (('self', 'emp-self'), ('peer', 'emp-peer')):
            row = {'tag': tag}
            for c in cols:
                if c in ('license_hash', 'app_id', '*'):
                    continue
                if c == 'data':
                    row['data'] = {'probe_a': None, 'probe_b': None, 'employee_id': emp,
                                   'assigned_employee_id': emp}
                elif OWNER_COL_RE.search(c):
                    row[c] = emp
                else:
                    row[c] = None
            rule['tables'][table].append(row)
        tables, markers = seed(rule)
        cases = [{'app': app, 'role': ro, 'employee_id': 'emp-self',
                  'body': {'action': b['action'], 'resource': b['resource']}, 'tables': tables}
                 for ro in roles]
        res = drive(root, cases)
        matrix = {}
        for ro, rr in zip(roles, res):
            if 'error' in rr:
                matrix[ro] = ('ERR', 0, 0)
                continue
            blob = json.dumps(rr.get('body'))
            selfn = sum(1 for k, v in markers.items() if k.startswith('self.') and v in blob)
            peern = sum(1 for k, v in markers.items() if k.startswith('peer.') and v in blob)
            matrix[ro] = (rr.get('status'), selfn, peern)
        verdict, why = classify(matrix, len(roles))
        rows_out.append((b, verdict, why, matrix))
    return rows_out


# ── LIVE: the deployed endpoint, per role, read-only, on an audit licence ───
def check_live(rules):
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    import sairn_http as H
    import urllib.error
    findings, cnr, ok = [], [], 0

    def post(url, body, key, token=None):
        h = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key}
        if token:
            h['X-SD-Auth'] = token
        try:
            r = H.fetch(url, method='POST', data=json.dumps(body).encode(), headers=H.with_browser_ua(h))
            return r.status, json.loads(r.body.decode('utf-8', 'replace'))
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode('utf-8', 'replace'))
            except ValueError:
                return e.code, {}
        except Exception as e:                                  # noqa: BLE001
            return None, {'_transport': '%s: %s' % (type(e).__name__, e)}

    for r in rules:
        live = r.get('live')
        if not live:
            cnr.append('%s: no live block declared, so the deployed endpoint was not read' % r['id'])
            continue
        key = os.environ.get(live['licence_env'], '')
        if not AUDIT_KEY_RE.match(key):
            cnr.append('%s: %s is %s -- live reads run on an *-AUDIT-* licence only'
                       % (r['id'], live['licence_env'], 'unset' if not key else 'not an audit key'))
            continue
        _t, markers = seed(r)
        # THE SAME JUDGE AS THE HANDLER MODE (cc b63). The audit licence holds
        # the rule's own fixture rows with the rule's own marker values
        # (sql/field_scope_live_fixtures_*.sql writes them FROM this file), so a
        # deployed response is diffed exactly the way a driven one is: closed
        # world, by marker, shape-independent. The b62 version compared item KEYS
        # and could not read a nested shape like sen_settings' {setting_key,
        # value}; this one can, and a leak is the same LEAK line in both modes.
        selfemp = (live.get('employees') or {}).get(r.get('caller', 'emp-self'))
        for role, (emp_env, pin_env) in sorted(live['creds'].items()):
            emp, pin = os.environ.get(emp_env, ''), os.environ.get(pin_env, '')
            if not emp or not pin:
                cnr.append('%s [%s]: %s / %s not set -- this arm DID NOT RUN' % (r['id'], role, emp_env, pin_env))
                continue
            spec = r['roles'][role]
            want = expand(r, spec.get('see', []), markers)
            own_rows = {k.split('.', 1)[0] for k in want}
            if own_rows == {'self'} and selfemp and emp != selfemp:
                # A self-only role signed in as somebody else would read "no row
                # of mine" as a pass. Refuse rather than judge the wrong person.
                cnr.append('%s [%s]: signed in as %s but the fixtures\' self row belongs to %s'
                           % (r['id'], role, emp, selfemp))
                continue
            st, body = post(LIVE_BASE + live['auth_path'], {'action': 'login', 'employee_id': emp, 'pin': pin}, key)
            tok = isinstance(body, dict) and body.get('token')
            if st != 200 or not tok:
                cnr.append('%s [%s]: login answered %s -- no session, not a scope result' % (r['id'], role, st))
                continue
            st, body = post(LIVE_BASE + '/api/sd-data', r['request'], key, tok)
            f, c = judge(r, role, spec, {'status': st, 'body': body}, markers)
            findings += ['LIVE ' + x for x in f]
            cnr += c
            if not f and not c:
                ok += 1
                blob = json.dumps(body, ensure_ascii=False)
                print('  ok   %s [%s]: received %d of %d markers, exactly its declaration'
                      % (r['id'], role, sum(1 for v in markers.values() if v in blob), len(markers)))
    return findings, cnr, ok


# ── REPLAY: the live path against a KNOWN-BAD handler (cc b63) ─────────────
# A live check that has only ever been pointed at a clean deployment has never
# been seen to fail. --replay runs check_live() unchanged -- same HTTP calls,
# same login, same judge -- against tools/field_scope_driver.js --serve, which
# serves the handler AT <ref> over 127.0.0.1 with the rule's own fixtures. Point
# it at the commit before a fix and it must report the leak that fix closed.
def replay(root, rules):
    import socket
    global LIVE_BASE
    findings, cnr, ok = [], [], 0
    for r in rules:
        live = r.get('live')
        if not live:
            cnr.append('%s: no live block, nothing to replay' % r['id'])
            continue
        emps = live.get('employees') or {}
        selfemp = emps.get(r.get('caller', 'emp-self'), 'replay-self')
        tables, markers = seed(r)
        creds, env = {}, {live['licence_env']: 'RP-AUDIT-0000'}
        for role, (emp_env, pin_env) in live['creds'].items():
            want = expand(r, r['roles'][role].get('see', []), markers)
            emp = selfemp if {k.split('.', 1)[0] for k in want} == {'self'} else 'replay-' + role
            if emp in creds:
                emp = 'replay-' + role
            creds[emp] = {'pin': '12345678', 'role': role}
            env[emp_env], env[pin_env] = emp, '12345678'
        s = socket.socket()
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
        s.close()
        cfg = os.path.join(tempfile.mkdtemp(prefix='field_scope_replay_'), 'cfg.json')
        io.open(cfg, 'w', encoding='utf-8').write(json.dumps({
            'handler': os.path.join(root, 'api', 'sd-data.js'), 'port': port, 'app': r['app'],
            'tables': substitute(tables, emps), 'creds': creds}))
        p = subprocess.Popen(['node', os.path.join(REPO, 'tools', 'field_scope_driver.js'), '--serve', cfg],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            line = p.stdout.readline()
            if not line.startswith('LISTENING'):
                cnr.append('%s: the replay server did not start: %s' % (r['id'], (p.stderr.read() or line)[:300]))
                continue
            saved_env = {k: os.environ.get(k) for k in env}
            os.environ.update(env)
            LIVE_BASE, base = 'http://127.0.0.1:%d' % port, LIVE_BASE
            try:
                f, c, k = check_live([r])
            finally:
                LIVE_BASE = base
                for k2, v2 in saved_env.items():
                    if v2 is None:
                        os.environ.pop(k2, None)
                    else:
                        os.environ[k2] = v2
            findings += f
            cnr += c
            ok += k
        finally:
            p.kill()
            p.wait()
    return findings, cnr, ok


# ── THE BLIND LOCK ─────────────────────────────────────────────────────────
FAKE_HANDLER = r"""
const auth = require(%(auth)s);
module.exports = async function (req, res) {
  const s = auth.verifySessionToken(req.headers['x-sd-auth'], 'field-scope-hash', 'sairnsenior');
  if (!s) { res.status(401).json({ error: 'no session' }); return; }
  const mode = process.env.FSC_FAKE_MODE || 'clean';
  if (mode === 'crash') { res.status(500).json({ error: 'boom' }); return; }
  const r = await fetch('https://x.supabase.co/rest/v1/fx_t?license_hash=eq.field-scope-hash&select=row_id,data');
  const rows = await r.json();
  const mgmt = s.role === 'owner' || s.role === 'billing';
  let data = rows.map((x) => Object.assign({ id: x.row_id }, x.data));
  if (!mgmt && mode !== 'leak') data = data.map((o) => { delete o.secret; return o; });
  if (!mgmt && mode !== 'peer') data = data.filter((o) => o.owner === s.employee_id);
  if (mode === 'empty' && !mgmt) data = [];
  res.status(200).json({ ok: true, data, secret_visible: mode === 'flag' ? true : mgmt });
};
"""

FAKE_RULE = {
    'id': 'fixture.read', 'app': 'sairnsenior', 'anchor': 'FIXTURE-ANCHOR',
    'declared_from': 'the blind lock itself',
    'request': {'action': 'read', 'resource': 'fx_t'}, 'caller': 'emp-self',
    'tables': {'fx_t': [
        {'tag': 'self', 'row_id': None, 'data': {'name': None, 'secret': None, 'owner': 'emp-self'}},
        {'tag': 'peer', 'row_id': None, 'data': {'name': None, 'secret': None, 'owner': 'emp-peer'}}]},
    'roles': dict([(r, {'see': ['self.*', 'peer.*'], 'flags': {'secret_visible': True}})
                   for r in ('owner', 'billing')] +
                  [(r, {'see': ['self.row_id', 'self.name'], 'flags': {'secret_visible': False}})
                   for r in ('scheduler', 'coordinator', 'caregiver')])}


def fixtures():
    bad = []

    def arm(label, cond, detail=''):
        print('  %-4s %s%s' % ('ok' if cond else 'FAIL', label, '' if cond else ' -- %s' % str(detail)[:300]))
        if not cond:
            bad.append(label)

    d = tempfile.mkdtemp(prefix='field_scope_fx_')
    try:
        os.makedirs(os.path.join(d, 'api', '_lib'))
        real_auth = os.path.join(REPO, 'api', '_lib', 'auth.js').replace('\\', '/')
        io.open(os.path.join(d, 'api', '_lib', 'auth.js'), 'w').write('module.exports = require(%s);\n' % json.dumps(real_auth))
        io.open(os.path.join(d, 'api', '_lib', 'license.js'), 'w').write('module.exports = {};\n')
        io.open(os.path.join(d, 'api', 'sd-data.js'), 'w').write(
            FAKE_HANDLER % {'auth': json.dumps(os.path.join(d, 'api', '_lib', 'auth.js').replace('\\', '/'))})

        def run(mode):
            return check_rules(d, [FAKE_RULE], env={'FSC_FAKE_MODE': mode})

        f, c, ok, n = run('clean')
        arm('CLEAN handler: 5/5 roles pass, no finding, nothing could-not-run', (f, c, ok) == ([], [], 5), (f, c))
        f, c, ok, n = run('leak')
        arm('LEAK: a non-management role handed `secret` is a LEAK on all three',
            len([x for x in f if x.startswith('LEAK') and '.secret' in x]) == 3, f)
        arm('...and management, which may see it, is NOT flagged', not [x for x in f if '[owner]' in x], f)
        f, c, ok, n = run('peer')
        arm('PEER: a colleague\'s row reaching an own-scope role is a LEAK', any('peer.' in x for x in f), f)
        f, c, ok, n = run('empty')
        arm('EMPTY: returning nothing is MISSING, not a pass -- the non-vacuity control',
            len([x for x in f if x.startswith('MISSING')]) == 3, f)
        f, c, ok, n = run('flag')
        arm('FLAG: a response claiming visibility it did not grant is a FLAG finding',
            len([x for x in f if x.startswith('FLAG')]) == 3, f)
        f, c, ok, n = run('crash')
        arm('CRASH: a 500 is COULD NOT RUN for every role, never a pass', (len(c), f) == (5, []), (c, f))

        roles = {'sairnsenior': ['owner', 'billing', 'scheduler', 'coordinator', 'caregiver']}
        src_ok = ("    if (resource === 'fx_t' && action === 'read') {\n      FIXTURE-ANCHOR\n"
                  "      const session = verifySessionToken(t, h, 'sairnsenior');\n"
                  "      res.status(200).json({ data, secret_visible: !!X[session.role] });\n    }\n")
        arm('COVERAGE: a declared redaction WITH a rule is clean', coverage([FAKE_RULE], src_ok, roles) == [],
            coverage([FAKE_RULE], src_ok, roles))
        src_undecl = src_ok + src_ok.replace('fx_t', 'fx_other').replace('FIXTURE-ANCHOR', '')
        arm('COVERAGE: the same redaction on an UNDECLARED resource is a finding',
            any('fx_other' in x for x in coverage([FAKE_RULE], src_undecl, roles)))
        arm('COVERAGE: an anchor that occurs twice is a finding',
            any('anchor occurs 2' in x for x in coverage([FAKE_RULE], src_ok + src_ok, roles)))
        short = dict(FAKE_RULE, roles={k: v for k, v in FAKE_RULE['roles'].items() if k != 'caregiver'})
        arm('COVERAGE: a rule that omits one of the app\'s roles is a finding',
            any("['caregiver']" in x for x in coverage([short], src_ok, roles)))
        arm('SWEEP: every role seeing peer rows alike is SUSPECT',
            classify({'a': (200, 2, 2), 'b': (200, 2, 2)}, 2)[0] == 'SUSPECT')
        arm('SWEEP: every role seeing only its own row is OWN-ROW ONLY, not SUSPECT',
            classify({'a': (200, 2, 0), 'b': (200, 2, 0)}, 2)[0] == 'OWN-ROW ONLY')
        arm('SWEEP: different exposure per role is DIFFERENTIATED',
            classify({'a': (200, 2, 2), 'b': (200, 2, 0)}, 2)[0] == 'DIFFERENTIATED')
        arm('SWEEP: nobody served is COULD NOT TELL, never clean',
            classify({'a': (403, 0, 0), 'b': (400, 0, 0)}, 2)[0] == 'COULD NOT TELL')
        arm('SCHEMA: a well-formed rule validates clean', validate([FAKE_RULE]) == [], validate([FAKE_RULE]))
        typo = dict(FAKE_RULE, roles=dict(FAKE_RULE['roles'], caregiver={'see_fields': ['self.*']}))
        arm('SCHEMA: a misspelled key is an ERROR, never silently ignored',
            any("unknown key 'see_fields'" in x for x in validate([typo])), validate([typo]))
        nobody = dict(FAKE_RULE, roles=dict(FAKE_RULE['roles'], caregiver={'see': ['ghost.*']}))
        arm('SCHEMA: a see entry naming an undeclared tag is an error',
            any('ghost' in x for x in validate([nobody])))
        dup = dict(FAKE_RULE, tables={'fx_t': FAKE_RULE['tables']['fx_t'] + [{'tag': 'x', 'a': {'marker': 'M1'}},
                                                                            {'tag': 'y', 'b': {'marker': 'M1'}}]})
        arm('SCHEMA: one marker literal used twice is an error (presence could not say which field)',
            any('used twice' in x for x in validate([dup])), validate([dup]))
        try:
            expand(FAKE_RULE, ['self.nope'], seed(FAKE_RULE)[1])
            arm('a `see` naming an unseeded field is COULD NOT RUN', False)
        except CouldNotRun:
            arm('a `see` naming an unseeded field is COULD NOT RUN', True)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print('FIELD SCOPE BLIND LOCK -- %d failed' % len(bad))
    return EXIT_COULD_NOT_RUN if bad else EXIT_OK


# ── ENTRY ──────────────────────────────────────────────────────────────────
def main(argv):
    if '--fixtures' in argv:
        return fixtures()
    tmp = None
    try:
        root = REPO
        if '--ref' in argv:
            tmp = root = export_ref(argv[argv.index('--ref') + 1])
        rules_root = root
        if '--handler-ref' in argv:
            # The handler AT a past commit, judged by TODAY's declarations: the
            # shape a replay of a pre-fix bug needs, since the old tree has no
            # registry (or an older one that would agree with the old code).
            tmp = root = export_ref(argv[argv.index('--handler-ref') + 1], paths=('api',))
        try:
            rules = json.load(io.open(os.path.join(rules_root, 'tools', 'field_scope_rules.json'),
                                      encoding='utf-8'))['rules']
            src = io.open(os.path.join(root, 'api', 'sd-data.js'), encoding='utf-8').read()
        except (OSError, ValueError, KeyError) as e:
            raise CouldNotRun('the registry or api/sd-data.js could not be read: %s' % e)
        bad = validate(rules) if isinstance(rules, list) else ['"rules" is not a list']
        if bad or '--validate' in argv:
            print('FIELD SCOPE REGISTRY -- %d rule(s), %d schema error(s)' % (
                len(rules) if isinstance(rules, list) else 0, len(bad)))
            for x in bad:
                print('  SCHEMA ' + x)
            if bad:
                return EXIT_FINDING
            if '--validate' in argv:
                return EXIT_OK
        if '--env-file' in argv:
            # KEY=VALUE lines, for the live credentials. Never overrides a value
            # already in the environment, so an explicit export still wins.
            try:
                for ln in io.open(argv[argv.index('--env-file') + 1], encoding='utf-8'):
                    k, eq, v = ln.strip().partition('=')
                    if eq and k and not k.startswith('#'):
                        os.environ.setdefault(k.strip(), v.strip())
            except (OSError, IndexError) as e:
                raise CouldNotRun('--env-file could not be read: %s' % e)
        if '--only' in argv:
            only = argv[argv.index('--only') + 1].split(',')
            rules = [r for r in rules if r['id'] in only]
            if not rules:
                raise CouldNotRun('--only matched no rule id')
        if '--replay' in argv:
            findings, cnr, ok = replay(root, rules)
            at = (argv[argv.index('--handler-ref') + 1] if '--handler-ref' in argv
                  else argv[argv.index('--ref') + 1] if '--ref' in argv else 'the working tree')
            print('FIELD SCOPE REPLAY -- the live path against the handler at %s, %d arm(s) clean' % (at, ok))
            for x in findings + ['COULD NOT RUN ' + y for y in cnr]:
                print('  ' + x)
            return EXIT_FINDING if findings else (EXIT_COULD_NOT_RUN if cnr else EXIT_OK)
        if '--live' in argv:
            findings, cnr, ok = check_live(rules)
            print('FIELD SCOPE LIVE -- %s, %d arm(s) verified' % (LIVE_BASE, ok))
            for x in findings + ['COULD NOT RUN ' + y for y in cnr]:
                print('  ' + x)
            return EXIT_FINDING if findings else (EXIT_COULD_NOT_RUN if cnr else EXIT_OK)
        if fixtures_quiet() != EXIT_OK:
            raise CouldNotRun('the blind lock failed, so the criteria are not fit to judge real code '
                              '(python tools/sairn_field_scope_check.py --fixtures)')
        roles_by_app = app_roles(root)
        cov = coverage(rules, src, roles_by_app)
        findings, cnr, ok, n = check_rules(root, rules)
        findings = cov + findings
        print('FIELD SCOPE -- %d rule(s), %d role arm(s): %d clean, %d finding(s), %d could not run'
              % (len(rules), n, ok, len(findings), len(cnr)))
        for x in findings:
            print('  ' + x)
        for x in cnr:
            print('  COULD NOT RUN ' + x)
        code = EXIT_FINDING if findings else (EXIT_COULD_NOT_RUN if cnr else EXIT_OK)
        if '--sweep' in argv:
            rows = sweep(root, src, rules, roles_by_app)
            print('\nEXPOSURE SWEEP -- %d role-scoped read(s) with no declared rule' % len(rows))
            for b, verdict, why, matrix in rows:
                print('  %-15s %s/%s api/sd-data.js:%d -- %s' % (verdict, b['resource'], b['action'], b['line'], why))
                for ro, (st, s_, p_) in sorted(matrix.items()):
                    print('      %-15s %s  own-row markers %d, peer-row markers %d' % (ro, st, s_, p_))
            if any(v == 'SUSPECT' for _b, v, _w, _m in rows) and code == EXIT_OK:
                code = EXIT_FINDING
        return code
    except CouldNotRun as e:
        print('COULD NOT RUN: %s. Nothing was checked; this is not a pass.' % e)
        return EXIT_COULD_NOT_RUN
    except subprocess.TimeoutExpired as e:
        print('COULD NOT RUN: the driver timed out (%s). Nothing was checked.' % e)
        return EXIT_COULD_NOT_RUN
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def fixtures_quiet():
    so = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return fixtures()
    finally:
        sys.stdout = so


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
