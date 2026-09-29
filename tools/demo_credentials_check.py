"""Does each app's demo credential still sign in?

Run:  python tools/demo_credentials_check.py
      python tools/demo_credentials_check.py --json

── THE INCIDENT ────────────────────────────────────────────────────────────
2026-09-29. SB-PINNACLE-2026 refused Michael's PIN. A demo credential is the
thing a prospect is shown and the thing every live verification on this platform
starts from -- and nothing anywhere checks that they still work. The stored PINs
for the other fourteen apps had exactly as much evidence behind them: none.

── IT NEVER PRINTS A PIN, ON ANY PATH ──────────────────────────────────────
Including the failing ones. A checker that reports WRONG-PIN by showing the PIN
it tried has made the problem worse than the stale credential it found, and the
failing path is the one somebody copies into a chat window. Every line this tool
emits is built by format_line(), the PIN is never passed to it, and
tests/run_demo_credentials_probe.py searches the whole output of EVERY verdict
for the PIN it used -- with a planted-leak control, so that search cannot quietly
stop working.

── CREDENTIALS COME FROM AN UNTRACKED LOCAL FILE, AND ONLY FROM THERE ──────
`.demo-credentials.local.json` in the repo root, gitignored, never written by
this tool. No environment fallback and no hardcoded default: a fallback is how a
credential ends up in a file somebody commits, and a default that works is a
default nobody notices is wrong.

    {"apps": [
      {"app": "stonedesk", "endpoint": "/api/sd-auth",
       "license_key": "SD-AUDIT-2026", "employee_id": "sairn-demo-owner",
       "pin": "..."}
    ]}

An absent or unparseable file is exit 2 COULD NOT RUN. It is NOT a clean run
with nothing to check -- those look identical from the outside and only one of
them is evidence.

── FOUR VERDICTS, AND THE FOURTH IS A THIRD STATE ──────────────────────────
  OK                200 with a token
  WRONG-PIN         401 INVALID_CREDENTIALS -- the stored credential is stale
  LICENCE-INACTIVE  401 INVALID_LICENSE or 403 LICENSE_INACTIVE
  COULD-NOT-REACH   a transport failure, a bot challenge, or any other status

COULD-NOT-REACH is never folded into either neighbour. "The platform said no"
and "I could not ask" are different answers and only the first is evidence about
the credential. It DOES count toward the exit code, because a check that could
not run is not a pass -- but it is reported under its own name.

── REPORT-ONLY, AND WHAT THAT MEANS HERE ───────────────────────────────────
It is not a push gate. A demo credential going stale is not something a push
introduced, and blocking somebody's unrelated push on it is how a check gets
switched off. It exits nonzero so a human or a scheduled run notices.

── WHAT IT CANNOT SEE ──────────────────────────────────────────────────────
* Whether the account it signed in as has the ROLE anybody expects. It reports
  the role the platform returns and does not judge it.
* Whether a licence is about to expire. It asks one question: can this
  credential sign in right now.
* Any app not named in the local file. The universe is whatever that file lists,
  and the count is printed so a shrinking list is visible.
"""
import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = '.demo-credentials.local.json'
HOST = 'https://sairn.vercel.app'


def format_line(app, verdict, detail=''):
    """The ONE place a reported line is built. The PIN is never an argument."""
    return '  %-10s %-18s %s' % (verdict, app, detail)


def load_credentials(path):
    """The parsed file, or None for COULD NOT RUN. Never creates it."""
    if not os.path.isfile(path):
        return None
    try:
        d = json.load(io.open(path, encoding='utf-8'))
    except Exception:                                          # noqa: BLE001
        return None
    apps = d.get('apps') if isinstance(d, dict) else None
    if not isinstance(apps, list) or not apps:
        return None
    return apps


def _default_fetch(url, payload=None, key=None, headers=None, timeout=None):
    import sairn_http
    return sairn_http.fetch_json(url, payload=payload, key=key,
                                 headers=headers or {}, timeout=timeout or 45)


