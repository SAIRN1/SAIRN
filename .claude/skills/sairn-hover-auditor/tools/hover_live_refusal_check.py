#!/usr/bin/env python
"""hover_live_refusal_check.py -- TIER 1 of the live-execution capability
queued 2026-09-21 item 3, built on Michael's explicit authorization
2026-09-22: "real API/production execution, scoped strictly to refusal
checks and public-data reads ... using the existing tools/*_live_probe.py
pattern and sairn_http.py. No writes, ever."

WHAT THIS IS. A GENERIC, REUSABLE version of the pattern build agents already
use for their own gates (tools/leg_session_gate_live_probe.py,
tools/sc_tier_a_write_gate_live_probe.py): hit the REAL deployed endpoint
(sairn.vercel.app/api/sd-data) with a caller-controlled, action='read'-only
request and confirm it is REFUSED with a specific status+code, plus a control
arm reading an already-ungated resource to prove the refusal is attributable
to the gate and not to the endpoint being down. Unlike those app-specific
scripts, this one takes the resource/expected-refusal shape as arguments, so
this role can INDEPENDENTLY re-verify any app's session gate live, without
depending on trusting a build agent's own probe script for the verification
(the same "who checks the auditor" symmetry SKILL.md already states, applied
to a live check instead of a source read).

WHY 'NO WRITES, EVER' IS A NARROWER PROMISE THAN THE EXISTING PATTERN, AND
HELD MECHANICALLY, NOT JUST DOCUMENTED. leg_session_gate_live_probe.py sends
a real action='write' arm too (payload id='ZZ-LIVE-PROBE') and accepts that
IF the gate under test were actually broken, that write would really land in
production -- an acceptable risk for a build agent testing their OWN code,
where a stray row is theirs to find and clean up. This role does not own
platform code and was told 'no writes, ever' with no such carve-out, so
`call()` below HARD-REFUSES any action other than 'read' by raising before
building a request -- not a comment, not a CLI default, an actual
ValueError raised from inside the one function that builds the HTTP call,
so a caller cannot reach the network with anything else even by mistake.

WHAT THIS DOES: read the REAL sairn_http.py from the discovered platform
clone (imported, never copied -- unlike the small single-purpose regexes
hover-audit-log's other tools duplicate, this module has real, actively-
maintained logic -- the Vercel bot-mitigation User-Agent workaround, the
Challenged exception -- and a frozen copy would silently drift from it,
the exact Ariane-5 "byte-identical is not safe-in-context" risk CLAUDE.md
names). Importing and RUNNING it is a read, not a write, to the platform
repo -- the same boundary this role already relies on to call
classify_own_commit() out of tools/hover_separation_audit.py for review.

THREE STATES, NEVER TWO, SAME AS EVERY LIVE PROBE ON THIS PLATFORM:
  VERIFIED    the control arm answered 200 (endpoint is up, licence/auth
              context is real) AND the target arm was refused with the
              expected status AND the expected code -- both, not either.
  FAILED      the control arm was fine but the target arm answered 200, or
              refused for a DIFFERENT reason than expected -- a real defect.
  UNVERIFIED  Vercel served a bot challenge, the control arm itself did not
              answer 200 (so nothing below is attributable), a required
              credential env var is unset, or the endpoint could not be
              reached at all -- never folded into VERIFIED or FAILED.

Run:
  # session-gate style check, needs a real licence key via env (never on the
  # command line, never hardcoded)
  python hover_live_refusal_check.py \
      --resource leg_deathrecords --expect-status 401 --expect-code NO_SESSION \
      --control-resource shared_knowledge --key-env LEG_LICENSE

  # credential-free check: does the endpoint refuse a caller with NO licence
  # at all -- needs no secret, safe to run any time
  python hover_live_refusal_check.py \
      --resource profile --expect-status 401 --no-key

  python hover_live_refusal_check.py --selftest
"""
import json
import os
import subprocess
import sys
import threading
import time

_KNOWN_CLONES = (
    'C:/Users/marsh/Documents/SAIRN-hover',
    'C:/Users/marsh/Documents/SAIRN-hover2',
)

URL = 'https://sairn.vercel.app/api/sd-data'


class CouldNotTell(Exception):
    pass


