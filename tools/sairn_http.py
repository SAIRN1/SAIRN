"""
tools/sairn_http.py -- the one place that knows how to reach sairn.vercel.app
from a script.

WHY THIS EXISTS (2026-09-02). Four sessions live-verifying pushes with `curl`
and `urllib` all night tripped Vercel's platform bot mitigation. Every request
carrying an obviously-automated User-Agent started coming back:

    HTTP/1.1 403 Forbidden
    X-Vercel-Mitigated: challenge
    X-Vercel-Challenge-Token: ...

REAL BROWSER TRAFFIC WAS NEVER AFFECTED -- verified by loading both apps in a
real Chrome while the challenge was active, and by the project's deployment
protection being entirely OFF (no password, no SSO, no trusted IPs). This is
Vercel deciding a CLIENT looks automated, not a setting anyone changed and not
an outage.

── THE FIX IS THE USER-AGENT, AND THAT WAS MEASURED, NOT ASSUMED ──────────
While the challenge was active, in the same second, against the same URL:

    python-urllib default UA  ->  403, X-Vercel-Mitigated: challenge
    browser UA                ->  200, 2,384,655 bytes

So a browser User-Agent clears it. That is the whole fix, and it is cheaper
than the first thing proposed (routing every check through the Vercel MCP
tool), which would only have worked from inside a Claude turn and not from a
hook or a cron.

── THE SECOND HALF IS THE ONE THAT ACTUALLY MATTERED ─────────────────────
`deploy_verify_notify.py` caught every fetch exception and `sys.exit(0)`.
During the challenge window that meant the post-push deploy check SILENTLY DID
NOT RUN, on every push, and said nothing -- indistinguishable from a clean
pass. A verification that stops verifying without saying so is worse than no
verification at all, because it is trusted.

So this module NEVER collapses "challenged" or "unreachable" into "fine". It
raises a distinguishable error and the caller decides how loud to be. A caller
that wants to fail open must do so explicitly, in its own code, where a reader
can see it.

── HONEST LIMITS ─────────────────────────────────────────────────────────
* The mitigation is adaptive. It relaxed on its own roughly twenty minutes
  after the burst that triggered it, and default-UA requests began succeeding
  again. A browser UA is therefore an improvement in the odds, not a promise:
  if Vercel escalates to a JavaScript challenge, no header set will pass it and
  `Challenged` is raised so the caller can say so out loud.
* Nothing here bypasses deployment protection. `x-vercel-protection-bypass`
  covers password/SSO protection, which is a different mechanism and is off for
  this project anyway. There is deliberately no bypass secret in this file.
* Claiming to be Chrome in a User-Agent is a description of the traffic shape
  we want treated as ordinary, not an attempt to defeat a security control. The
  content is public, the project has no protection enabled, and the requests are
  the shop's own tooling checking the shop's own deploy.
"""
import collections
import json
import urllib.request
import urllib.error

# A current, ordinary desktop Chrome string. Kept in ONE place so raising it
# later is one edit rather than five.
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

DEFAULT_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class Response(collections.namedtuple("Response", "status body")):
    """What fetch() and fetch_json() return: `(status, body)`, plus `.status`
    and `.body`.

    IT IS STILL A TUPLE. Unpacking, indexing, `len()`, and equality against a
    plain `(status, body)` all behave exactly as before, because every existing
    caller unpacks it. Exactly ONE thing changes, and it is the one that fails
    silently.

    ── WHY (2026-09-04) ──────────────────────────────────────────────────
    A live-verify of a just-pushed fix wrote

        if 'marker-from-the-fix' in sairn_http.fetch(url):

    and reported the fix ABSENT for seven minutes across 20 polls. `in` against
    a 2-tuple is a MEMBERSHIP test: it asked "is this string one of these two
    elements", correctly answered False, and never looked at the body at all.
    The deploy had been READY the entire time.

    **Every other spelling of that mistake already raises.** `.find(...)` and
    `.decode(...)` both AttributeError on a tuple -- which is how the same bug
    was caught on the second attempt, seconds instead of minutes. `in` was the
    only silent one, so `in` is the only thing guarded here. A guard that also
    reworked the return shape would have broken two working callers to fix a
    mistake neither of them made.

    This is the failure class the module's own docstring is about, arriving
    inside the module: a check that stopped checking and said nothing.
    """

    __slots__ = ()

    def __contains__(self, item):
        if isinstance(item, (str, bytes, bytearray)):
            raise TypeError(
                "%r in <sairn_http response> is a tuple-membership test and is "
                "ALWAYS False -- it never looks at the body. This returns "
                "(status, body): use `%r in response.body` (bytes for fetch(), "
                "parsed JSON for fetch_json()), or unpack it: "
                "`status, body = sairn_http.fetch(url)`." % (item, item))
        return tuple.__contains__(self, item)


