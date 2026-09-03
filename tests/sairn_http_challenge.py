"""
tests/sairn_http_challenge.py -- the Vercel bot-mitigation contract.

WHAT THIS PROTECTS. On 2026-09-02 four sessions live-verifying pushes with curl
and urllib tripped Vercel's platform bot mitigation. Every automated-looking
request came back 403 with `X-Vercel-Mitigated: challenge`. Two things were
wrong and only one of them was the 403:

  1. The tooling identified itself as automated (`Python-urllib/3.x`,
     `sairn-app-map-check`) and was treated accordingly.
  2. MORE IMPORTANTLY -- `deploy_verify_notify.py` caught every fetch exception
     and `sys.exit(0)`, so during the challenge window the post-push deploy
     check SILENTLY DID NOT RUN on any push and said nothing. From the outside
     that is indistinguishable from a clean pass.

These assertions exist so neither can come back quietly. They are offline: no
assertion here touches the network, because a test that needs a live challenge
to fail is a test that only works during an outage.
"""
import os
import sys
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sairn_http  # noqa: E402

passed = failed = 0


def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
        print('  ok   ' + name)
    else:
        failed += 1
        print('  FAIL ' + name + '\n         expected %r\n         actual   %r' % (expected, actual))


class FakeHeaders(dict):
    def get(self, k, d=None):
        for kk, vv in self.items():
            if kk.lower() == k.lower():
                return vv
        return d


def fake_error(headers, code=403, url='https://sairn.vercel.app/stonedesk'):
    e = urllib.error.HTTPError(url, code, 'Forbidden', FakeHeaders(headers), None)
    return e


print('sairn_http -- the challenge is recognised, and never mistaken for an answer')

# ── the User-Agent, which is the actual fix ─────────────────────────────
check('a browser User-Agent is sent by default',
      'Chrome/' in sairn_http.DEFAULT_HEADERS['User-Agent'] and
      sairn_http.DEFAULT_HEADERS['User-Agent'].startswith('Mozilla/5.0'), True)
check('with_browser_ua adds it without clobbering the caller',
      sairn_http.with_browser_ua({'Authorization': 'Bearer k',
                                  'Content-Type': 'application/json'}),
      dict(sairn_http.DEFAULT_HEADERS,
           **{'Authorization': 'Bearer k', 'Content-Type': 'application/json'}))
# A caller that deliberately sets its own UA must keep it. Silently overriding
# a caller's identity is its own surprise.
check('a caller-supplied User-Agent wins over the default',
      sairn_http.with_browser_ua({'User-Agent': 'mine'})['User-Agent'], 'mine')

# ── the challenge is its own type, not a generic failure ────────────────
try:
    sairn_http.raise_if_challenge(fake_error({'X-Vercel-Mitigated': 'challenge'}))
    check('a mitigated response raises Challenged', 'did not raise', 'Challenged')
except sairn_http.Challenged as c:
    check('a mitigated response raises Challenged', c.status, 403)
    # The message has to tell the reader the two things they will get wrong:
    # that this is not a broken deploy, and that it is not a pass either.
    check('and the message says it is NOT a failed deploy',
          'NOT a failed deploy' in str(c), True)
    check('and names the tool that gets past it',
          'mcp__claude_ai_Vercel__web_fetch_vercel_url' in str(c), True)

try:
    sairn_http.raise_if_challenge(fake_error({'X-Vercel-Challenge-Token': 'abc.def'}))
    check('the challenge TOKEN alone is enough to recognise it', 'did not raise', 'Challenged')
except sairn_http.Challenged as c:
    check('the challenge TOKEN alone is enough to recognise it', c.token, 'abc.def')

# ── and an ordinary error is NOT swallowed as a challenge ──────────────
# The opposite mistake: calling every 403 a challenge would hide a real
# permission failure behind a reassuring "not an outage" message.
for hdrs, label in [({}, 'a bare 403'),
                    ({'X-Vercel-Id': 'iad1::x'}, 'a 403 with only a Vercel id'),
                    ({'X-Vercel-Mitigated': 'other'}, 'a different mitigation')]:
    try:
        sairn_http.raise_if_challenge(fake_error(hdrs))
        check(label + ' is left alone, not reported as a challenge', True, True)
    except sairn_http.Challenged:
        check(label + ' is left alone, not reported as a challenge', 'raised', 'no raise')

# ── the silent-skip regression, asserted on the source ─────────────────
# This is the one that actually cost something, and it is asserted on the
# structure rather than the wording: the challenge branch must exist and must
# exit non-zero, so a future edit that folds it back into the quiet
# `except Exception: sys.exit(0)` fails here.
dvn = open(os.path.join(ROOT, 'tools', 'deploy_verify_notify.py'), encoding='utf-8').read()
check('the deploy watcher fetches through sairn_http, not raw urllib',
      'sairn_http.fetch(' in dvn and 'urllib.request.urlopen(' not in dvn, True)
check('a challenge is reported, not skipped',
      'except sairn_http.Challenged' in dvn, True)
check('and reporting it means a non-zero exit, the same as a real mismatch',
      dvn.count('sys.exit(2)') >= 2, True)
check('the notify says the deploy is UNVERIFIED rather than implying it passed',
      'THE DEPLOY IS UNVERIFIED' in dvn, True)

# ── every sairn.vercel.app fetcher in tools/ is wired ──────────────────
# Named explicitly rather than globbed: a new fetcher should fail this list and
# make someone decide, instead of quietly inheriting or quietly missing it.
WIRED = ['deploy_verify_notify.py', 'sairn_load_state_check.py',
         'licence_recoverability_check.py', 'load_deadline_seed.py',
         'sairn_app_map_check.py']
for f in WIRED:
    src = open(os.path.join(ROOT, 'tools', f), encoding='utf-8').read()
    check(f + ' imports the shared fetcher', 'import sairn_http' in src, True)
for f in ['sairn_load_state_check.py', 'licence_recoverability_check.py',
          'load_deadline_seed.py']:
    src = open(os.path.join(ROOT, 'tools', f), encoding='utf-8').read()
    check(f + ' sends the browser UA on its POST',
          'sairn_http.with_browser_ua(' in src, True)
    check(f + ' turns a challenge into a raise rather than parsing it as a reply',
          'sairn_http.raise_if_challenge(e)' in src, True)

# ── no bypass secret smuggled in ───────────────────────────────────────
# Deployment protection is a different mechanism and is OFF for this project.
# A bypass token in here would be an unrelated credential in a file that does
# not need one.
lib = open(os.path.join(ROOT, 'tools', 'sairn_http.py'), encoding='utf-8').read()
check('no protection-bypass secret is used or read',
      'x-vercel-protection-bypass' in lib.lower() and
      'VERCEL_AUTOMATION_BYPASS_SECRET' not in lib.replace(
          'covers password/SSO protection', ''), True)

print(('FAILED %d/%d' % (failed, passed + failed)) if failed
      else ('ALL %d CHALLENGE-HANDLING ASSERTIONS PASS' % passed))
sys.exit(1 if failed else 0)