def discover_repo(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if '--repo' in argv:
        i = argv.index('--repo')
        if i + 1 < len(argv):
            return argv[i + 1]
    env = os.environ.get('HOVER_LEDGER_REPO')
    if env:
        return env
    for candidate in _KNOWN_CLONES:
        if os.path.isdir(os.path.join(candidate, '.git')):
            return candidate
    return None


def import_sairn_http(repo):
    """Import the REAL, current tools/sairn_http.py from the discovered
    platform clone -- a read-only use of platform code (running it), never
    a write to it. Fails closed (CouldNotTell) if it is missing or fails to
    import, rather than falling back to any local substitute."""
    if not repo or not os.path.isdir(repo):
        raise CouldNotTell('no readable clone: %r (checked --repo, '
                            '$HOVER_LEDGER_REPO, and %s)'
                            % (repo, ', '.join(_KNOWN_CLONES)))
    tools_dir = os.path.join(repo, 'tools')
    if not os.path.isfile(os.path.join(tools_dir, 'sairn_http.py')):
        raise CouldNotTell('tools/sairn_http.py not found under %s' % repo)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import sairn_http  # noqa: E402  (import after sys.path insert, by design)
    return sairn_http


def err_code(body):
    """Same extraction shape as every *_live_probe.py in tools/ --
    body['error']['code'], or the bare string if the endpoint answered a
    plain string error, or '' for 'no code found' (never confused with a
    real empty-string code)."""
    if isinstance(body, dict):
        e = body.get('error')
        if isinstance(e, dict):
            return e.get('code') or ''
        if isinstance(e, str):
            return e
    return ''


def call(http, url, resource, action, key=None):
    """The ONE function that builds and sends the HTTP request. Hard-refuses
    (raises ValueError, sends nothing) for any action other than 'read' --
    this is the mechanical enforcement of 'no writes, ever', not a
    convention callers are trusted to follow."""
    if action != 'read':
        raise ValueError("hover_live_refusal_check only ever sends "
                          "action='read' -- refusing action=%r before "
                          "building a request. This role does not send "
                          "write-shaped requests to production, even ones "
                          "expected to be refused." % action)
    payload = {'action': 'read', 'resource': resource}
    return http.fetch_json(url, payload=payload, key=key)


def run_check(http, url, resource, expect_status, expect_code, key=None,
              control_resource=None):
    """Drives the control arm (if given) then the target arm, and returns a
    structured verdict dict. Never raises for an ordinary refusal/success
    response -- only for a genuine inability to reach the endpoint at all
    (Challenged, network error), which the caller turns into UNVERIFIED."""
    result = {'control': None, 'target': None}

    if control_resource:
        try:
            st, body = call(http, url, control_resource, 'read', key)
        except http.Challenged as c:
            result['verdict'] = 'UNVERIFIED'
            result['reason'] = 'control arm challenged: %s' % c
            return result
        result['control'] = {'status': st, 'code': err_code(body)}
        if st != 200:
            result['verdict'] = 'UNVERIFIED'
            result['reason'] = (
                'control resource %r did not answer 200 (got %s %s) -- '
                'cannot attribute a refusal on the target resource to a '
                'gate when the endpoint/credential itself is not confirmed '
                'live' % (control_resource, st, result['control']['code']))
            return result

    try:
        st, body = call(http, url, resource, 'read', key)
    except http.Challenged as c:
        result['verdict'] = 'UNVERIFIED'
        result['reason'] = 'target arm challenged: %s' % c
        return result
    code = err_code(body)
    result['target'] = {'status': st, 'code': code}

    if st == expect_status and (not expect_code or code == expect_code):
        result['verdict'] = 'VERIFIED'
        result['reason'] = ('target resource %r refused with %s %s as '
                             'expected' % (resource, st, code or '(no code)'))
    elif st == 200:
        result['verdict'] = 'FAILED'
        result['reason'] = ('target resource %r answered 200 -- NOT '
                             'refused at all' % resource)
    else:
        result['verdict'] = 'FAILED'
        result['reason'] = ('target resource %r refused with %s %s, not '
                             'the expected %s %s -- refused, but not by '
                             'the gate under test'
                             % (resource, st, code or '(no code)',
                                expect_status, expect_code or '(any code)'))
    return result


def _print_report(args_summary, result):
    print('HOVER LIVE REFUSAL CHECK (Tier 1) -- %s' % args_summary)
    if result.get('control') is not None:
        print('  control arm: %s' % result['control'])
    if result.get('target') is not None:
        print('  target  arm: %s' % result['target'])
    print('%s -- %s' % (result['verdict'], result['reason']))


# ---------------------------------------------------------------------------
# Fixture server: a REAL local HTTP server (not a mock of urllib), so the
# selftest drives the actual network code path -- just against localhost
# instead of production. Proves the classification logic against real
# bytes-over-a-socket, the same standard the other three tools' fixtures
# already hold themselves to, without touching sairn.vercel.app at all.
def _make_fixture_server(routes):
    """routes: {resource_name: (status, json_body)}. Returns (server, thread,
    base_url); caller must call server.shutdown() when done."""
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            try:
                req = json.loads(raw.decode('utf-8'))
            except ValueError:
                req = {}
            resource = req.get('resource')
            status, body = routes.get(resource, (404, {'error': {'code': 'UNKNOWN_RESOURCE'}}))
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(body).encode('utf-8'))

        def log_message(self, *a):
            pass  # keep selftest output clean; not a functional guard

    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = 'http://127.0.0.1:%d/api/sd-data' % server.server_port
    return server, thread, base_url