def check_one(entry, fetch=None):
    """(verdict, line). The PIN is sent and never returned or printed."""
    fetch = fetch or _default_fetch
    app = str(entry.get('app') or '?')
    url = HOST + str(entry.get('endpoint') or '')
    payload = {'action': 'login',
               'employee_id': str(entry.get('employee_id') or ''),
               'pin': str(entry.get('pin') or '')}
    try:
        r = fetch(url, payload=payload, key=str(entry.get('license_key') or ''),
                  headers={}, timeout=45)
    except Exception as exc:                                   # noqa: BLE001
        # THE TYPE, NOT THE MESSAGE. A transport error can carry the request in
        # its string form on some clients, and that request contains the PIN.
        return 'COULD-NOT-REACH', format_line(
            app, 'COULD-NOT-REACH', 'transport: ' + type(exc).__name__)

    status = getattr(r, 'status', None)
    body = getattr(r, 'body', None)
    body = body if isinstance(body, dict) else {}
    code = ((body.get('error') or {}).get('code') or '') if body else ''

    if status == 200 and body.get('token'):
        return 'OK', format_line(app, 'OK',
                                 'role=%s' % (body.get('role') or '?'))
    if status == 401 and code == 'INVALID_CREDENTIALS':
        return 'WRONG-PIN', format_line(
            app, 'WRONG-PIN', 'the stored credential no longer signs in')
    if code in ('INVALID_LICENSE', 'LICENSE_INACTIVE') or status == 403:
        return 'LICENCE-INACTIVE', format_line(
            app, 'LICENCE-INACTIVE', 'HTTP %s %s' % (status, code or ''))
    if status == 200:
        # A 200 with no token is not a sign-in. Reported as could-not-reach
        # rather than OK, because whatever happened, the credential was not
        # demonstrated to work.
        return 'COULD-NOT-REACH', format_line(
            app, 'COULD-NOT-REACH', 'HTTP 200 with no token in the response')
    return 'COULD-NOT-REACH', format_line(
        app, 'COULD-NOT-REACH', 'HTTP %s %s' % (status, code or ''))


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--file', default=None)
    args = ap.parse_args(argv)

    path = args.file or os.path.join(REPO, CREDENTIALS_FILE)
    apps = load_credentials(path)
    if apps is None:
        sys.stderr.write(
            'COULD NOT RUN: %s is absent, unreadable, or has no "apps" list.\n'
            'This tool has NO fallback and NO default on purpose -- a fallback '
            'is how a credential ends up in a file somebody commits, and a '
            'default that works is a default nobody notices is wrong.\n'
            'Create it in the repo root (it is gitignored):\n'
            '  {"apps": [{"app": "...", "endpoint": "/api/xx-auth", '
            '"license_key": "...", "employee_id": "...", "pin": "..."}]}\n'
            % CREDENTIALS_FILE)
        return EXIT_COULD_NOT_RUN

    results, lines = [], []
    for entry in apps:
        verdict, line = check_one(entry)
        results.append((str(entry.get('app') or '?'), verdict))
        lines.append(line)

    print('DEMO CREDENTIAL CHECK')
    print('  apps checked : %d  (the universe is whatever %s lists)'
          % (len(apps), CREDENTIALS_FILE))
    print()
    for line in lines:
        print(line)
    print()
    counts = {}
    for _, v in results:
        counts[v] = counts.get(v, 0) + 1
    print('  ' + ', '.join('%s %d' % (k, counts[k]) for k in sorted(counts)))
    print()
    print('  NO PIN IS PRINTED ON ANY PATH, including the failing ones, and')
    print('  tests/run_demo_credentials_probe.py searches every verdict output')
    print('  for the PIN it used -- with a planted-leak control, so that search')
    print('  cannot quietly stop working.')
    print('  COULD-NOT-REACH is a THIRD STATE: the platform was not asked, so')
    print('  nothing was learned about that credential either way.')

    if args.json:
        print(json.dumps({'results': [{'app': a, 'verdict': v}
                                      for a, v in results]}, indent=2))

    bad = [a for a, v in results if v != 'OK']
    return EXIT_FINDING if bad else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