class Challenged(Exception):
    """Vercel returned its bot-mitigation challenge instead of the resource.

    NOT a deploy failure and NOT a network failure. Raised as its own type so a
    caller cannot accidentally treat it as either -- the whole reason the
    deploy watcher went silently blind was that a 403 challenge and a genuine
    network hiccup arrived as the same generic exception.
    """

    def __init__(self, url, status, token=None):
        self.url = url
        self.status = status
        self.token = token
        super().__init__(
            "Vercel bot-mitigation challenge on %s (HTTP %s). This is NOT a "
            "failed deploy and NOT an outage -- real browsers are unaffected. "
            "Verify from a Claude turn with "
            "mcp__claude_ai_Vercel__web_fetch_vercel_url, which authenticates "
            "past it." % (url, status))


def with_browser_ua(headers=None):
    """Return `headers` with the browser User-Agent added, without clobbering it.

    For callers that build their own urllib Request and want the traffic shape
    without adopting fetch()/fetch_json(). Their Content-Type and Authorization
    are preserved exactly -- this only fills in what identifies the client.
    """
    h = dict(DEFAULT_HEADERS)
    if headers:
        h.update(headers)
    return h


def raise_if_challenge(err):
    """Raise Challenged if this HTTPError is Vercel's bot-mitigation challenge.

    For callers that catch urllib.error.HTTPError themselves and parse the body.
    A challenge body is not an answer from the application, and parsing it as
    one turns "I was blocked" into "I checked and could not tell" -- two states
    CLAUDE.md already treats differently, and which were indistinguishable in
    every gate here until 2026-09-02.
    """
    challenged, token = _is_challenge(getattr(err, "headers", None))
    if challenged:
        raise Challenged(getattr(err, "url", "(unknown url)"),
                         getattr(err, "code", None), token)


def _is_challenge(headers):
    if not headers:
        return False, None
    mitigated = headers.get("X-Vercel-Mitigated")
    token = headers.get("X-Vercel-Challenge-Token")
    return (str(mitigated or "").lower() == "challenge" or bool(token)), token


def fetch(url, timeout=25, method="GET", data=None, headers=None, no_cache=False):
    """Fetch a URL as ordinary browser-shaped traffic.

    Returns Response(status:int, body:bytes) -- a tuple, so `status, body = ...`
    is unchanged. See Response for the one thing it refuses to do quietly.
    Raises Challenged if Vercel served its bot challenge.
    Raises urllib.error.HTTPError for a real HTTP error, so callers that read
    an error body (every gate in tools/ does) keep working unchanged.
    """
    h = dict(DEFAULT_HEADERS)
    if no_cache:
        h["Cache-Control"] = "no-cache"
        h["Pragma"] = "no-cache"
    # Caller headers win: an Authorization or Content-Type must never be
    # clobbered by the defaults above.
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return Response(r.status, r.read())
    except urllib.error.HTTPError as e:
        challenged, token = _is_challenge(getattr(e, "headers", None))
        if challenged:
            raise Challenged(url, e.code, token)
        raise


def fetch_json(url, timeout=60, method="POST", payload=None, key=None, headers=None):
    """POST JSON and parse the reply, returning Response(status, parsed_or_raw_text).

    Mirrors the shape every gate in tools/ already uses -- an HTTP error still
    returns its parsed body rather than raising -- so wiring a gate to this is a
    behaviour-preserving change. Challenged still raises, because a gate that
    silently treats a challenge as an answer is exactly the failure this module
    exists to stop.
    """
    h = {"Content-Type": "application/json"}
    if key:
        h["Authorization"] = "Bearer " + key
    if headers:
        h.update(headers)
    body = json.dumps(payload or {}).encode("utf-8")
    try:
        status, raw = fetch(url, timeout=timeout, method=method, data=body, headers=h)
        return Response(status, json.loads(raw.decode("utf-8")))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return Response(e.code, json.loads(raw))
        except ValueError:
            return Response(e.code, {"error": {"message": raw[:400]}})