def run_fixtures(repo):
    ok_count = [0]
    fail_count = [0]

    def ck(name, cond):
        if cond:
            ok_count[0] += 1
            print('  ok   ' + name)
        else:
            fail_count[0] += 1
            print('  FAIL ' + name)

    http = import_sairn_http(repo)

    # --- call(): THE MECHANICAL 'no writes, ever' GUARANTEE, driven ---
    sent = []
    real_fetch_json = http.fetch_json
    http.fetch_json = lambda *a, **k: sent.append((a, k)) or (200, {})
    try:
        raised = False
        try:
            call(http, 'http://example.invalid', 'x', 'write', 'k')
        except ValueError:
            raised = True
        ck("call() with action='write' raises ValueError and sends NOTHING "
           '-- the real mechanism behind "no writes, ever", not a convention',
           raised and sent == [])
        call(http, 'http://example.invalid', 'x', 'read', 'k')
        ck("call() with action='read' does send a request",
           len(sent) == 1 and sent[0][0][0] == 'http://example.invalid')
    finally:
        http.fetch_json = real_fetch_json

    # --- err_code() ---
    ck('dict error with code is extracted',
       err_code({'error': {'code': 'NO_SESSION'}}) == 'NO_SESSION')
    ck('string error is returned as-is', err_code({'error': 'boom'}) == 'boom')
    ck('no error key at all is empty string', err_code({}) == '')

    # --- run_check() against a REAL local HTTP server, all four real
    # outcome shapes, each one an actual socket round-trip ---
    server, thread, base = _make_fixture_server({
        'ctl': (200, {'ok': True}),
        'gated_ok': (401, {'error': {'code': 'NO_SESSION'}}),
        'gated_open': (200, {'ok': True, 'data': []}),
        'gated_wrong_reason': (403, {'error': {'code': 'FORBIDDEN'}}),
    })
    try:
        r1 = run_check(http, base, 'gated_ok', 401, 'NO_SESSION',
                        key='k', control_resource='ctl')
        ck('VERIFIED: control 200 + target refused with the exact expected '
           'status+code', r1['verdict'] == 'VERIFIED')

        r2 = run_check(http, base, 'gated_open', 401, 'NO_SESSION',
                        key='k', control_resource='ctl')
        ck('FAILED: target answers 200 -- the gate is not live',
           r2['verdict'] == 'FAILED' and 'NOT' in r2['reason'])

        r3 = run_check(http, base, 'gated_wrong_reason', 401, 'NO_SESSION',
                        key='k', control_resource='ctl')
        ck('FAILED: target refused, but with the WRONG status/code -- '
           'refused for a reason that is not the gate under test',
           r3['verdict'] == 'FAILED' and 'not by the gate' in r3['reason'])

        r4 = run_check(http, base, 'gated_ok', 401, 'NO_SESSION',
                        key='k', control_resource='does_not_exist')
        ck('UNVERIFIED: control arm itself does not answer 200 -- refuses '
           'to attribute the target refusal to anything',
           r4['verdict'] == 'UNVERIFIED')

        # A real, live network error (nobody listening on this port) must
        # not be silently swallowed into any of the three named verdicts --
        # it should raise up through fetch_json as a real connection error.
        raised_conn = False
        try:
            run_check(http, 'http://127.0.0.1:1/api/sd-data', 'x', 401,
                      'NO_SESSION', key='k')
        except OSError:
            raised_conn = True
        ck('a genuine connection failure (nothing listening) raises rather '
           'than being silently reported as any of VERIFIED/FAILED/UNVERIFIED',
           raised_conn)
    finally:
        server.shutdown()
        thread.join(timeout=5)

    print()
    print('%d ok, %d failed' % (ok_count[0], fail_count[0]))
    return fail_count[0] == 0


def main(argv):
    repo = discover_repo(argv)
    if '--selftest' in argv:
        if not repo:
            print('COULD NOT RUN: no readable clone found for --selftest '
                  '(needs tools/sairn_http.py to import)')
            return 2
        ok = run_fixtures(repo)
        sys.exit(0 if ok else 1)

    def opt(flag, required=True, default=None):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv):
                return argv[i + 1]
        if required:
            print('missing %s' % flag, file=sys.stderr)
            sys.exit(2)
        return default

    resource = opt('--resource')
    expect_status = int(opt('--expect-status'))
    expect_code = opt('--expect-code', required=False, default='')
    control_resource = opt('--control-resource', required=False, default=None)
    url = opt('--url', required=False, default=URL)
    no_key = '--no-key' in argv
    key = None
    if not no_key:
        key_env = opt('--key-env')
        key = os.environ.get(key_env, '').strip()
        if not key:
            print('UNVERIFIED -- $%s is not set. This check cannot be driven '
                  'without a real credential; pass --no-key explicitly if a '
                  'credential-free refusal check is what you meant.' % key_env)
            return 2

    try:
        http = import_sairn_http(repo)
    except CouldNotTell as e:
        print('COULD NOT RUN: %s' % e)
        return 2

    result = run_check(http, url, resource, expect_status, expect_code,
                        key=key, control_resource=control_resource)
    _print_report('resource=%s expect=%s/%s%s' % (
        resource, expect_status, expect_code or '(any code)',
        ' control=%s' % control_resource if control_resource else ''
    ), result)
    return {'VERIFIED': 0, 'FAILED': 1, 'UNVERIFIED': 2}[result['verdict']]


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
