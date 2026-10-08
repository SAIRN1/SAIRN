#!/usr/bin/env python
"""Minimal real-HTTP helper, stdlib only, no dependency on tools/sairn_http.py.

Own tool, own location. Built 2026-10-06 (H1, batch J, item 4). Design
logged (seq 1004) before this file was written. Replaces this role's
"weaker justification" exemption of sairn_http.py for any FUTURE real-path
drive -- narrower than that tool on purpose (no Vercel bot-challenge
detection, no retry policy), named rather than hidden.
"""
import json as _json
import sys
import urllib.error
import urllib.request


def fetch(url, method='GET', payload=None, headers=None, timeout=20):
    headers = dict(headers or {})
    data = None
    if payload is not None:
        data = _json.dumps(payload).encode('utf-8')
        headers.setdefault('Content-Type', 'application/json')
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            return {'status': resp.status, 'body': body}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return {'status': e.code, 'body': body}
    except urllib.error.URLError as e:
        return {'status': None, 'error': str(e)}


def _selftest():
    # No network assumed available/desired in a selftest -- this checks the
    # REQUEST-BUILDING logic only (method, headers, json body), not a real
    # round trip. A real round trip is exercised by hand on an actual drive,
    # same as every other real-path check this role has done this session.
    import io
    import unittest.mock as mock
    ok = 0
    total = 2
    captured = {}

    class FakeResp:
        status = 200
        def read(self):
            return b'{"ok":true}'
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured['method'] = req.get_method()
        captured['data'] = req.data
        captured['headers'] = dict(req.headers)
        return FakeResp()

    with mock.patch('urllib.request.urlopen', fake_urlopen):
        r = fetch('https://example.invalid/x', method='POST', payload={'a': 1})
    if captured.get('method') == 'POST' and captured.get('data') == b'{"a": 1}':
        ok += 1
        print('  ok   POST with JSON payload builds the right method and body')
    else:
        print('  FAIL got method=%r data=%r' % (captured.get('method'), captured.get('data')))
    if r.get('status') == 200 and r.get('body') == '{"ok":true}':
        ok += 1
        print('  ok   response status/body surfaced correctly')
    else:
        print('  FAIL got %r' % r)
    print('%d/%d fixture checks correct' % (ok, total))
    return ok == total


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    print('usage: hover_own_http.py --selftest  (library use: import and call fetch())')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
