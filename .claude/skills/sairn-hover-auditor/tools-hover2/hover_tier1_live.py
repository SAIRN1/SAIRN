#!/usr/bin/env python
"""hover_tier1_live.py -- Tier 1 real production execution, read-only.

Built independently from H1's published interface spec
(.claude/skills/sairn-hover-auditor/SKILL.md, commit 1b66a71e, "Spec 2 --
live execution, two tiers, Tier 1 authorized by Michael 2026-09-22").
Interface only -- no source seen or copied.

WHAT THIS IS. A generic, reusable version of the pattern build agents
already use for their own session-gate probes (control arm plus gated
arm, VERIFIED/FAILED/UNVERIFIED, never folding "could not tell" into a
pass) -- generalised so this role can independently re-verify ANY app's
session gate LIVE, rather than trusting a build agent's own probe script
for the same question.

Reuses this platform's own existing HTTP client (tools/sairn_http.py) for
reaching production -- IMPORTED LIVE FROM THE PLATFORM REPO AT CALL TIME
(see _load_sairn_http()), never copied into this private tooling. It
carries real, actively-maintained logic (the Vercel bot-mitigation
User-Agent fix, the Challenged exception, the tuple-membership footgun
guard) a frozen copy would silently drift from.

"NO WRITES, EVER" IS HELD MECHANICALLY, NOT BY PROMISE, AND IS NARROWER
THAN THE PATTERN BEING REUSED. build_read_request() -- the ONE function
that constructs an outbound request body -- refuses (raises, sends
nothing) for any action other than 'read', before a urllib.request.Request
object is ever built. Real build-agent session-gate probes DO send a real
write arm (accepting that a broken gate would really write, because it is
their own code under test) -- this role has no such carve-out and was
told so explicitly. Proven by spying on the real HTTP call and confirming
zero requests are sent for a write-shaped action (see selftest()).

    python hover_tier1_live.py --gate-check \\
        --app sen --control-resource does_not_exist_xyz \\
        --target-resource sen_clients --expected-status 401 \\
        --expected-code NO_LICENSE
    python hover_tier1_live.py --selftest
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys

DEFAULT_PLATFORM_REPO = os.environ.get(
    'HOVER_PLATFORM_REPO', r'C:\Users\marsh\Documents\SAIRN-hover2')
DEFAULT_ENDPOINT = 'https://sairn.vercel.app/api/sd-data'

VERIFIED, FAILED, UNVERIFIED = 'VERIFIED', 'FAILED', 'UNVERIFIED'


def _run_git(repo, args, timeout=20):
    try:
        p = subprocess.run(['git', '-C', repo] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding='utf-8', errors='replace', timeout=timeout)
        return p.returncode, (p.stdout or ''), (p.stderr or '')
    except subprocess.TimeoutExpired:
        return None, '', 'TIMEOUT after %ss' % timeout
    except OSError as exc:
        return None, '', 'could not run git: %s' % exc


def _load_sairn_http(repo=None, ref='origin/main', fetch_timeout=25):
    """Imports tools/sairn_http.py LIVE from the platform repo, fresh off
    origin/main, at call time -- never a static copy in this directory, and
    never even the possibly-stale local working tree (same discipline as
    Tier 0's fetch_app_source() and the --source staleness guard). Returns
    the loaded module object; callers use mod.fetch_json / mod.fetch /
    mod.Response / mod.Challenged exactly as any real caller of that file
    would."""
    repo = repo or DEFAULT_PLATFORM_REPO
    rc, _out, err = _run_git(repo, ['fetch', 'origin', 'main'], timeout=fetch_timeout)
    if rc != 0:
        raise RuntimeError('could not fetch origin/main to load tools/sairn_http.py '
                          'live: %s' % (err.strip() or 'unknown error'))
    rc, source, err = _run_git(repo, ['show', '%s:tools/sairn_http.py' % ref])
    if rc != 0:
        raise RuntimeError('could not read %s:tools/sairn_http.py -- %s'
                          % (ref, err.strip() or 'unknown error'))
    spec = importlib.util.spec_from_loader('sairn_http_live_%s' % ref.replace('/', '_'),
                                          loader=None)
    mod = importlib.util.module_from_spec(spec)
    code = compile(source, '<%s:tools/sairn_http.py, loaded live>' % ref, 'exec')
    exec(code, mod.__dict__)
    return mod


class WriteRefused(Exception):
    """Raised by build_read_request() for anything other than action='read'.
    Nothing is constructed, nothing is sent -- this is checked BEFORE a
    urllib.request.Request object exists, not caught after."""


def build_read_request(action, resource, app_id, payload=None, key=None, token=None):
    """THE ONE function that builds the outbound request body+headers.
    Mechanically read-only: raises WriteRefused for any action other than
    'read', before any request is constructed. This is the entire
    enforcement mechanism -- every caller in this file, including the CLI,
    is required to route through here rather than building a payload dict
    by hand, so there is exactly one place capable of sending a
    write-shaped request, and it refuses to."""
    if action != 'read':
        raise WriteRefused(
            "Tier 1 refuses to construct a request for action=%r -- this "
            "capability is read-only, mechanically, with no carve-out, even "
            "though the build-agent pattern it is generalised from does send "
            "a real write arm against its own code under test. Only "
            "action='read' is ever built here." % action)
    body = {'action': 'read', 'resource': resource, 'app_id': app_id,
            'payload': payload or {}}
    headers = {}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    if token:
        headers['X-SD-Auth'] = token
    return body, headers


def _call(http_mod, endpoint, action, resource, app_id, payload=None, key=None,
          token=None, timeout=25):
    """One read call. Returns (state_component, status, code, message,
    raw_body) where state_component is None on a clean HTTP round-trip
    (caller judges VERIFIED/FAILED from status+code) or a string reason
    when the call itself could not be completed cleanly (-> UNVERIFIED)."""
    try:
        body, headers = build_read_request(action, resource, app_id, payload, key, token)
    except WriteRefused:
        raise
    try:
        status, parsed = http_mod.fetch_json(endpoint, timeout=timeout,
                                            method='POST', payload=body,
                                            headers=headers)
    except http_mod.Challenged as exc:
        return ('challenged: %s' % exc, None, None, None, None)
    except Exception as exc:  # noqa: BLE001 -- any transport failure is UNVERIFIED, not FAILED
        return ('transport error: %s: %s' % (type(exc).__name__, exc), None, None, None, None)
    code = None
    message = None
    if isinstance(parsed, dict):
        err = parsed.get('error') or {}
        if isinstance(err, dict):
            code = err.get('code')
            message = err.get('message')
    return (None, status, code, message, parsed)


def probe_gate(app_id, control_resource, target_resource, expected_status,
              expected_code, control_key=None, target_key=None,
              target_token=None, endpoint=DEFAULT_ENDPOINT, repo=None,
              ref='origin/main'):
    """Control arm, then target arm -- three states, never two.

    CONTROL proves the premise before the target arm is judged at all: a
    resource this role has independent reason to expect behaves a KNOWN
    way (default use: a resource name that does not exist, isolating the
    auth-layer check from any resource-specific logic) is read with
    `control_key` (may be None for the credential-free mode: does the
    endpoint refuse an entirely unauthenticated caller at all, uniformly,
    before ever reaching resource-specific code). If the control arm does
    not match expected_status/expected_code exactly -> UNVERIFIED: the
    premise itself could not be established, so the target arm is never
    even judged.

    TARGET is then read with the specific under-privileged caller shape
    being checked (`target_key`/`target_token`, independently settable so
    e.g. 'licence key present, no session token' can be probed once real
    credentials are available). Both STATUS and CODE are asserted --
    never 'anything other than 200' alone, so a refusal for an unrelated
    reason is never mistaken for the gate actually under test.
        VERIFIED -- control matched AND target refused with the exact
                    expected status+code.
        FAILED   -- control matched but target did NOT refuse as expected
                    (a real defect: either it answered 200, or refused with
                    a different status/code than the one under test).
        UNVERIFIED -- the control arm itself did not succeed as expected
                    (bot-mitigation challenge, transport failure, or the
                    live API's error shape has moved since this was last
                    calibrated), or a required credential was not set.
    """
    http_mod = _load_sairn_http(repo=repo, ref=ref)

    c_reason, c_status, c_code, c_msg, _c_raw = _call(
        http_mod, endpoint, 'read', control_resource, app_id, key=control_key)
    if c_reason is not None:
        return {'verdict': UNVERIFIED,
               'reason': 'control arm could not be completed: %s' % c_reason,
               'control': None, 'target': None}
    control_matched = (c_status == expected_status and c_code == expected_code)
    if not control_matched:
        return {'verdict': UNVERIFIED,
               'reason': ('control arm did not answer as expected (got status=%r '
                          'code=%r, wanted status=%r code=%r) -- the premise this '
                          'probe rests on could not be established, so the target '
                          'arm is not judged'
                          % (c_status, c_code, expected_status, expected_code)),
               'control': {'status': c_status, 'code': c_code, 'message': c_msg},
               'target': None}

    t_reason, t_status, t_code, t_msg, _t_raw = _call(
        http_mod, endpoint, 'read', target_resource, app_id,
        key=target_key, token=target_token)
    if t_reason is not None:
        return {'verdict': UNVERIFIED,
               'reason': 'target arm could not be completed: %s' % t_reason,
               'control': {'status': c_status, 'code': c_code, 'message': c_msg},
               'target': None}

    target_matched = (t_status == expected_status and t_code == expected_code)
    return {
        'verdict': VERIFIED if target_matched else FAILED,
        'reason': ('target refused exactly as expected' if target_matched else
                  ('target did NOT refuse as expected -- got status=%r code=%r, '
                   'wanted status=%r code=%r' % (t_status, t_code,
                                               expected_status, expected_code))),
        'control': {'status': c_status, 'code': c_code, 'message': c_msg},
        'target': {'status': t_status, 'code': t_code, 'message': t_msg},
    }


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--gate-check', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--app', default=None, help='app_id, e.g. sairnsenior')
    ap.add_argument('--control-resource', default=None)
    ap.add_argument('--target-resource', default=None)
    ap.add_argument('--expected-status', type=int, default=401)
    ap.add_argument('--expected-code', default='NO_LICENSE')
    ap.add_argument('--control-key', default=None)
    ap.add_argument('--target-key', default=None)
    ap.add_argument('--target-token', default=None)
    ap.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    ap.add_argument('--repo', default=None)
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.gate_check:
        if not (args.app and args.control_resource and args.target_resource):
            print('--gate-check needs --app --control-resource --target-resource')
            return 2
        result = probe_gate(args.app, args.control_resource, args.target_resource,
                           args.expected_status, args.expected_code,
                           control_key=args.control_key, target_key=args.target_key,
                           target_token=args.target_token, endpoint=args.endpoint,
                           repo=args.repo)
        print(json.dumps(result, indent=2))
        return {'VERIFIED': 0, 'FAILED': 1, 'UNVERIFIED': 3}[result['verdict']]

    print(__doc__)
    return 0


def selftest():
    bad = []
    total = [0]

    def ck(name, cond):
        total[0] += 1
        ok = bool(cond)
        print(('  ok   ' if ok else '  FAIL ') + name)
        if not ok:
            bad.append(name)

    ck("build_read_request('read', ...) builds a normal, well-formed request",
       build_read_request('read', 'r', 'a')[0] == {'action': 'read', 'resource': 'r',
                                                    'app_id': 'a', 'payload': {}})
    ck("build_read_request('write', ...) refuses -- WriteRefused, nothing built",
       _raises(WriteRefused, build_read_request, 'write', 'r', 'a'))
    ck("build_read_request('delete', ...) refuses",
       _raises(WriteRefused, build_read_request, 'delete', 'r', 'a'))
    ck("build_read_request('evaluate', ...) refuses -- only the literal "
       "string 'read' is ever accepted, no allowlist of 'probably safe' verbs",
       _raises(WriteRefused, build_read_request, 'evaluate', 'r', 'a'))

    # THE MECHANICAL PROOF: spy on the real transport call and confirm ZERO
    # requests are sent for a write-shaped action -- not "it raised before I
    # checked", but "the network layer itself was never invoked".
    calls = []

    class _FakeHttpMod:
        class Challenged(Exception):
            pass

        @staticmethod
        def fetch_json(*a, **kw):
            calls.append((a, kw))
            return (200, {'ok': True})

    try:
        _call(_FakeHttpMod, DEFAULT_ENDPOINT, 'write', 'r', 'a')
        write_raised = False
    except WriteRefused:
        write_raised = True
    ck("a write-shaped action raises WriteRefused before _call() ever "
       "reaches the transport layer, AND zero requests were actually sent "
       "(spied on the real call site, not inferred from the exception alone)",
       write_raised and len(calls) == 0)

    _call(_FakeHttpMod, DEFAULT_ENDPOINT, 'read', 'r', 'a')
    ck("a read-shaped action DOES reach the transport layer exactly once "
       "(confirms the spy itself is wired correctly, not just silent)",
       len(calls) == 1)

    # -- three-state contract on a stubbed transport, no network involved --
    class _StubHttpMod:
        class Challenged(Exception):
            pass

        def __init__(self, control_answer, target_answer=None, raise_on_target=None):
            self.control_answer = control_answer
            self.target_answer = target_answer
            self.raise_on_target = raise_on_target
            self.n = 0

        def fetch_json(self, endpoint, timeout=25, method='POST', payload=None, headers=None):
            self.n += 1
            if self.n == 1:
                return self.control_answer
            if self.raise_on_target:
                raise self.raise_on_target
            return self.target_answer

    def probe_with_stub(stub):
        import types
        real_load = globals()['_load_sairn_http']
        globals()['_load_sairn_http'] = lambda repo=None, ref='origin/main': stub
        try:
            return probe_gate('a', 'ctrl', 'tgt', 401, 'NO_LICENSE')
        finally:
            globals()['_load_sairn_http'] = real_load

    r_verified = probe_with_stub(_StubHttpMod(
        (401, {'error': {'code': 'NO_LICENSE', 'message': 'x'}}),
        (401, {'error': {'code': 'NO_LICENSE', 'message': 'x'}})))
    ck('VERIFIED: control matches, target refuses exactly as expected',
       r_verified['verdict'] == VERIFIED)

    r_failed = probe_with_stub(_StubHttpMod(
        (401, {'error': {'code': 'NO_LICENSE', 'message': 'x'}}),
        (200, {'ok': True, 'data': [{'name': 'a real row'}]})))
    ck('FAILED: control matches but target answers 200 -- a real gate defect',
       r_failed['verdict'] == FAILED)

    r_failed2 = probe_with_stub(_StubHttpMod(
        (401, {'error': {'code': 'NO_LICENSE', 'message': 'x'}}),
        (403, {'error': {'code': 'FORBIDDEN', 'message': 'y'}})))
    ck('FAILED: target refuses, but with a DIFFERENT status+code than the '
       'one under test -- never mistaken for the gate actually being probed',
       r_failed2['verdict'] == FAILED)

    r_unverified_control = probe_with_stub(_StubHttpMod(
        (200, {'ok': True}),  # control itself did not refuse as expected
        (401, {'error': {'code': 'NO_LICENSE', 'message': 'x'}})))
    ck("UNVERIFIED: the control arm did not answer as expected, so the "
       "target arm is not even judged (never silently promoted to a pass)",
       r_unverified_control['verdict'] == UNVERIFIED
       and r_unverified_control['target'] is None)

    r_unverified_challenge = probe_with_stub(_StubHttpMod(
        (401, {'error': {'code': 'NO_LICENSE', 'message': 'x'}}),
        raise_on_target=_StubHttpMod.Challenged('bot mitigation')))
    ck('UNVERIFIED: a bot-mitigation challenge on the target arm never '
       'folds into FAILED or VERIFIED -- a third state, always',
       r_unverified_challenge['verdict'] == UNVERIFIED)

    print('')
    if bad:
        print('%d of %d selftest arm(s) failed' % (len(bad), total[0]))
        return 2
    print('OK -- %d arms passed.' % total[0])
    return 0


def _raises(exc_type, fn, *a, **kw):
    try:
        fn(*a, **kw)
        return False
    except exc_type:
        return True


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
